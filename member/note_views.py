"""Internal notes on a voucher (the Notes pop-up): list / add / delete, as JSON."""
import json
from zoneinfo import ZoneInfo

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from . import attendance as att_rules
from .decorators import member_required
from .models import Booking, BookingNote

MAX_LEN = 2000


def _office_zone(agency):
    try:
        return ZoneInfo(att_rules.get_settings(agency).time_zone)
    except Exception:
        return timezone.get_current_timezone()


def note_dict(note, user, zone):
    name = (note.author.get_full_name() or note.author.username) if note.author_id else _("Former team member")
    return {
        "id": note.id,
        "text": note.text,
        "author": name,
        "initial": (name[:1] or "•").upper(),
        "at": timezone.localtime(note.created_at, zone).strftime("%d %b %Y, %I:%M %p").lstrip("0"),
        "mine": bool(note.author_id and note.author_id == user.id),
    }


def notes_for(booking, user):
    zone = _office_zone(booking.agency)
    return [note_dict(n, user, zone) for n in booking.voucher_notes.select_related("author")]


@member_required
@require_http_methods(["GET", "POST"])
def booking_notes(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id, agency=request.user.agency)
    if request.method == "GET":
        return JsonResponse({"notes": notes_for(booking, request.user)})
    try:
        text = str(json.loads(request.body or b"{}").get("text") or "").strip()
    except (ValueError, AttributeError):
        text = ""
    if not text:
        return JsonResponse({"error": _("Write something first.")}, status=400)
    note = BookingNote.objects.create(agency=booking.agency, booking=booking, author=request.user, text=text[:MAX_LEN])
    return JsonResponse({"note": note_dict(note, request.user, _office_zone(booking.agency))}, status=201)


@member_required
@require_POST
def booking_note_delete(request, note_id):
    note = get_object_or_404(BookingNote, pk=note_id, agency=request.user.agency)
    if note.author_id != request.user.id:
        return JsonResponse({"error": _("You can only delete your own notes.")}, status=403)
    note.delete()
    return JsonResponse({"ok": True})
