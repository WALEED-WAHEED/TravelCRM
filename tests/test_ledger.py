"""
Ledger: party statement math (matches the NAHD sample statement), the
simplified entry API (auto Trans.#, foreign-currency conversion,
validation), and the ledger page / export / printable statement.
"""
import datetime
from decimal import Decimal

import pytest

from utils.tenancy import tenant_context

PARTY = "NAHD TRAVEL & TOUR"


def _entry(agency, user, **kw):
    from member.models import LedgerEntry
    defaults = dict(
        transaction_date=datetime.date(2025, 7, 10), transaction_type="receipt", bucket="lein_dein",
        direction="credit", counterparty_name=PARTY, amount=Decimal("0"), payment_method="bank_transfer",
        description="entry", agency=agency, created_by=user,
    )
    defaults.update(kw)
    with tenant_context(bypass=True):
        return LedgerEntry.objects.create(**defaults)


@pytest.fixture
def sample_statement(agency_a, user_a):
    """First rows of the sample PDF: running balance -400,000 / -219,820 / 7,330."""
    _entry(agency_a, user_a, transaction_date=datetime.date(2025, 7, 10), transaction_type="receipt",
           direction="credit", amount=Decimal("400000"), rate=Decimal("76.00"),
           description="Payment transfer to Ahmad Fareed MBL")
    _entry(agency_a, user_a, transaction_date=datetime.date(2025, 7, 11), transaction_type="visa",
           direction="debit", amount=Decimal("180180"), pax=3, payment_method="", inv_ref="UB-101040",
           description="Shireen Saba")
    _entry(agency_a, user_a, transaction_date=datetime.date(2025, 7, 11), transaction_type="hotel",
           direction="debit", amount=Decimal("227150"), pax=3, payment_method="", inv_ref="UB-101040",
           description="Shireen Saba")


def test_party_statement_running_balance_matches_sample(agency_a, sample_statement):
    from member.ledger import party_statement
    with tenant_context(agency_id=agency_a.id):
        s = party_statement(agency_a, PARTY, datetime.date(2025, 7, 1), datetime.date(2025, 10, 27))
    assert [e.running for e in s["rows"]] == [Decimal("-400000"), Decimal("-219820"), Decimal("7330")]
    assert s["opening"] == 0
    assert s["debit"] == Decimal("407330") and s["credit"] == Decimal("400000")
    assert s["closing"] == Decimal("7330")
    assert s["pax"] == {"Visa / MOFA": 3, "Hotel": 3}


def test_opening_balance_carries_earlier_entries(agency_a, user_a, sample_statement):
    from member.ledger import party_statement
    _entry(agency_a, user_a, transaction_date=datetime.date(2025, 7, 24), direction="credit",
           amount=Decimal("300000"))
    with tenant_context(agency_id=agency_a.id):
        s = party_statement(agency_a, PARTY, datetime.date(2025, 7, 20), None)
    assert s["opening"] == Decimal("7330")
    assert s["rows"][0].running == Decimal("-292670")  # matches the sample's 24/07 row


def test_party_balances_split_receivable_and_payable(agency_a, user_a, sample_statement):
    from member.ledger import party_balances, receivable_payable
    _entry(agency_a, user_a, counterparty_name="Noor Al Hojj", transaction_type="hotel",
           direction="credit", amount=Decimal("50000"), payment_method="")
    with tenant_context(agency_id=agency_a.id):
        receivable, payable = receivable_payable(party_balances(agency_a))
    assert receivable == Decimal("7330")
    assert payable == Decimal("50000")


def test_trans_no_and_type_code_are_assigned(agency_a, user_a):
    cash = _entry(agency_a, user_a, transaction_type="receipt", payment_method="cash", amount=Decimal("10"))
    bank = _entry(agency_a, user_a, transaction_type="payment", direction="debit", amount=Decimal("10"))
    ticket = _entry(agency_a, user_a, transaction_type="ticket", direction="debit", amount=Decimal("10"))
    assert cash.type_code == "CR" and bank.type_code == "BP" and ticket.type_code == "TK"
    assert cash.trans_no == f"CR-{cash.pk:06d}"
    custom = _entry(agency_a, user_a, trans_no="BR-2-104280", amount=Decimal("10"))
    assert custom.trans_no == "BR-2-104280"


