"""
Regression test for a real bug found during Phase 11 live-flow testing:
deleting an Agency (e.g. offboarding a tenant) crashed, because the
audit-log post_delete signal tried to write a log entry referencing the
agency being deleted in the very same transaction — a foreign-key
violation on every single tenant deletion. Fixed in utils/audit.py.
"""
from datetime import date

import pytest

from utils.tenancy import tenant_context


@pytest.mark.django_db
def test_deleting_an_agency_does_not_raise(agency_a, user_a, hotel_a):
    """The actual crash scenario: an agency with dependent rows across
    multiple models, including LedgerEntry (whose __str__ dereferences
    `self.agency.name` — a second way the same root cause could bite),
    deleted the way Super Admin's tenant-offboarding flow would do it."""
    from agencies.models import Agency
    from member.models import LedgerEntry

    with tenant_context(bypass=True):
        LedgerEntry.objects.create(
            agency=agency_a, transaction_date=date.today(), transaction_type="expense",
            payment_method="cash", amount=50, description="regression test entry",
        )
        # Must not raise IntegrityError/DoesNotExist.
        Agency.objects.filter(pk=agency_a.pk).delete()
        assert not Agency.objects.filter(pk=agency_a.pk).exists()


@pytest.mark.django_db
def test_deleted_agencys_children_log_with_no_dangling_agency_reference(agency_a, user_a, hotel_a):
    """The audit trail for cascade-deleted rows must reference agency=NULL
    (not the vanished agency id), while still keeping the human-readable
    object_repr — the whole point of not losing the audit record."""
    from agencies.models import Agency
    from system_config.models import AuditLog

    with tenant_context(bypass=True):
        Agency.objects.filter(pk=agency_a.pk).delete()
        entries = AuditLog.all_tenants.filter(model_name="Hotel", action="delete", object_id=str(hotel_a.pk))
        assert entries.exists()
        entry = entries.first()
        assert entry.agency_id is None
        assert hotel_a.name in entry.object_repr
