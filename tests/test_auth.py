"""
Tests for frontend/views/auth.py and frontend/services/two_factor_service.py

Covers:
- Login with valid credentials → redirect to dashboard
- Login with invalid credentials → error shown
- Login with 2FA enabled → redirected to verify_2fa, session seeded
- 2FA verify view: valid code → logged in, code marked used
- 2FA verify view: invalid / expired / used code → error
- 2FA verify view: too many attempts → redirect to login
- Signup: creates User + UserProfile + starter board with 3 columns
- Signup: duplicate username → error
- Signup: password mismatch → error
- Password reset: page renders, POST redirects (unknown email not revealed)
- Logout: clears session, GET not allowed
- Delete account: valid → user removed, wrong password → error
"""

import pytest
from datetime import timedelta

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from frontend.models import Board, TwoFactorCode


# Password used for the shared `user` fixture (matches conftest.py).
USER_PASSWORD = "testpassword123"


# ── Extra fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def user_2fa(db):
    """User with two-factor authentication enabled."""
    u = User.objects.create_user(
        username="twofa_user",
        email="twofa@example.com",
        password=USER_PASSWORD,
    )
    u.profile.two_factor_enabled = True
    u.profile.save()
    return u


@pytest.fixture
def valid_code(user_2fa):
    """Unexpired, unused 2FA code for user_2fa."""
    return TwoFactorCode.objects.create(
        user=user_2fa,
        code="123456",
        expires_at=timezone.now() + timedelta(minutes=10),
    )


@pytest.fixture
def expired_code(user_2fa):
    """Already-expired 2FA code for user_2fa."""
    return TwoFactorCode.objects.create(
        user=user_2fa,
        code="999999",
        expires_at=timezone.now() - timedelta(minutes=1),
    )


# ── Login ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestLogin:

    def test_get_renders_login_form(self, client):
        assert client.get(reverse("login")).status_code == 200

    def test_valid_credentials_redirect_to_dashboard(self, client, user):
        response = client.post(reverse("login"), {
            "username": user.username,
            "password": USER_PASSWORD,
        })
        assert response.status_code == 302
        assert response["Location"] == reverse("dashboard")

    def test_valid_login_sets_session(self, client, user):
        client.post(reverse("login"), {
            "username": user.username,
            "password": USER_PASSWORD,
        })
        assert "_auth_user_id" in client.session

    def test_invalid_credentials_re_renders_form(self, client, user):
        response = client.post(reverse("login"), {
            "username": user.username,
            "password": "wrongpassword",
        })
        assert response.status_code == 200
        assert "_auth_user_id" not in client.session

    def test_login_respects_safe_next_param(self, client, user):
        target = reverse("user_settings")
        response = client.post(f"{reverse('login')}?next={target}", {
            "username": user.username,
            "password": USER_PASSWORD,
            "next": target,
        })
        assert response.status_code == 302
        assert response["Location"] == target

    def test_unsafe_next_falls_back_to_dashboard(self, client, user):
        response = client.post(reverse("login"), {
            "username": user.username,
            "password": USER_PASSWORD,
            "next": "http://evil.example.com/steal",
        })
        assert response.status_code == 302
        assert "evil.example.com" not in response["Location"]

    def test_2fa_user_redirected_to_verify(self, client, user_2fa):
        response = client.post(reverse("login"), {
            "username": user_2fa.username,
            "password": USER_PASSWORD,
        })
        assert response.status_code == 302
        assert response["Location"] == reverse("verify_2fa")

    def test_2fa_user_not_logged_in_yet(self, client, user_2fa):
        client.post(reverse("login"), {
            "username": user_2fa.username,
            "password": USER_PASSWORD,
        })
        assert "_auth_user_id" not in client.session

    def test_2fa_pending_session_keys_set(self, client, user_2fa):
        client.post(reverse("login"), {
            "username": user_2fa.username,
            "password": USER_PASSWORD,
        })
        assert client.session.get("pending_2fa_user_id") == user_2fa.pk


# ── Two-Factor Authentication ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestTwoFactor:

    def _seed_session(self, client, user_id, attempts=0):
        session = client.session
        session["pending_2fa_user_id"] = user_id
        session["2fa_next_url"] = "dashboard"
        session["remember"] = False
        session["2fa_attempts"] = attempts
        session.save()

    def test_get_without_pending_session_redirects_to_login(self, client):
        response = client.get(reverse("verify_2fa"))
        assert response.status_code == 302
        assert response["Location"] == reverse("login")

    def test_get_with_pending_session_renders_form(self, client, user_2fa):
        self._seed_session(client, user_2fa.pk)
        assert client.get(reverse("verify_2fa")).status_code == 200

    def test_valid_code_logs_user_in(self, client, user_2fa, valid_code):
        self._seed_session(client, user_2fa.pk)
        response = client.post(reverse("verify_2fa"), {"code": valid_code.code})
        assert response.status_code == 302
        assert int(client.session["_auth_user_id"]) == user_2fa.pk

    def test_valid_code_marked_used(self, client, user_2fa, valid_code):
        self._seed_session(client, user_2fa.pk)
        client.post(reverse("verify_2fa"), {"code": valid_code.code})
        valid_code.refresh_from_db()
        assert valid_code.used is True

    def test_valid_code_clears_pending_session_keys(self, client, user_2fa, valid_code):
        self._seed_session(client, user_2fa.pk)
        client.post(reverse("verify_2fa"), {"code": valid_code.code})
        assert "pending_2fa_user_id" not in client.session

    def test_wrong_code_re_renders_with_error(self, client, user_2fa, valid_code):
        self._seed_session(client, user_2fa.pk)
        response = client.post(reverse("verify_2fa"), {"code": "000000"})
        assert response.status_code == 200
        assert "_auth_user_id" not in client.session

    def test_wrong_code_increments_attempts(self, client, user_2fa, valid_code):
        self._seed_session(client, user_2fa.pk, attempts=0)
        client.post(reverse("verify_2fa"), {"code": "000000"})
        assert client.session["2fa_attempts"] == 1

    def test_expired_code_rejected(self, client, user_2fa, expired_code):
        self._seed_session(client, user_2fa.pk)
        response = client.post(reverse("verify_2fa"), {"code": expired_code.code})
        assert response.status_code == 200
        assert "_auth_user_id" not in client.session

    def test_used_code_rejected(self, client, user_2fa, valid_code):
        valid_code.used = True
        valid_code.save()
        self._seed_session(client, user_2fa.pk)
        response = client.post(reverse("verify_2fa"), {"code": valid_code.code})
        assert response.status_code == 200
        assert "_auth_user_id" not in client.session

    def test_too_many_attempts_redirects_to_login(self, client, user_2fa, valid_code):
        self._seed_session(client, user_2fa.pk, attempts=5)
        response = client.post(reverse("verify_2fa"), {"code": "000000"})
        assert response.status_code == 302
        assert response["Location"] == reverse("login")
        assert "pending_2fa_user_id" not in client.session


