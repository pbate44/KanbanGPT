
import json
import logging

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from frontend.models import Board, Card, Swimlane, UserProfile
from .helpers import max_swimlanes_for_user

logger = logging.getLogger(__name__)


@login_required
@require_POST
def add_swimlane(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    board_id = data.get('board_id')
    name     = data.get('name', 'New Swimlane').strip()

    if not board_id:
        return HttpResponseBadRequest("Board ID is required")

    if len(name) > 100:
        return HttpResponseBadRequest("Swimlane name must be 100 characters or fewer")

    try:
        height = max(100, min(int(data.get('height', 300)), 2000))
    except (ValueError, TypeError):
        return HttpResponseBadRequest("Height must be a number")

    board = get_object_or_404(Board, pk=board_id, owner=request.user)

    try:
        with transaction.atomic():
            UserProfile.objects.select_for_update().get(user=request.user)

            current_count = board.swimlanes.count()
            max_allowed   = max_swimlanes_for_user(request.user)

            if current_count >= max_allowed:
                return JsonResponse({
                    "status":        "error",
                    "code":          "plan_limit_reached",
                    "message":       f"Your plan allows up to {max_allowed} swimlanes per board. Upgrade to add more.",
                    "max_allowed":   max_allowed,
                    "current_count": current_count,
                }, status=403)

            swimlane = Swimlane.objects.create(
                board=board,
                name=name,
                position=current_count,
                height=height,
            )

            if current_count == 0:
                Card.objects.filter(column__board=board).update(swimlane=swimlane)

    except Exception:
        logger.exception("Error creating swimlane on board %s for user %s", board_id, request.user.pk)
        return JsonResponse({"status": "error", "message": "An error occurred while creating the swimlane."}, status=500)

    return JsonResponse({
        "status": "success",
        "swimlane": {
            "id":       swimlane.id,
            "name":     swimlane.name,
            "position": swimlane.position,
            "height":   swimlane.height,
            "board_id": swimlane.board_id,
        },
    })


@login_required
@require_POST
def update_swimlane_name(request, swimlane_id):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    name = data.get('name', '').strip()

    if not name:
        return HttpResponseBadRequest("Swimlane name is required")

    if len(name) > 100:
        return HttpResponseBadRequest("Swimlane name must be 100 characters or fewer")

    swimlane = get_object_or_404(Swimlane, pk=swimlane_id, board__owner=request.user)

    try:
        swimlane.name = name
        swimlane.save(update_fields=['name'])
    except Exception:
        logger.exception("Error updating swimlane %s", swimlane_id)
        return JsonResponse({"status": "error", "message": "An error occurred while updating the swimlane."}, status=500)

    return JsonResponse({"status": "success", "name": swimlane.name})


@login_required
@require_POST
def delete_swimlane(request, swimlane_id):
    swimlane = get_object_or_404(Swimlane, pk=swimlane_id, board__owner=request.user)

    try:
        with transaction.atomic():
            other_swimlanes = list(swimlane.board.swimlanes.exclude(pk=swimlane.pk).order_by('position'))

            if other_swimlanes:
                target = next(
                    (s for s in reversed(other_swimlanes) if s.position < swimlane.position),
                    other_swimlanes[0],
                )
                Card.objects.filter(swimlane=swimlane).update(swimlane=target)
            else:
                Card.objects.filter(swimlane=swimlane).update(swimlane=None)

            swimlane.delete()

            for i, s in enumerate(other_swimlanes):
                s.position = i
            if other_swimlanes:
                Swimlane.objects.bulk_update(other_swimlanes, ['position'])

    except Exception:
        logger.exception("Error deleting swimlane %s", swimlane_id)
        return JsonResponse({"status": "error", "message": "An error occurred while deleting the swimlane."}, status=500)

    return JsonResponse({"status": "success"})
