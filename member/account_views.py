"""
Settings that belong to the signed-in person rather than the agency: the
Settings landing page, My profile (details, photo, password) and the UI language.
"""
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import translation

from travelcrm.languages import ENABLED_LANGUAGES, NATIVE_NAMES

from .decorators import agent_required


@agent_required
def settings_home(request):
    """Sidebar → Settings. Everyone lands on their own profile, the first tab."""
    return redirect("my-profile")


def _apply_language(request, response):
    """Save the chosen language on the account and in the cookie; returns an error message or None."""
    lang = (request.POST.get("language") or "").strip() or None
    valid_codes = {code for code, _label in ENABLED_LANGUAGES}
    if lang is not None and lang not in valid_codes:
        return translation.gettext("Unknown language.")
    request.user.preferred_language = lang
    request.user.save(update_fields=["preferred_language", "updated_at"])
    if lang:
        translation.activate(lang)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang, max_age=settings.LANGUAGE_COOKIE_AGE)
    else:
        translation.activate(translation.get_language_from_request(request))
        response.delete_cookie(settings.LANGUAGE_COOKIE_NAME)
    return None


@agent_required
def language_settings(request):
    """The language picker lives on My profile now; this URL keeps old links and the form post working."""
    response = redirect("my-profile")
    if request.method == "POST":
        error = _apply_language(request, response)
        if error:
            messages.error(request, error)
        else:
            messages.success(request, translation.gettext("Language updated."))
    return response


@agent_required
def my_profile(request):
    """Every signed-in person's own profile: details, picture, password and language."""
    from django.contrib.auth import update_session_auth_hash
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError

    from accounts.avatars import AvatarError, process_avatar
    from accounts.models import User

    user = request.user
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "details":
            username = (request.POST.get("username") or "").strip()
            if not username:
                messages.error(request, translation.gettext("Username is required."))
            elif User.objects.filter(username__iexact=username).exclude(pk=user.pk).exists():
                messages.error(request, translation.gettext("Username '%(username)s' is already taken.") % {"username": username})
            else:
                user.username = username[:150]
                user.first_name = (request.POST.get("first_name") or "").strip()[:150]
                user.last_name = (request.POST.get("last_name") or "").strip()[:150]
                user.email = (request.POST.get("email") or "").strip()[:254]
                user.phone = (request.POST.get("phone") or "").strip()[:20]
                user.save(update_fields=["username", "first_name", "last_name", "email", "phone", "updated_at"])
                messages.success(request, translation.gettext("Profile updated."))
        elif action == "avatar":
            upload = request.FILES.get("avatar")
            if not upload:
                messages.error(request, translation.gettext("Choose a picture first."))
            else:
                try:
                    picture = process_avatar(upload)
                except AvatarError as exc:
                    messages.error(request, str(exc))
                else:
                    if user.avatar:
                        user.avatar.delete(save=False)
                    user.avatar.save("avatar.jpg", picture, save=False)
                    user.save(update_fields=["avatar", "updated_at"])
                    messages.success(request, translation.gettext("Profile picture updated."))
        elif action == "remove_avatar":
            if user.avatar:
                user.avatar.delete(save=False)
                user.avatar = ""
                user.save(update_fields=["avatar", "updated_at"])
            messages.success(request, translation.gettext("Profile picture removed."))
        elif action == "password":
            current = request.POST.get("current_password") or ""
            new = request.POST.get("new_password") or ""
            confirm = request.POST.get("confirm_password") or ""
            if not user.check_password(current):
                messages.error(request, translation.gettext("Your current password is wrong."))
            elif new != confirm:
                messages.error(request, translation.gettext("The new passwords don't match."))
            else:
                try:
                    validate_password(new, user)
                except ValidationError as exc:
                    for line in exc.messages:
                        messages.error(request, line)
                else:
                    user.set_password(new)
                    user.save(update_fields=["password", "updated_at"])
                    update_session_auth_hash(request, user)  # stay signed in on this device
                    messages.success(request, translation.gettext("Password changed."))
        return redirect("my-profile")

    return render(request, "member/my_profile.html", {
        "page_title": "My profile",
        "languages": [(c, NATIVE_NAMES.get(c, label), label) for c, label in ENABLED_LANGUAGES],
        "current_language": user.preferred_language,
        "role_label": translation.gettext("Super Admin") if user.is_superuser else (translation.gettext(user.custom_role.name) if user.custom_role_id else user.get_role_display()),
    })
