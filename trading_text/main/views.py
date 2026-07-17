from django.contrib import messages
from django.conf import settings
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.static import serve

from .forms import (
    BookEditForm,
    BookForm,
    EcsLoginForm,
    EcsUserCreationForm,
    MessageForm,
    ProfileForm,
    TradeOfferForm,
)
from .models import Book, Favorite, Message, TradeOffer, UserProfile
from .services import apply_cancellation, submit_evaluation
from .supabase_auth import SupabaseAuthError, is_configured as supabase_is_configured
from .supabase_auth import sign_in_with_password, sign_up


def sync_supabase_user(email, supabase_user_id=None):
    user, _created = User.objects.get_or_create(
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
    if request.user.is_authenticated:
        return redirect("search")
    return redirect("login")


def search(request):
    return render(request, "main/search.html", get_search_context(request))


def signup(request):
    if request.user.is_authenticated:
        return redirect("search")

    if request.method == "POST":
        form = EcsUserCreationForm(request.POST)
        if form.is_valid():
            if not supabase_is_configured():
                form.add_error(None, "認証サービスの設定が未完了です。管理者にお問い合わせください。")
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
                form.add_error(None, "認証サービスの設定が未完了です。管理者にお問い合わせください。")
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
            try:
                book.save()
            except OSError as error:
                form.add_error("image", str(error))
            else:
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
    if request.method == "POST":
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
        key = (message.book_id, other_user.id)
        if key not in threads:
            chat_url = reverse("chat", kwargs={"book_id": message.book_id})
            if request.user == message.book.seller:
                chat_url = f"{chat_url}?partner={other_user.id}"
            threads[key] = {
                "book": message.book,
                "other_user": other_user,
                "message": message,
                "chat_url": chat_url,
            }
    return render(request, "main/inbox.html", {"threads": threads.values()})


@login_required
def chat(request, book_id):
    book = get_object_or_404(Book.objects.select_related("seller", "buyer"), id=book_id)
    is_seller = request.user == book.seller
    if is_seller:
        partner_id = request.POST.get("partner") or request.GET.get("partner") or book.buyer_id
        if partner_id is None:
            messages.error(request, "取引相手がまだ設定されていません。")
            return redirect("inbox")
        partner = get_object_or_404(User, id=partner_id)
        has_thread = Message.objects.filter(book=book).filter(
            Q(sender=book.seller, receiver=partner) | Q(sender=partner, receiver=book.seller)
        ).exists()
        if partner == book.seller or (not has_thread and partner != book.buyer):
            messages.error(request, "この取引メッセージは閲覧できません。")
            return redirect("inbox")
    else:
        partner = book.seller
        has_thread = Message.objects.filter(book=book).filter(
            Q(sender=request.user, receiver=partner) | Q(sender=partner, receiver=request.user)
        ).exists()
        if book.status == "sold" and request.user != book.buyer and not has_thread:
            messages.error(request, "売却済みの出品には購入相談できません。")
            return redirect("book_detail", book_id=book.id)

    thread_messages = Message.objects.filter(book=book).filter(
        Q(sender=request.user, receiver=partner) | Q(sender=partner, receiver=request.user)
    ).select_related("sender", "receiver")

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            Message.objects.create(
                book=book,
                sender=request.user,
                receiver=partner,
                content=form.cleaned_data["content"],
            )
            chat_url = reverse("chat", kwargs={"book_id": book.id})
            if is_seller:
                chat_url = f"{chat_url}?partner={partner.id}"
            return redirect(chat_url)
    else:
        form = MessageForm()

    thread_buyer = partner if is_seller else request.user
    latest_offer = (
        TradeOffer.objects.filter(book=book, buyer=thread_buyer)
        .select_related("buyer", "seller")
        .first()
    )

    return render(
        request,
        "main/chat.html",
        {
            "book": book,
            "partner": partner,
            "chat_messages": thread_messages,
            "form": form,
            "offer_form": TradeOfferForm(initial={"price": book.price}),
            "latest_offer": latest_offer,
            "is_seller": is_seller,
            "can_create_offer": is_seller and book.status == "available" and has_thread,
            "can_accept_offer": (
                not is_seller
                and book.status == "available"
                and latest_offer is not None
                and latest_offer.status == "pending"
            ),
            "can_manage_trade": book.status == "in_progress" and partner == book.buyer,
        },
    )


@login_required
def create_trade_offer(request, book_id):
    book = get_object_or_404(Book.objects.select_related("seller"), id=book_id)
    if request.user != book.seller or request.method != "POST":
        messages.error(request, "取引条件を提示できるのは出品者だけです。")
        return redirect("book_detail", book_id=book.id)

    buyer = get_object_or_404(User, id=request.POST.get("buyer"))
    chat_url = f"{reverse('chat', kwargs={'book_id': book.id})}?partner={buyer.id}"
    has_thread = Message.objects.filter(book=book).filter(
        Q(sender=book.seller, receiver=buyer) | Q(sender=buyer, receiver=book.seller)
    ).exists()
    if buyer == book.seller or not has_thread:
        messages.error(request, "この購入希望者には取引条件を提示できません。")
        return redirect(chat_url)

    form = TradeOfferForm(request.POST)
    if not form.is_valid():
        messages.error(request, "取引価格を正しく入力してください。")
        return redirect(chat_url)

    with transaction.atomic():
        locked_book = Book.objects.select_for_update().get(id=book.id)
        if locked_book.status != "available":
            messages.error(request, "この出品はすでに取引が成立しています。")
            return redirect(chat_url)
        TradeOffer.objects.filter(book=locked_book, status="pending").update(status="withdrawn")
        TradeOffer.objects.create(
            book=locked_book,
            seller=request.user,
            buyer=buyer,
            price=form.cleaned_data["price"],
        )

    messages.success(request, "取引条件を提示しました。購入者の同意待ちです。")
    return redirect(chat_url)


@login_required
def accept_trade_offer(request, offer_id):
    offer = get_object_or_404(TradeOffer.objects.select_related("book", "seller", "buyer"), id=offer_id)
    book = offer.book
    chat_url = reverse("chat", kwargs={"book_id": book.id})
    if request.user != offer.buyer or request.method != "POST":
        messages.error(request, "この取引条件には同意できません。")
        return redirect(chat_url)

    with transaction.atomic():
        locked_book = Book.objects.select_for_update().get(id=book.id)
        locked_offer = TradeOffer.objects.select_for_update().get(id=offer.id)
        if locked_offer.status != "pending":
            messages.info(request, "この取引条件はすでに処理されています。")
            return redirect(chat_url)
        if locked_book.status != "available":
            locked_offer.status = "withdrawn"
            locked_offer.save(update_fields=["status", "updated_at"])
            messages.error(request, "この参考書はすでに別の取引が成立しています。")
            return redirect(chat_url)

        TradeOffer.objects.filter(book=locked_book, status="pending").exclude(id=locked_offer.id).update(
            status="withdrawn"
        )
        locked_offer.status = "accepted"
        locked_offer.save(update_fields=["status", "updated_at"])
        locked_book.buyer = request.user
        locked_book.price = locked_offer.price
        locked_book.status = "in_progress"
        locked_book.save(update_fields=["buyer", "price", "status"])

    messages.success(request, "この参考書の取引が成立しました。")
    return redirect(chat_url)


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
def cancel_trade(request, book_id):
    book = get_object_or_404(Book.objects.select_related("seller", "buyer"), id=book_id)
    if request.user not in [book.seller, book.buyer] or book.buyer is None:
        messages.error(request, "この取引はキャンセルできません。")
        return redirect("inbox")
    if request.method != "POST":
        return redirect("chat", book_id=book.id)

    kind = request.POST.get("kind")
    target = request.user if kind == "cancel" else (book.buyer if request.user == book.seller else book.seller)
    try:
        _log, created = apply_cancellation(book, request.user, target, kind)
    except ValueError as error:
        messages.error(request, str(error))
    else:
        if created:
            messages.success(request, "取引を解除し、出品を再開しました。")
        else:
            messages.info(request, "この内容はすでに報告済みです。")
    return redirect("book_detail", book_id=book.id)


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
            try:
                form.save()
            except OSError as error:
                form.add_error("image", str(error))
            else:
                messages.success(request, "出品情報を更新しました。")
                return redirect("book_detail", book_id=book.id)
    else:
        form = BookEditForm(instance=book)
    return render(request, "main/edit_book.html", {"form": form, "book": book})


def terms(request):
    return render(request, "main/terms.html")


def help_contact(request):
    return render(request, "main/help_contact.html")


def media_file(request, path):
    return serve(request, path, document_root=settings.MEDIA_ROOT)
