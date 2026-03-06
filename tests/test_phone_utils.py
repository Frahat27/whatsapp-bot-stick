"""
Tests para src/utils/phone.py
"""

from src.utils.phone import normalize_phone, to_whatsapp_format, is_admin_phone


class TestNormalizePhone:
    """Tests de normalización de teléfono argentino."""

    def test_full_international_with_plus(self):
        assert normalize_phone("+5491123266671") == "1123266671"

    def test_full_international_no_plus(self):
        assert normalize_phone("5491123266671") == "1123266671"

    def test_ten_digits(self):
        assert normalize_phone("1123266671") == "1123266671"

    def test_with_spaces_and_dashes(self):
        assert normalize_phone("+54 9 11 2326-6671") == "1123266671"

    def test_with_leading_zero(self):
        assert normalize_phone("01123266671") == "1123266671"

    def test_without_nine(self):
        """54 sin 9 (formato fijo)."""
        assert normalize_phone("541123266671") == "1123266671"

    def test_short_number(self):
        """Número corto — devuelve tal cual."""
        assert normalize_phone("12345") == "12345"

    def test_cynthia_phone(self):
        assert normalize_phone("5491171342438") == "1171342438"

    def test_cynthia_phone_full(self):
        assert normalize_phone("+54 9 11 7134-2438") == "1171342438"


class TestToWhatsAppFormat:
    def test_from_normalized(self):
        assert to_whatsapp_format("1123266671") == "5491123266671"

    def test_from_full(self):
        assert to_whatsapp_format("+5491123266671") == "5491123266671"


class TestIsAdminPhone:
    def test_franco_is_admin(self):
        admins = ["1123266671", "1171342438"]
        assert is_admin_phone("5491123266671", admins) is True

    def test_cynthia_is_admin(self):
        admins = ["1123266671", "1171342438"]
        assert is_admin_phone("+54 9 11 7134-2438", admins) is True

    def test_patient_is_not_admin(self):
        admins = ["1123266671", "1171342438"]
        assert is_admin_phone("5491155554444", admins) is False
