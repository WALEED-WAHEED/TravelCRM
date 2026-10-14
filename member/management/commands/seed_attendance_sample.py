"""
Load sample attendance for one agency: four sample staff with this month's
check-ins (present / late / absent / leave, verified by Wi-Fi + QR, one field
rep checking in from Jeddah), today's board, and two pending correction requests.

If no check-in rules are switched on yet, it also turns on Office Wi-Fi
(127.0.0.1, so it works on this computer) + QR code and sets an office location.

    python manage.py seed_attendance_sample --agency "Nahd Travels"
    python manage.py seed_attendance_sample --agency "Nahd Travels" --reset
"""
import datetime
import random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from agencies.models import Agency
from member import attendance as att
from member.models import AttendanceCorrection, AttendanceLog
from rbac.models import Role
from utils.tenancy import tenant_context

SAMPLE_PREFIX = "sample_staff_"
OFFICE = (31.520400, 74.358700)   # Lahore
JEDDAH = (21.679564, 39.156536)   # King Abdulaziz Intl. Airport
STAFF = [
    ("Bilal", "Ahmed", False),
    ("Ayesha", "Khan", False),
    ("Usman", "Tariq", True),   # field staff
    ("Sana", "Iqbal", False),
]


class Command(BaseCommand):
    help = "Load sample attendance data (sample staff, this month's records, pending corrections)."

    def add_arguments(self, parser):
        parser.add_argument("--agency", required=True)
        parser.add_argument("--reset", action="store_true", help="Remove previously seeded sample attendance first")

    def handle(self, *args, agency, reset, **options):
        with tenant_context(bypass=True):
            ag = Agency.objects.filter(name__iexact=agency).first()
        if not ag:
            raise CommandError(f'No agency named "{agency}".')
        with tenant_context(agency_id=ag.id), transaction.atomic():
            if AttendanceLog.objects.filter(agency=ag, check_in_meta__sample=True).exists():
                if not reset:
                    self.stdout.write(self.style.WARNING("Sample attendance already loaded. Use --reset to reload."))
                    return
                AttendanceLog.objects.filter(agency=ag, check_in_meta__sample=True).delete()
                AttendanceCorrection.objects.filter(agency=ag, reason__startswith="[sample]").delete()
            self._seed(ag)

    def _seed(self, ag):
        s = att.get_settings(ag)
        if not (s.require_network or s.require_qr or s.require_location):
            s.require_network = s.require_qr = True
            s.office_ips = sorted(set(s.office_ips or []) | {"127.0.0.1"})
            s.office_lat, s.office_lng = OFFICE
            s.save()
            self.stdout.write("Switched on Office Wi-Fi (127.0.0.1) + QR code and set the office location (Lahore).")

        agent_role = Role.all_tenants.filter(agency__isnull=True, is_template=True, name="Agent").first()
        staff = []
        for i, (first, last, field) in enumerate(STAFF, 1):
            u, created = User.objects.get_or_create(
                username=f"{SAMPLE_PREFIX}{i}",
                defaults={"first_name": first, "last_name": last, "role": "agent", "agency": ag,
                          "custom_role": agent_role, "email": f"{first.lower()}@example.com"},
            )
            if created:
                u.set_unusable_password()  # sample people, not real logins
                u.save(update_fields=["password"])
            if field:
                s.field_staff.add(u)
            staff.append((u, field))
        # The real agent account gets history too (but not today, so you can check in live).
        real_agents = [(u, False) for u in ag.users.filter(role="agent", is_active=True)
                       .exclude(username__startswith=SAMPLE_PREFIX)]

        tz = att.office_tz(s)
        today = att.office_now(s).date()
        rng = random.Random(7)
        count = 0

        def make(u, field, day, status, t_in=None, t_out=None, source="self"):
            nonlocal count
            meta = {"sample": True, "mode": "field" if field else "office"}
            if status in ("present", "late"):
                if field:
                    meta.update({"lat": JEDDAH[0], "lng": JEDDAH[1], "accuracy": 18, "checks": {"location": True}})
                else:
                    meta.update({"ip": "127.0.0.1", "lat": OFFICE[0] + 0.0001, "lng": OFFICE[1], "accuracy": 22,
                                 "distance_m": 11, "checks": {"network": True, "qr": True}})
            fields = {"user": u, "status": status, "source": "field" if field and source == "self" else source,
                      "check_in_meta": meta}
            if t_in:
                fields["check_in_time"] = t_in
                fields["check_in_at"] = timezone.make_aware(datetime.datetime.combine(day, t_in), tz)
            if t_out:
                fields["check_out_time"] = t_out
                fields["check_out_at"] = timezone.make_aware(datetime.datetime.combine(day, t_out), tz)
                fields["work_hours"] = round((fields["check_out_at"] - fields["check_in_at"]).seconds / 3600, 2)
            if status == "absent":
                fields["notes"] = "No check-in by the absent cut-off."
            if status == "leave":
                fields["notes"] = "Approved leave."
            AttendanceLog.objects.update_or_create(agency=ag, person_name=u.full_name, date=day, defaults=fields)
            count += 1

        def t(h, m):
            return datetime.time(h, m)

        day = today.replace(day=1)
        while day < today:
            if day.weekday() in (s.work_days or []):
                for u, field in staff + real_agents:
                    roll = rng.random()
                    if roll < 0.70:
                        make(u, field, day, "present", t(8, rng.randint(35, 59)) if rng.random() < .5 else t(9, rng.randint(0, 14)),
                             t(rng.choice([17, 18]), rng.randint(5, 55)))
                    elif roll < 0.85:
                        make(u, field, day, "late", t(9, rng.randint(20, 59)) if rng.random() < .7 else t(10, rng.randint(0, 40)),
                             t(18, rng.randint(10, 59)))
                    elif roll < 0.93:
                        make(u, field, day, "absent", source="auto")
                    else:
                        make(u, field, day, "leave", source="correction")
            day += datetime.timedelta(days=1)

        # Today: two in, one late, one field rep at the airport; Sana not in yet.
        (bilal, _), (ayesha, _), (usman, _), (sana, _) = staff
        make(bilal, False, today, "present", t(8, 52))
        make(ayesha, False, today, "late", t(9, 41))
        make(usman, True, today, "present", t(7, 30))

        yesterday = today - datetime.timedelta(days=1)
        AttendanceCorrection.objects.get_or_create(
            agency=ag, user=ayesha, date=yesterday, requested_status="present",
            defaults={"requested_check_in": t(9, 0), "requested_check_out": t(18, 0),
                      "reason": "[sample] Phone battery died at the door — I arrived at 9:00."},
        )
        AttendanceCorrection.objects.get_or_create(
            agency=ag, user=sana, date=today, requested_status="leave",
            defaults={"reason": "[sample] Family emergency, informed the manager by phone."},
        )
        self.stdout.write(self.style.SUCCESS(
            f"Loaded {count} sample attendance records for {len(staff)} sample staff"
            f"{' + your agent account' if real_agents else ''}, and 2 pending corrections."
        ))
