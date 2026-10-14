"""Notifications end to end: booking events -> email -> delivery log; settings; test email."""
import pytest
from django.core import mail

from utils.tenancy import tenant_context


@pytest.fixture
def booking_with_contact(agency_a, user_a):
    from member.models import Booking, BookingContact, Contact
    with tenant_context(agency_id=agency_a.id):
        b = Booking.objects.create(agency=agency_a, agent=user_a, status="draft", voucher_number="N-001",
                                   total_amount=1000, total_price=1000, client_company="Ali Group")
        c = Contact.objects.create(agency=agency_a, created_by=user_a, name="Ali", contact_type="customer",
                                   email="ali@example.com", phone="0300", address="x", city="Lahore",
                                   state="Punjab", country="PK", postal_code="54000")
        BookingContact.objects.create(booking=b, contact=c)
        return b


def _log(agency):
    from notifications.models import NotificationDeliveryLog
    with tenant_context(agency_id=agency.id):
        return list(NotificationDeliveryLog.objects.order_by("id").values_list("event_type", "channel", "status", "recipient"))


def test_confirming_a_booking_emails_the_contact(agency_a, booking_with_contact):
    with tenant_context(agency_id=agency_a.id):
        booking_with_contact.status = "confirmed"
        booking_with_contact.save()
    assert [m.to for m in mail.outbox] == [["ali@example.com"], ["ali@example.com"]]
    assert "N-001" in mail.outbox[0].subject
    assert _log(agency_a) == [("booking_confirmation", "email", "sent", "ali@example.com"),
                              ("voucher_generated", "email", "sent", "ali@example.com")]


def test_disabled_event_is_skipped_not_sent(agency_a, booking_with_contact, client_a):
    client_a.post("/member/notifications/preferences/", {"email_payment_received": "on"})  # everything else off
    with tenant_context(agency_id=agency_a.id):
        booking_with_contact.status = "cancelled"
        booking_with_contact.save()
    assert mail.outbox == []
    assert _log(agency_a) == [("booking_cancelled", "email", "skipped", "")]


def test_no_recipient_is_logged(agency_a, booking_a):
    from member.models import BookingPayment
    with tenant_context(agency_id=agency_a.id):
        BookingPayment.objects.create(booking=booking_a, amount=500, payment_method="cash", status="paid",
                                      agent=booking_a.agent)
    assert mail.outbox == []
    assert _log(agency_a) == [("payment_receipt", "email", "skipped", "")]


def test_preferences_page_saves(client_a, agency_a):
    from system_config.models import NotificationSettings
    r = client_a.post("/member/notifications/preferences/", {"email_booking_confirmation": "on", "sms_payment_received": "on"})
    assert r.status_code == 302
    with tenant_context(agency_id=agency_a.id):
        s = NotificationSettings.objects.get(agency=agency_a)
    assert s.email_booking_confirmation and s.sms_payment_received and not s.email_payment_received
    page = client_a.get("/member/notifications/preferences/").content.decode()
    assert "Automatic messages" in page and "settings-tabs" in page


def test_send_test_email(client_a, user_a):
    r = client_a.post("/member/notifications/test-email/")
    assert r.status_code == 302 and mail.outbox == []  # owner has no email yet -> friendly error
    user_a.email = "owner@example.com"
    user_a.save()
    client_a.post("/member/notifications/test-email/")
    assert [m.to for m in mail.outbox] == [["owner@example.com"]]


def test_delivery_log_page(client_a, agency_a, booking_with_contact):
    with tenant_context(agency_id=agency_a.id):
        booking_with_contact.status = "confirmed"
        booking_with_contact.save()
    r = client_a.get("/member/notifications/delivery-log/")
    assert r.status_code == 200 and r.context["counts"]["sent"] == 2
    assert "N-001" in r.content.decode()
    assert len(client_a.get("/member/notifications/delivery-log/", {"event": "voucher_generated"}).context["rows"]) == 1
    assert client_a.get("/member/notifications/delivery-log/", {"status": "failed"}).context["rows"] == []


def test_messages_are_shown_once(client_a):
    r = client_a.post("/member/notifications/test-email/", follow=True)  # no email -> one error message
    assert r.content.decode().count("Add an email address to your account first") == 1
