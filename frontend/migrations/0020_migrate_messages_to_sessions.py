from django.db import migrations
from django.utils import timezone


def create_sessions_for_existing_messages(apps, schema_editor):
    AIChatMessage = apps.get_model('frontend', 'AIChatMessage')
    AIChatSession = apps.get_model('frontend', 'AIChatSession')

    card_ids = AIChatMessage.objects.filter(session__isnull=True).values_list('card_id', flat=True).distinct()
    for card_id in card_ids:
        session = AIChatSession.objects.create(card_id=card_id, title='New Chat')
        AIChatMessage.objects.filter(card_id=card_id, session__isnull=True).update(session=session)


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0019_add_ai_chat_sessions'),
    ]

    operations = [
        migrations.RunPython(create_sessions_for_existing_messages, migrations.RunPython.noop),
    ]
