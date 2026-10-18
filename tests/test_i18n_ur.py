"""Urdu/Arabic coverage for text that is not literal template text: stored role names, model labels, % strings."""
import pytest
from django.utils import translation

from member.templatetags.i18n_extra import tr
from rbac import activity


@pytest.mark.parametrize("lang", ["ur", "ar"])
def test_standard_role_names_and_model_choices_are_translated(lang):
    from member.models import AttendanceLog

    with translation.override(lang):
        for name in ("Owner", "Manager", "Agent", "Read-only"):
            assert tr(name) != name, f"{name} is not translated in {lang}"
        assert tr("An agency's own role name") == "An agency's own role name"  # nothing to translate: unchanged
        assert str(dict(AttendanceLog._meta.get_field("status").flatchoices)["present"]) != "Present"


@pytest.mark.parametrize("lang", ["ur", "ar"])
def test_activity_log_labels_follow_the_language(lang):
    with translation.override("en"):
        english = activity.model_label("LedgerEntry")
    with translation.override(lang):
        assert activity.model_label("LedgerEntry") != english
        rows = activity.readable_changes(
            type("E", (), {"model_name": "User", "changes": {"preferred_language": {"old": "en", "new": "ur"}, "is_active": {"old": True, "new": False}}})(),
            __import__("zoneinfo").ZoneInfo("Asia/Karachi"),
        )
    assert rows[0]["label"] != "Preferred language" and rows[1]["new"] != "No"


@pytest.mark.parametrize("lang", ["ur", "ar"])
def test_template_strings_with_a_percent_sign_are_translated(lang):
    # {% trans "…(%)" %} is looked up with the % doubled, so the catalogue needs that exact msgid
    with translation.override(lang):
        assert translation.gettext("Approval rate (%%)") != "Approval rate (%%)"
        assert translation.gettext("Saved rate (%%)") != "Saved rate (%%)"
