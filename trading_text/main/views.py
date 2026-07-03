from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import BookForm, ChatMessageForm, LoginForm, ScheduleForm, SignupForm
from .models import Book, ChatMessage, Favorite, Profile, Transaction


def ensure_profile(user):
    if not user.is_authenticated:
        return None

    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={
            "display_name": user.first_name or user.email or user.username,
        },
    )
    return profile


def get_search_context(request):
    books = Book.objects.filter(status="available")

    keyword = request.GET.get("keyword", "").strip()
    category = request.GET.get("category", "").strip()
    campus = request.GET.get("campus", "").strip()
    sort = request.GET.get("sort", "newest").strip()

    if keyword:
        books = books.filter(
            Q(title__icontains=keyword)
            | Q(author__icontains=keyword)
        )

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

    favorite_book_ids = set()
    if request.user.is_authenticated:
        favorite_book_ids = set(
            Favorite.objects.filter(user=request.user, book__in=books).values_list("book_id", flat=True)
        )

    return {
        "books": books,
        "favorite_book_ids": favorite_book_ids,
        "keyword": keyword,
        "selected_category": category,
        "selected_campus": campus,
        "selected_sort": sort,
        "categories": Book.CATEGORY_CHOICES,
        "campuses": Book.CAMPUS_CHOICES,
    }


def index(request):
    return render(request, 'main/search.html', get_search_context(request))


def search(request):
    return render(request, 'main/search.html', get_search_context(request))


def signup(request):
    if request.user.is_authenticated:
        return redirect("search")

    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        auth_login(request, user)
        return redirect("search")

    return render(request, "main/signup.html", {"form": form})


def login(request):
    if request.user.is_authenticated:
        return redirect("search")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        auth_login(request, form.cleaned_data["user"])
        return redirect(request.GET.get("next") or "search")

    return render(request, "main/login.html", {"form": form})


def logout(request):
    auth_logout(request)
    return redirect("login")


def book_detail(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    is_favorite = False
    active_transaction = None

    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, book=book).exists()
        active_transaction = Transaction.objects.filter(
            Q(seller=request.user) | Q(buyer=request.user),
            book=book,
        ).exclude(status__in=["cancelled", "completed"]).first()

    return render(
        request,
        "main/book_detail.html",
        {
            "book": book,
            "is_favorite": is_favorite,
            "active_transaction": active_transaction,
        },
    )


@login_required
def listing_form(request):
    ensure_profile(request.user)
    form = BookForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        book = form.save(commit=False)
        book.owner = request.user
        book.save()
        messages.success(request, "出品しました。")
        return redirect("book_detail", book_id=book.id)

    return render(request, 'main/listing_form.html', {"form": form})


@login_required
def inbox(request):
    ensure_profile(request.user)
    transactions = Transaction.objects.filter(
        Q(seller=request.user) | Q(buyer=request.user)
    ).select_related("book", "seller", "buyer")
    for transaction in transactions:
        transaction.other_display = transaction.participant_display(request.user)
    return render(request, 'main/inbox.html', {"transactions": transactions})


@login_required
def mypage(request):
    profile = ensure_profile(request.user)
    user_books = Book.objects.filter(owner=request.user)
    completed_count = Transaction.objects.filter(
        Q(seller=request.user) | Q(buyer=request.user),
        status="completed",
    ).count()
    favorites = Favorite.objects.filter(user=request.user).select_related("book")[:5]

    return render(
        request,
        'main/mypage.html',
        {
            "profile": profile,
            "user_books": user_books,
            "listing_count": user_books.count(),
            "completed_count": completed_count,
            "favorites": favorites,
        },
    )


@login_required
@require_POST
def toggle_favorite(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, book=book)
    if created:
        Book.objects.filter(id=book.id).update(likes_count=book.likes_count + 1)
    else:
        favorite.delete()
        Book.objects.filter(id=book.id, likes_count__gt=0).update(likes_count=book.likes_count - 1)

    return redirect(request.POST.get("next") or "search")


@login_required
@require_POST
def start_transaction(request, book_id):
    book = get_object_or_404(Book, id=book_id, status="available")
    if book.owner == request.user:
        messages.error(request, "自分の出品とは取引を開始できません。")
        return redirect("book_detail", book_id=book.id)

    seller = book.owner
    if seller is None:
        messages.error(request, "この出品は出品者情報が不足しているため取引を開始できません。")
        return redirect("book_detail", book_id=book.id)

    transaction, created = Transaction.objects.get_or_create(
        book=book,
        seller=seller,
        buyer=request.user,
        defaults={"status": "open"},
    )
    if created:
        book.status = "matching"
        book.save(update_fields=["status"])
        ChatMessage.objects.create(
            transaction=transaction,
            sender=request.user,
            body="購入希望です。受け渡しの相談をお願いします。",
        )

    return redirect("transaction_detail", transaction_id=transaction.id)


@login_required
def transaction_detail(request, transaction_id):
    transaction = get_object_or_404(
        Transaction.objects.select_related("book", "seller", "buyer"),
        id=transaction_id,
    )
    if request.user not in [transaction.seller, transaction.buyer]:
        messages.error(request, "この取引を見る権限がありません。")
        return redirect("inbox")

    message_form = ChatMessageForm()
    schedule_form = ScheduleForm(instance=transaction)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "message":
            message_form = ChatMessageForm(request.POST)
            if message_form.is_valid():
                message = message_form.save(commit=False)
                message.transaction = transaction
                message.sender = request.user
                message.save()
                return redirect("transaction_detail", transaction_id=transaction.id)
        elif action == "schedule":
            schedule_form = ScheduleForm(request.POST, instance=transaction)
            if schedule_form.is_valid():
                scheduled_transaction = schedule_form.save(commit=False)
                scheduled_transaction.status = "scheduled"
                scheduled_transaction.save()
                return redirect("transaction_detail", transaction_id=transaction.id)
        elif action == "complete":
            if request.user == transaction.seller:
                transaction.seller_completed = True
            if request.user == transaction.buyer:
                transaction.buyer_completed = True
            if transaction.seller_completed and transaction.buyer_completed:
                transaction.status = "completed"
                transaction.book.status = "completed"
                transaction.book.save(update_fields=["status"])
            transaction.save()
            return redirect("transaction_detail", transaction_id=transaction.id)
        elif action == "cancel":
            transaction.status = "cancelled"
            transaction.book.status = "available"
            transaction.book.save(update_fields=["status"])
            transaction.save()
            return redirect("inbox")

    return render(
        request,
        "main/transaction_detail.html",
        {
            "transaction": transaction,
            "messages": transaction.messages.select_related("sender"),
            "message_form": message_form,
            "schedule_form": schedule_form,
        },
    )
