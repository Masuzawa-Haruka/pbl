from django.db import migrations, models


SAMPLE_TITLES = [
    "基礎からの線形代数",
    "ミクロ経済学の基礎",
    "化学の新研究",
    "物理学のエッセンス",
]
SAMPLE_USERNAMES = [
    "seller@ecs.osaka-u.ac.jp",
    "buyer@ecs.osaka-u.ac.jp",
]


def remove_sample_data(apps, schema_editor):
    Book = apps.get_model("main", "Book")
    User = apps.get_model("auth", "User")

    Book.objects.filter(title__in=SAMPLE_TITLES).delete()
    User.objects.filter(username__in=SAMPLE_USERNAMES).delete()


class Migration(migrations.Migration):
    dependencies = [("main", "0005_userprofile_supabase_user_id")]

    operations = [
        migrations.RunPython(remove_sample_data, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="userprofile",
            name="display_name",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="university",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="faculty",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="school_year",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="rating",
            field=models.DecimalField(decimal_places=1, default=0, max_digits=2),
        ),
        migrations.AddConstraint(
            model_name="cancellationlog",
            constraint=models.UniqueConstraint(
                fields=("book", "reporter", "target", "kind"),
                name="unique_cancellation_report",
            ),
        ),
    ]
