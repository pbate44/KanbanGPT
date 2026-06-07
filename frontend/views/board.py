
import json
import logging

from PIL import Image as PilImage

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch
from django.http import (
    HttpResponseBadRequest,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from .helpers import max_swimlanes_for_user, max_boards_for_user
from frontend.models import Board, Column, Card, Swimlane, UserProfile

logger = logging.getLogger(__name__)


def _validate_image_file(file):
    allowed_formats = {"JPEG", "PNG", "GIF", "WEBP"}
    try:
        img = PilImage.open(file)
        fmt = img.format
        img.load()
    except Exception:
        return False, "File is not a valid image."
    finally:
        file.seek(0)

    if fmt not in allowed_formats:
        return False, "Invalid image type. Please upload a JPEG, PNG, GIF, or WebP image."
    return True, None


@login_required
def board_detail(request, board_id):
    board = get_object_or_404(Board, pk=board_id, owner=request.user)
    columns = list(
        board.columns.all()
        .prefetch_related(Prefetch("cards", queryset=Card.objects.order_by("position")))
    )

    swimlanes = board.swimlanes.all()
    card_count = sum(len(col.cards.all()) for col in columns)
    max_swimlanes = max_swimlanes_for_user(request.user)

    is_premium = request.user.profile.is_premium()
    user_boards = Board.objects.filter(owner=request.user).only("id", "name").order_by("name")

    if not swimlanes.exists():
        default_swimlane = Swimlane.objects.create(
            board=board,
            name="Default",
            position=0,
            height=300,
        )
        for column in columns:
            column.cards.update(swimlane=default_swimlane)
        swimlanes = [default_swimlane]

    return render(request, "board_detail.html", {
        "board": board,
        "columns": columns,
        "swimlanes": swimlanes,
        "max_swimlanes": max_swimlanes,
        "is_premium": is_premium,
        "card_count": card_count,
        "user_boards": user_boards,
    })


@login_required
@require_POST
def create_board(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = data.get("name", "").strip()
    description = data.get("description", "").strip()

    if not name:
        return JsonResponse({"error": "Board name is required"}, status=400)

    if len(name) > 100:
        return JsonResponse({"error": "Board name must be 100 characters or fewer"}, status=400)

    try:
        with transaction.atomic():
            UserProfile.objects.select_for_update().get(user=request.user)
            current_board_count = Board.objects.filter(owner=request.user).count()
            max_allowed = max_boards_for_user(request.user)

            if current_board_count >= max_allowed:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"Maximum of {max_allowed} boards allowed on your plan.",
                    },
                    status=400,
                )

            board = Board.objects.create(
                name=name,
                description=description,
                owner=request.user,
            )

            Column.objects.bulk_create([
                Column(board=board, name="To Do", position=0),
                Column(board=board, name="In Progress", position=1),
                Column(board=board, name="Done", position=2),
            ])

            Swimlane.objects.create(board=board, name="Default", position=0, height=300)

    except Exception:
        logger.exception("Error creating board for user %s", request.user.pk)
        return JsonResponse({"error": "An error occurred while creating the board."}, status=500)

    return JsonResponse({
        "status": "success",
        "board": {
            "id": board.id,
            "name": board.name,
            "description": board.description,
            "created_at": board.created_at.isoformat(),
            "updated_at": board.updated_at.isoformat(),
            "image_url": board.image.url if board.image else None,
        },
    })


@login_required
@require_POST
def update_board(request, board_id):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = data.get("name", "").strip()
    description = data.get("description", "").strip()

    if not name:
        return JsonResponse({"error": "Board name is required"}, status=400)

    if len(name) > 100:
        return JsonResponse({"error": "Board name must be 100 characters or fewer"}, status=400)

    try:
        board = get_object_or_404(Board, pk=board_id, owner=request.user)
        board.name = name
        board.description = description
        board.save()
    except Exception:
        logger.exception("Error updating board %s for user %s", board_id, request.user.pk)
        return JsonResponse({"error": "An error occurred while updating the board."}, status=500)

    return JsonResponse({
        "status": "success",
        "board": {
            "id": board.id,
            "name": board.name,
            "description": board.description,
            "created_at": board.created_at.isoformat(),
            "updated_at": board.updated_at.isoformat(),
        },
    })


