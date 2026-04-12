from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import re


def validate_phone_number(value):
    """
    Validate phone number format
    Accepts: +1234567890, 1234567890, etc.
    """
    pattern = r'^\+?1?\d{9,15}$'
    if not re.match(pattern, value):
        raise ValidationError(
            _('%(value)s is not a valid phone number'),
            params={'value': value},
        )


def validate_passport_number(value):
    """
    Validate passport number format
    Accepts alphanumeric passport numbers
    """
    pattern = r'^[A-Z0-9]{6,12}$'
    if not re.match(pattern, value.upper()):
        raise ValidationError(
            _('%(value)s is not a valid passport number'),
            params={'value': value},
        )


def validate_positive_amount(value):
    """
    Validate that amount is positive
    """
    if value < 0:
        raise ValidationError(
            _('Amount must be positive'),
        )


def validate_currency_code(value):
    """
    Validate 3-letter currency code (ISO 4217)
    """
    pattern = r'^[A-Z]{3}$'
    if not re.match(pattern, value.upper()):
        raise ValidationError(
            _('%(value)s is not a valid currency code'),
            params={'value': value},
        )