# ── Signup ────────────────────────────────────────────────────────────────────

SIGNUP_DATA = {
    "username": "brandnewuser",
    "email": "brandnew@example.com",
    "password1": "Str0ng!Pass99",
    "password2": "Str0ng!Pass99",
}


@pytest.mark.django_db
class TestSignup:

    def test_get_renders_signup_form(self, client):
        assert client.get(reverse("signup")).status_code == 200

    def test_valid_signup_creates_user(self, client):
        client.post(reverse("signup"), SIGNUP_DATA)
        assert User.objects.filter(username="brandnewuser").exists()

    def test_valid_signup_creates_user_profile(self, client):
        client.post(reverse("signup"), SIGNUP_DATA)
        u = User.objects.get(username="brandnewuser")
        assert hasattr(u, "profile")

    def test_valid_signup_creates_starter_board(self, client):
        client.post(reverse("signup"), SIGNUP_DATA)
        u = User.objects.get(username="brandnewuser")
        assert Board.objects.filter(owner=u).count() == 1

    def test_valid_signup_starter_board_has_three_columns(self, client):
        client.post(reverse("signup"), SIGNUP_DATA)
        u = User.objects.get(username="brandnewuser")
        assert Board.objects.get(owner=u).columns.count() == 3

    def test_valid_signup_redirects(self, client):
        response = client.post(reverse("signup"), SIGNUP_DATA)
        assert response.status_code == 302

    def test_duplicate_username_rejected(self, client, user):
        response = client.post(reverse("signup"), {
            **SIGNUP_DATA,
            "username": user.username,
        })
        assert response.status_code == 200
        assert User.objects.filter(username=user.username).count() == 1

    def test_password_mismatch_rejected(self, client):
        response = client.post(reverse("signup"), {
            **SIGNUP_DATA,
            "password2": "DifferentPass99!",
        })
        assert response.status_code == 200
        assert not User.objects.filter(username="brandnewuser").exists()

    def test_missing_email_rejected(self, client):
        response = client.post(reverse("signup"), {
            **SIGNUP_DATA,
            "email": "",
        })
        assert response.status_code == 200
        assert not User.objects.filter(username="brandnewuser").exists()


# ── Password Reset ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPasswordReset:

    def test_forgot_password_page_renders(self, client):
        assert client.get(reverse("password_reset")).status_code == 200

    def test_post_with_registered_email_redirects(self, client, user):
        response = client.post(reverse("password_reset"), {"email": user.email})
        assert response.status_code == 302

    def test_post_with_unknown_email_still_redirects(self, client):
        # Django does not reveal whether an email is registered.
        response = client.post(reverse("password_reset"), {"email": "nobody@example.com"})
        assert response.status_code == 302


# ── Logout ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestLogout:

    def test_post_clears_session(self, auth_client):
        auth_client.post(reverse("logout"))
        assert "_auth_user_id" not in auth_client.session

    def test_post_redirects_to_home(self, auth_client):
        response = auth_client.post(reverse("logout"))
        assert response.status_code == 302
        assert response["Location"] == reverse("home")

    def test_get_not_allowed(self, auth_client):
        assert auth_client.get(reverse("logout")).status_code == 405


# ── Delete Account ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDeleteAccount:

    def test_valid_deletion_removes_user(self, auth_client, user):
        pk = user.pk
        auth_client.post(reverse("delete_account"), {
            "confirm_delete": "yes",
            "password": USER_PASSWORD,
        })
        assert not User.objects.filter(pk=pk).exists()

    def test_valid_deletion_redirects_to_goodbye(self, auth_client, user):
        response = auth_client.post(reverse("delete_account"), {
            "confirm_delete": "yes",
            "password": USER_PASSWORD,
        })
        assert response.status_code == 302
        assert response["Location"] == reverse("goodbye")

    def test_wrong_password_does_not_delete(self, auth_client, user):
        response = auth_client.post(reverse("delete_account"), {
            "confirm_delete": "yes",
            "password": "wrongpassword",
        })
        assert response.status_code == 302
        assert User.objects.filter(pk=user.pk).exists()

    def test_missing_confirm_does_not_delete(self, auth_client, user):
        response = auth_client.post(reverse("delete_account"), {"password": USER_PASSWORD})
        assert response.status_code == 302
        assert User.objects.filter(pk=user.pk).exists()

    def test_unauthenticated_request_redirects(self, client):
        response = client.post(reverse("delete_account"), {
            "confirm_delete": "yes",
            "password": USER_PASSWORD,
        })
        assert response.status_code == 302
