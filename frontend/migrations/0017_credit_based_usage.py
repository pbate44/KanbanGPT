from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0016_openrouter_ai_usage'),
    ]

    operations = [
        migrations.RemoveField(model_name='userprofile', name='ai_tokens_this_month'),
        migrations.RemoveField(model_name='userprofile', name='ai_tokens_month'),
        migrations.AddField(
            model_name='userprofile',
            name='ai_credits_used_this_month',
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='ai_credits_month',
            field=models.DateField(null=True, blank=True),
        ),
    ]
