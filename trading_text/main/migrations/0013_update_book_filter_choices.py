from django.db import migrations, models


def update_legacy_book_choices(apps, schema_editor):
    Book = apps.get_model("main", "Book")
    Book.objects.filter(category__in=["science", "humanities"]).update(category="specialized")
    Book.objects.filter(condition="good").update(condition="no_writing")
    Book.objects.filter(condition="normal").update(condition="used")


def restore_legacy_book_choices(apps, schema_editor):
    Book = apps.get_model("main", "Book")
    Book.objects.filter(condition="like_new").update(condition="good")
    Book.objects.filter(condition__in=["no_writing", "writing"]).update(condition="normal")


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0012_alter_book_status"),
    ]

    operations = [
        migrations.RunPython(update_legacy_book_choices, restore_legacy_book_choices),
        migrations.AlterField(
            model_name="book",
            name="category",
            field=models.CharField(
                choices=[("general", "基盤教養"), ("specialized", "専門")],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="book",
            name="condition",
            field=models.CharField(
                choices=[
                    ("like_new", "新品同様"),
                    ("no_writing", "書き込みなし"),
                    ("writing", "書き込みあり"),
                    ("used", "使用感あり"),
                ],
                default="like_new",
                max_length=20,
            ),
        ),
    ]
