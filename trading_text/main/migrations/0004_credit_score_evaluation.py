from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0003_auth_trade_features"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="credit_score",
            field=models.IntegerField(default=100),
        ),
        migrations.CreateModel(
            name="Evaluation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("evaluation_type", models.CharField(choices=[("good", "good"), ("bad", "bad")], max_length=10)),
                ("score_change", models.IntegerField()),
                ("is_applied", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("book", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="evaluations", to="main.book")),
                ("evaluator", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="submitted_evaluations", to=settings.AUTH_USER_MODEL)),
                ("target", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="received_evaluations", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("book", "evaluator", "target")},
            },
        ),
        migrations.CreateModel(
            name="CancellationLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("cancel", "予定確定後のキャンセル"), ("no_show", "ドタキャン報告")], max_length=20)),
                ("score_change", models.IntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("book", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cancellation_logs", to="main.book")),
                ("reporter", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reported_cancellations", to=settings.AUTH_USER_MODEL)),
                ("target", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="received_cancellations", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
