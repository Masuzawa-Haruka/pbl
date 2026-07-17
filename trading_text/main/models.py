from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=80, blank=True, default="")
    university = models.CharField(max_length=80, blank=True, default="")
    faculty = models.CharField(max_length=120, blank=True, default="")
    school_year = models.CharField(max_length=20, blank=True, default="")
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    credit_score = models.IntegerField(default=100)
    supabase_user_id = models.CharField(max_length=80, blank=True, default="")

    def __str__(self):
        return self.display_name

    @property
    def credit_rank(self):
        if self.credit_score >= 150:
            return "エキスパート"
        if self.credit_score >= 120:
            return "トラスト"
        return "レギュラー"


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
        ("available", "出品中"),
        ("in_progress", "取引中"),
        ("sold", "売却済み"),
    ]

    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="selling_books")
    buyer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="buying_books",
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
    image = models.FileField(
        upload_to="book_images/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "gif", "webp"])],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def refresh_likes_count(self):
        self.likes_count = self.favorites.count()
        self.save(update_fields=["likes_count"])


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "book")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} -> {self.book.title}"


class Message(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.book.title}: {self.sender.username}"


class Evaluation(models.Model):
    TYPE_CHOICES = [
        ("good", "good"),
        ("bad", "bad"),
    ]

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="evaluations")
    evaluator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submitted_evaluations")
    target = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_evaluations")
    evaluation_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    score_change = models.IntegerField()
    is_applied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("book", "evaluator", "target")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.evaluator.username} -> {self.target.username}: {self.score_change}"


class CancellationLog(models.Model):
    KIND_CHOICES = [
        ("cancel", "予定確定後のキャンセル"),
        ("no_show", "ドタキャン報告"),
    ]

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="cancellation_logs")
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reported_cancellations")
    target = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_cancellations")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    score_change = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=("book", "reporter", "target", "kind"),
                name="unique_cancellation_report",
            )
        ]

    def __str__(self):
        return f"{self.kind}: {self.target.username} {self.score_change}"
