"""Plan & billing: admin-customisable plan cards, and the tenant page that shows them."""
import pytest
from django.test import Client

from billing.models import Plan, Subscription
from utils.tenancy import tenant_context


@pytest.fixture
def plans(db):
    with tenant_context(bypass=True):
        starter = Plan.objects.create(name="Starter", slug="starter", price_amount=5000, max_seats=5, max_bookings_per_month=50, sort_order=1)
        growth = Plan.objects.create(
            name="Growth", slug="growth", price_amount=15000, max_seats=15, sort_order=2, description="For growing agencies",
            features="Priority support\nVoice assistant", badge="Most popular", is_featured=True,
        )
    return starter, growth


@pytest.fixture
def on_starter(agency_a, plans):
    with tenant_context(bypass=True):
        return Subscription.objects.create(agency=agency_a, plan=plans[0], status="active")  # no end date


def test_plan_card_shows_admin_features_badge_and_the_right_buttons(client_a, on_starter):
    page = client_a.get("/member/billing/").content.decode()
    assert "Priority support" in page and "Voice assistant" in page and "Most popular" in page
    assert "For growing agencies" in page
    assert "Upgrade to this plan" in page and "Your current plan" in page
    assert "renews ." not in page and "No end date" in page  # no empty renewal sentence


def test_downgrade_label_and_unlimited_usage(client_a, agency_a, plans):
    with tenant_context(bypass=True):
        Subscription.objects.create(agency=agency_a, plan=plans[1], status="active")
    page = client_a.get("/member/billing/").content.decode()
    assert "Switch to this plan" in page  # Starter is cheaper than Growth
    assert "No booking limit on this plan" in page  # Growth has no booking cap


def test_super_admin_can_set_features_badge_and_highlight(plans):
    from accounts.models import User
    admin = User.objects.create_superuser(username="root_admin", password="x" * 12, email="r@example.com")
    c = Client()
    c.force_login(admin)
    starter = plans[0]
    r = c.post(f"/platform-admin/plans/{starter.id}/edit/", {
        "name": "Starter", "slug": "starter", "price_amount": "5000", "currency": "PKR", "billing_interval": "monthly",
        "trial_days": "14", "sort_order": "1", "is_active": "on", "is_featured": "on",
        "features": "  Email support \n\nQR vouchers\n", "badge": "Best value",
    })
    assert r.status_code == 302, r.content[:300]
    starter.refresh_from_db()
    assert starter.features_list == ["Email support", "QR vouchers"] and starter.badge == "Best value" and starter.is_featured
