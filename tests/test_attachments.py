"""
Tests for frontend/views/attachments.py

InMemoryStorage is configured in settings_test.py, so no AWS credentials or
mocking are needed — file I/O stays entirely in-process.

Covers:
- Upload valid image / PDF → CardAttachment record created
- Upload disallowed file type → rejected with 400
- Upload extension / MIME mismatch → rejected with 400
- Upload oversized file → rejected with 400
- Upload with no file → rejected with 400
- List attachments for a card (populated and empty)
- View attachment returns redirect to file URL
- Delete attachment removes DB record
- Method guards (GET on POST-only endpoints, etc.)
- Unauthenticated access returns 302
- Another user's card / attachment returns 404
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from frontend.models import Board, Card, CardAttachment, Column, Swimlane


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def swimlane_card(user):
    """Card assigned to a swimlane — required because attachment views resolve
    ownership via card__swimlane__board__owner."""
    board = Board.objects.create(name="Attachment Board", owner=user)
    column = Column.objects.create(name="Todo", board=board, position=0)
    swimlane = Swimlane.objects.create(name="Lane", board=board, position=0)
    return Card.objects.create(
        title="Attachment Card", column=column, swimlane=swimlane, position=0
    )


@pytest.fixture
def attachment(swimlane_card):
    """A CardAttachment already saved to the test card."""
    f = SimpleUploadedFile("existing.png", b"fakepng", content_type="image/png")
    return CardAttachment.objects.create(
        card=swimlane_card,
        file=f,
        filename="existing.png",
        file_type="image/png",
        file_size=7,
    )


# ── Upload ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAttachmentUpload:

    def test_upload_valid_image_creates_record(self, auth_client, swimlane_card):
        url = reverse("upload_attachment", args=[swimlane_card.pk])
        f = SimpleUploadedFile("photo.png", b"x" * 100, content_type="image/png")
        response = auth_client.post(url, {"file": f})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["filename"] == "photo.png"
        assert data["file_type"] == "image/png"
        assert CardAttachment.objects.filter(card=swimlane_card).count() == 1

    def test_upload_valid_pdf(self, auth_client, swimlane_card):
        url = reverse("upload_attachment", args=[swimlane_card.pk])
        f = SimpleUploadedFile("report.pdf", b"pdfdata", content_type="application/pdf")
        response = auth_client.post(url, {"file": f})
        assert response.status_code == 200
        assert response.json()["file_type"] == "application/pdf"

    def test_upload_response_includes_all_fields(self, auth_client, swimlane_card):
        url = reverse("upload_attachment", args=[swimlane_card.pk])
        f = SimpleUploadedFile("img.jpg", b"jpgdata", content_type="image/jpeg")
        data = auth_client.post(url, {"file": f}).json()
        for field in ("attachment_id", "filename", "file_type", "file_size", "icon_class", "upload_date"):
            assert field in data, f"Missing field: {field}"

    def test_upload_disallowed_extension_rejected(self, auth_client, swimlane_card):
        url = reverse("upload_attachment", args=[swimlane_card.pk])
        f = SimpleUploadedFile("script.exe", b"mzdata", content_type="application/octet-stream")
        response = auth_client.post(url, {"file": f})
        assert response.status_code == 400
        assert "error" in response.json()

    def test_upload_extension_mime_mismatch_rejected(self, auth_client, swimlane_card):
        url = reverse("upload_attachment", args=[swimlane_card.pk])
        # .png extension but declares text/plain — not in the .png allow-set
        f = SimpleUploadedFile("disguised.png", b"notimage", content_type="text/plain")
        response = auth_client.post(url, {"file": f})
        assert response.status_code == 400

    def test_upload_oversized_file_rejected(self, auth_client, swimlane_card, settings):
        settings.MAX_UPLOAD_SIZE = 10  # 10 bytes for this test only
        url = reverse("upload_attachment", args=[swimlane_card.pk])
        f = SimpleUploadedFile("big.png", b"x" * 100, content_type="image/png")
        response = auth_client.post(url, {"file": f})
        assert response.status_code == 400
        assert "error" in response.json()

    def test_upload_no_file_provided(self, auth_client, swimlane_card):
        url = reverse("upload_attachment", args=[swimlane_card.pk])
        response = auth_client.post(url)
        assert response.status_code == 400
        assert response.json()["error"] == "No file was provided"

    def test_upload_nonexistent_card_returns_404(self, auth_client):
        url = reverse("upload_attachment", args=[99999])
        f = SimpleUploadedFile("photo.png", b"data", content_type="image/png")
        response = auth_client.post(url, {"file": f})
        assert response.status_code == 404

    def test_upload_requires_post(self, auth_client, swimlane_card):
        url = reverse("upload_attachment", args=[swimlane_card.pk])
        assert auth_client.get(url).status_code == 405


# ── List ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestGetAttachments:

    def test_list_returns_existing_attachments(self, auth_client, swimlane_card, attachment):
        url = reverse("get_attachments", args=[swimlane_card.pk])
        response = auth_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["attachments"]) == 1
        assert data["attachments"][0]["filename"] == "existing.png"

    def test_list_empty_when_no_attachments(self, auth_client, swimlane_card):
        url = reverse("get_attachments", args=[swimlane_card.pk])
        response = auth_client.get(url)
        assert response.status_code == 200
        assert response.json()["attachments"] == []

    def test_list_includes_icon_class_and_upload_date(self, auth_client, swimlane_card, attachment):
        url = reverse("get_attachments", args=[swimlane_card.pk])
        item = auth_client.get(url).json()["attachments"][0]
        assert "icon_class" in item
        assert "upload_date" in item

    def test_list_requires_get(self, auth_client, swimlane_card):
        url = reverse("get_attachments", args=[swimlane_card.pk])
        assert auth_client.post(url).status_code == 405


# ── View ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAttachmentView:

    def test_view_redirects_to_file_url(self, auth_client, attachment):
        url = reverse("view_attachment", args=[attachment.pk])
        response = auth_client.get(url)
        assert response.status_code == 302

    def test_view_nonexistent_attachment_returns_404(self, auth_client):
        url = reverse("view_attachment", args=[99999])
        assert auth_client.get(url).status_code == 404


# ── Delete ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAttachmentDelete:

    def test_delete_removes_db_record(self, auth_client, swimlane_card, attachment):
        pk = attachment.pk
        url = reverse("delete_attachment", args=[pk])
        response = auth_client.post(url)
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert not CardAttachment.objects.filter(pk=pk).exists()

    def test_delete_nonexistent_attachment_returns_404(self, auth_client):
        url = reverse("delete_attachment", args=[99999])
        assert auth_client.post(url).status_code == 404

    def test_delete_requires_post(self, auth_client, attachment):
        url = reverse("delete_attachment", args=[attachment.pk])
        assert auth_client.get(url).status_code == 405


# ── Permissions ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAttachmentPermissions:

    def test_unauthenticated_upload_redirects(self, client, swimlane_card):
        url = reverse("upload_attachment", args=[swimlane_card.pk])
        f = SimpleUploadedFile("photo.png", b"data", content_type="image/png")
        assert client.post(url, {"file": f}).status_code == 302

    def test_unauthenticated_list_redirects(self, client, swimlane_card):
        url = reverse("get_attachments", args=[swimlane_card.pk])
        assert client.get(url).status_code == 302

    def test_unauthenticated_view_redirects(self, client, attachment):
        url = reverse("view_attachment", args=[attachment.pk])
        assert client.get(url).status_code == 302

    def test_unauthenticated_delete_redirects(self, client, attachment):
        url = reverse("delete_attachment", args=[attachment.pk])
        assert client.post(url).status_code == 302

    def test_other_user_cannot_upload_to_card(self, client, other_user, swimlane_card):
        client.force_login(other_user)
        url = reverse("upload_attachment", args=[swimlane_card.pk])
        f = SimpleUploadedFile("photo.png", b"data", content_type="image/png")
        assert client.post(url, {"file": f}).status_code == 404

    def test_other_user_cannot_list_card_attachments(self, client, other_user, swimlane_card):
        client.force_login(other_user)
        url = reverse("get_attachments", args=[swimlane_card.pk])
        assert client.get(url).status_code == 404

    def test_other_user_cannot_view_attachment(self, client, other_user, attachment):
        client.force_login(other_user)
        url = reverse("view_attachment", args=[attachment.pk])
        assert client.get(url).status_code == 404

    def test_other_user_cannot_delete_attachment(self, client, other_user, attachment):
        client.force_login(other_user)
        url = reverse("delete_attachment", args=[attachment.pk])
        assert client.post(url).status_code == 404
