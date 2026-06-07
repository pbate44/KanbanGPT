
import logging
import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST

from frontend.models import *

logger = logging.getLogger(__name__)


ALLOWED_ATTACHMENT_TYPES = {
    '.pdf':  {'application/pdf'},
    '.doc':  {'application/msword'},
    '.docx': {'application/vnd.openxmlformats-officedocument.wordprocessingml.document'},
    '.xls':  {'application/vnd.ms-excel'},
    '.xlsx': {'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'},
    '.csv':  {'text/csv', 'text/plain', 'application/csv'},
    '.txt':  {'text/plain'},
    '.rtf':  {'application/rtf', 'text/rtf', 'text/richtext'},
    '.png':  {'image/png'},
    '.jpg':  {'image/jpeg'},
    '.jpeg': {'image/jpeg'},
    '.gif':  {'image/gif'},
    '.webp': {'image/webp'},
}


@require_POST
@login_required
def upload_attachment(request, card_id):
    try:
        card = get_object_or_404(Card, pk=card_id, swimlane__board__owner=request.user)
        
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file was provided'}, status=400)
        
        uploaded_file = request.FILES['file']
        
        if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
            return JsonResponse({'error': 'File size exceeds the limit'}, status=400)

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        declared_mime = uploaded_file.content_type.lower().split(';')[0].strip()
        allowed_mimes = ALLOWED_ATTACHMENT_TYPES.get(ext)
        if not allowed_mimes or declared_mime not in allowed_mimes:
            return JsonResponse({'error': 'File type not allowed'}, status=400)

        file_type = declared_mime
        
        attachment = CardAttachment.objects.create(
            card=card,
            file=uploaded_file,
            filename=uploaded_file.name,
            file_type=file_type,
            file_size=uploaded_file.size
        )
        
        return JsonResponse({
            'status': 'success',
            'attachment_id': attachment.id,
            'filename': attachment.filename,
            'file_type': attachment.file_type,
            'file_size': attachment.file_size,
            'icon_class': attachment.get_icon_class(),
            'upload_date': attachment.upload_date.strftime('%Y-%m-%d %H:%M')
        })
        
    except Http404:
        raise
    except Exception:
        logger.exception("Attachment upload failed")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)


@login_required
@require_GET
def get_attachments(request, card_id):
    try:
        card = get_object_or_404(Card, pk=card_id, swimlane__board__owner=request.user)
        attachments = card.attachments.all()
        
        return JsonResponse({
            'status': 'success',
            'attachments': [
                {
                    'id': attachment.id,
                    'filename': attachment.filename,
                    'file_type': attachment.file_type,
                    'file_size': attachment.file_size,
                    'icon_class': attachment.get_icon_class(),
                    'upload_date': attachment.upload_date.strftime('%Y-%m-%d %H:%M')
                }
                for attachment in attachments
            ]
        })
        
    except Http404:
        raise
    except Exception:
        logger.exception("Get attachments failed")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)


@require_GET
@login_required
def view_attachment(request, attachment_id):
    try:
        attachment = get_object_or_404(CardAttachment, pk=attachment_id, card__swimlane__board__owner=request.user)
        return redirect(attachment.file.url)
        
    except Http404:
        raise
    except Exception:
        logger.exception("View attachment failed")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)


@require_POST
@login_required
def delete_attachment(request, attachment_id):
    try:
        attachment = get_object_or_404(CardAttachment, pk=attachment_id, card__swimlane__board__owner=request.user)
        attachment.file.delete(save=False)
        attachment.delete()
        return JsonResponse({'status': 'success'})
    except Http404:
        raise
    except Exception:
        logger.exception("Delete attachment failed")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)