@login_required
@require_POST
def delete_board(request, board_id):
    try:
        board = get_object_or_404(Board, pk=board_id, owner=request.user)

        user_board_count = Board.objects.filter(owner=request.user).count()
        if user_board_count <= 1:
            return JsonResponse(
                {"error": "Cannot delete your last board. Create another board first."},
                status=400,
            )

        board_name = board.name
        board.delete()
    except Exception:
        logger.exception("Error deleting board %s for user %s", board_id, request.user.pk)
        return JsonResponse({"error": "An error occurred while deleting the board."}, status=500)

    return JsonResponse({
        "status": "success",
        "message": f'Board "{board_name}" deleted successfully',
    })


@login_required
@require_POST
def upload_board_image(request, board_id):
    try:
        board = get_object_or_404(Board, pk=board_id, owner=request.user)

        if "image" not in request.FILES:
            return JsonResponse({"error": "No image file provided"}, status=400)

        uploaded_file = request.FILES["image"]

        max_size = 5 * 1024 * 1024
        if uploaded_file.size > max_size:
            return JsonResponse(
                {"error": "File size too large. Maximum size is 5MB."},
                status=400,
            )

        valid, error_msg = _validate_image_file(uploaded_file)
        if not valid:
            return JsonResponse({"error": error_msg}, status=400)

        if board.image:
            board.image.delete(save=False)

        board.image = uploaded_file
        board.save()

    except Exception:
        logger.exception("Error uploading image for board %s", board_id)
        return JsonResponse({"error": "An error occurred while uploading the image."}, status=500)

    return JsonResponse({
        "status": "success",
        "image_url": board.image.url,
        "message": "Image uploaded successfully",
    })


@login_required
@require_POST
def remove_board_image(request, board_id):
    try:
        board = get_object_or_404(Board, pk=board_id, owner=request.user)

        if not board.image:
            return JsonResponse({"error": "No image to remove"}, status=400)

        # Delete from storage (works with S3 and local backends)
        board.image.delete(save=False)
        board.image = None
        board.save()

    except Exception:
        logger.exception("Error removing image for board %s", board_id)
        return JsonResponse({"error": "An error occurred while removing the image."}, status=500)

    return JsonResponse({"status": "success", "message": "Image removed successfully"})


@login_required
@require_GET
def get_board_details(request, board_id):
    try:
        board = get_object_or_404(Board, pk=board_id, owner=request.user)
    except Exception:
        logger.exception("Error fetching board %s for user %s", board_id, request.user.pk)
        return JsonResponse({"error": "An error occurred while fetching board details."}, status=500)

    return JsonResponse({
        "status": "success",
        "board": {
            "id": board.id,
            "name": board.name,
            "description": board.description,
            "image_url": board.image.url if board.image else None,
            "created_at": board.created_at.isoformat(),
            "updated_at": board.updated_at.isoformat(),
        },
    })


@login_required
@require_GET
def board_data_api(request, board_id):
    """API endpoint to fetch board data for Kanban layout."""
    try:
        board = get_object_or_404(Board, pk=board_id, owner=request.user)
        columns = list(
            board.columns.all()
            .order_by("position")
            .prefetch_related(Prefetch("cards", queryset=Card.objects.order_by("position")))
        )
        swimlanes = list(board.swimlanes.all().order_by("position"))

        columns_data = []
        cards_data = []

        for column in columns:
            columns_data.append({
                "id": column.id,
                "name": column.name,
                "position": column.position,
                "color": column.color,
            })
            for card in column.cards.all():
                cards_data.append({
                    "id": card.id,
                    "title": card.title,
                    "description": card.description,
                    "column_id": column.id,
                    "swimlane_id": card.swimlane_id,
                    "priority": card.priority,
                    "color": card.color,
                    "position": card.position,
                })

        swimlanes_data = [
            {
                "id": sl.id,
                "name": sl.name,
                "position": sl.position,
                "height": f"{sl.height}px",
            }
            for sl in swimlanes
        ]

    except Exception:
        logger.exception("Error fetching board data for board %s", board_id)
        return JsonResponse({"status": "error", "message": "An error occurred while fetching board data."}, status=500)

    return JsonResponse({
        "status": "success",
        "board": {"id": board.id, "name": board.name},
        "columns": columns_data,
        "swimlanes": swimlanes_data,
        "cards": cards_data,
    })


@login_required
@require_POST
def update_board_title(request, board_id):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    title = data.get("title", "").strip()

    if not title:
        return HttpResponseBadRequest("Title is required")

    if len(title) > 100:
        return HttpResponseBadRequest("Title must be 100 characters or fewer")

    try:
        board = get_object_or_404(Board, pk=board_id, owner=request.user)
        board.name = title
        board.save()
    except Exception:
        logger.exception("Error updating title for board %s", board_id)
        return HttpResponseBadRequest("An error occurred while updating the board title")

    return JsonResponse({"status": "success", "title": board.name})
