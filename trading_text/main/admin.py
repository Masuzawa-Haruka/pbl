from django.contrib import admin
from .models import Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "price", "category", "campus", "likes_count", "created_at")
    list_filter = ("category", "campus", "condition")
    search_fields = ("title", "author")
