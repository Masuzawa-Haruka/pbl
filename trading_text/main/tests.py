from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse

from .forms import EcsUserCreationForm
from .models import Book, Favorite, Message, UserProfile
from .services import apply_cancellation, submit_evaluation


class AuthFormTests(TestCase):
    def test_signup_requires_ecs_email(self):
        form = EcsUserCreationForm(
            data={
                "email": "student@osaka-u.ac.jp",
                "password1": "StrongPass12345",
                "password2": "StrongPass12345",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_signup_accepts_ecs_email_as_inactive_user(self):
        form = EcsUserCreationForm(
            data={
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
                "email": "student@ecs.osaka-u.ac.jp",
                "password1": "StrongPass12345",
                "password2": "StrongPass12345",
            },
        )

        self.assertEqual(response.status_code, 200)
        mock_sign_up.assert_called_once()

    @override_settings(SUPABASE_URL="https://example.supabase.co", SUPABASE_ANON_KEY="anon-key")
    @patch("main.views.sign_in_with_password")
    def test_login_uses_supabase_auth_and_syncs_local_user(self, mock_sign_in):
        mock_sign_in.return_value = {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "user": {"id": "supabase-user-id"},
        }

        response = self.client.post(
            reverse("login"),
            {
                "email": "student@ecs.osaka-u.ac.jp",
                "password": "StrongPass12345",
            },
        )

        self.assertRedirects(response, reverse("search"))
        self.assertTrue(User.objects.filter(username="student@ecs.osaka-u.ac.jp").exists())


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
        UserProfile.objects.get_or_create(user=self.seller, defaults={"display_name": "大阪 太郎"})
        UserProfile.objects.get_or_create(user=self.buyer, defaults={"display_name": "大阪 花子"})
        self.book = Book.objects.create(
            seller=self.seller,
            title="基礎からの線形代数",
            author="石村園子",
            price=300,
            category="general",
            campus="toyonaka",
            condition="good",
        )

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
                "status": "available",
            },
        )

        created_book = Book.objects.get(title="ミクロ経済学の基礎", seller=self.buyer)
        self.assertRedirects(response, reverse("book_detail", args=[created_book.id]))
        self.assertEqual(created_book.seller, self.buyer)

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

    def test_consultation_creates_message_and_marks_book_in_progress(self):
        self.client.login(username="buyer@ecs.osaka-u.ac.jp", password="password12345")

        response = self.client.post(
            reverse("start_consultation", args=[self.book.id]),
            {"content": "購入したいです。"},
        )

        self.book.refresh_from_db()
        self.assertRedirects(response, reverse("chat", args=[self.book.id]))
        self.assertEqual(self.book.status, "in_progress")
        self.assertEqual(self.book.buyer, self.buyer)
        self.assertTrue(Message.objects.filter(book=self.book, sender=self.buyer, receiver=self.seller).exists())

    def test_evaluation_applies_after_both_sides_submit(self):
        self.book.buyer = self.buyer
        self.book.status = "in_progress"
        self.book.save(update_fields=["buyer", "status"])

        submit_evaluation(self.book, self.buyer, self.seller, "good")
        self.seller.profile.refresh_from_db()
        self.assertEqual(self.seller.profile.credit_score, 100)

        submit_evaluation(self.book, self.seller, self.buyer, "bad")
        self.seller.profile.refresh_from_db()
        self.buyer.profile.refresh_from_db()
        self.book.refresh_from_db()
        self.assertEqual(self.seller.profile.credit_score, 110)
        self.assertEqual(self.buyer.profile.credit_score, 90)
        self.assertEqual(self.book.status, "sold")

    def test_invalid_evaluation_type_is_rejected(self):
        with self.assertRaises(ValueError):
            submit_evaluation(self.book, self.buyer, self.seller, "normal")

    def test_cancellation_scores_apply_immediately(self):
        apply_cancellation(self.book, reporter=self.buyer, target=self.buyer, kind="cancel")
        self.buyer.profile.refresh_from_db()
        self.assertEqual(self.buyer.profile.credit_score, 90)

        apply_cancellation(self.book, reporter=self.seller, target=self.buyer, kind="no_show")
        self.buyer.profile.refresh_from_db()
        self.assertEqual(self.buyer.profile.credit_score, 60)

    def test_evaluation_view_accepts_good_or_bad(self):
        self.book.buyer = self.buyer
        self.book.status = "in_progress"
        self.book.save(update_fields=["buyer", "status"])
        self.client.login(username="buyer@ecs.osaka-u.ac.jp", password="password12345")

        response = self.client.post(
            reverse("evaluate_trade", args=[self.book.id]),
            {"evaluation_type": "good"},
        )

        self.assertRedirects(response, reverse("chat", args=[self.book.id]))
