
import json
import logging

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Case, IntegerField, Value, When
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from .helpers import max_columns_for_user
from frontend.models import Board, Card, Column, Swimlane, UserProfile

logger = logging.getLogger(__name__)


@login_required
@require_POST
def add_column(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    board_id = data.get('board_id')
    name = data.get('name', '').strip()

    if not board_id or not name:
        return HttpResponseBadRequest("Board ID and name are required")

    if len(name) > 50:
        return HttpResponseBadRequest("Column name must be 50 characters or fewer")

    board = get_object_or_404(Board, pk=board_id, owner=request.user)

    try:
        with transaction.atomic():
            UserProfile.objects.select_for_update().get(user=request.user)

            current_column_count = board.columns.count()
            max_allowed = max_columns_for_user(request.user)

            if current_column_count >= max_allowed:
                return JsonResponse(
                    {"status": "error", "message": f"Maximum of {max_allowed} columns allowed on your plan."},
                    status=400,
                )

            column = Column.objects.create(
                board=board,
                name=name,
                position=current_column_count,
            )
    except Exception:
        logger.exception("Error creating column on board %s for user %s", board_id, request.user.pk)
        return JsonResponse({"status": "error", "message": "An error occurred while creating the column."}, status=500)

    return JsonResponse({
        "status": "success",
        "column": {
            "id":       column.id,
            "name":     column.name,
            "position": column.position,
            "board_id": column.board_id,  # avoids an extra board query
        },
    })


@login_required
@require_POST
def update_column_name(request, column_id):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    name = data.get('name', '').strip()

    if not name:
        return HttpResponseBadRequest("Column name is required")

    if len(name) > 50:
        return HttpResponseBadRequest("Column name must be 50 characters or fewer")

    try:
        column = get_object_or_404(Column, pk=column_id, board__owner=request.user)
        column.name = name
        column.save(update_fields=['name'])
    except Exception:
        logger.exception("Error updating column %s", column_id)
        return HttpResponseBadRequest("An error occurred while updating the column name")

    return JsonResponse({"status": "success", "name": column.name})


@login_required
@require_POST
def delete_column(request, column_id):
    column = get_object_or_404(Column, pk=column_id, board__owner=request.user)

    if Column.objects.filter(board_id=column.board_id).count() <= 1:
        return HttpResponseBadRequest("Cannot delete the last column on a board")

    try:
        column.cards.all().delete()
        column.delete()
    except Exception:
        logger.exception("Error deleting column %s", column_id)
        return JsonResponse({"status": "error", "message": "An error occurred while deleting the column."}, status=500)

    return JsonResponse({"status": "success", "message": "Column deleted successfully"})


@login_required
@require_POST
def save_column_sort_order(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    column_id   = data.get('column_id')
    card_orders = data.get('card_orders')

    if not column_id or card_orders is None:
        return HttpResponseBadRequest("Column ID and card orders are required")

    try:
        card_ids = [int(cid) for cid in card_orders]
    except (ValueError, TypeError):
        return HttpResponseBadRequest("card_orders must be a list of integer card IDs")

    column = get_object_or_404(Column, pk=column_id, board__owner=request.user)

    try:
        Card.objects.filter(id__in=card_ids, column=column).update(
            position=Case(
                *[When(id=cid, then=Value(i)) for i, cid in enumerate(card_ids)],
                output_field=IntegerField(),
            )
        )
    except Exception:
        logger.exception("Error saving sort order for column %s", column_id)
        return JsonResponse({"status": "error", "message": "An error occurred while saving the sort order."}, status=500)

    return JsonResponse({
        "status": "success",
        "message": f"Updated positions for {len(card_ids)} cards",
    })


@login_required
@require_POST
def update_card_position_manual(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    card_id         = data.get('card_id')
    new_pos         = data.get('position')
    new_col_id      = data.get('column')
    new_swimlane_id = data.get('swimlane_id')

    if card_id is None or new_pos is None or new_col_id is None:
        return HttpResponseBadRequest("Missing required parameters")

    try:
        card = get_object_or_404(
            Card.objects.select_related('column'),
            pk=card_id,
            column__board__owner=request.user,
        )
        board = card.column.board
        new_column = get_object_or_404(Column, pk=int(new_col_id), board=board)

        card.column   = new_column
        card.position = int(new_pos)

        update_fields = ['column', 'position']

        if new_swimlane_id not in (None, ''):
            swimlane = get_object_or_404(Swimlane, pk=int(new_swimlane_id), board=board)
            card.swimlane = swimlane
            update_fields.append('swimlane')

        card.save(update_fields=update_fields)

    except Exception:
        logger.exception("Error updating card position for card %s", card_id)
        return HttpResponseBadRequest("An error occurred while updating the card position")

    return JsonResponse({
        "status": "success",
        "card": {
            "id":       card.id,
            "column":   card.column_id,
            "position": card.position,
            "title":    card.title,
        },
        "cleared_sorting": True,
    })
