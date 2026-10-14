from django.db import migrations


def backfill(apps, schema_editor):
    BookingMutamer = apps.get_model('member', 'BookingMutamer')
    qs = BookingMutamer.objects.filter(mutamer__isnull=False).select_related('mutamer')
    for bm in qs:
        bm.name = bm.mutamer.name
        bm.passport_number = bm.mutamer.passport_number or ''
        bm.visa_number = bm.mutamer.visa_number or ''
        bm.nationality = bm.mutamer.nationality or ''
        bm.gender = bm.mutamer.gender or ''
        bm.phone = bm.mutamer.phone or ''
        bm.email = bm.mutamer.email or ''
        bm.family_label = bm.mutamer.family_id or ''
        bm.save(update_fields=[
            'name', 'passport_number', 'visa_number', 'nationality', 'gender', 'phone', 'email', 'family_label',
        ])

    Voucher = apps.get_model('member', 'Voucher')
    qs = Voucher.objects.filter(mutamer__isnull=False).select_related('mutamer')
    for v in qs:
        v.mutamer_name = v.mutamer.name
        v.mutamer_passport_number = v.mutamer.passport_number or ''
        v.mutamer_visa_number = v.mutamer.visa_number or ''
        v.mutamer_nationality = v.mutamer.nationality or ''
        v.mutamer_gender = v.mutamer.gender or ''
        v.mutamer_phone = v.mutamer.phone or ''
        v.mutamer_email = v.mutamer.email or ''
        v.save(update_fields=[
            'mutamer_name', 'mutamer_passport_number', 'mutamer_visa_number',
            'mutamer_nationality', 'mutamer_gender', 'mutamer_phone', 'mutamer_email',
        ])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('member', '0016_bookingmutamer_snapshot_fields'),
    ]

    operations = [
        migrations.RunPython(backfill, reverse_code=noop),
    ]
