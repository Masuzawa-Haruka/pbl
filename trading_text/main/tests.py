import io
import json
from contextlib import redirect_stdout
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from main.services.figma import FigmaAPIError, fetch_figma_document
from .forms import LoginForm, SignupForm
from .models import Book, ChatMessage, Favorite, Profile, Transaction


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class FigmaServiceTests(SimpleTestCase):
    def test_fetch_figma_document_returns_document(self):
        captured = {}

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["token"] = request.get_header("X-figma-token")
            captured["timeout"] = timeout
            return FakeResponse({"document": {"name": "OU Textbook"}})

        document = fetch_figma_document(
            "abc123",
            token="test-token",
            timeout=5,
            opener=opener,
        )

        self.assertEqual(document, {"name": "OU Textbook"})
        self.assertEqual(captured["url"], "https://api.figma.com/v1/files/abc123")
        self.assertEqual(captured["token"], "test-token")
        self.assertEqual(captured["timeout"], 5)

    def test_fetch_figma_document_requires_token(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesMessage(
                FigmaAPIError,
                "FIGMA_PERSONAL_ACCESS_TOKEN is required",
            ):
                fetch_figma_document("abc123")


class FigmaCommandTests(SimpleTestCase):
    def test_fetch_figma_file_command_prints_document(self):
        stdout = io.StringIO()

        with patch(
            "main.management.commands.fetch_figma_file.fetch_figma_document",
            return_value={"name": "OU Textbook"},
        ):
            call_command("fetch_figma_file", "abc123", stdout=stdout)

        self.assertIn('"name": "OU Textbook"', stdout.getvalue())

    def test_fetch_figma_file_command_raises_command_error(self):
        with patch(
            "main.management.commands.fetch_figma_file.fetch_figma_document",
            side_effect=FigmaAPIError("token missing"),
        ):
            with self.assertRaisesMessage(CommandError, "token missing"):
                with redirect_stdout(io.StringIO()):
                    call_command("fetch_figma_file", "abc123")


class OsakaAuthTests(TestCase):
    def test_signup_rejects_non_osaka_email(self):
        form = SignupForm(
            data={
                "display_name": "Test User",
                "email": "test@example.com",
                "password": "password12345",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("大阪大学メール", form.errors["email"][0])

    def test_signup_creates_user_and_profile_for_osaka_email(self):
        form = SignupForm(
            data={
                "display_name": "大阪 太郎",
                "email": "taro@osaka-u.ac.jp",
                "department": "工学部",
                "year": 2,
                "password": "password12345",
            }
        )

        self.assertTrue(form.is_valid())
        user = form.save()

        self.assertEqual(user.username, "taro@osaka-u.ac.jp")
        self.assertEqual(user.profile.display_name, "大阪 太郎")
        self.assertEqual(user.profile.trust_score, 100)

    def test_login_rejects_non_osaka_email(self):
        form = LoginForm(data={"email": "user@example.com", "password": "password12345"})

        self.assertFalse(form.is_valid())
        self.assertIn("大阪大学メール", form.errors["email"][0])


class MarketplaceFlowTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username="seller@osaka-u.ac.jp",
            email="seller@osaka-u.ac.jp",
            password="password12345",
        )
        Profile.objects.create(user=self.seller, display_name="出品者")
        self.buyer = User.objects.create_user(
            username="buyer@osaka-u.ac.jp",
            email="buyer@osaka-u.ac.jp",
            password="password12345",
        )
        Profile.objects.create(user=self.buyer, display_name="購入者")

    def test_listing_form_creates_book_for_logged_in_user(self):
        self.client.force_login(self.seller)

        response = self.client.post(
            reverse("listing_form"),
            {
                "title": "線形代数",
                "author": "石村園子",
                "price": 300,
                "category": "general",
                "campus": "toyonaka",
                "condition": "good",
                "description": "書き込みはほとんどありません。",
            },
        )

        book = Book.objects.get(owner=self.seller, title="線形代数")
        self.assertRedirects(response, reverse("book_detail", args=[book.id]))
        self.assertEqual(book.owner, self.seller)
        self.assertEqual(book.status, "available")

    def test_favorite_toggle_adds_and_removes_favorite(self):
        book = Book.objects.create(
            owner=self.seller,
            title="線形代数",
            author="石村園子",
            price=300,
            category="general",
            campus="toyonaka",
        )
        self.client.force_login(self.buyer)

        self.client.post(reverse("toggle_favorite", args=[book.id]))
        self.assertTrue(Favorite.objects.filter(user=self.buyer, book=book).exists())
        book.refresh_from_db()
        self.assertEqual(book.likes_count, 1)

        self.client.post(reverse("toggle_favorite", args=[book.id]))
        self.assertFalse(Favorite.objects.filter(user=self.buyer, book=book).exists())
        book.refresh_from_db()
        self.assertEqual(book.likes_count, 0)

    def test_start_transaction_creates_thread_and_matching_status(self):
        book = Book.objects.create(
            owner=self.seller,
            title="線形代数",
            author="石村園子",
            price=300,
            category="general",
            campus="toyonaka",
        )
        self.client.force_login(self.buyer)

        response = self.client.post(reverse("start_transaction", args=[book.id]))

        transaction = Transaction.objects.get()
        self.assertRedirects(response, reverse("transaction_detail", args=[transaction.id]))
        self.assertEqual(transaction.seller, self.seller)
        self.assertEqual(transaction.buyer, self.buyer)
        book.refresh_from_db()
        self.assertEqual(book.status, "matching")
        self.assertEqual(transaction.messages.count(), 1)

    def test_transaction_detail_accepts_chat_message(self):
        book = Book.objects.create(
            owner=self.seller,
            title="線形代数",
            author="石村園子",
            price=300,
            category="general",
            campus="toyonaka",
        )
        transaction = Transaction.objects.create(book=book, seller=self.seller, buyer=self.buyer)
        self.client.force_login(self.buyer)

        response = self.client.post(
            reverse("transaction_detail", args=[transaction.id]),
            {"action": "message", "body": "明日の午後に受け取れます。"},
        )

        self.assertRedirects(response, reverse("transaction_detail", args=[transaction.id]))
        self.assertTrue(ChatMessage.objects.filter(transaction=transaction, body__contains="明日").exists())

    def test_core_pages_render(self):
        book = Book.objects.create(
            owner=self.seller,
            title="線形代数",
            author="石村園子",
            price=300,
            category="general",
            campus="toyonaka",
        )

        self.assertEqual(self.client.get(reverse("search")).status_code, 200)
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)
        self.assertEqual(self.client.get(reverse("signup")).status_code, 200)
        self.assertEqual(self.client.get(reverse("book_detail", args=[book.id])).status_code, 200)

        self.assertEqual(self.client.get(reverse("listing_form")).status_code, 302)
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(reverse("listing_form")).status_code, 200)
        self.assertEqual(self.client.get(reverse("mypage")).status_code, 200)
