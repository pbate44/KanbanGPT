
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from frontend.forms import CustomUserCreationForm
from frontend.models import Board, TwoFactorCode
from frontend.services.two_factor_service import TwoFactorService

logger = logging.getLogger(__name__)

User = get_user_model()

_2FA_MAX_ATTEMPTS = 5


def _safe_redirect_url(request, url, fallback="dashboard"):
    if url and url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}):
        return url
    return fallback


def Login(request):
    next_url = request.GET.get("next") or request.POST.get("next") or "dashboard"
    next_url = _safe_redirect_url(request, next_url)

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            remember_me = request.POST.get("remember") == "on"

            if user.profile.two_factor_enabled:
                success, code = TwoFactorService.create_and_send_code(user)

                if success:
                    request.session["pending_2fa_user_id"] = user.id
                    request.session["2fa_next_url"] = next_url
                    request.session["remember"] = bool(remember_me)
                    request.session["2fa_attempts"] = 0

                    messages.info(request, "A verification code has been sent to your email.")
                    return redirect("verify_2fa")

                messages.error(request, "Failed to send verification code. Please try again.")
                return render(request, "Login.html", {"form": form})

            request.session.set_expiry(60 * 60 * 24 * 30 if remember_me else 0)

            login(request, user)
            return redirect(next_url)

    else:
        form = AuthenticationForm()

    return render(request, "Login.html", {"form": form, "next": request.GET.get("next", "")})


def verify_2fa(request):
    user_id = request.session.get("pending_2fa_user_id")

    if not user_id:
        messages.error(request, "No pending two-factor authentication found.")
        return redirect("login")

    user = get_object_or_404(User, pk=user_id)

    if request.method == "POST":
        attempts = request.session.get("2fa_attempts", 0)

        if attempts >= _2FA_MAX_ATTEMPTS:
            request.session.pop("pending_2fa_user_id", None)
            request.session.pop("2fa_next_url", None)
            request.session.pop("remember", None)
            request.session.pop("2fa_attempts", None)
            messages.error(request, "Too many incorrect attempts. Please log in again.")
            return redirect("login")

        input_code = request.POST.get("code", "").strip()

        code_obj = (
            TwoFactorCode.objects
            .filter(user=user, used=False)
            .order_by("-created_at")
            .first()
        )

        if not code_obj or not code_obj.is_valid() or code_obj.code != input_code:
            request.session["2fa_attempts"] = attempts + 1
            messages.error(request, "Invalid or expired verification code.")
            return render(request, "verify_2fa.html")

        request.session.pop("pending_2fa_user_id", None)
        next_url = request.session.pop("2fa_next_url", "dashboard")
        remember = request.session.pop("remember", False)
        request.session.pop("2fa_attempts", None)
        next_url = _safe_redirect_url(request, next_url)
        code_obj.used = True
        code_obj.save()
        login(request, user)

        request.session.set_expiry(60 * 60 * 24 * 30 if remember else 0)
        return redirect(next_url)

    return render(request, "verify_2fa.html")


def Signup(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                user = form.save()

                starter_board = Board.objects.create(
                    name="My First Board",
                    description="Getting started with KanbanGPT",
                    owner=user,
                )
                starter_board.columns.create(name="To Do", position=0)
                starter_board.columns.create(name="In progress", position=1)
                starter_board.columns.create(name="Done", position=2)

            transaction.on_commit(lambda: send_welcome_email(user))

            messages.success(request, "Account successfully created. Please log in.")
            return redirect("dashboard")
    else:
        form = CustomUserCreationForm()

    return render(request, "Signup.html", {"form": form})


def send_welcome_email(user):
    subject = "Welcome to KanbanGPT"
    message = (
        f"Hi {user.username},\n\n"
        "Welcome to KanbanGPT! Your account has been created successfully.\n\n"
        "You can now start organising your work with boards, cards and AI!\n\n"
        "— The KanbanGPT team"
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Failed to send welcome email to user %s", user.pk)


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("home")


@login_required
@require_POST
def delete_account(request):
    confirm = request.POST.get("confirm_delete")
    user = request.user

    if not confirm:
        messages.error(request, "Please confirm account deletion.")
        return redirect("user_settings")

    password = request.POST.get("password", "")
    if not user.check_password(password):
        messages.error(request, "Incorrect password. Account was not deleted.")
        return redirect("user_settings")

    logout(request)
    user.delete()
    return redirect("goodbye")


def goodbye(request):
    return render(request, "account/goodbye.html")
