from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import F
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import BookEditForm, BookForm, EcsLoginForm, EcsUserCreationForm, MessageForm, ProfileForm
from .models import Book, Favorite, Message, UserProfile
from .services import submit_evaluation
from .supabase_auth import SupabaseAuthError, is_configured as supabase_is_configured
from .supabase_auth import sign_in_with_password, sign_up


def sync_supabase_user(email, supabase_user_id=None):
    user, created = User.objects.get_or_create(
        username=email,
        defaults={
            "email": email,
            "is_active": True,
        },
    )
    updates = []
    if user.email != email:
        user.email = email
        updates.append("email")
    if not user.is_active:
        user.is_active = True
        updates.append("is_active")
    if updates:
        user.save(update_fields=updates)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if supabase_user_id and profile.supabase_user_id != supabase_user_id:
        profile.supabase_user_id = supabase_user_id
        profile.save(update_fields=["supabase_user_id"])
    return user


def get_search_context(request):
    books = Book.objects.select_related("seller").all()

    keyword = request.GET.get("keyword", "").strip()
    category = request.GET.get("category", "").strip()
    campus = request.GET.get("campus", "").strip()
    sort = request.GET.get("sort", "newest").strip()

    if keyword:
        books = books.filter(Q(title__icontains=keyword) | Q(author__icontains=keyword))

    if category:
        books = books.filter(category=category)

    if campus:
        books = books.filter(campus=campus)

    if sort == "price_low":
        books = books.order_by("price", "-created_at")
    elif sort == "price_high":
        books = books.order_by("-price", "-created_at")
    else:
        books = books.order_by("-created_at")

    return {
        "books": books,
        "keyword": keyword,
        "selected_category": category,
        "selected_campus": campus,
        "selected_sort": sort,
        "categories": Book.CATEGORY_CHOICES,
        "campuses": Book.CAMPUS_CHOICES,
    }


def index(request):
    return render(request, "main/search.html", get_search_context(request))


def search(request):
    return render(request, "main/search.html", get_search_context(request))


def signup(request):
    if request.user.is_authenticated:
        return redirect("search")

    if request.method == "POST":
        form = EcsUserCreationForm(request.POST)
        if form.is_valid():
            if not supabase_is_configured():
                form.add_error(None, "Supabase Auth の設定が未完了です。SUPABASE_URL と SUPABASE_ANON_KEY を設定してください。")
            else:
                email = form.cleaned_data["email"]
                password = form.cleaned_data["password1"]
                try:
                    sign_up(
                        email,
                        password,
                        request.build_absolute_uri(reverse("login")),
                    )
                except SupabaseAuthError as error:
                    form.add_error(None, str(error))
                else:
                    return render(request, "main/signup_done.html", {"email": email})
    else:
        form = EcsUserCreationForm()
    return render(request, "main/signup.html", {"form": form})


def activate(request, uidb64, token):
    return redirect("login")


def login(request):
    if request.user.is_authenticated:
        return redirect("search")

    if request.method == "POST":
        form = EcsLoginForm(request.POST)
        if form.is_valid():
            if not supabase_is_configured():
                form.add_error(None, "Supabase Auth の設定が未完了です。SUPABASE_URL と SUPABASE_ANON_KEY を設定してください。")
            else:
                email = form.cleaned_data["email"]
                password = form.cleaned_data["password"]
                try:
                    auth_response = sign_in_with_password(email, password)
                except SupabaseAuthError as error:
                    form.add_error(None, str(error))
                else:
                    supabase_user = auth_response.get("user") or {}
                    user = sync_supabase_user(email, supabase_user.get("id"))
                    request.session["supabase_access_token"] = auth_response.get("access_token", "")
                    request.session["supabase_refresh_token"] = auth_response.get("refresh_token", "")
                    request.session["supabase_user_id"] = supabase_user.get("id", "")
                    auth_login(request, user)
                    return redirect(request.GET.get("next") or "search")
    else:
        form = EcsLoginForm()
    return render(request, "main/login.html", {"form": form})


def logout(request):
    auth_logout(request)
    return redirect("login")


@login_required
def listing_form(request):
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save(commit=False)
            book.seller = request.user
            book.status = "available"
            book.buyer = None
            book.save()
            messages.success(request, "出品しました。")
            return redirect("book_detail", book_id=book.id)
    else:
        form = BookForm(initial={"status": "available"})

    return render(
        request,
        "main/listing_form.html",
        {
            "form": form,
            "categories": Book.CATEGORY_CHOICES,
            "campuses": Book.CAMPUS_CHOICES,
            "conditions": Book.CONDITION_CHOICES,
            "statuses": Book.STATUS_CHOICES,
        },
    )


def book_detail(request, book_id):
    book = get_object_or_404(Book.objects.select_related("seller", "buyer"), id=book_id)
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, book=book).exists()
    return render(
        request,
        "main/book_detail.html",
        {
            "book": book,
            "is_favorited": is_favorited,
            "message_form": MessageForm(),
        },
    )


