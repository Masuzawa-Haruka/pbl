from django.test import TestCase
from django.urls import reverse

from .models import Book


class BookDetailTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title="基礎からの線形代数",
            author="石村園子",
            price=300,
            category="general",
            campus="toyonaka",
            condition="good",
            description="授業で使いました。",
        )

    def test_book_detail_page_renders(self):
        response = self.client.get(reverse("book_detail", args=[self.book.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.book.title)
        self.assertContains(response, "相手に連絡する")

    def test_search_page_links_to_book_detail(self):
        response = self.client.get(reverse("search"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("book_detail", args=[self.book.id]))
