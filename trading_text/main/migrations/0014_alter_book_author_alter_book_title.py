from django.db import migrations, models


def truncate_existing_book_text(apps, schema_editor):
    Book = apps.get_model("main", "Book")
    database_alias = schema_editor.connection.alias

    for book in Book.objects.using(database_alias).only("id", "title", "author").iterator():
        truncated_title = book.title[:60]
        truncated_author = book.author[:40]
        if truncated_title != book.title or truncated_author != book.author:
            Book.objects.using(database_alias).filter(pk=book.pk).update(
                title=truncated_title,
                author=truncated_author,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0013_update_book_filter_choices"),
    ]

    operations = [
        migrations.RunPython(
            truncate_existing_book_text,
            reverse_code=migrations.RunPython.noop,
        ),
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
