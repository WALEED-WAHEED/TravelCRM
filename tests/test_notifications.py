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


def test_confirming_a_booking_emails_the_voucher_only(agency_a, booking_with_contact):
    with tenant_context(agency_id=agency_a.id):
        booking_with_contact.status = "confirmed"
        booking_with_contact.save()
    assert [m.to for m in mail.outbox] == [["ali@example.com"]]
    assert "N-001" in mail.outbox[0].subject
    assert _log(agency_a) == [("voucher_generated", "email", "sent", "ali@example.com")]  # no separate "booking confirmed" email


def test_cancelling_a_booking_sends_nothing(agency_a, booking_with_contact):
    with tenant_context(agency_id=agency_a.id):
        booking_with_contact.status = "cancelled"
        booking_with_contact.save()
    assert mail.outbox == [] and _log(agency_a) == []


def test_disabled_event_is_skipped_not_sent(agency_a, booking_with_contact, client_a):
    client_a.post("/member/notifications/preferences/", {"email_payment_received": "on"})  # everything else off
    with tenant_context(agency_id=agency_a.id):
        booking_with_contact.status = "confirmed"
        booking_with_contact.save()
    assert mail.outbox == []
    assert _log(agency_a) == [("voucher_generated", "email", "skipped", "")]


def test_no_recipient_is_logged(agency_a, booking_a):
    from member.models import BookingPayment
    with tenant_context(agency_id=agency_a.id):
        BookingPayment.objects.create(booking=booking_a, amount=500, payment_method="cash", status="paid",
                                      agent=booking_a.agent)
    assert mail.outbox == []
    assert _log(agency_a) == [("payment_receipt", "email", "skipped", "")]


def test_preferences_page_saves(client_a, agency_a):
    from system_config.models import NotificationSettings
    r = client_a.post("/member/notifications/preferences/", {"email_voucher_generated": "on", "sms_payment_received": "on"})
    assert r.status_code == 302
    with tenant_context(agency_id=agency_a.id):
        s = NotificationSettings.objects.get(agency=agency_a)
    assert s.email_voucher_generated and s.sms_payment_received and not s.email_payment_received
    # the old URL now lands on the notifications section of the company profile page
    r = client_a.get("/member/notifications/preferences/")
    assert r.status_code == 302 and r["Location"] == "/profile/#notifications"
    page = client_a.get("/profile/").content.decode()
    assert "Payment received" in page and "Voucher generated" in page and 'id="notifications"' in page
    assert "Booking confirmed" not in page and "Booking cancelled" not in page
    assert "settings-tab" in page and "Notifications</a>" not in page  # no separate Notifications tab


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
    assert r.status_code == 200 and r.context["counts"]["sent"] == 1
    assert "N-001" in r.content.decode()
    assert len(client_a.get("/member/notifications/delivery-log/", {"event": "voucher_generated"}).context["rows"]) == 1
    assert client_a.get("/member/notifications/delivery-log/", {"status": "failed"}).context["rows"] == []


def test_messages_are_shown_once(client_a):
    r = client_a.post("/member/notifications/test-email/", follow=True)  # no email -> one error message
    assert r.content.decode().count("Add an email address to your account first") == 1


def test_bell_menu_lists_the_latest_messages(client_a, agency_a, booking_with_contact):
    with tenant_context(agency_id=agency_a.id):
        booking_with_contact.status = "confirmed"
        booking_with_contact.save()
    r = client_a.get("/member/notifications/recent/")
    page = r.content.decode()
    assert r.status_code == 200 and "Voucher generated" in page and "ali@example.com" in page and "N-001" in page
    assert "Notification settings" not in page  # the menu shows messages, not options
    # an agency with nothing sent yet gets a friendly empty state
    assert "No messages sent yet." in client_b_empty(client_a, agency_a)


def client_b_empty(client_a, agency_a):
    from notifications.models import NotificationDeliveryLog
    with tenant_context(bypass=True):
        NotificationDeliveryLog.all_tenants.filter(agency=agency_a).delete()
    return client_a.get("/member/notifications/recent/").content.decode()
