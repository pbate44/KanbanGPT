
import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from frontend.models import Card, Subtask

logger = logging.getLogger(__name__)


@login_required
@require_GET
def list_subtasks(request, card_id):
    card = get_object_or_404(Card, pk=card_id, column__board__owner=request.user)
    subtasks = card.subtasks.order_by('is_complete', 'created_at')
    data = [
        {
            'id':          s.id,
            'title':       s.title,
            'is_complete': s.is_complete,
        }
        for s in subtasks
    ]
    return JsonResponse({'status': 'success', 'subtasks': data})


@login_required
@require_POST
def add_subtask(request, card_id):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    title = data.get('title', '').strip()

    if not title:
        return JsonResponse({'status': 'error', 'message': 'Title is required'}, status=400)

    if len(title) > 100:
        return JsonResponse({'status': 'error', 'message': 'Title must be 100 characters or fewer'}, status=400)

    card = get_object_or_404(Card, pk=card_id, column__board__owner=request.user)

    try:
        subtask = Subtask.objects.create(card=card, title=title)
    except Exception:
        logger.exception("Error creating subtask for card %s", card_id)
        return JsonResponse({'status': 'error', 'message': 'An error occurred while creating the subtask.'}, status=500)

    return JsonResponse({
        'status': 'success',
        'subtask': {
            'id':          subtask.id,
            'title':       subtask.title,
            'is_complete': subtask.is_complete,
        },
    })


@login_required
@require_POST
def toggle_subtask(request, subtask_id):
    subtask = get_object_or_404(
        Subtask, pk=subtask_id, card__column__board__owner=request.user
    )

    try:
        subtask.is_complete = not subtask.is_complete
        subtask.save(update_fields=['is_complete'])
    except Exception:
        logger.exception("Error toggling subtask %s", subtask_id)
        return JsonResponse({'status': 'error', 'message': 'An error occurred while updating the subtask.'}, status=500)

    return JsonResponse({
        'status': 'success',
        'subtask': {
            'id':          subtask.id,
            'is_complete': subtask.is_complete,
        },
    })


@login_required
@require_POST
def update_subtask(request, subtask_id):
    subtask = get_object_or_404(
        Subtask, pk=subtask_id, card__column__board__owner=request.user
    )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    title = data.get('title', '').strip()

    if not title:
        return JsonResponse({'status': 'error', 'message': 'Title is required'}, status=400)

    if len(title) > 100:
        return JsonResponse({'status': 'error', 'message': 'Title must be 100 characters or fewer'}, status=400)

    try:
        subtask.title = title
        subtask.save(update_fields=['title'])
    except Exception:
        logger.exception("Error updating subtask %s", subtask_id)
        return JsonResponse({'status': 'error', 'message': 'An error occurred while updating the subtask.'}, status=500)

    return JsonResponse({
        'status': 'success',
        'subtask': {'id': subtask.id, 'title': subtask.title},
    })


@login_required
@require_POST
def delete_subtask(request, subtask_id):
    subtask = get_object_or_404(
        Subtask, pk=subtask_id, card__column__board__owner=request.user
    )

    try:
        subtask.delete()
    except Exception:
        logger.exception("Error deleting subtask %s", subtask_id)
        return JsonResponse({'status': 'error', 'message': 'An error occurred while deleting the subtask.'}, status=500)

    return JsonResponse({'status': 'success'})
