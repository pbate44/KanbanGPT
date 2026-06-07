
import json
import logging
import time
import requests as http_requests
from zoneinfo import available_timezones

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

_openrouter_models_cache    = None
_openrouter_models_cache_ts = 0

_username_validator = UnicodeUsernameValidator()
_VALID_TIMEZONES = available_timezones()


def _safe_back_url(url):
    """Return url only if it's a same-site relative path that isn't the settings page."""
    if url and url.startswith('/') and not url.startswith('//') and 'user_settings' not in url:
        return url
    return None


@login_required
def user_settings(request):
    profile = request.user.profile

    if request.method == "POST":
        two_factor_enabled  = request.POST.get("two_factor_enabled") == "on"
        ai_chat_always_open = request.POST.get("ai_chat_always_open") == "on"
        tz = request.POST.get("timezone", profile.timezone)

        if tz not in _VALID_TIMEZONES:
            messages.error(request, "Invalid timezone selected.")
            tz = profile.timezone

        profile.two_factor_enabled  = two_factor_enabled
        profile.ai_chat_always_open = ai_chat_always_open
        profile.timezone = tz
        profile.save(update_fields=["two_factor_enabled", "ai_chat_always_open", "timezone"])
    else:
        next_url = _safe_back_url(request.GET.get('next', ''))
        if next_url:
            request.session['settings_back_url'] = next_url

    back_url = request.session.get('settings_back_url') or reverse('dashboard')

    return render(request, "user_settings.html", {
        "profile":  profile,
        "back_url": back_url,
    })


@login_required
@require_POST
def edit_username(request):
    new_username = request.POST.get('username', '').strip()

    if not new_username:
        messages.error(request, "Username cannot be empty.")
        return redirect('user_settings')

    if len(new_username) > 150:
        messages.error(request, "Username must be 150 characters or fewer.")
        return redirect('user_settings')

    try:
        _username_validator(new_username)
    except ValidationError as e:
        messages.error(request, e.message)
        return redirect('user_settings')

    if User.objects.filter(username=new_username).exclude(pk=request.user.pk).exists():
        messages.error(request, "That username is already taken.")
        return redirect('user_settings')

    request.user.username = new_username
    request.user.save(update_fields=['username'])
    messages.success(request, "Username updated successfully.")
    return redirect('user_settings')


@login_required
@require_POST
def edit_email(request):
    new_email = request.POST.get('email', '').strip()
    entered_password = request.POST.get('email-confirm-password', '').strip()

    try:
        validate_email(new_email)
    except ValidationError:
        return JsonResponse({'status': 'error', 'message': 'Please enter a valid email address.'}, status=400)

    if not request.user.check_password(entered_password):
        return JsonResponse({'status': 'error', 'message': 'Incorrect password. Please try again.'}, status=400)

    if User.objects.filter(email=new_email).exclude(pk=request.user.pk).exists():
        return JsonResponse({'status': 'error', 'message': 'This email is already associated with another account.'}, status=400)

    request.user.email = new_email
    request.user.save(update_fields=['email'])
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def edit_password(request):
    current_password = request.POST.get('current_password', '').strip()
    new_password     = request.POST.get('new_password', '').strip()
    confirm_password = request.POST.get('confirm_password', '').strip()

    if not request.user.check_password(current_password):
        return JsonResponse({'status': 'error', 'message': 'Current password is incorrect.'}, status=400)

    if new_password != confirm_password:
        return JsonResponse({'status': 'error', 'message': 'New passwords do not match.'}, status=400)

    try:
        validate_password(new_password, request.user)
    except ValidationError as e:
        return JsonResponse({'status': 'error', 'message': ' '.join(e.messages)}, status=400)

    request.user.set_password(new_password)
    request.user.save(update_fields=['password'])

    update_session_auth_hash(request, request.user)
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def edit_theme(request):
    theme = request.POST.get('theme', 'system')
    if theme not in ('light', 'dark', 'system'):
        theme = 'system'

    profile = request.user.profile
    profile.theme = theme
    profile.save(update_fields=['theme'])
    return redirect('user_settings')


@login_required
@require_POST
def save_ai_model(request):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)

    model_id = data.get('model_id', '').strip()
    if not model_id:
        return JsonResponse({'status': 'error', 'message': 'Model ID cannot be empty.'}, status=400)
    if len(model_id) > 150:
        return JsonResponse({'status': 'error', 'message': 'Invalid model ID.'}, status=400)

    try:
        profile          = request.user.profile
        profile.ai_model = model_id
        profile.save(update_fields=['ai_model'])
    except Exception:
        logger.exception("Error saving AI model for user %s", request.user.pk)
        return JsonResponse({'status': 'error', 'message': 'An error occurred while saving your model selection.'}, status=500)

    return JsonResponse({'status': 'success', 'model_id': model_id})


def _fetch_openrouter_models():
    global _openrouter_models_cache, _openrouter_models_cache_ts
    if _openrouter_models_cache and (time.time() - _openrouter_models_cache_ts) < 3600:
        return _openrouter_models_cache
    try:
        resp = http_requests.get(
            'https://openrouter.ai/api/v1/models',
            headers={'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}'},
            timeout=10,
        )
        resp.raise_for_status()
        raw = resp.json().get('data', [])
        _openrouter_models_cache = [
            {
                'id':             m['id'],
                'name':           m.get('name', m['id']),
                'context_length': m.get('context_length'),
            }
            for m in raw
            if float(m.get('pricing', {}).get('prompt') or 1) == 0
            and float(m.get('pricing', {}).get('completion') or 1) == 0
            and m.get('id')
        ]
        _openrouter_models_cache_ts = time.time()
    except Exception:
        logger.exception("Failed to fetch OpenRouter models list")
        _openrouter_models_cache = _openrouter_models_cache or []
    return _openrouter_models_cache


@login_required
def get_openrouter_models(request):
    models = _fetch_openrouter_models()
    return JsonResponse({'status': 'success', 'models': models})
