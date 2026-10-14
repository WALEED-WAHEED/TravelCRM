"""
Load sample ledger data for one agency, for demos and local testing.

The supplier account mirrors the real "Abu Saleh Travel & Tours" statement
(NAHD_Leger.pdf, 01-07-2025 to 27-10-2025) from the agency's side: their
debits (MOFA/hotel/ticket charges) are supplier bills here, and their
credits (NAHD's bank transfers) are payments made. Closing balance:
7,263 Dr — the supplier holds an advance. (The PDF prints 7,265: its
amounts carry hidden decimals, so the rows as printed sum 2 rupees off.)

Client sales/receipts and current-month expenses are added so every card
and filter on the ledger page has something to show.

    python manage.py seed_ledger_sample --agency "Nahd Travels"
    python manage.py seed_ledger_sample --agency "Nahd Travels" --reset
"""
import datetime
import random
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from agencies.models import Agency
from member.models import Booking, LedgerEntry
from utils.tenancy import tenant_context

SUPPLIER = "Abu Saleh Travel & Tours"
MARKER = "sample"  # stored in counterparty_type (not shown in the UI) so --reset only removes seeded rows
PAY_TEXT = "Payment transfer to Ahmad Fareed MBL acc against approval"

# (date, NAHD-side mode, type, trans_no, particulars, pax, rate, amount)
# "bill" = supplier charged us (credit), "paid" = we paid them (debit).
SUPPLIER_ROWS = [
    ("2025-07-10", "paid", "payment", "BR-2-104280", PAY_TEXT, None, "76.00", 400000),
    ("2025-07-11", "bill", "visa", "UB-101040", "Shireen Saba", 3, "77.00", 180180),
    ("2025-07-11", "bill", "hotel", "UB-101040", "Shireen Saba", 3, "77.00", 227150),
    ("2025-07-24", "paid", "payment", "BR-2-104427", "Payment transfer to Noor Al Hojj against approval", None, "77.75", 300000),
    ("2025-07-26", "bill", "visa", "UB-101069", "Habib Ur Rehman", 7, "77.75", 370090),
    ("2025-07-26", "bill", "hotel", "UB-101069", "Habib Ur Rehman", 7, "77.75", 265128),
    ("2025-07-26", "paid", "payment", "BR-2-104457", "Payment transfer to Ahmad Fareed MBL against approval", None, "77.75", 200000),
    ("2025-08-06", "paid", "payment", "BR-2-104559", PAY_TEXT, None, "77.75", 150000),
    ("2025-08-18", "paid", "payment", "BR-2-104642", PAY_TEXT, None, "77.75", 1000000),
    ("2025-08-18", "bill", "ticket", "TK-1-100411", "Ali Saad : 214-2429-136-674, 99KZCP", 5, "77.75", 789000),
    ("2025-08-18", "bill", "hotel", "UB-101099", "Aftab Aslam Malik", 5, "77.75", 1115713),
    ("2025-08-18", "bill", "visa", "UB-101099", "Aftab Aslam Malik", 5, "77.75", 314888),
    ("2025-08-19", "bill", "journal", "JV-2-104800", "Flight change charges 400 SR", None, "77.75", None),  # 400 SAR
    ("2025-08-20", "paid", "payment", "BR-2-104677", PAY_TEXT, None, "77.75", 1000000),
    ("2025-08-27", "paid", "journal", "JV-2-104742", "Payment less approval of Saleh Bhai for NAHD Travel", None, "77.75", 7600),
    ("2025-08-28", "paid", "payment", "BR-2-104759", PAY_TEXT, None, "77.75", 200000),
    ("2025-09-17", "paid", "payment", "BR-2-104918", PAY_TEXT, None, "77.75", 500000),
    ("2025-10-08", "bill", "visa", "UB-101162", "Hamayun Majeed", 5, "77.50", 320850),
    ("2025-10-08", "bill", "hotel", "UB-101162", "Hamayun Majeed", 5, "77.50", 166238),
    ("2025-10-18", "paid", "payment", "BR-2-105182", PAY_TEXT, None, "77.75", 30000),
]

