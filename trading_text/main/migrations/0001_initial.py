from django.db import migrations, models


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
    ]
