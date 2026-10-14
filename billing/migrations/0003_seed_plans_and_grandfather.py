from django.db import migrations
from django.utils import timezone

PLANS = [
    dict(name='Trial', slug='trial', description='14-day free trial.', price_amount=0, currency='PKR',
         billing_interval='monthly', max_seats=3, max_bookings_per_month=20,
         is_active=True, is_default_trial=True, trial_days=14, sort_order=0),
    dict(name='Starter', slug='starter', description='For a small team getting started.', price_amount=5000, currency='PKR',
         billing_interval='monthly', max_seats=5, max_bookings_per_month=50,
         is_active=True, is_default_trial=False, trial_days=14, sort_order=1),
    dict(name='Growth', slug='growth', description='For a growing agency.', price_amount=15000, currency='PKR',
         billing_interval='monthly', max_seats=15, max_bookings_per_month=200,
         is_active=True, is_default_trial=False, trial_days=14, sort_order=2),
    dict(name='Unlimited', slug='unlimited', description='No limits.', price_amount=35000, currency='PKR',
         billing_interval='monthly', max_seats=None, max_bookings_per_month=None,
         is_active=True, is_default_trial=False, trial_days=14, sort_order=3),
]


def seed(apps, schema_editor):
    Plan = apps.get_model('billing', 'Plan')
    Agency = apps.get_model('agencies', 'Agency')
    Subscription = apps.get_model('billing', 'Subscription')

    plans_by_slug = {}
    for data in PLANS:
        plan, _ = Plan.objects.get_or_create(slug=data['slug'], defaults=data)
        plans_by_slug[data['slug']] = plan

    # Grandfather every agency that already existed before this phase —
    # they signed up (informally, via you) before "subscriptions" existed
    # at all, and shouldn't suddenly be locked out by the new access gate.
    unlimited = plans_by_slug['unlimited']
    for agency in Agency.objects.all():
        Subscription.objects.get_or_create(
            agency=agency,
            defaults=dict(plan=unlimited, status='active', current_period_end=None),
        )


def unseed(apps, schema_editor):
    Plan = apps.get_model('billing', 'Plan')
    Plan.objects.filter(slug__in=[p['slug'] for p in PLANS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_row_level_security'),
        ('agencies', '0002_agency_attendance_admin'),
    ]

    operations = [
        migrations.RunPython(seed, reverse_code=unseed),
    ]
