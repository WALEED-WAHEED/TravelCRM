"""
Cross-tenant analytics for the Super Admin. Everything here is computed
live from real rows (Agency, Subscription) — no historical MRR trend is
shown because nothing in the schema snapshots subscription state over
time; faking one would repeat the mistake fixed elsewhere in Phase 08
(member/views.py's old `count * 450 + 1000` placeholder revenue chart).
"""
from django.db.models import Count
from django.db.models.functions import TruncMonth

from agencies.models import Agency
from billing.models import Subscription


def agency_growth(months=6):
    """New agency signups per month, trailing N months — real, from
    Agency.created_at."""
    qs = (
        Agency.objects.annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
    )
    by_month = {(m['month'].year, m['month'].month): m['count'] for m in qs if m['month']}

    from reports.services import _last_n_months_labels
    labels, values = [], []
    for year, month in _last_n_months_labels(months):
        labels.append(f"{year:04d}-{month:02d}")
        values.append(by_month.get((year, month), 0))
    return labels, values


def plan_mix():
    """Active/trialing subscriptions grouped by plan — current snapshot."""
    qs = (
        Subscription.all_tenants.exclude(status__in=['expired', 'cancelled'])
        .values('plan__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    return [{'plan': row['plan__name'], 'count': row['count']} for row in qs]


def mrr_by_plan():
    """Current MRR broken down per plan (monthly plans at face value,
    yearly plans divided by 12) — same convention as the platform_admin
    dashboard's single MRR figure, just split out per plan."""
    active_subs = Subscription.all_tenants.filter(status='active').select_related('plan')
    totals = {}
    for s in active_subs:
        monthly_value = s.plan.price_amount / 12 if s.plan.billing_interval == 'yearly' else s.plan.price_amount
        totals[s.plan.name] = totals.get(s.plan.name, 0) + monthly_value
    return sorted(({'plan': name, 'mrr': total} for name, total in totals.items()), key=lambda r: r['mrr'], reverse=True)
