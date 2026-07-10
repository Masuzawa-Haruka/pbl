from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0004_credit_score_evaluation"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="supabase_user_id",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
    ]