# (date, party, mode, type, particulars, pax, amount, method)
CLIENT_ROWS = [
    ("2025-07-11", "Shireen Saba", "sale", "package", "Umrah package — visa + Makkah/Madina hotel", 3, 450000, ""),
    ("2025-07-15", "Shireen Saba", "received", "receipt", "Full payment received", None, 450000, "cash"),
    ("2025-07-26", "Habib Ur Rehman", "sale", "package", "Umrah package — visa + hotel", 7, 700000, ""),
    ("2025-07-30", "Habib Ur Rehman", "received", "receipt", "Advance received via Meezan transfer", None, 500000, "bank_transfer"),
    ("2025-08-18", "Ali Saad", "sale", "ticket", "Return tickets LHE-JED", 5, 850000, ""),
    ("2025-08-21", "Ali Saad", "received", "receipt", "Ticket payment received", None, 850000, "bank_transfer"),
    ("2025-08-18", "Aftab Aslam Malik", "sale", "package", "Umrah package — visa, hotel, transport", 5, 1600000, ""),
    ("2025-08-25", "Aftab Aslam Malik", "received", "receipt", "Part payment by cheque", None, 1200000, "cheque"),
    ("2025-10-08", "Hamayun Majeed", "sale", "package", "Umrah package — visa + hotel", 5, 560000, ""),
    ("2025-10-12", "Hamayun Majeed", "received", "receipt", "Advance received", None, 300000, "cash"),
]

# Current-month activity, relative to today: (day offset into month, ...)
RECENT_CLIENT_ROWS = [
    (1, "Rizwan Ahmed", "sale", "ticket", "Tickets ISB-MED for family", 2, 210000, ""),
    (4, "Rizwan Ahmed", "received", "receipt", "Advance received", None, 100000, "cash"),
]
BOOKING_PREFIX = "SMP-"  # voucher numbers of sample bookings, so --reset can find them
SAMPLE_CLIENTS = [
    "Al Noor Group", "Tariq Mehmood", "Bilal & Family", "Gulshan Travels (sub-agent)",
    "Nadia Hussain", "Faisal Textile Staff", "Madina Welfare Trust", "Usman Ghani",
]
SAMPLE_PACKAGES = [
    "15 Days Economy Umrah", "21 Days Standard Umrah", "10 Days Executive Umrah",
    "Ramadan Last Ashra Umrah", "Ziyarat Iraq & Iran Tour",
]
RECENT_EXPENSES = [
    (0, "Rent", "Office rent", 85000, "bank_transfer"),
    (3, "Salary", "Staff salaries", 240000, "bank_transfer"),
    (5, "Fuel", "Fuel for office vehicle", 12500, "cash"),
    (5, "Utilities", "Electricity and internet bills", 18400, "cash"),
]


def _d(s):
    return datetime.date.fromisoformat(s)


