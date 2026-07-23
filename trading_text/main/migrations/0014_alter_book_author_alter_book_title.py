from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0013_update_book_filter_choices"),
    ]

    operations = [
        migrations.AlterField(
            model_name="book",
            name="author",
            field=models.CharField(max_length=40),
        ),
        migrations.AlterField(
            model_name="book",
            name="title",
            field=models.CharField(max_length=60),
        ),
    ]
