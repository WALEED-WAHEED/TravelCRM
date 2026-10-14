"""Agent portal views.

An agent creates vouchers with the very same form the team uses (member/views.py's worksheet), saves them as drafts,
and submits them for approval. The team reviews them on the Approvals page, may edit them with the same form, and
approves or sends them back with a reason — the agent then fixes and resubmits.
"""
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext
from django.views.decorators.http import require_http_methods, require_POST

from member.decorators import agent_required
from member.models import Booking, BookingMutamer
from member.views import (
    decorate_voucher_rows,
    render_voucher_pdf,
    render_voucher_print,
    worksheet_detail_context,
    worksheet_new_context,
    worksheet_save,
)

EDITABLE = ("draft", "pending", "rejected")      # an approved voucher is final


def _mine(request):
    return Booking.objects.filter(agent=request.user, agency=request.user.agency).exclude(status="cancelled")


@agent_required
def dashboard(request):
    mine = _mine(request)
    return render(request, "agent/dashboard.html", {
        "page_title": gettext("Agent Dashboard"),
        "stats": {
            "total": mine.count(),
            "draft": mine.filter(status="draft").count(),
            "pending": mine.filter(status="pending").count(),
            "rejected": mine.filter(status="rejected").count(),
            "approved": mine.filter(status__in=("confirmed", "completed")).count(),
        },
    })


@agent_required
def bookings(request):
    """The old agent bookings page is now My Vouchers."""
    return redirect("agent-vouchers")


@agent_required
def vouchers(request):
    mine = _mine(request)
    q = (request.GET.get("q") or "").strip()
    status = request.GET.get("status") if request.GET.get("status") in ("draft", "pending", "rejected", "approved") else ""
    qs = mine
    if status == "approved":
        qs = qs.filter(status__in=("confirmed", "completed"))
    elif status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(
            Q(voucher_number__icontains=q) | Q(package_name__icontains=q)
            | Q(id__in=BookingMutamer.objects.filter(
                Q(name__icontains=q) | Q(passport_number__icontains=q)).values("booking_id")))
    return render(request, "agent/vouchers.html", {
        "vouchers": decorate_voucher_rows(qs.order_by("-created_at")),
        "page_title": gettext("My Vouchers"),
        "stats": {
            "total": mine.count(),
            "draft": mine.filter(status="draft").count(),
            "pending": mine.filter(status="pending").count(),
            "rejected": mine.filter(status="rejected").count(),
            "approved": mine.filter(status__in=("confirmed", "completed")).count(),
        },
        "search_q": q,
        "status_filter": status,
    })


@agent_required
def voucher_new(request):
    ctx = worksheet_new_context(request)
    ctx["vw_mode"] = "agent"
    return render(request, "member/booking_new.html", ctx)


@agent_required
def voucher_edit(request, booking_id):
    booking = get_object_or_404(_mine(request), pk=booking_id)
    if booking.status not in EDITABLE:
        messages.info(request, gettext("This voucher is already approved, so it can't be changed."))
        return redirect("agent-vouchers")
    ctx = worksheet_detail_context(request, booking)
    ctx["vw_mode"] = "agent"
    return render(request, "member/booking_detail.html", ctx)


@agent_required
@require_POST
def voucher_save(request):
    return worksheet_save(request, "agent")


@agent_required
@require_http_methods(["GET", "HEAD"])
def voucher_print(request, booking_id):
    return render_voucher_print(request, get_object_or_404(_mine(request), pk=booking_id))


@agent_required
def voucher_pdf(request, booking_id):
    return render_voucher_pdf(request, get_object_or_404(_mine(request), pk=booking_id))


@agent_required
@require_POST
def voucher_delete(request, booking_id):
    """An agent can throw away their own drafts (anything submitted stays on record)."""
    booking = get_object_or_404(_mine(request), pk=booking_id, status="draft")
    number = booking.voucher_number
    booking.delete()
    messages.success(request, gettext("Voucher %(n)s deleted.") % {"n": number})
    return redirect("agent-vouchers")
