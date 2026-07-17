from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import migrations, models
import django.db.models.deletion


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
                ("display_name", models.CharField(blank=True, default="", max_length=80)),
                ("university", models.CharField(blank=True, default="", max_length=80)),
                ("faculty", models.CharField(blank=True, default="", max_length=120)),
                ("school_year", models.CharField(blank=True, default="", max_length=20)),
                ("rating", models.DecimalField(decimal_places=1, default=0, max_digits=2)),
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
        migrations.AlterField(
            model_name="book",
            name="seller",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="selling_books", to=settings.AUTH_USER_MODEL),
        ),
    ]
