from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.validators import FileExtensionValidator
from django.db import migrations, models
import django.db.models.deletion


def seed_users_and_profiles(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Book = apps.get_model("main", "Book")
    UserProfile = apps.get_model("main", "UserProfile")

    seller, _ = User.objects.get_or_create(
        username="seller@ecs.osaka-u.ac.jp",
        defaults={
            "email": "seller@ecs.osaka-u.ac.jp",
            "password": make_password("password12345"),
            "is_active": True,
            "first_name": "大阪",
            "last_name": "太郎",
        },
    )
    seller.password = make_password("password12345")
    seller.email = "seller@ecs.osaka-u.ac.jp"
    seller.is_active = True
    seller.save()

    buyer, _ = User.objects.get_or_create(
        username="buyer@ecs.osaka-u.ac.jp",
        defaults={
            "email": "buyer@ecs.osaka-u.ac.jp",
            "password": make_password("password12345"),
            "is_active": True,
            "first_name": "大阪",
            "last_name": "花子",
        },
    )
    buyer.password = make_password("password12345")
    buyer.email = "buyer@ecs.osaka-u.ac.jp"
    buyer.is_active = True
    buyer.save()

    UserProfile.objects.get_or_create(
        user=seller,
        defaults={
            "display_name": "大阪 太郎",
            "university": "大阪大学",
            "faculty": "工学部 電子情報工学科",
            "school_year": "2年",
        },
    )
    UserProfile.objects.get_or_create(
        user=buyer,
        defaults={
            "display_name": "大阪 花子",
            "university": "大阪大学",
            "faculty": "基礎工学部 情報科学科",
            "school_year": "1年",
        },
    )

    for user in User.objects.all():
        UserProfile.objects.get_or_create(user=user)

    Book.objects.filter(seller__isnull=True).update(seller=seller)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("main", "0002_book_description"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("display_name", models.CharField(default="大阪 太郎", max_length=80)),
                ("university", models.CharField(default="大阪大学", max_length=80)),
                ("faculty", models.CharField(default="工学部 電子情報工学科", max_length=120)),
                ("school_year", models.CharField(default="2年", max_length=20)),
                ("rating", models.DecimalField(decimal_places=1, default=4.8, max_digits=2)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name="book",
            name="buyer",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="buying_books", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="book",
            name="image",
            field=models.FileField(blank=True, null=True, upload_to="book_images/", validators=[FileExtensionValidator(["jpg", "jpeg", "png", "gif", "webp"])]),
        ),
        migrations.AddField(
            model_name="book",
            name="seller",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="selling_books", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="book",
            name="status",
            field=models.CharField(choices=[("available", "出品中"), ("in_progress", "取引中"), ("sold", "売却済み")], default="available", max_length=20),
        ),
        migrations.CreateModel(
            name="Favorite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("book", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="favorites", to="main.book")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="favorites", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("user", "book")},
            },
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("book", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="main.book")),
                ("receiver", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="received_messages", to=settings.AUTH_USER_MODEL)),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sent_messages", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
        migrations.RunPython(seed_users_and_profiles, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="book",
            name="seller",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="selling_books", to=settings.AUTH_USER_MODEL),
        ),
    ]
