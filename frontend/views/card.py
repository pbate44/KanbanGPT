
import json
import logging
import re
from urllib.parse import quote

import weasyprint

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .helpers import max_cards_for_user
from frontend.forms import CardLogEntryForm
from frontend.models import (
    ActivityLog,
    AIChatMessage,
    Card,
    CardLogEntry,
    Column,
    Swimlane,
    UserProfile,
)

logger = logging.getLogger(__name__)

_VALID_COLOR_RE = re.compile(
    r'^(#[0-9a-fA-F]{3,6}|rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\))$'
)

@login_required
@require_POST
def add_card(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    column_id   = data.get('column_id')
    title       = data.get('title', '').strip()
    description = data.get('description', '')
    swimlane_id = data.get('swimlane_id')
    color       = data.get('color', '').strip()
    priority    = data.get('priority', 0)

    if not column_id or not title:
        return JsonResponse({"status": "error", "message": "Column ID and title are required"}, status=400)

    if len(title) > 100:
        return JsonResponse({"status": "error", "message": "Title must be 100 characters or fewer"}, status=400)

    if color and not _VALID_COLOR_RE.match(color):
        return JsonResponse({"status": "error", "message": "Invalid color format."}, status=400)

    try:
        priority = int(priority)
        if not (0 <= priority <= 10):
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse({"status": "error", "message": "Priority must be between 0 and 10"}, status=400)

    column = get_object_or_404(Column, pk=column_id, board__owner=request.user)
    board = column.board

    try:
        with transaction.atomic():
            UserProfile.objects.select_for_update().get(user=request.user)

            current_card_count = Card.objects.filter(column__board=board).count()
            max_allowed = max_cards_for_user(request.user)

            if current_card_count >= max_allowed:
                return JsonResponse(
                    {"status": "error", "message": f"Maximum of {max_allowed} cards allowed on your plan."},
                    status=400,
                )

            position = column.cards.count()

            if swimlane_id:
                swimlane = get_object_or_404(Swimlane, pk=swimlane_id, board=board)
            else:
                swimlane = board.swimlanes.first()
                if not swimlane:
                    swimlane = Swimlane.objects.create(board=board, name="Default", position=0)

            create_kwargs = dict(
                column=column,
                swimlane=swimlane,
                title=title,
                description=description,
                position=position,
                priority=priority,
            )
            if color:
                create_kwargs['color'] = color
                css_class = Card.determine_css_class_from_color(color)
                if css_class:
                    create_kwargs['css_class'] = css_class

            card = Card.objects.create(**create_kwargs)

            AIChatMessage.objects.create(
                card=card,
                role='system',
                content="Hello! I'm your AI assistant. I can help answer questions about this card. How can I help you today?",
            )

    except Exception:
        logger.exception("Error creating card for user %s", request.user.pk)
        return JsonResponse({"status": "error", "message": "An error occurred while creating the card."}, status=500)

    return JsonResponse({
        "status": "success",
        "card": {
            "id":          card.id,
            "title":       card.title,
            "description": card.description,
            "position":    card.position,
            "priority":    card.priority,
            "color":       card.color,
            "css_class":   card.css_class,
            "column_id":   card.column_id,
            "swimlane_id": card.swimlane_id,
        },
    })


@login_required
@require_http_methods(["GET", "POST"])
def card_detail(request, card_id):
    card = get_object_or_404(Card, pk=card_id, column__board__owner=request.user)
    log_entries = card.log_entries.order_by('-created_at')

    if request.method == 'POST':
        form = CardLogEntryForm(request.POST)

        if form.is_valid():
            entry = form.save(commit=False)
            entry.card = card
            entry.source = 'manual'
            entry.save()

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'ok',
                    'entry': {
                        'id': entry.id,
                        'text': entry.text,
                        'source': entry.get_source_display(),
                        'created_at': entry.created_at.strftime('%Y-%m-%d %H:%M'),
                    },
                })

            return redirect('card_detail', card_id=card.id)
    else:
        form = CardLogEntryForm()

    subtasks = card.subtasks.order_by('is_complete', 'created_at')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        profile    = request.user.profile
        ai_model_display = profile.ai_model or "Claude Haiku 4.5"

        return render(request, 'card_detail_content.html', {
            'card':                 card,
            'log_entries':          log_entries,
            'form':                 form,
            'subtasks':             subtasks,
            'ai_model_display':     ai_model_display,
            'ai_chat_always_open':  profile.ai_chat_always_open,
        })

    return render(request, 'card_detail.html', {
        'card': card,
        'log_entries': log_entries,
        'form': form,
        'subtasks': subtasks,
    })


