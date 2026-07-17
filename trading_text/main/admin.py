from django.contrib import admin
from .models import Book, CancellationLog, Evaluation, Favorite, HandoffProposal, Message, TradeOffer, UserProfile


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "seller", "buyer", "price", "category", "campus", "status", "likes_count", "created_at")
    list_filter = ("category", "campus", "condition", "status")
    search_fields = ("title", "author", "seller__username", "buyer__username")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "university", "faculty", "school_year", "credit_score", "rating")
    search_fields = ("display_name", "user__username", "faculty")


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "book", "created_at")
    search_fields = ("user__username", "book__title")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("book", "sender", "receiver", "created_at")
    search_fields = ("book__title", "sender__username", "receiver__username", "content")


@admin.register(TradeOffer)
class TradeOfferAdmin(admin.ModelAdmin):
    list_display = ("book", "seller", "buyer", "price", "status", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("book__title", "seller__username", "buyer__username")


@admin.register(HandoffProposal)
class HandoffProposalAdmin(admin.ModelAdmin):
    list_display = ("trade_offer", "handoff_at", "location", "status", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("trade_offer__book__title", "location")


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ("book", "evaluator", "target", "evaluation_type", "score_change", "is_applied", "created_at")
    list_filter = ("evaluation_type", "is_applied")
    search_fields = ("book__title", "evaluator__username", "target__username")


@admin.register(CancellationLog)
class CancellationLogAdmin(admin.ModelAdmin):
    list_display = ("book", "reporter", "target", "kind", "score_change", "created_at")
    list_filter = ("kind",)
    search_fields = ("book__title", "reporter__username", "target__username")
