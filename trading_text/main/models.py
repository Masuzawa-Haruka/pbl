from django.db import models
from django.conf import settings
from django.db.models import Q


class Book(models.Model):
    CATEGORY_CHOICES = [
        ("general", "教養・基礎"),
        ("specialized", "専門"),
        ("science", "理系"),
        ("humanities", "文系"),
    ]

    CAMPUS_CHOICES = [
        ("toyonaka", "豊中キャンパス"),
        ("suita", "吹田キャンパス"),
        ("minoh", "箕面キャンパス"),
    ]

    CONDITION_CHOICES = [
        ("good", "良い"),
        ("normal", "普通"),
        ("used", "使用感あり"),
    ]

    COVER_CHOICES = [
        ("blue", "ブルー"),
        ("green", "グリーン"),
        ("red", "レッド"),
        ("purple", "パープル"),
    ]

    STATUS_CHOICES = [
        ("available", "公開中"),
        ("matching", "マッチング中"),
        ("completed", "完了"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="books",
        blank=True,
        null=True,
    )
    title = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    price = models.PositiveIntegerField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    campus = models.CharField(max_length=20, choices=CAMPUS_CHOICES)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default="good")
    likes_count = models.PositiveIntegerField(default=0)
    cover_theme = models.CharField(max_length=20, choices=COVER_CHOICES, default="blue")
    description = models.TextField(blank=True, null=True, verbose_name="説明文")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="available")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=80)
    department = models.CharField(max_length=120, blank=True)
    year = models.PositiveSmallIntegerField(blank=True, null=True)
    trust_score = models.PositiveSmallIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "book"], name="unique_user_book_favorite"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} -> {self.book}"


class Transaction(models.Model):
    STATUS_CHOICES = [
        ("open", "進行中"),
        ("scheduled", "確定"),
        ("cancelled", "中止"),
        ("completed", "完了"),
    ]

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="transactions")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="selling_transactions")
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="buying_transactions")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    meeting_place = models.CharField(max_length=120, blank=True)
    scheduled_at = models.DateTimeField(blank=True, null=True)
    seller_completed = models.BooleanField(default=False)
    buyer_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(seller=models.F("buyer")),
                name="transaction_seller_and_buyer_are_different",
            ),
        ]

    def __str__(self):
        return f"{self.book} / {self.buyer}"

    def participant_display(self, user):
        other = self.seller if user == self.buyer else self.buyer
        return getattr(getattr(other, "profile", None), "display_name", other.get_username())


class ChatMessage(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_messages")
    body = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.body[:40]
