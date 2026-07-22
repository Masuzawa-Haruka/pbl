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
from django.utils import timezone
from django.views.static import serve

from .forms import (
    BookEditForm,
    BookForm,
    EcsLoginForm,
    EcsUserCreationForm,
    HandoffProposalForm,
    MessageForm,
    ProfileForm,
    TradeOfferForm,
)
from .models import Book, Evaluation, Favorite, HandoffProposal, Message, TradeOffer, UserProfile
from .services import apply_cancellation, submit_evaluation
from .supabase_auth import SupabaseAuthError, is_configured as supabase_is_configured
from .supabase_auth import sign_in_with_password, sign_up


def sync_supabase_user(email, supabase_user_id=None, display_name=None):
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
    profile_updates = []
    if supabase_user_id and profile.supabase_user_id != supabase_user_id:
        profile.supabase_user_id = supabase_user_id
        profile_updates.append("supabase_user_id")
    if display_name and profile.display_name != display_name:
        profile.display_name = display_name
        profile_updates.append("display_name")
    if profile_updates:
        profile.save(update_fields=profile_updates)
    return user


def get_search_context(request):
    books = Book.objects.select_related("seller").filter(status="available")

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


def user_profile(request, user_id):
    profile_user = get_object_or_404(User.objects.select_related("profile"), id=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=profile_user)
    listing_count = Book.objects.filter(seller=profile_user).count()
    completed_trade_count = Book.objects.filter(
        Q(seller=profile_user) | Q(buyer=profile_user),
        status="sold",
    ).distinct().count()
    active_listings = Book.objects.filter(
        seller=profile_user,
        status__in=["available", "in_progress"],
    )[:6]
    return render(
        request,
        "main/user_profile.html",
        {
            "profile_user": profile_user,
            "profile": profile,
            "listing_count": listing_count,
            "completed_trade_count": completed_trade_count,
            "active_listings": active_listings,
        },
    )


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
                display_name = form.cleaned_data["display_name"]
                try:
                    sign_up(
                        email,
                        password,
                        request.build_absolute_uri(reverse("login")),
                        display_name,
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
                    user_metadata = supabase_user.get("user_metadata") or {}
                    user = sync_supabase_user(
                        email,
                        supabase_user.get("id"),
                        user_metadata.get("display_name"),
                    )
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
    consultation_threads = []
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, book=book).exists()
        if request.user == book.seller:
            thread_by_buyer = {}
            book_messages = book.messages.select_related("sender", "receiver").order_by("-created_at")
            for message in book_messages:
                buyer = message.receiver if message.sender == book.seller else message.sender
                if buyer == book.seller or buyer.id in thread_by_buyer:
                    continue
                thread_by_buyer[buyer.id] = {
                    "buyer": buyer,
                    "latest_message": message,
                    "chat_url": f"{reverse('chat', kwargs={'book_id': book.id})}?partner={buyer.id}",
                }
            consultation_threads = list(thread_by_buyer.values())
    return render(
        request,
        "main/book_detail.html",
        {
            "book": book,
            "is_favorited": is_favorited,
            "consultation_threads": consultation_threads,
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
                "message": None,
                "chat_url": chat_url,
            }
        if message.receiver == request.user and threads[key]["message"] is None:
            threads[key]["message"] = message
    for thread in threads.values():
        thread_buyer = thread["other_user"] if request.user == thread["book"].seller else request.user
        accepted_offer = (
            TradeOffer.objects.filter(
                book=thread["book"],
                buyer=thread_buyer,
                status="accepted",
            )
            .select_related("buyer", "seller")
            .first()
        )
        thread["accepted_offer"] = accepted_offer
        if accepted_offer:
            thread["handoff"] = accepted_offer.handoff_proposals.filter(
                status__in=["accepted", "pending"]
            ).first()
            handoff = thread["handoff"]
            if handoff:
                thread["handoff_due"] = handoff.handoff_at <= timezone.now()
                thread["user_confirmed"] = (
                    handoff.seller_confirmed_at is not None
                    if request.user == accepted_offer.seller
                    else handoff.buyer_confirmed_at is not None
                )
                if handoff.completed_at:
                    thread["chat_url"] = reverse("evaluate_trade", kwargs={"book_id": thread["book"].id})
    visible_threads = [thread for thread in threads.values() if thread["message"] or thread["accepted_offer"]]
    return render(request, "main/inbox.html", {"threads": visible_threads})


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
        TradeOffer.objects.filter(book=book, buyer=thread_buyer, status__in=["accepted", "pending", "rejected"])
        .select_related("buyer", "seller")
        .first()
    )
    handoff = None
    if latest_offer and latest_offer.status == "accepted":
        handoff = latest_offer.handoff_proposals.filter(status__in=["accepted", "pending", "rejected"]).first()
    user_handoff_confirmed = False
    if handoff and handoff.status == "accepted":
        user_handoff_confirmed = (
            handoff.seller_confirmed_at is not None if is_seller else handoff.buyer_confirmed_at is not None
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
            "handoff_form": HandoffProposalForm(),
            "latest_offer": latest_offer,
            "handoff": handoff,
            "handoff_due": handoff is not None and handoff.handoff_at <= timezone.now(),
            "user_handoff_confirmed": user_handoff_confirmed,
            "is_seller": is_seller,
            "can_create_offer": is_seller and book.status == "available" and has_thread,
            "can_accept_offer": (
                not is_seller
                and book.status == "available"
                and latest_offer is not None
                and latest_offer.status == "pending"
            ),
            "can_manage_trade": book.status == "in_progress" and thread_buyer == book.buyer,
            "can_create_handoff": (
                is_seller
                and book.status == "in_progress"
                and latest_offer is not None
                and latest_offer.status == "accepted"
                and (handoff is None or handoff.status == "rejected")
            ),
            "can_accept_handoff": (
                not is_seller
                and book.status == "in_progress"
                and latest_offer is not None
                and latest_offer.status == "accepted"
                and handoff is not None
                and handoff.status == "pending"
            ),
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
def reject_trade_offer(request, offer_id):
    offer = get_object_or_404(TradeOffer.objects.select_related("book", "buyer"), id=offer_id)
    book = offer.book
    chat_url = reverse("chat", kwargs={"book_id": book.id})
    if request.method != "POST" or request.user != offer.buyer:
        messages.error(request, "この取引条件は拒否できません。")
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
        locked_offer.status = "rejected"
        locked_offer.save(update_fields=["status", "updated_at"])

    messages.success(request, "提示された価格には同意しませんでした。")
    return redirect(chat_url)


@login_required
def create_handoff_proposal(request, offer_id):
    offer = get_object_or_404(TradeOffer.objects.select_related("book", "seller", "buyer"), id=offer_id)
    book = offer.book
    chat_url = f"{reverse('chat', kwargs={'book_id': book.id})}?partner={offer.buyer_id}"
    if request.method != "POST" or request.user != offer.seller:
        messages.error(request, "受け渡し日時と場所を提示できるのは出品者だけです。")
        return redirect(chat_url)

    form = HandoffProposalForm(request.POST)
    if not form.is_valid():
        error = next(iter(form.errors.values()))[0]
        messages.error(request, str(error))
        return redirect(chat_url)

    with transaction.atomic():
        locked_book = Book.objects.select_for_update().get(id=book.id)
        locked_offer = TradeOffer.objects.select_for_update().get(id=offer.id)
        if (
            locked_offer.status != "accepted"
            or locked_book.status != "in_progress"
            or locked_book.buyer_id != locked_offer.buyer_id
        ):
            messages.error(request, "成立済みの取引にだけ受け渡し条件を提示できます。")
            return redirect(chat_url)
        if HandoffProposal.objects.filter(trade_offer=locked_offer, status="accepted").exists():
            messages.info(request, "受け渡し日時と場所はすでに確定しています。")
            return redirect(chat_url)

        HandoffProposal.objects.filter(trade_offer=locked_offer, status="pending").update(status="withdrawn")
        HandoffProposal.objects.create(
            trade_offer=locked_offer,
            handoff_at=form.cleaned_data["handoff_at"],
            location=form.cleaned_data["location"],
        )

    messages.success(request, "受け渡し日時と場所を提示しました。購入者の同意待ちです。")
    return redirect(chat_url)


@login_required
def accept_handoff_proposal(request, proposal_id):
    proposal = get_object_or_404(
        HandoffProposal.objects.select_related("trade_offer__book", "trade_offer__buyer"),
        id=proposal_id,
    )
    offer = proposal.trade_offer
    book = offer.book
    chat_url = reverse("chat", kwargs={"book_id": book.id})
    if request.method != "POST" or request.user != offer.buyer:
        messages.error(request, "この受け渡し条件には同意できません。")
        return redirect(chat_url)

    with transaction.atomic():
        locked_book = Book.objects.select_for_update().get(id=book.id)
        locked_offer = TradeOffer.objects.select_for_update().get(id=offer.id)
        locked_proposal = HandoffProposal.objects.select_for_update().get(id=proposal.id)
        if locked_proposal.status != "pending":
            messages.info(request, "この受け渡し条件はすでに処理されています。")
            return redirect(chat_url)
        if (
            locked_offer.status != "accepted"
            or locked_book.status != "in_progress"
            or locked_book.buyer_id != request.user.id
            or locked_offer.buyer_id != request.user.id
        ):
            locked_proposal.status = "withdrawn"
            locked_proposal.save(update_fields=["status", "updated_at"])
            messages.error(request, "この取引の受け渡し条件には同意できません。")
            return redirect(chat_url)

        HandoffProposal.objects.filter(trade_offer=locked_offer, status="pending").exclude(
            id=locked_proposal.id
        ).update(status="withdrawn")
        locked_proposal.status = "accepted"
        locked_proposal.save(update_fields=["status", "updated_at"])

    messages.success(request, "受け渡し日時と場所が確定しました。あとは参考書を渡すだけです。")
    return redirect(chat_url)


@login_required
def reject_handoff_proposal(request, proposal_id):
    proposal = get_object_or_404(
        HandoffProposal.objects.select_related("trade_offer__book", "trade_offer__buyer"),
        id=proposal_id,
    )
    offer = proposal.trade_offer
    book = offer.book
    chat_url = reverse("chat", kwargs={"book_id": book.id})
    if request.method != "POST" or request.user != offer.buyer:
        messages.error(request, "この受け渡し条件は拒否できません。")
        return redirect(chat_url)

    with transaction.atomic():
        locked_book = Book.objects.select_for_update().get(id=book.id)
        locked_offer = TradeOffer.objects.select_for_update().get(id=offer.id)
        locked_proposal = HandoffProposal.objects.select_for_update().get(id=proposal.id)
        if locked_proposal.status != "pending":
            messages.info(request, "この受け渡し条件はすでに処理されています。")
            return redirect(chat_url)
        if (
            locked_offer.status != "accepted"
            or locked_book.status != "in_progress"
            or locked_book.buyer_id != request.user.id
            or locked_offer.buyer_id != request.user.id
        ):
            locked_proposal.status = "withdrawn"
            locked_proposal.save(update_fields=["status", "updated_at"])
            messages.error(request, "この取引の受け渡し条件は拒否できません。")
            return redirect(chat_url)
        locked_proposal.status = "rejected"
        locked_proposal.save(update_fields=["status", "updated_at"])

    messages.success(request, "提示された日時と場所には同意しませんでした。")
    return redirect(chat_url)


@login_required
def confirm_handoff_complete(request, proposal_id):
    proposal = get_object_or_404(
        HandoffProposal.objects.select_related("trade_offer__book", "trade_offer__seller", "trade_offer__buyer"),
        id=proposal_id,
    )
    offer = proposal.trade_offer
    book = offer.book
    chat_url = reverse("chat", kwargs={"book_id": book.id})
    if request.user == offer.seller:
        chat_url = f"{chat_url}?partner={offer.buyer_id}"
    if request.method != "POST" or request.user not in [offer.seller, offer.buyer]:
        messages.error(request, "この受け渡し完了は確認できません。")
        return redirect(chat_url)

    now = timezone.now()
    with transaction.atomic():
        locked_book = Book.objects.select_for_update().get(id=book.id)
        locked_offer = TradeOffer.objects.select_for_update().get(id=offer.id)
        locked_proposal = HandoffProposal.objects.select_for_update().get(id=proposal.id)
        if (
            locked_proposal.status != "accepted"
            or locked_offer.status != "accepted"
            or locked_book.status != "in_progress"
            or locked_book.buyer_id != locked_offer.buyer_id
        ):
            messages.error(request, "この受け渡しは完了確認できる状態ではありません。")
            return redirect(chat_url)
        if now < locked_proposal.handoff_at:
            messages.error(request, "受け渡し予定日時になるまで完了確認はできません。")
            return redirect(chat_url)

        update_fields = []
        if request.user.id == locked_offer.seller_id and locked_proposal.seller_confirmed_at is None:
            locked_proposal.seller_confirmed_at = now
            update_fields.append("seller_confirmed_at")
        if request.user.id == locked_offer.buyer_id and locked_proposal.buyer_confirmed_at is None:
            locked_proposal.buyer_confirmed_at = now
            update_fields.append("buyer_confirmed_at")
        if (
            locked_proposal.seller_confirmed_at
            and locked_proposal.buyer_confirmed_at
            and locked_proposal.completed_at is None
        ):
            locked_proposal.completed_at = now
            update_fields.append("completed_at")
        if update_fields:
            update_fields.append("updated_at")
            locked_proposal.save(update_fields=update_fields)

    if locked_proposal.completed_at:
        messages.success(request, "双方の受け渡し完了を確認しました。相手を評価してください。")
        return redirect("evaluate_trade", book_id=book.id)
    messages.success(request, "受け渡し完了を記録しました。相手の完了確認を待っています。")
    return redirect(chat_url)


@login_required
def evaluate_trade(request, book_id):
    book = get_object_or_404(Book.objects.select_related("seller", "buyer"), id=book_id)
    if request.user not in [book.seller, book.buyer] or book.buyer is None:
        messages.error(request, "この取引は評価できません。")
        return redirect("inbox")

    handoff = HandoffProposal.objects.filter(
        trade_offer__book=book,
        trade_offer__status="accepted",
        status="accepted",
        completed_at__isnull=False,
    ).select_related("trade_offer").first()
    if handoff is None:
        messages.error(request, "双方が受け渡し完了を確認した後に評価できます。")
        return redirect("chat", book_id=book.id)

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
        return redirect("evaluate_trade", book_id=book.id)
    existing_evaluation = Evaluation.objects.filter(book=book, evaluator=request.user, target=target).first()
    return render(
        request,
        "main/evaluate_trade.html",
        {
            "book": book,
            "target": target,
            "handoff": handoff,
            "existing_evaluation": existing_evaluation,
        },
    )


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
    active_view = request.GET.get("view", "listings")
    if active_view not in {"listings", "favorites", "trades"}:
        active_view = "listings"

    selling_books = Book.objects.filter(seller=request.user, status="available")
    favorite_books = Book.objects.filter(favorites__user=request.user).order_by(
        "-favorites__created_at"
    )
    trading_books = Book.objects.filter(
        Q(seller=request.user) | Q(buyer=request.user),
        status__in=["in_progress", "sold"],
    ).select_related("seller", "buyer").distinct()
    completed_trade_count = Book.objects.filter(
        Q(seller=request.user) | Q(buyer=request.user),
        status="sold",
    ).distinct().count()
    trade_items = []
    for book in trading_books:
        chat_url = reverse("book_detail", kwargs={"book_id": book.id})
        if book.buyer_id:
            chat_url = reverse("chat", kwargs={"book_id": book.id})
            if request.user == book.seller:
                chat_url = f"{chat_url}?partner={book.buyer_id}"
        trade_items.append({"book": book, "url": chat_url})
    accepted_handoffs = HandoffProposal.objects.filter(
        Q(trade_offer__seller=request.user) | Q(trade_offer__buyer=request.user),
        status="accepted",
        trade_offer__status="accepted",
        trade_offer__book__status="in_progress",
    ).select_related("trade_offer__book", "trade_offer__seller", "trade_offer__buyer")
    handoff_trades = []
    for handoff in accepted_handoffs:
        offer = handoff.trade_offer
        partner = offer.buyer if request.user == offer.seller else offer.seller
        chat_url = reverse("chat", kwargs={"book_id": offer.book_id})
        if request.user == offer.seller:
            chat_url = f"{chat_url}?partner={offer.buyer_id}"
        if handoff.completed_at:
            chat_url = reverse("evaluate_trade", kwargs={"book_id": offer.book_id})
        handoff_trades.append(
            {
                "book": offer.book,
                "partner": partner,
                "handoff": handoff,
                "chat_url": chat_url,
            }
        )

    return render(
        request,
        "main/mypage.html",
        {
            "profile": profile,
            "selling_books": selling_books,
            "favorite_books": favorite_books,
            "trading_books": trading_books,
            "trade_items": trade_items,
            "completed_trade_count": completed_trade_count,
            "active_view": active_view,
            "handoff_trades": handoff_trades,
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
