from django.db import migrations, models


def create_sample_books(apps, schema_editor):
    Book = apps.get_model("main", "Book")
    books = [
        {
            "title": "基礎からの線形代数",
            "author": "石村園子",
            "price": 300,
            "category": "general",
            "campus": "toyonaka",
            "condition": "good",
            "likes_count": 12,
            "cover_theme": "blue",
        },
        {
            "title": "ミクロ経済学の基礎",
            "author": "大山道広",
            "price": 400,
            "category": "general",
            "campus": "suita",
            "condition": "good",
            "likes_count": 8,
            "cover_theme": "green",
        },
        {
            "title": "化学の新研究",
            "author": "卯田正彦",
            "price": 350,
            "category": "science",
            "campus": "toyonaka",
            "condition": "normal",
            "likes_count": 5,
            "cover_theme": "red",
        },
        {
            "title": "物理学のエッセンス",
            "author": "浜島清利",
            "price": 300,
            "category": "science",
            "campus": "minoh",
            "condition": "used",
            "likes_count": 3,
            "cover_theme": "purple",
        },
    ]
    for book in books:
        Book.objects.get_or_create(
            title=book["title"],
            author=book["author"],
            defaults=book,
        )


def delete_sample_books(apps, schema_editor):
    Book = apps.get_model("main", "Book")
    Book.objects.filter(
        title__in=[
            "基礎からの線形代数",
            "ミクロ経済学の基礎",
            "化学の新研究",
            "物理学のエッセンス",
        ]
    ).delete()


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Book",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=100)),
                ("author", models.CharField(max_length=100)),
                ("price", models.PositiveIntegerField()),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("general", "教養・基礎"),
                            ("specialized", "専門"),
                            ("science", "理系"),
                            ("humanities", "文系"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "campus",
                    models.CharField(
                        choices=[
                            ("toyonaka", "豊中キャンパス"),
                            ("suita", "吹田キャンパス"),
                            ("minoh", "箕面キャンパス"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "condition",
                    models.CharField(
                        choices=[
                            ("good", "良い"),
                            ("normal", "普通"),
                            ("used", "使用感あり"),
                        ],
                        default="good",
                        max_length=20,
                    ),
                ),
                ("likes_count", models.PositiveIntegerField(default=0)),
                (
                    "cover_theme",
                    models.CharField(
                        choices=[
                            ("blue", "ブルー"),
                            ("green", "グリーン"),
                            ("red", "レッド"),
                            ("purple", "パープル"),
                        ],
                        default="blue",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.RunPython(create_sample_books, delete_sample_books),
    ]
