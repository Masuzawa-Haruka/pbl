from unittest.mock import MagicMock, patch
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import EcsUserCreationForm, ProfileForm
from .models import Book, Favorite, HandoffProposal, Message, TradeOffer, UserProfile
from .services import apply_cancellation, submit_evaluation
from .storage import SupabaseStorage
from .views import sync_supabase_user


class AuthFormTests(TestCase):
    def test_root_redirects_to_login_when_anonymous(self):
        response = self.client.get(reverse("index"))

        self.assertRedirects(response, reverse("login"))

    def test_root_redirects_to_search_when_authenticated(self):
        user = User.objects.create_user(
            username="root@ecs.osaka-u.ac.jp",
            email="root@ecs.osaka-u.ac.jp",
            password="password12345",
        )
        self.client.login(username=user.username, password="password12345")

        response = self.client.get(reverse("index"))

        self.assertRedirects(response, reverse("search"))

    def test_signup_requires_ecs_email(self):
        form = EcsUserCreationForm(
            data={
                "display_name": "大阪 太郎",
                "email": "student@osaka-u.ac.jp",
                "password1": "StrongPass12345",
                "password2": "StrongPass12345",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_signup_accepts_ecs_email(self):
        form = EcsUserCreationForm(
            data={
                "display_name": "大阪 太郎",
                "email": "student@ecs.osaka-u.ac.jp",
                "password1": "StrongPass12345",
                "password2": "StrongPass12345",
            }
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["email"], "student@ecs.osaka-u.ac.jp")

    @override_settings(SUPABASE_URL="https://example.supabase.co", SUPABASE_ANON_KEY="anon-key")
    @patch("main.views.sign_up")
    def test_signup_uses_supabase_auth(self, mock_sign_up):
        response = self.client.post(
            reverse("signup"),
            {
                "display_name": "大阪 太郎",
                "email": "student@ecs.osaka-u.ac.jp",
                "password1": "StrongPass12345",
                "password2": "StrongPass12345",
            },
        )

        self.assertEqual(response.status_code, 200)
        mock_sign_up.assert_called_once_with(
            "student@ecs.osaka-u.ac.jp",
            "StrongPass12345",
            "http://testserver/login/",
            "大阪 太郎",
        )

    def test_signup_requires_display_name(self):
        form = EcsUserCreationForm(
            data={
                "display_name": "   ",
                "email": "student@ecs.osaka-u.ac.jp",
                "password1": "StrongPass12345",
                "password2": "StrongPass12345",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("display_name", form.errors)

    @override_settings(SUPABASE_URL="https://example.supabase.co", SUPABASE_ANON_KEY="anon-key")
    @patch("main.views.sign_in_with_password")
    def test_login_uses_supabase_auth_and_syncs_local_user(self, mock_sign_in):
        mock_sign_in.return_value = {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "user": {
                "id": "supabase-user-id",
                "user_metadata": {"display_name": "大阪 花子"},
            },
        }

        response = self.client.post(
            reverse("login"),
            {
                "email": "student@ecs.osaka-u.ac.jp",
                "password": "StrongPass12345",
            },
        )

        self.assertRedirects(response, reverse("search"))
        user = User.objects.get(username="student@ecs.osaka-u.ac.jp")
        self.assertEqual(user.profile.supabase_user_id, "supabase-user-id")
        self.assertEqual(user.profile.display_name, "大阪 花子")

    def test_sync_supabase_user_persists_supabase_user_id(self):
        user = sync_supabase_user("sync@ecs.osaka-u.ac.jp", "supabase-id-123", "同期 太郎")

        self.assertEqual(user.profile.supabase_user_id, "supabase-id-123")
        self.assertEqual(user.profile.display_name, "同期 太郎")

    def test_profile_accepts_only_official_faculty_department_choices(self):
        valid_form = ProfileForm(
            data={
                "display_name": "大阪 太郎",
                "faculty": "基礎工学部 情報科学科",
                "school_year": "2年",
            }
        )
        invalid_form = ProfileForm(
            data={
                "display_name": "大阪 太郎",
                "faculty": "部部科科",
                "school_year": "2年",
            }
        )

        self.assertTrue(valid_form.is_valid())
        self.assertFalse(invalid_form.is_valid())
        self.assertIn("faculty", invalid_form.errors)


class TradeFlowTests(TestCase):
    def setUp(self):
        self.seller, _ = User.objects.get_or_create(
            username="seller@ecs.osaka-u.ac.jp",
            defaults={"email": "seller@ecs.osaka-u.ac.jp"},
        )
        self.seller.set_password("password12345")
        self.seller.save()
        self.buyer, _ = User.objects.get_or_create(
            username="buyer@ecs.osaka-u.ac.jp",
            defaults={"email": "buyer@ecs.osaka-u.ac.jp"},
        )
        self.buyer.set_password("password12345")
        self.buyer.save()
        self.other_buyer, _ = User.objects.get_or_create(
            username="other@ecs.osaka-u.ac.jp",
            defaults={"email": "other@ecs.osaka-u.ac.jp"},
        )
        self.other_buyer.set_password("password12345")
        self.other_buyer.save()
        UserProfile.objects.get_or_create(user=self.seller, defaults={"display_name": "大阪 太郎"})
        UserProfile.objects.get_or_create(user=self.buyer, defaults={"display_name": "大阪 花子"})
        UserProfile.objects.get_or_create(user=self.other_buyer, defaults={"display_name": "大阪 次郎"})
        self.book = Book.objects.create(
            seller=self.seller,
            title="基礎からの線形代数",
            author="石村園子",
            price=300,
            category="general",
            campus="toyonaka",
            condition="good",
            description="授業で使いました。",
        )

    def _create_completed_handoff(self):
        self.book.buyer = self.buyer
        self.book.status = "in_progress"
        self.book.save(update_fields=["buyer", "status"])
        offer = TradeOffer.objects.create(
            book=self.book,
            seller=self.seller,
            buyer=self.buyer,
            price=self.book.price,
            status="accepted",
        )
        confirmed_at = timezone.now()
        return HandoffProposal.objects.create(
            trade_offer=offer,
            handoff_at=confirmed_at - timedelta(hours=1),
            location="豊中キャンパス 図書館前",
            status="accepted",
            seller_confirmed_at=confirmed_at,
            buyer_confirmed_at=confirmed_at,
            completed_at=confirmed_at,
        )

    def test_book_detail_page_renders_current_ui_and_backend_actions(self):
        response = self.client.get(reverse("book_detail", args=[self.book.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.book.title)
        self.assertContains(response, "著者：石村園子")
        self.assertContains(response, "出品者：")
        self.assertContains(response, "大阪 太郎")
        self.assertContains(response, reverse("user_profile", args=[self.seller.id]))
        self.assertContains(response, "状態 良い")
        self.assertContains(response, "豊中キャンパス")
        self.assertContains(response, "300")
        self.assertContains(response, "いいね 0")
        self.assertContains(response, "ログインして購入相談する")

    def test_public_profile_shows_score_listing_and_completed_trade_counts(self):
        Book.objects.create(
            seller=self.seller,
            buyer=self.buyer,
            title="取引完了した教科書",
            author="著者",
            price=200,
            category="general",
            campus="toyonaka",
            status="sold",
        )

        response = self.client.get(reverse("user_profile", args=[self.seller.id]))

        self.assertContains(response, "大阪 太郎")
        self.assertContains(response, "信用点数")
        self.assertContains(response, "100点")
        self.assertContains(response, "出品数")
        self.assertContains(response, "2件")
        self.assertContains(response, "取引完了数")
        self.assertContains(response, "1件")
        self.assertNotContains(response, self.seller.email)

    def test_chat_partner_name_links_to_public_profile(self):
        self.client.login(username=self.buyer.username, password="password12345")

        response = self.client.get(reverse("chat", args=[self.book.id]))

        self.assertContains(response, "大阪 太郎")
        self.assertContains(response, reverse("user_profile", args=[self.seller.id]))

    def test_profile_edit_uses_official_faculty_department_select(self):
        self.client.login(username=self.seller.username, password="password12345")

        response = self.client.get(reverse("edit_profile"))

        self.assertContains(response, '<select name="faculty"', html=False)
        self.assertContains(response, "工学部 電子情報工学科")
        self.assertContains(response, "基礎工学部 情報科学科")
        self.assertNotContains(response, 'type="text" name="faculty"')

    def test_profile_edit_rejects_unknown_faculty_department(self):
        self.client.login(username=self.seller.username, password="password12345")

        response = self.client.post(
            reverse("edit_profile"),
            {
                "display_name": "大阪 太郎",
                "faculty": "部部科科",
                "school_year": "2年",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.seller.profile.refresh_from_db()
        self.assertNotEqual(self.seller.profile.faculty, "部部科科")
        self.assertContains(response, "一覧から正しい学部・学科を選択してください。")

    def test_seller_can_open_each_buyer_chat_from_book_detail(self):
        Message.objects.create(
            book=self.book,
            sender=self.buyer,
            receiver=self.seller,
            content="購入したいので相談します。",
        )
        self.client.login(username="seller@ecs.osaka-u.ac.jp", password="password12345")

        response = self.client.get(reverse("book_detail", args=[self.book.id]))

        chat_url = f"{reverse('chat', args=[self.book.id])}?partner={self.buyer.id}"
        self.assertContains(response, "購入相談のチャット")
        self.assertContains(response, "チャットを開く")
        self.assertContains(response, chat_url)
        self.assertContains(response, "購入したいので相談します。")

    def test_search_page_links_to_book_detail(self):
        response = self.client.get(reverse("search"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("book_detail", args=[self.book.id]))

    def test_listing_sets_logged_in_user_as_seller(self):
        self.client.login(username="buyer@ecs.osaka-u.ac.jp", password="password12345")

        response = self.client.post(
            reverse("listing_form"),
            {
                "title": "ミクロ経済学の基礎",
                "author": "大山道広",
                "price": 400,
                "category": "general",
                "campus": "suita",
                "condition": "good",
                "description": "授業で使いました。",
                "status": "sold",
            },
        )

        created_book = Book.objects.get(title="ミクロ経済学の基礎", seller=self.buyer)
        self.assertRedirects(response, reverse("book_detail", args=[created_book.id]))
        self.assertEqual(created_book.seller, self.buyer)
        self.assertEqual(created_book.status, "available")

    def test_edit_succeeds_when_existing_image_file_is_missing(self):
        self.book.image = "book_images/missing-cover.png"
        self.book.save(update_fields=["image"])
        self.client.login(username="seller@ecs.osaka-u.ac.jp", password="password12345")

        response = self.client.post(
            reverse("edit_book", args=[self.book.id]),
            {
                "title": "更新した線形代数",
                "author": self.book.author,
                "price": self.book.price,
                "category": self.book.category,
                "campus": self.book.campus,
                "condition": self.book.condition,
                "description": self.book.description,
                "status": self.book.status,
            },
        )

        self.assertRedirects(response, reverse("book_detail", args=[self.book.id]))
        self.book.refresh_from_db()
        self.assertEqual(self.book.title, "更新した線形代数")
        self.assertEqual(self.book.image.name, "book_images/missing-cover.png")

    def test_like_toggles_favorite_and_likes_count(self):
        self.client.login(username="buyer@ecs.osaka-u.ac.jp", password="password12345")

        self.client.post(reverse("toggle_like", args=[self.book.id]))
        self.book.refresh_from_db()
        self.assertEqual(self.book.likes_count, 1)
        self.assertTrue(Favorite.objects.filter(user=self.buyer, book=self.book).exists())

        self.client.post(reverse("toggle_like", args=[self.book.id]))
        self.book.refresh_from_db()
        self.assertEqual(self.book.likes_count, 0)
        self.assertFalse(Favorite.objects.filter(user=self.buyer, book=self.book).exists())

    def test_consultation_opens_chat_without_sending_message(self):
        self.client.login(username="buyer@ecs.osaka-u.ac.jp", password="password12345")

        response = self.client.post(
            reverse("start_consultation", args=[self.book.id]),
            {"content": "購入したいです。"},
        )

        self.book.refresh_from_db()
        self.assertRedirects(response, reverse("chat", args=[self.book.id]))
        self.assertEqual(self.book.status, "available")
        self.assertIsNone(self.book.buyer)
        self.assertFalse(Message.objects.filter(book=self.book).exists())

    def test_message_does_not_establish_trade(self):
        self.client.login(username="buyer@ecs.osaka-u.ac.jp", password="password12345")

        response = self.client.post(reverse("chat", args=[self.book.id]), {"content": "購入を相談します。"})

        self.assertRedirects(response, reverse("chat", args=[self.book.id]))
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, "available")
        self.assertIsNone(self.book.buyer)

    def test_chat_messages_do_not_render_as_flash_notifications(self):
        Message.objects.create(
            book=self.book,
            sender=self.buyer,
            receiver=self.seller,
            content="価格を相談したいです。",
        )
        self.client.login(username="buyer@ecs.osaka-u.ac.jp", password="password12345")

        response = self.client.get(reverse("chat", args=[self.book.id]))

        self.assertContains(response, "価格を相談したいです。")
        self.assertContains(response, "本の詳細に戻る")
        self.assertContains(response, reverse("book_detail", args=[self.book.id]))
        self.assertNotContains(response, f"{self.book.title}: {self.buyer.username}")

    def test_inbox_does_not_show_messages_sent_by_the_current_user(self):
        Message.objects.create(
            book=self.book,
            sender=self.buyer,
            receiver=self.seller,
            content="自分が送っただけのメッセージ",
        )
        self.client.login(username=self.buyer.username, password="password12345")

        response = self.client.get(reverse("inbox"))

        self.assertNotContains(response, "自分が送っただけのメッセージ")
        self.assertNotContains(response, self.book.title)

    def test_inbox_preview_uses_latest_received_message_not_own_reply(self):
        Message.objects.create(
            book=self.book,
            sender=self.seller,
            receiver=self.buyer,
            content="相手から届いたメッセージ",
        )
        Message.objects.create(
            book=self.book,
            sender=self.buyer,
            receiver=self.seller,
            content="その後に自分が送った返信",
        )
        self.client.login(username=self.buyer.username, password="password12345")

        response = self.client.get(reverse("inbox"))

        self.assertContains(response, "相手から届いたメッセージ")
        self.assertNotContains(response, "その後に自分が送った返信")

    def test_seller_can_offer_a_changed_price(self):
        Message.objects.create(
            book=self.book,
            sender=self.buyer,
            receiver=self.seller,
            content="購入を相談します。",
        )
        self.client.login(username="seller@ecs.osaka-u.ac.jp", password="password12345")

        response = self.client.post(
            reverse("create_trade_offer", args=[self.book.id]),
            {"buyer": self.buyer.id, "price": 250},
        )

        self.assertRedirects(
            response,
            f"{reverse('chat', args=[self.book.id])}?partner={self.buyer.id}",
        )
        offer = TradeOffer.objects.get(book=self.book, buyer=self.buyer)
        self.assertEqual(offer.price, 250)
        self.assertEqual(offer.status, "pending")
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, "available")

    def test_buyer_cannot_create_trade_offer(self):
        Message.objects.create(
            book=self.book,
            sender=self.buyer,
            receiver=self.seller,
            content="購入を相談します。",
        )
        self.client.login(username="buyer@ecs.osaka-u.ac.jp", password="password12345")

        self.client.post(
            reverse("create_trade_offer", args=[self.book.id]),
            {"buyer": self.buyer.id, "price": 1},
        )

        self.assertFalse(TradeOffer.objects.filter(book=self.book).exists())

    def test_buyer_acceptance_establishes_trade_at_offered_price(self):
        offer = TradeOffer.objects.create(
            book=self.book,
            seller=self.seller,
            buyer=self.buyer,
            price=250,
        )
        self.client.login(username="buyer@ecs.osaka-u.ac.jp", password="password12345")

        response = self.client.get(reverse("chat", args=[self.book.id]))
        self.assertContains(response, "このボタンを押すと取引が確定し、この参考書の募集は終了します。")

        response = self.client.post(reverse("accept_trade_offer", args=[offer.id]), follow=True)

        self.assertContains(response, "この参考書の取引が成立しました。")
        offer.refresh_from_db()
        self.book.refresh_from_db()
        self.assertEqual(offer.status, "accepted")
        self.assertEqual(self.book.status, "in_progress")
        self.assertEqual(self.book.buyer, self.buyer)
        self.assertEqual(self.book.price, 250)

        response = self.client.get(reverse("chat", args=[self.book.id]))
        self.assertNotContains(response, "flash-message--success")

    def test_buyer_can_reject_price_without_establishing_trade(self):
        offer = TradeOffer.objects.create(
            book=self.book,
            seller=self.seller,
            buyer=self.buyer,
            price=250,
        )
        self.client.login(username=self.buyer.username, password="password12345")
        response = self.client.get(reverse("chat", args=[self.book.id]))
        self.assertContains(response, "この条件に同意する")
        self.assertContains(response, "同意しない")

        response = self.client.post(reverse("reject_trade_offer", args=[offer.id]), follow=True)

        offer.refresh_from_db()
        self.book.refresh_from_db()
        self.assertEqual(offer.status, "rejected")
        self.assertEqual(self.book.status, "available")
        self.assertIsNone(self.book.buyer)
        self.assertContains(response, "この価格への同意を見送りました。")

    def test_non_target_buyer_cannot_reject_price(self):
        offer = TradeOffer.objects.create(
            book=self.book,
            seller=self.seller,
            buyer=self.buyer,
            price=250,
        )
        self.client.login(username=self.other_buyer.username, password="password12345")

        self.client.post(reverse("reject_trade_offer", args=[offer.id]))

        offer.refresh_from_db()
        self.assertEqual(offer.status, "pending")

    def test_non_target_buyer_cannot_accept_offer(self):
        offer = TradeOffer.objects.create(
            book=self.book,
            seller=self.seller,
            buyer=self.buyer,
            price=250,
        )
        self.client.login(username="other@ecs.osaka-u.ac.jp", password="password12345")

        self.client.post(reverse("accept_trade_offer", args=[offer.id]))

        offer.refresh_from_db()
        self.book.refresh_from_db()
        self.assertEqual(offer.status, "pending")
        self.assertEqual(self.book.status, "available")
        self.assertIsNone(self.book.buyer)

    def test_new_offer_withdraws_previous_buyers_offer(self):
        for buyer in (self.buyer, self.other_buyer):
            Message.objects.create(
                book=self.book,
                sender=buyer,
                receiver=self.seller,
                content="購入を相談します。",
            )
        first_offer = TradeOffer.objects.create(
            book=self.book,
            seller=self.seller,
            buyer=self.buyer,
            price=250,
        )
        self.client.login(username="seller@ecs.osaka-u.ac.jp", password="password12345")

        self.client.post(
            reverse("create_trade_offer", args=[self.book.id]),
            {"buyer": self.other_buyer.id, "price": 280},
        )

        first_offer.refresh_from_db()
        self.assertEqual(first_offer.status, "withdrawn")
        self.assertTrue(
            TradeOffer.objects.filter(
                book=self.book,
                buyer=self.other_buyer,
                price=280,
                status="pending",
            ).exists()
        )

    def test_only_one_buyer_can_establish_trade(self):
        first_offer = TradeOffer.objects.create(
            book=self.book,
            seller=self.seller,
            buyer=self.buyer,
            price=250,
        )
        second_offer = TradeOffer.objects.create(
            book=self.book,
            seller=self.seller,
            buyer=self.other_buyer,
            price=280,
        )
        self.client.login(username="buyer@ecs.osaka-u.ac.jp", password="password12345")
        self.client.post(reverse("accept_trade_offer", args=[first_offer.id]))
        self.client.logout()
        self.client.login(username="other@ecs.osaka-u.ac.jp", password="password12345")

        self.client.post(reverse("accept_trade_offer", args=[second_offer.id]))

        first_offer.refresh_from_db()
        second_offer.refresh_from_db()
        self.book.refresh_from_db()
        self.assertEqual(first_offer.status, "accepted")
        self.assertEqual(second_offer.status, "withdrawn")
        self.assertEqual(self.book.buyer, self.buyer)
        self.assertEqual(self.book.price, 250)

    def test_seller_proposes_and_target_buyer_accepts_handoff(self):
        offer = TradeOffer.objects.create(
            book=self.book,
            seller=self.seller,
            buyer=self.buyer,
            price=250,
            status="accepted",
        )
        self.book.buyer = self.buyer
        self.book.price = 250
        self.book.status = "in_progress"
        self.book.save(update_fields=["buyer", "price", "status"])
        Message.objects.create(
            book=self.book,
            sender=self.buyer,
            receiver=self.seller,
            content="受け渡し予定を相談します。",
        )
        handoff_at = timezone.now() + timedelta(days=2)
        self.client.login(username=self.seller.username, password="password12345")

        response = self.client.post(
            reverse("create_handoff_proposal", args=[offer.id]),
            {
                "handoff_at": timezone.localtime(handoff_at).strftime("%Y-%m-%dT%H:%M"),
                "location": "豊中キャンパス 図書館前",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('chat', args=[self.book.id])}?partner={self.buyer.id}",
        )
        proposal = HandoffProposal.objects.get(trade_offer=offer)
        self.assertEqual(proposal.status, "pending")
        self.client.logout()
        self.client.login(username=self.buyer.username, password="password12345")
        response = self.client.get(reverse("chat", args=[self.book.id]))
        self.assertContains(response, "この日時と場所に同意する")
        self.assertContains(response, "豊中キャンパス 図書館前")

        response = self.client.post(reverse("accept_handoff_proposal", args=[proposal.id]), follow=True)

        proposal.refresh_from_db()
        self.assertEqual(proposal.status, "accepted")
        self.assertContains(response, "受け渡し日時と場所が確定しました。")
        self.assertContains(response, "取引は終わり、あとは渡すだけです")

    def test_other_buyer_cannot_accept_handoff_and_accepted_handoff_cannot_change(self):
        offer = TradeOffer.objects.create(
            book=self.book,
            seller=self.seller,
            buyer=self.buyer,
            price=250,
            status="accepted",
        )
        self.book.buyer = self.buyer
        self.book.status = "in_progress"
        self.book.save(update_fields=["buyer", "status"])
        proposal = HandoffProposal.objects.create(
            trade_offer=offer,
            handoff_at=timezone.now() + timedelta(days=1),
            location="吹田キャンパス 正門",
        )
        self.client.login(username=self.other_buyer.username, password="password12345")

        self.client.post(reverse("accept_handoff_proposal", args=[proposal.id]))

        proposal.refresh_from_db()
        self.assertEqual(proposal.status, "pending")
        self.client.logout()
        self.client.login(username=self.buyer.username, password="password12345")
        self.client.post(reverse("accept_handoff_proposal", args=[proposal.id]))
        self.client.post(reverse("accept_handoff_proposal", args=[proposal.id]))
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, "accepted")
        self.assertEqual(HandoffProposal.objects.filter(trade_offer=offer, status="accepted").count(), 1)

    def test_buyer_can_reject_handoff_and_seller_can_propose_again(self):
        offer = TradeOffer.objects.create(
            book=self.book,
            seller=self.seller,
            buyer=self.buyer,
            price=250,
            status="accepted",
        )
        self.book.buyer = self.buyer
        self.book.status = "in_progress"
        self.book.save(update_fields=["buyer", "status"])
        proposal = HandoffProposal.objects.create(
            trade_offer=offer,
            handoff_at=timezone.now() + timedelta(days=1),
            location="吹田キャンパス 正門",
        )
        self.client.login(username=self.buyer.username, password="password12345")
        response = self.client.get(reverse("chat", args=[self.book.id]))
        self.assertContains(response, "この日時と場所に同意する")
        self.assertContains(response, "同意しない")

        self.client.post(reverse("reject_handoff_proposal", args=[proposal.id]))

        proposal.refresh_from_db()
        self.assertEqual(proposal.status, "rejected")
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, "in_progress")
        self.assertEqual(self.book.buyer, self.buyer)
        self.client.logout()
        self.client.login(username=self.seller.username, password="password12345")
        chat_url = f"{reverse('chat', args=[self.book.id])}?partner={self.buyer.id}"
        response = self.client.get(chat_url)
        self.assertContains(response, "購入者が前回の日時・場所に同意しませんでした。")

        self.client.post(
            reverse("create_handoff_proposal", args=[offer.id]),
            {
                "handoff_at": timezone.localtime(timezone.now() + timedelta(days=2)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "location": "豊中キャンパス 図書館前",
            },
        )
        self.assertEqual(HandoffProposal.objects.filter(trade_offer=offer, status="pending").count(), 1)

    def test_non_target_buyer_cannot_reject_handoff(self):
        offer = TradeOffer.objects.create(
            book=self.book,
            seller=self.seller,
            buyer=self.buyer,
            price=250,
            status="accepted",
        )
        self.book.buyer = self.buyer
        self.book.status = "in_progress"
        self.book.save(update_fields=["buyer", "status"])
        proposal = HandoffProposal.objects.create(
            trade_offer=offer,
            handoff_at=timezone.now() + timedelta(days=1),
            location="吹田キャンパス 正門",
        )
        self.client.login(username=self.other_buyer.username, password="password12345")

        self.client.post(reverse("reject_handoff_proposal", args=[proposal.id]))

        proposal.refresh_from_db()
        self.assertEqual(proposal.status, "pending")

    def test_confirmed_handoff_is_prominent_in_inbox_and_mypage(self):
        offer = TradeOffer.objects.create(
            book=self.book,
            seller=self.seller,
            buyer=self.buyer,
            price=250,
            status="accepted",
        )
        self.book.buyer = self.buyer
        self.book.status = "in_progress"
        self.book.save(update_fields=["buyer", "status"])
        Message.objects.create(
            book=self.book,
            sender=self.buyer,
            receiver=self.seller,
            content="当日よろしくお願いします。",
        )
        HandoffProposal.objects.create(
            trade_offer=offer,
            handoff_at=timezone.now() + timedelta(days=1),
            location="箕面キャンパス 1階入口",
            status="accepted",
        )
        self.client.login(username=self.buyer.username, password="password12345")

        response = self.client.get(reverse("inbox"))
        self.assertContains(response, "受け渡し予定が確定しました")
        self.assertContains(response, "箕面キャンパス 1階入口")
        response = self.client.get(reverse("mypage"))
        self.assertContains(response, "取引は終わり、あとは渡すだけ")
        self.assertContains(response, "箕面キャンパス 1階入口")

    def test_handoff_completion_requires_scheduled_time_and_both_parties(self):
        offer = TradeOffer.objects.create(
            book=self.book,
            seller=self.seller,
            buyer=self.buyer,
            price=250,
            status="accepted",
        )
        self.book.buyer = self.buyer
        self.book.status = "in_progress"
        self.book.save(update_fields=["buyer", "status"])
        handoff = HandoffProposal.objects.create(
            trade_offer=offer,
            handoff_at=timezone.now() + timedelta(hours=1),
            location="吹田キャンパス 正門",
            status="accepted",
        )
        self.client.login(username=self.buyer.username, password="password12345")

        self.client.post(reverse("confirm_handoff_complete", args=[handoff.id]))

        handoff.refresh_from_db()
        self.assertIsNone(handoff.buyer_confirmed_at)
        handoff.handoff_at = timezone.now() - timedelta(minutes=1)
        handoff.save(update_fields=["handoff_at"])
        self.client.post(reverse("confirm_handoff_complete", args=[handoff.id]))
        handoff.refresh_from_db()
        self.assertIsNotNone(handoff.buyer_confirmed_at)
        self.assertIsNone(handoff.completed_at)

        response = self.client.get(reverse("evaluate_trade", args=[self.book.id]))
        self.assertRedirects(response, reverse("chat", args=[self.book.id]))
        self.client.logout()
        self.client.login(username=self.seller.username, password="password12345")
        response = self.client.post(reverse("confirm_handoff_complete", args=[handoff.id]))

        handoff.refresh_from_db()
        self.assertIsNotNone(handoff.seller_confirmed_at)
        self.assertIsNotNone(handoff.completed_at)
        self.assertRedirects(response, reverse("evaluate_trade", args=[self.book.id]))

    def test_chat_hides_old_evaluation_actions_and_styles_cancellation_actions(self):
        offer = TradeOffer.objects.create(
            book=self.book,
            seller=self.seller,
            buyer=self.buyer,
            price=250,
            status="accepted",
        )
        self.book.buyer = self.buyer
        self.book.status = "in_progress"
        self.book.save(update_fields=["buyer", "status"])
        HandoffProposal.objects.create(
            trade_offer=offer,
            handoff_at=timezone.now() + timedelta(days=1),
            location="豊中キャンパス 図書館前",
            status="accepted",
        )
        self.client.login(username=self.buyer.username, password="password12345")

        response = self.client.get(reverse("chat", args=[self.book.id]))

        self.assertNotContains(response, "取引完了後の評価")
        self.assertNotContains(response, "良い評価を送る")
        self.assertContains(response, 'class="cancel-button"', html=False)
        self.assertContains(response, 'class="cancel-button cancel-button--report"', html=False)

    def test_both_parties_receive_completion_notice_and_evaluation_screen(self):
        handoff = self._create_completed_handoff()
        Message.objects.create(
            book=self.book,
            sender=self.buyer,
            receiver=self.seller,
            content="受け渡し完了です。",
        )
        for user in (self.seller, self.buyer):
            self.client.login(username=user.username, password="password12345")
            response = self.client.get(reverse("inbox"))
            self.assertContains(response, "受け渡しが完了しました")
            self.assertContains(response, "相手を評価してください")
            response = self.client.get(reverse("evaluate_trade", args=[self.book.id]))
            self.assertContains(response, "相手との取引はいかがでしたか？")
            self.assertContains(response, handoff.location)
            self.client.logout()

    def test_non_participant_cannot_confirm_handoff_completion(self):
        handoff = self._create_completed_handoff()
        handoff.seller_confirmed_at = None
        handoff.buyer_confirmed_at = None
        handoff.completed_at = None
        handoff.save(update_fields=["seller_confirmed_at", "buyer_confirmed_at", "completed_at"])
        self.client.login(username=self.other_buyer.username, password="password12345")

        self.client.post(reverse("confirm_handoff_complete", args=[handoff.id]))

        handoff.refresh_from_db()
        self.assertIsNone(handoff.completed_at)
        self.assertIsNone(handoff.seller_confirmed_at)
        self.assertIsNone(handoff.buyer_confirmed_at)

    def test_second_buyer_can_send_a_separate_consultation(self):
        self.book.buyer = self.buyer
        self.book.status = "in_progress"
        self.book.save(update_fields=["buyer", "status"])
        self.client.login(username="other@ecs.osaka-u.ac.jp", password="password12345")

        response = self.client.post(reverse("start_consultation", args=[self.book.id]))
        self.assertRedirects(response, reverse("chat", args=[self.book.id]))

        response = self.client.post(reverse("chat", args=[self.book.id]), {"content": "横取り相談です。"})

        self.assertRedirects(response, reverse("chat", args=[self.book.id]))
        self.book.refresh_from_db()
        self.assertEqual(self.book.buyer, self.buyer)
        self.assertTrue(Message.objects.filter(book=self.book, sender=self.other_buyer).exists())

    def test_sold_book_cannot_be_consulted(self):
        self.book.status = "sold"
        self.book.save(update_fields=["status"])
        self.client.login(username="buyer@ecs.osaka-u.ac.jp", password="password12345")

        response = self.client.post(
            reverse("start_consultation", args=[self.book.id]),
            {"content": "購入したいです。"},
        )

        self.assertRedirects(response, reverse("book_detail", args=[self.book.id]))
        self.assertFalse(Message.objects.filter(book=self.book, sender=self.buyer).exists())

    def test_parallel_buyer_only_sees_their_own_thread(self):
        self.book.buyer = self.buyer
        self.book.status = "in_progress"
        self.book.save(update_fields=["buyer", "status"])
        Message.objects.create(
            book=self.book,
            sender=self.buyer,
            receiver=self.seller,
            content="最初の購入者の相談です。",
        )
        self.client.login(username="other@ecs.osaka-u.ac.jp", password="password12345")

        response = self.client.post(reverse("chat", args=[self.book.id]), {"content": "割り込みます。"})

        self.assertRedirects(response, reverse("chat", args=[self.book.id]))
        response = self.client.get(reverse("chat", args=[self.book.id]))
        self.assertContains(response, "割り込みます。")
        self.assertNotContains(response, "最初の購入者の相談です。")

    def test_evaluation_applies_after_both_sides_submit(self):
        self._create_completed_handoff()

        _evaluation, created = submit_evaluation(self.book, self.buyer, self.seller, "good")
        self.assertTrue(created)
        self.seller.profile.refresh_from_db()
        self.assertEqual(self.seller.profile.credit_score, 100)

        _evaluation, created = submit_evaluation(self.book, self.seller, self.buyer, "bad")
        self.assertTrue(created)
        self.seller.profile.refresh_from_db()
        self.buyer.profile.refresh_from_db()
        self.book.refresh_from_db()
        self.assertEqual(self.seller.profile.credit_score, 110)
        self.assertEqual(self.buyer.profile.credit_score, 90)
        self.assertEqual(self.book.status, "sold")

    def test_duplicate_evaluation_does_not_apply_score_twice(self):
        self._create_completed_handoff()

        submit_evaluation(self.book, self.buyer, self.seller, "good")
        submit_evaluation(self.book, self.seller, self.buyer, "good")
        _evaluation, created = submit_evaluation(self.book, self.buyer, self.seller, "good")

        self.assertFalse(created)
        self.seller.profile.refresh_from_db()
        self.assertEqual(self.seller.profile.credit_score, 110)

    def test_invalid_evaluation_type_is_rejected(self):
        with self.assertRaises(ValueError):
            submit_evaluation(self.book, self.buyer, self.seller, "normal")

    def test_cancellation_scores_apply_immediately_and_reopens_listing(self):
        self.book.buyer = self.buyer
        self.book.status = "in_progress"
        self.book.save(update_fields=["buyer", "status"])
        offer = TradeOffer.objects.create(
            book=self.book,
            seller=self.seller,
            buyer=self.buyer,
            price=self.book.price,
            status="accepted",
        )
        handoff = HandoffProposal.objects.create(
            trade_offer=offer,
            handoff_at=timezone.now() + timedelta(days=1),
            location="豊中キャンパス",
            status="accepted",
        )

        _log, created = apply_cancellation(self.book, reporter=self.buyer, target=self.buyer, kind="cancel")
        self.assertTrue(created)
        self.buyer.profile.refresh_from_db()
        self.assertEqual(self.buyer.profile.credit_score, 90)
        self.book.refresh_from_db()
        handoff.refresh_from_db()
        self.assertEqual(self.book.status, "available")
        self.assertIsNone(self.book.buyer)
        self.assertEqual(handoff.status, "cancelled")

    def test_no_show_report_scores_the_other_party(self):
        self.book.buyer = self.buyer
        self.book.status = "in_progress"
        self.book.save(update_fields=["buyer", "status"])

        _log, created = apply_cancellation(self.book, reporter=self.seller, target=self.buyer, kind="no_show")
        self.assertTrue(created)
        self.buyer.profile.refresh_from_db()
        self.assertEqual(self.buyer.profile.credit_score, 70)

    def test_cancellation_view_reopens_listing(self):
        self.book.buyer = self.buyer
        self.book.status = "in_progress"
        self.book.save(update_fields=["buyer", "status"])
        self.client.login(username="buyer@ecs.osaka-u.ac.jp", password="password12345")

        response = self.client.post(reverse("cancel_trade", args=[self.book.id]), {"kind": "cancel"})

        self.assertRedirects(response, reverse("book_detail", args=[self.book.id]))
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, "available")
        self.assertIsNone(self.book.buyer)

    def test_evaluation_view_accepts_good_or_bad(self):
        self._create_completed_handoff()
        self.client.login(username="buyer@ecs.osaka-u.ac.jp", password="password12345")

        response = self.client.post(
            reverse("evaluate_trade", args=[self.book.id]),
            {"evaluation_type": "good"},
        )

        self.assertRedirects(response, reverse("evaluate_trade", args=[self.book.id]))


class MediaDeliveryTests(TestCase):
    def test_uploaded_book_image_is_available_when_debug_is_disabled(self):
        with TemporaryDirectory() as media_root:
            with override_settings(DEBUG=False, MEDIA_ROOT=Path(media_root)):
                user = User.objects.create_user(
                    username="media@ecs.osaka-u.ac.jp",
                    email="media@ecs.osaka-u.ac.jp",
                    password="password12345",
                )
                book = Book.objects.create(
                    seller=user,
                    title="画像付き教科書",
                    author="著者",
                    price=300,
                    category="general",
                    campus="toyonaka",
                    image=SimpleUploadedFile(
                        "cover.png",
                        b"\x89PNG\r\n\x1a\nimage-content",
                        content_type="image/png",
                    ),
                )

                response = self.client.get(book.image.url)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(b"".join(response.streaming_content), b"\x89PNG\r\n\x1a\nimage-content")


@override_settings(
    SUPABASE_URL="https://project.supabase.co",
    SUPABASE_STORAGE_BUCKET="book-images",
    SUPABASE_STORAGE_KEY="server-secret",
)
class SupabaseStorageTests(SimpleTestCase):
    @patch("main.storage.urlopen")
    def test_saves_to_storage_and_returns_public_url(self, mock_urlopen):
        mock_urlopen.return_value = MagicMock(__enter__=MagicMock(), __exit__=MagicMock())
        storage = SupabaseStorage()

        saved_name = storage._save("book_images/表紙.png", ContentFile(b"image"))

        request = mock_urlopen.call_args.args[0]
        self.assertEqual(saved_name, "book_images/表紙.png")
        self.assertEqual(
            request.full_url,
            "https://project.supabase.co/storage/v1/object/book-images/book_images/%E8%A1%A8%E7%B4%99.png",
        )
        self.assertEqual(
            storage.url(saved_name),
            "https://project.supabase.co/storage/v1/object/public/book-images/book_images/%E8%A1%A8%E7%B4%99.png",
        )