@login_required
@require_POST
def update_card_position(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    card_id     = data.get('card_id')
    new_pos     = data.get('position')
    new_col_id  = data.get('column')
    new_lane_id = data.get('swimlane') or data.get('swimlane_id')

    if card_id is None or new_pos is None or new_col_id is None:
        return JsonResponse({"status": "error", "message": "Missing card_id, position or column"}, status=400)

    try:
        card = get_object_or_404(
            Card.objects.select_related('column'),
            pk=card_id,
            column__board__owner=request.user,
        )
        new_column = get_object_or_404(Column, pk=int(new_col_id), board=card.column.board)

        card.column   = new_column
        card.position = int(new_pos)
        if new_lane_id is not None:
            card.swimlane_id = int(new_lane_id)

        update_fields = ['column', 'position']
        if new_lane_id is not None:
            update_fields.append('swimlane')
        card.save(update_fields=update_fields)

    except Exception:
        logger.exception("Error updating position for card %s", card_id)
        return JsonResponse({"status": "error", "message": "An error occurred while updating the card position."}, status=400)

    return JsonResponse({
        "status": "success",
        "card": {
            "id":       card.id,
            "column":   card.column_id,
            "swimlane": card.swimlane_id,
            "position": card.position,
            "title":    card.title,
        },
    })


@login_required
@require_POST
def delete_card(request, card_id):
    try:
        card = get_object_or_404(Card, pk=card_id, column__board__owner=request.user)
        card.delete()
    except Exception:
        logger.exception("Error deleting card %s", card_id)
        return JsonResponse({"status": "error", "message": "An error occurred while deleting the card."}, status=500)

    return JsonResponse({"status": "success"})


@login_required
@require_POST
def update_card_description(request, card_id):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    description = data.get('description', '')
    title = data.get('title', None)

    if title is not None:
        if not title.strip():
            return JsonResponse({"status": "error", "message": "Title cannot be empty"}, status=400)
        if len(title) > 100:
            return JsonResponse({"status": "error", "message": "Title must be 100 characters or fewer"}, status=400)

    if len(description) > 16000:
        return JsonResponse({"status": "error", "message": "Description must be 16,000 characters or fewer"}, status=400)

    try:
        card = get_object_or_404(Card, pk=card_id, column__board__owner=request.user)

        update_fields = ['description']
        card.description = description

        if title is not None:
            card.title = title
            update_fields.append('title')

        card.save(update_fields=update_fields)

    except Exception:
        logger.exception("Error updating card %s", card_id)
        return JsonResponse({"status": "error", "message": "An error occurred while updating the card."}, status=500)

    return JsonResponse({
        "status": "success",
        "description": card.description,
        "title": card.title,
    })


@login_required
@require_POST
def update_card_priority(request, card_id):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    priority = data.get('priority')

    if priority is None:
        return JsonResponse({"status": "error", "message": "Priority value is required"}, status=400)

    if not (0 <= priority <= 10):
        return JsonResponse({"status": "error", "message": "Priority must be between 0 and 10"}, status=400)

    try:
        card = get_object_or_404(Card, pk=card_id, column__board__owner=request.user)
        card.priority = priority
        card.save(update_fields=['priority'])
    except Exception:
        logger.exception("Error updating priority for card %s", card_id)
        return JsonResponse({"status": "error", "message": "An error occurred while updating the card priority."}, status=500)

    return JsonResponse({"status": "success", "priority": card.priority})


@login_required
@require_POST
def update_card_color(request, card_id):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    color = data.get('color', '').strip()

    if not color:
        return JsonResponse({"status": "error", "message": "Card color is required"}, status=400)

    if not _VALID_COLOR_RE.match(color):
        return JsonResponse({"status": "error", "message": "Invalid color format."}, status=400)

    css_class = Card.determine_css_class_from_color(color)

    try:
        card = get_object_or_404(Card, pk=card_id, column__board__owner=request.user)
        card.color = color
        card.css_class = css_class
        card.save(update_fields=['color', 'css_class'])
    except Exception:
        logger.exception("Error updating color for card %s", card_id)
        return JsonResponse({"status": "error", "message": "An error occurred while updating the card color."}, status=500)

    return JsonResponse({
        "status": "success",
        "color": card.color,
        "css_class": card.css_class,
    })


@login_required
@require_POST
def delete_log_entry(request, entry_id):
    try:
        entry = CardLogEntry.objects.get(id=entry_id, card__column__board__owner=request.user)
        entry.delete()
    except CardLogEntry.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Log entry not found'}, status=404)
    except Exception:
        logger.exception("Error deleting log entry %s", entry_id)
        return JsonResponse({'status': 'error', 'message': 'An error occurred while deleting the log entry.'}, status=500)

    return JsonResponse({'status': 'ok', 'message': 'Log entry deleted successfully'})


@login_required
@require_POST
def update_log_entry(request, entry_id):
    try:
        entry = CardLogEntry.objects.get(id=entry_id, card__column__board__owner=request.user)
    except CardLogEntry.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Log entry not found'}, status=404)

    try:
        data = json.loads(request.body)
        text = data.get('text', '').strip()
    except (json.JSONDecodeError, AttributeError):
        text = request.POST.get('text', '').strip()

    if not text:
        return JsonResponse({'status': 'error', 'message': 'Text cannot be empty'}, status=400)

    entry.text = text
    entry.save()
    return JsonResponse({'status': 'ok', 'text': entry.text})


@login_required
@require_POST
def update_card_swimlane(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    card_id     = data.get('card_id')
    swimlane_id = data.get('swimlane_id')

    if not card_id or swimlane_id is None:
        return JsonResponse({"status": "error", "message": "Card ID and swimlane ID are required"}, status=400)

    try:
        card = get_object_or_404(
            Card.objects.select_related('column'),
            pk=card_id,
            column__board__owner=request.user,
        )
        swimlane = get_object_or_404(Swimlane, pk=swimlane_id, board=card.column.board)

        card.swimlane = swimlane
        card.save(update_fields=['swimlane'])

    except Exception:
        logger.exception("Error updating swimlane for card %s", card_id)
        return JsonResponse({"status": "error", "message": "An error occurred while updating the card swimlane."}, status=500)

    return JsonResponse({
        "status": "success",
        "card": {"id": card.id, "swimlane_id": card.swimlane_id},
    })


@login_required
@require_POST
def move_card_api(request, card_id):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    column_id   = data.get('column_id')
    swimlane_id = data.get('swimlane_id')

    if not column_id or not swimlane_id:
        return JsonResponse({"status": "error", "message": "Column ID and swimlane ID are required"}, status=400)

    try:
        card = get_object_or_404(
            Card.objects.select_related('column'),
            pk=card_id,
            column__board__owner=request.user,
        )
        board = card.column.board
        column   = get_object_or_404(Column,   pk=column_id,   board=board)
        swimlane = get_object_or_404(Swimlane,  pk=swimlane_id, board=board)

        old_column = card.column
        card.column   = column
        card.swimlane = swimlane
        card.save(update_fields=['column', 'swimlane'])

        ActivityLog.objects.create(
            content_type=ContentType.objects.get_for_model(card),
            object_id=card.id,
            action_type="moved",
            message=f"Moved from {old_column.name} to {column.name}",
            user=request.user,
        )

    except Exception:
        logger.exception("Error moving card %s", card_id)
        return JsonResponse({'status': 'error', 'message': 'An error occurred while moving the card.'}, status=500)

    return JsonResponse({
        'status': 'success',
        'card': {
            'id':          card.id,
            'column_id':   card.column_id,
            'swimlane_id': card.swimlane_id,
        },
    })


@login_required
def export_card_log_pdf(request, card_id):
    card = get_object_or_404(Card, id=card_id, column__board__owner=request.user)
    log_entries = card.log_entries.all().order_by('-created_at')
    html_string = render_to_string('pdf_template.html', {
        'card': card,
        'log_entries': log_entries,
        'now': timezone.now(),
    })
    filename = quote(f"{card.title}_log.pdf")
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f"attachment; filename*=UTF-8''{filename}"
    pdf_file = weasyprint.HTML(string=html_string).write_pdf()
    response.write(pdf_file)
    return response