@login_required
def toggle_like(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    with transaction.atomic():
        try:
            favorite, created = Favorite.objects.get_or_create(user=request.user, book=book)
        except IntegrityError:
            created = False
            favorite = Favorite.objects.get(user=request.user, book=book)

        if created:
            Book.objects.filter(id=book.id).update(likes_count=F("likes_count") + 1)
            messages.success(request, "お気に入りに追加しました。")
        else:
            deleted_count, _ = favorite.delete()
            if deleted_count:
                Book.objects.filter(id=book.id, likes_count__gt=0).update(likes_count=F("likes_count") - 1)
            messages.success(request, "お気に入りを解除しました。")
    return redirect("book_detail", book_id=book.id)


@login_required
def start_consultation(request, book_id):
    book = get_object_or_404(Book.objects.select_related("seller", "buyer"), id=book_id)
    if book.seller == request.user:
        messages.error(request, "自分の出品には購入相談できません。")
        return redirect("book_detail", book_id=book.id)
    if book.status == "sold":
        messages.error(request, "売却済みの出品には購入相談できません。")
        return redirect("book_detail", book_id=book.id)
    if book.buyer_id is not None and book.buyer != request.user:
        messages.error(request, "この出品は既に別の購入希望者と取引中です。")
        return redirect("book_detail", book_id=book.id)

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            Message.objects.create(
                book=book,
                sender=request.user,
                receiver=book.seller,
                content=form.cleaned_data["content"],
            )
            if book.status == "available":
                book.status = "in_progress"
            if book.buyer_id is None:
                book.buyer = request.user
            book.save(update_fields=["status", "buyer"])
            messages.success(request, "購入相談を送信しました。")
            return redirect("chat", book_id=book.id)

    return redirect("book_detail", book_id=book.id)


@login_required
def inbox(request):
    messages_qs = (
        Message.objects.filter(Q(sender=request.user) | Q(receiver=request.user))
        .select_related("book", "sender", "receiver")
        .order_by("-created_at")
    )
    threads = {}
    for message in messages_qs:
        other_user = message.receiver if message.sender == request.user else message.sender
        threads.setdefault((message.book_id, other_user.id), message)
    return render(request, "main/inbox.html", {"threads": threads.values()})


@login_required
def chat(request, book_id):
    book = get_object_or_404(Book.objects.select_related("seller", "buyer"), id=book_id)
    if request.user not in [book.seller, book.buyer]:
        messages.error(request, "この取引メッセージは閲覧できません。")
        return redirect("inbox")

    partner = book.buyer if request.user == book.seller else book.seller
    if partner is None:
        messages.error(request, "取引相手がまだ設定されていません。")
        return redirect("inbox")

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            Message.objects.create(
                book=book,
                sender=request.user,
                receiver=partner,
                content=form.cleaned_data["content"],
            )
            return redirect("chat", book_id=book.id)
    else:
        form = MessageForm()

    return render(
        request,
        "main/chat.html",
        {
            "book": book,
            "partner": partner,
            "messages": book.messages.select_related("sender", "receiver"),
            "form": form,
        },
    )


@login_required
def evaluate_trade(request, book_id):
    book = get_object_or_404(Book.objects.select_related("seller", "buyer"), id=book_id)
    if request.user not in [book.seller, book.buyer] or book.buyer is None:
        messages.error(request, "この取引は評価できません。")
        return redirect("inbox")

    target = book.buyer if request.user == book.seller else book.seller
    if request.method == "POST":
        evaluation_type = request.POST.get("evaluation_type")
        try:
            _evaluation, created = submit_evaluation(book, request.user, target, evaluation_type)
            if created:
                messages.success(request, "評価を送信しました。双方の評価が揃うと信用スコアに反映されます。")
            else:
                messages.info(request, "この取引は既に評価済みです。")
        except ValueError as error:
            messages.error(request, str(error))
    return redirect("chat", book_id=book.id)


@login_required
def mypage(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    selling_books = Book.objects.filter(seller=request.user)
    favorite_books = Book.objects.filter(favorites__user=request.user)
    trading_books = Book.objects.filter(
        Q(seller=request.user) | Q(buyer=request.user),
        status__in=["in_progress", "sold"],
    ).distinct()

    return render(
        request,
        "main/mypage.html",
        {
            "profile": profile,
            "selling_books": selling_books,
            "favorite_books": favorite_books,
            "trading_books": trading_books,
        },
    )


@login_required
def edit_profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "プロフィールを更新しました。")
            return redirect("mypage")
    else:
        form = ProfileForm(instance=profile)
    return render(request, "main/edit_profile.html", {"form": form})


@login_required
def edit_book(request, book_id):
    book = get_object_or_404(Book, id=book_id, seller=request.user)
    if request.method == "POST":
        form = BookEditForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, "出品情報を更新しました。")
            return redirect("book_detail", book_id=book.id)
    else:
        form = BookEditForm(instance=book)
    return render(request, "main/edit_book.html", {"form": form, "book": book})


def terms(request):
    return render(request, "main/terms.html")


def help_contact(request):
    return render(request, "main/help_contact.html")
