import uuid
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext

from member.decorators import member_required
from member.models import Booking, BookingPayment

from .models import Installment, PaymentPlan


@member_required
def collect_payment(request, booking_id):
    agency = request.user.agency
    booking = get_object_or_404(Booking, pk=booking_id, agency=agency)
    installments = Installment.objects.filter(payment_plan__booking=booking).order_by('sequence')
    payments = booking.payments.order_by('-created_at')
    total_paid = sum((p.amount for p in payments), start=Decimal('0'))

    if request.method == 'POST':
        key = request.POST.get('idempotency_key', '').strip()
        if key and BookingPayment.objects.filter(idempotency_key=key).exists():
            messages.info(request, gettext("That payment was already recorded."))
            return redirect('payments-collect', booking_id=booking.id)

        try:
            amount = Decimal(str(request.POST.get('amount', '0')).strip().replace(',', ''))
        except InvalidOperation:
            amount = Decimal('0')

        if amount <= 0:
            messages.error(request, gettext("Enter a valid amount."))
        else:
            installment_id = request.POST.get('installment_id') or None
            installment = installments.filter(pk=installment_id).first() if installment_id else None
            BookingPayment.objects.create(
                booking=booking, amount=amount,
                payment_method=request.POST.get('payment_method', 'cash'),
                transaction_id=request.POST.get('transaction_id', '').strip(),
                notes=request.POST.get('notes', '').strip(),
                status='paid',
                installment=installment,
                idempotency_key=key or None,
                agent=request.user,
            )
            messages.success(request, gettext("Recorded payment of %(amount)s — the ledger has been updated automatically.") % {'amount': amount})
            return redirect('payments-collect', booking_id=booking.id)

    return render(request, 'payments/collect_payment.html', {
        'booking': booking,
        'installments': installments,
        'payments': payments,
        'total_paid': total_paid,
        'balance': (booking.total_amount or Decimal('0')) - total_paid,
        'new_idempotency_key': uuid.uuid4().hex,
    })


@member_required
def payment_plan(request, booking_id):
    agency = request.user.agency
    booking = get_object_or_404(Booking, pk=booking_id, agency=agency)
    plan, _ = PaymentPlan.objects.get_or_create(booking=booking, defaults={'agency': agency, 'created_by': request.user})
    installments = plan.installments.order_by('sequence')

    if request.method == 'POST':
        if request.POST.get('action') == 'delete':
            installments.filter(pk=request.POST.get('installment_id')).delete()
            messages.success(request, gettext("Installment removed."))
        else:
            try:
                amount = Decimal(str(request.POST.get('amount', '0')).strip().replace(',', ''))
            except InvalidOperation:
                amount = Decimal('0')
            label = request.POST.get('label', '').strip()
            due_date = request.POST.get('due_date', '').strip()
            if amount > 0 and label and due_date:
                next_seq = installments.count() + 1
                Installment.objects.create(
                    payment_plan=plan, agency=agency, sequence=next_seq,
                    label=label, amount=amount, due_date=due_date,
                )
                messages.success(request, gettext("Added '%(label)s' installment.") % {'label': label})
            else:
                messages.error(request, gettext("Fill in a label, amount, and due date."))
        return redirect('payments-plan', booking_id=booking.id)

    return render(request, 'payments/payment_plan.html', {
        'booking': booking,
        'plan': plan,
        'installments': installments,
    })

