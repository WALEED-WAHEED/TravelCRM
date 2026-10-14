"""
Single source of truth for the languages this product supports.
Referenced by settings.LANGUAGES, accounts.User.preferred_language,
assistant.models.ChatSession's language choices, and the Settings ->
Language picker — never duplicate this list elsewhere.

Deliberately has no Django imports (no models, no settings) so both
settings.py and models.py can import it without circularity.
"""

SUPPORTED_LANGUAGES = [
    ('en', 'English'),
    ('ur', 'Urdu'),
    ('ar', 'Arabic'),
    ('hi', 'Hindi'),
    ('es', 'Spanish'),
    ('fr', 'French'),
    ('de', 'German'),
]

# The languages actually offered in the UI right now (settings.LANGUAGES and
# the Settings -> Language picker). Model choices keep the full list above so
# narrowing this never needs a migration; a stored code outside it simply
# falls back to the default language.
ENABLED_LANGUAGES = [
    ('en', 'English'),
    ('ur', 'Urdu'),
    ('ar', 'Arabic'),
]

# Each language written in itself, so it can be found whatever the UI language is.
NATIVE_NAMES = {'en': 'English', 'ur': 'اردو', 'ar': 'العربية'}

RTL_LANGUAGES = {'ur', 'ar'}
