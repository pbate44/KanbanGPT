
import json

from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from frontend.models import Card, AIChatMessage, AIChatSession
from frontend.services.ai_service import CardAIAssistant

WELCOME_MESSAGE = "Hello! I'm your AI assistant. I can help answer questions about this card. How can I help you today?"


def _get_or_create_active_session(card, session_id=None):
    """Return the requested session (if valid), the most recent session, or a brand-new one."""
    if session_id:
        session = AIChatSession.objects.filter(pk=session_id, card=card).first()
        if session:
            return session
    session = AIChatSession.objects.filter(card=card).order_by('-updated_at').first()
    if not session:
        session = AIChatSession.objects.create(card=card)
        AIChatMessage.objects.create(card=card, session=session, role='system', content=WELCOME_MESSAGE)
    return session


@require_POST
@login_required
def card_ai_chat(request, card_id):
    card = get_object_or_404(Card, pk=card_id)
    try:
        data = json.loads(request.body or "{}")
        question      = data.get('question', '').strip()
        session_id    = data.get('session_id')
        web_search    = bool(data.get('web_search', False))
        attachment_ids = data.get('attachment_ids') or []

        if not question:
            return JsonResponse({'error': 'No question provided'}, status=400)

        session = _get_or_create_active_session(card, session_id)

        AIChatMessage.objects.create(card=card, session=session, role='user', content=question)
        ai_assistant = CardAIAssistant()
        response = ai_assistant.ask_question(card_id, question, user_profile=request.user.profile, session_id=session.id, web_search=web_search, attachment_ids=attachment_ids)
        AIChatMessage.objects.create(card=card, session=session, role='assistant', content=response)

        AIChatSession.objects.filter(pk=session.id).update(updated_at=timezone.now())

        return JsonResponse({'status': 'success', 'response': response, 'session_id': session.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def card_ai_history(request, card_id):
    try:
        session_id = request.GET.get('session_id')
        if session_id:
            messages = AIChatMessage.objects.filter(session_id=session_id, card_id=card_id).order_by('created_at')
        else:
            session = AIChatSession.objects.filter(card_id=card_id).order_by('-updated_at').first()
            messages = AIChatMessage.objects.filter(session=session).order_by('created_at') if session else AIChatMessage.objects.none()

        return JsonResponse({
            'status': 'success',
            'messages': [
                {
                    'role': msg.role,
                    'content': msg.content,
                    'created_at': msg.created_at.isoformat()
                } for msg in messages
            ]
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def list_chat_sessions(request, card_id):
    try:
        sessions = AIChatSession.objects.filter(card_id=card_id).order_by('-updated_at')
        result = []
        for s in sessions:
            msg_count = s.messages.filter(role__in=['user', 'assistant']).count()
            result.append({
                'id': s.id,
                'title': s.title,
                'created_at': s.created_at.isoformat(),
                'updated_at': s.updated_at.isoformat(),
                'message_count': msg_count,
            })
        return JsonResponse({'status': 'success', 'sessions': result})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@login_required
def new_chat_session(request, card_id):
    try:
        card = get_object_or_404(Card, pk=card_id)
        session = AIChatSession.objects.create(card=card)
        AIChatMessage.objects.create(card=card, session=session, role='system', content=WELCOME_MESSAGE)
        return JsonResponse({
            'status': 'success',
            'session': {
                'id': session.id,
                'title': session.title,
                'created_at': session.created_at.isoformat(),
                'message_count': 0,
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@login_required
def delete_chat_session(request, card_id, session_id):
    session = get_object_or_404(AIChatSession, pk=session_id, card_id=card_id)
    try:
        session.delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@login_required
def clear_chat_history(request, card_id):
    try:
        card = get_object_or_404(Card, pk=card_id)
        session = AIChatSession.objects.create(card=card)
        AIChatMessage.objects.create(card=card, session=session, role='system', content=WELCOME_MESSAGE)
        return JsonResponse({
            'status': 'success',
            'session_id': session.id,
            'message': 'New chat session started'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
