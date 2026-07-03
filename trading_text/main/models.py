from django.db import models


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

    title = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    price = models.PositiveIntegerField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    campus = models.CharField(max_length=20, choices=CAMPUS_CHOICES)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default="good")
    likes_count = models.PositiveIntegerField(default=0)
    cover_theme = models.CharField(max_length=20, choices=COVER_CHOICES, default="blue")
    description = models.TextField(blank=True, null=True, verbose_name="説明文")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