def test_api_converts_foreign_amount(client_a, agency_a):
    from member.models import LedgerEntry
    r = client_a.post("/api/v1/ledger/", {
        "transaction_date": "2025-08-19", "bucket": "lein_dein", "direction": "debit",
        "transaction_type": "journal", "counterparty_name": PARTY, "payment_method": "",
        "fx_currency": "SAR", "fx_amount": "400", "rate": "77.75",
        "description": "Flight change charges",
    })
    assert r.status_code == 201, r.content
    with tenant_context(agency_id=agency_a.id):
        e = LedgerEntry.objects.get(pk=r.json()["id"])
    assert e.amount == Decimal("31100.00")
    assert e.trans_no.startswith("JV-")


@pytest.mark.parametrize("payload,field", [
    ({"fx_currency": "SAR", "fx_amount": "400"}, "rate"),
    ({"amount": "100", "counterparty_name": ""}, "counterparty_name"),
    ({}, "amount"),
])
def test_api_validation(client_a, payload, field):
    data = {
        "transaction_date": "2025-08-19", "bucket": "lein_dein", "direction": "credit",
        "transaction_type": "receipt", "counterparty_name": PARTY, "payment_method": "cash",
        "description": "x",
    }
    data.update(payload)
    r = client_a.post("/api/v1/ledger/", data)
    assert r.status_code == 400
    assert field in r.json()


def test_expense_is_always_debit(client_a):
    r = client_a.post("/api/v1/ledger/", {
        "transaction_date": "2025-08-19", "bucket": "company_expense", "direction": "credit",
        "transaction_type": "expense", "amount": "5000", "payment_method": "cash", "description": "Rent",
    })
    assert r.status_code == 201, r.content
    assert r.json()["direction"] == "debit"


def test_ledger_page_and_partials_render(client_a, sample_statement):
    page = client_a.get("/member/ledger/")
    assert page.status_code == 200
    assert b"Parties owe you" in page.content

    party = client_a.get("/member/ledger/", {"party": PARTY, "from": "2025-07-01"}, HTTP_HX_REQUEST="true")
    assert party.status_code == 200
    assert b"Previous balance" in party.content and b"7,330 Dr" in party.content

    # Party filter suggestions carry each party's balance.
    assert b'label="7,330 Dr' in page.content


def test_export_csv(client_a, sample_statement):
    r = client_a.get("/member/ledger/export/", {"party": PARTY})
    assert r.status_code == 200
    text = r.content.decode("utf-8-sig")
    assert "Balance" in text.splitlines()[0]
    assert "7330" in text


def test_report_statement_layout(client_a, sample_statement):
    r = client_a.get("/member/ledger/report/", {"party": PARTY, "from": "2025-07-01", "to": "2025-10-27"})
    assert r.status_code == 200
    body = r.content.decode()
    assert "Account Ledger" in body and "Previous Balance" in body
    assert "407,330" in body and "Total Hotel PAX:" in body
    # All-parties mode (legacy month link) still works.
    assert client_a.get("/member/ledger/report/", {"month": "2025-07"}).status_code == 200


def test_other_agency_cannot_see_statement(client_b, sample_statement):
    r = client_b.get("/member/ledger/report/", {"party": PARTY, "preset": "all"})
    assert r.status_code == 200
    assert b"227,150" not in r.content


def test_seed_sample_matches_pdf_and_is_idempotent(agency_a, user_a):
    from django.core.management import call_command

    from member.ledger import party_statement
    from member.models import Booking, LedgerEntry

    call_command("seed_ledger_sample", agency="Agency A")
    call_command("seed_ledger_sample", agency="Agency A")  # second run is a no-op
    with tenant_context(agency_id=agency_a.id):
        s = party_statement(agency_a, "Abu Saleh Travel & Tours", datetime.date(2025, 7, 1), datetime.date(2025, 10, 27))
        count = LedgerEntry.objects.count()
        sample_bookings = Booking.objects.filter(voucher_number__startswith="SMP-")
        active = sample_bookings.filter(status__in=["confirmed", "completed"]).count()
        total_bookings = sample_bookings.count()
    # Mirror of the PDF rows as printed. The PDF's own footer says 3,780,335 /
    # -7,265: its amounts carry hidden decimals, so the printed rows sum 2 higher.
    assert s["credit"] == Decimal("3780337") and s["debit"] == Decimal("3787600")
    assert s["closing"] == Decimal("7263")
    assert s["pax"] == {"Visa / MOFA": 20, "Hotel": 20, "Ticket": 5}
    # ledger rows: PDF statement + client rows + (sale + payment) per active booking + 11 months x 2 fixed costs
    assert total_bookings == 30
    assert count == 36 + active * 2 + 22