class Command(BaseCommand):
    help = "Load sample ledger entries (supplier statement from the NAHD sample PDF, clients, expenses)."

    def add_arguments(self, parser):
        parser.add_argument("--agency", required=True, help="Agency name, e.g. \"Nahd Travels\"")
        parser.add_argument("--reset", action="store_true", help="Remove previously seeded sample rows first")

    def handle(self, *args, agency, reset, **options):
        with tenant_context(bypass=True):
            ag = Agency.objects.filter(name__iexact=agency).first()
        if not ag:
            raise CommandError(f'No agency named "{agency}".')
        owner = ag.users.filter(role__in=["member", "admin"]).order_by("id").first()

        with tenant_context(agency_id=ag.id), transaction.atomic():
            # Earlier versions tagged the category with "[sample]" instead.
            seeded = LedgerEntry.objects.filter(agency=ag).filter(
                Q(counterparty_type=MARKER) | Q(category__endswith="[sample]")
            )
            if seeded.exists():
                if not reset:
                    self.stdout.write(self.style.WARNING(
                        f"Sample data already loaded for {ag.name} ({seeded.count()} rows). Use --reset to reload."
                    ))
                    return
                n = seeded.count()
                seeded.delete()
                nb, _ = Booking.objects.filter(agency=ag, voucher_number__startswith=BOOKING_PREFIX).delete()
                self.stdout.write(f"Removed {n} previously seeded ledger rows and {nb} sample booking records.")

            def add(**kw):
                LedgerEntry.objects.create(
                    agency=ag, created_by=owner, currency=ag.default_currency or "PKR",
                    counterparty_type=MARKER, **kw,
                )

            for date, mode, ttype, trans, text, pax, rate, amount in SUPPLIER_ROWS:
                fx = {}
                if amount is None:  # the 400 SAR flight-change charge
                    fx = {"fx_currency": "SAR", "fx_amount": Decimal("400")}
                    amount = 0
                add(
                    transaction_date=_d(date), bucket="lein_dein", counterparty_name=SUPPLIER,
                    direction="credit" if mode == "bill" else "debit", transaction_type=ttype,
                    payment_method="bank_transfer" if ttype == "payment" else "",
                    trans_no=trans, description=text, pax=pax, rate=Decimal(rate),
                    amount=Decimal(amount), **fx,
                )

            for date, party, mode, ttype, text, pax, amount, method in CLIENT_ROWS:
                add(
                    transaction_date=_d(date), bucket="lein_dein", counterparty_name=party,
                    direction="debit" if mode == "sale" else "credit", transaction_type=ttype,
                    payment_method=method, description=text, pax=pax, amount=Decimal(amount),
                )

            month_start = datetime.date.today().replace(day=1)
            today = datetime.date.today()

            def recent(offset):
                return min(month_start + datetime.timedelta(days=offset), today)

            for offset, party, mode, ttype, text, pax, amount, method in RECENT_CLIENT_ROWS:
                add(
                    transaction_date=recent(offset), bucket="lein_dein", counterparty_name=party,
                    direction="debit" if mode == "sale" else "credit", transaction_type=ttype,
                    payment_method=method, description=text, pax=pax, amount=Decimal(amount),
                )
            for offset, category, text, amount, method in RECENT_EXPENSES:
                add(
                    transaction_date=recent(offset), bucket="company_expense", direction="debit",
                    transaction_type="expense", payment_method=method, description=text,
                    amount=Decimal(amount), category=category,
                )

            booking_count = self._seed_bookings(ag, owner, add, today)
            total = LedgerEntry.objects.filter(agency=ag, counterparty_type=MARKER).count()
        self.stdout.write(self.style.SUCCESS(
            f"Loaded {total} sample ledger entries and {booking_count} sample bookings for {ag.name}."
        ))

    def _seed_bookings(self, ag, owner, add, today):
        """A year of bookings, each with its ledger sale + payment(s), plus
        monthly rent and salaries —."""
        rng = random.Random(42)  # deterministic: same data every run
        staff = list(ag.users.filter(is_active=True).order_by("id")) or [owner]
        count = 0
        for i in range(30):
            days_ago = int(365 * (29 - i) / 29)
            created = today - datetime.timedelta(days=days_ago)
            if days_ago > 60:
                status = rng.choices(["completed", "cancelled"], [9, 1])[0]
            else:
                status = rng.choices(["confirmed", "draft", "cancelled"], [6, 2, 1])[0]
            adults = rng.randint(1, 6)
            children = rng.choice([0, 0, 1, 2])
            pax = adults + children
            value = Decimal(pax * rng.choice([95000, 120000, 145000, 180000]))
            client = rng.choice(SAMPLE_CLIENTS)
            package = rng.choice(SAMPLE_PACKAGES)
            b = Booking.objects.create(
                agency=ag, agent=rng.choice(staff), status=status,
                voucher_number=f"{BOOKING_PREFIX}{i + 1:04d}", package_name=package,
                client_company=client, pax_adults=adults, pax_children=children,
                total_price=value, total_amount=value,
            )
            # created_at is auto_now_add; backdate it so the timeline is realistic.
            Booking.all_tenants.filter(pk=b.pk).update(
                created_at=timezone.make_aware(datetime.datetime.combine(created, datetime.time(11, 0)))
            )
            count += 1
            if status not in ("confirmed", "completed"):
                continue
            add(
                transaction_date=created, bucket="lein_dein", counterparty_name=client, direction="debit",
                transaction_type="package", payment_method="", pax=pax, amount=value,
                description=f"{package} — {b.voucher_number}", inv_ref=b.voucher_number,
            )
            paid_share = Decimal("1") if status == "completed" else Decimal(rng.choice(["0.5", "0.6", "0.75"]))
            add(
                transaction_date=min(created + datetime.timedelta(days=rng.randint(1, 10)), today),
                bucket="lein_dein", counterparty_name=client, direction="credit", transaction_type="receipt",
                payment_method=rng.choice(["cash", "bank_transfer", "bank_transfer", "cheque"]),
                amount=(value * paid_share).quantize(Decimal("1")), inv_ref=b.voucher_number,
                description=f"Payment received for {b.voucher_number}",
            )
        # Monthly fixed costs for the 11 months before the current one.
        month = today.replace(day=1)
        for _ in range(11):
            month = (month - datetime.timedelta(days=1)).replace(day=1)
            for day, category, text, amount in [(1, "Rent", "Office rent", 85000), (5, "Salary", "Staff salaries", 240000)]:
                add(
                    transaction_date=month.replace(day=day), bucket="company_expense", direction="debit",
                    transaction_type="expense", payment_method="bank_transfer", description=text,
                    amount=Decimal(amount), category=category,
                )
        return count
