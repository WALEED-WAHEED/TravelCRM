from django.db import migrations

from notifications.engine import EVENT_CONFIG

TEMPLATE_NAMES = {
    'booking_confirmation': 'Default: Booking Confirmation',
    'payment_receipt': 'Default: Payment Receipt',
    'voucher_generated': 'Default: Voucher Generated',
    'booking_cancelled': 'Default: Booking Cancelled',
}


def seed(apps, schema_editor):
    EmailTemplate = apps.get_model('system_config', 'EmailTemplate')
    for event_type, config in EVENT_CONFIG.items():
        EmailTemplate.objects.get_or_create(
            agency=None,
            template_type=event_type,
            is_default=True,
            defaults={
                'name': TEMPLATE_NAMES[event_type],
                'subject': config['default_subject'],
                'html_content': config['default_body'],
                'text_content': '',
                'variables': ['booking', 'agency', 'payment', 'recipient_name', 'mutamer_names'],
                'is_active': True,
            },
        )


def unseed(apps, schema_editor):
    EmailTemplate = apps.get_model('system_config', 'EmailTemplate')
    EmailTemplate.objects.filter(agency__isnull=True, is_default=True, template_type__in=TEMPLATE_NAMES.keys()).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_initial'),
        ('system_config', '0010_auditlog_disable_rls'),
    ]

    operations = [
        migrations.RunPython(seed, reverse_code=unseed),
    ]
