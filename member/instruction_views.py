"""Voucher instructions: the numbered rules printed at the end of every voucher.
Managed from the Contacts page; read by the voucher views."""
from django.contrib import messages
from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .decorators import member_required
from .models import VoucherInstruction

# The agency's usual Umrah rules — a starting point the owner can edit.
STANDARD_UMRAH = [
    "آپ کا ہوٹل اور پیکج اس دستاویز میں درج ہے، اسی کے مطابق رہائش اور دیگر سہولیات فراہم کی جائیں گی۔",
    "سفری سامان حرمین شریفین کے اندر لے جانا سعودی انتظامیہ کی طرف سے ممنوع ہے، خلاف ورزی کی صورت میں جرمانہ ہو سکتا ہے جس کی ادائیگی آپ کے ذمہ ہوگی۔",
    "نشہ آور اشیاء شرعاً اور قانوناً ممنوع ہیں، سعودی عرب میں منشیات لے جانے کی سزا موت ہے۔",
    "حرمین شریفین (مسجد الحرام و مسجد نبوی) کے اندر زمین پر گری ہوئی کوئی چیز (پرس، موبائل فون یا کوئی قیمتی چیز) ہرگز نہ اٹھائیں ورنہ آپ مشکل میں پڑ سکتے ہیں۔",
    "جدہ ایئرپورٹ پر امیگریشن اور سعودی وزارت کے انتظام میں 3 سے 5 گھنٹے لگ سکتے ہیں، سعودیہ پہنچ کر اپنے گھر والوں کو خیریت سے پہنچنے کی اطلاع ضرور دیں۔",
    "ہوٹل سے چیک آؤٹ کا وقت دوپہر 2 بجے ہے، اس کے بعد اگلی رات کا کرایہ لاگو ہوگا۔ ہوٹل واؤچر کی کاپی ہر وقت اپنے پاس رکھیں۔",
    "واپسی کی پرواز سے دس گھنٹے پہلے اپنے سامان سمیت ہوٹل کی ریسپشن پر موجود رہیں۔ واپسی کی پرواز کی معلومات معلوم رکھنا معتمر کی اپنی ذمہ داری ہے، نیچے دیے گئے نمبروں پر رابطہ کریں۔",
    "سعودی حکومت کے قانون کے مطابق کمپنی کے ہوٹلوں کے علاوہ کسی غیر رجسٹرڈ ہوٹل میں قیام کرنا جرم ہے۔ اگر کوئی معتمر اپنے طور پر کسی ہوٹل میں کمرہ لے گا تو اس کے قانونی اور مالی نقصان کا خود ذمہ دار ہوگا۔",
]


def active_instructions(agency, unscoped=False):
    """Instructions to print on a voucher, in order. `unscoped` for the public
    (anonymous) voucher page, which has no tenant context."""
    manager = VoucherInstruction.all_tenants if unscoped else VoucherInstruction.objects
    return list(manager.filter(agency=agency, is_active=True).order_by("sort_order", "id"))


def _back():
    return redirect(reverse("member-contacts") + "#voucher-instructions")


def _next_order(agency):
    return (VoucherInstruction.objects.filter(agency=agency).aggregate(m=Max("sort_order"))["m"] or 0) + 1


@member_required
@require_POST
def instruction_add(request):
    text = (request.POST.get("text") or "").strip()
    if not text:
        messages.error(request, _("Write the instruction first."))
        return _back()
    VoucherInstruction.objects.create(
        agency=request.user.agency, text=text[:2000], sort_order=_next_order(request.user.agency),
        created_by=request.user,
    )
    messages.success(request, _("Instruction added — it will appear on every voucher."))
    return _back()


@member_required
@require_POST
def instruction_update(request, instruction_id):
    item = get_object_or_404(VoucherInstruction, pk=instruction_id, agency=request.user.agency)
    if "text" in request.POST:
        text = (request.POST.get("text") or "").strip()
        if not text:
            messages.error(request, _("An instruction can't be empty — delete it instead."))
            return _back()
        item.text = text[:2000]
    if "is_active" in request.POST:
        item.is_active = request.POST.get("is_active") == "1"
    item.save()
    messages.success(request, _("Instruction updated."))
    return _back()


@member_required
@require_POST
def instruction_delete(request, instruction_id):
    get_object_or_404(VoucherInstruction, pk=instruction_id, agency=request.user.agency).delete()
    messages.success(request, _("Instruction deleted."))
    return _back()


@member_required
@require_POST
@transaction.atomic
def instruction_move(request, instruction_id):
    agency = request.user.agency
    items = list(VoucherInstruction.objects.filter(agency=agency).order_by("sort_order", "id"))
    idx = next((i for i, it in enumerate(items) if it.pk == instruction_id), None)
    if idx is None:
        return _back()
    swap = idx - 1 if request.POST.get("direction") == "up" else idx + 1
    if 0 <= swap < len(items):
        items[idx], items[swap] = items[swap], items[idx]
        for order, it in enumerate(items, 1):  # renumber so orders stay tidy
            if it.sort_order != order:
                it.sort_order = order
                it.save(update_fields=["sort_order", "updated_at"])
    return _back()


@member_required
@require_POST
def instruction_load_standard(request):
    agency = request.user.agency
    existing = set(VoucherInstruction.objects.filter(agency=agency).values_list("text", flat=True))
    order = _next_order(agency)
    added = 0
    for text in STANDARD_UMRAH:
        if text not in existing:
            VoucherInstruction.objects.create(agency=agency, text=text, sort_order=order, created_by=request.user)
            order += 1
            added += 1
    messages.success(request, _("Added %(n)d standard Umrah instructions — edit them as you like.") % {"n": added})
    return _back()
