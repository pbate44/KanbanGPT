from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0015_card_ai_context_card_ai_context_updated_at'),
    ]

    operations = [
        migrations.RemoveField(model_name='userprofile', name='ai_provider'),
        migrations.RemoveField(model_name='userprofile', name='ai_api_key_encrypted'),
        migrations.RemoveField(model_name='userprofile', name='ai_configured'),
        migrations.AlterField(
            model_name='userprofile',
            name='ai_model',
            field=models.CharField(max_length=150, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='ai_questions_today',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='ai_questions_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='ai_tokens_today',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='ai_tokens_this_month',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='ai_tokens_month',
            field=models.DateField(null=True, blank=True),
        ),
    ]
