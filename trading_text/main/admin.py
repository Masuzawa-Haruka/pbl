from django.contrib import admin
from .models import Book, ChatMessage, Favorite, Profile, Transaction


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "author", "price", "category", "campus", "status", "likes_count", "created_at")
    list_filter = ("category", "campus", "condition", "status")
    search_fields = ("title", "author")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "department", "year", "trust_score")
    search_fields = ("display_name", "user__email")


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "book", "created_at")
    search_fields = ("user__email", "book__title")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("book", "seller", "buyer", "status", "scheduled_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("book__title", "seller__email", "buyer__email")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("transaction", "sender", "created_at")
    search_fields = ("body", "sender__email", "transaction__book__title")
