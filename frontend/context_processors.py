
def theme_context(request):

    theme_override = None

    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        profile = getattr(user, 'profile', None)
        if profile and profile.theme in ("light", "dark"):
            theme_override = profile.theme

    return {'theme_override': theme_override}