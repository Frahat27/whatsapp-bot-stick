"""
Tests para src/utils/dates.py
"""

from datetime import date, time

from src.utils.dates import (
    to_appsheet_date,
    from_appsheet_date,
    to_appsheet_time,
    from_appsheet_time,
)


class TestToAppSheetDate:
    """Formato de fechas para AppSheet API: MM/DD/YYYY."""

    def test_standard_date(self):
        assert to_appsheet_date(date(2026, 3, 15)) == "03/15/2026"

    def test_single_digit_month(self):
        assert to_appsheet_date(date(2026, 1, 5)) == "01/05/2026"

    def test_december(self):
        assert to_appsheet_date(date(2026, 12, 31)) == "12/31/2026"


class TestFromAppSheetDate:
    def test_standard(self):
        assert from_appsheet_date("03/15/2026") == date(2026, 3, 15)

    def test_empty_string(self):
        assert from_appsheet_date("") is None

    def test_invalid_format(self):
        assert from_appsheet_date("15/03/2026") is None  # DD/MM/YYYY no es válido

    def test_none_like(self):
        assert from_appsheet_date("") is None


class TestToAppSheetTime:
    def test_standard(self):
        assert to_appsheet_time(time(14, 30)) == "14:30:00"

    def test_morning(self):
        assert to_appsheet_time(time(9, 0)) == "09:00:00"


class TestFromAppSheetTime:
    def test_standard(self):
        assert from_appsheet_time("14:30:00") == time(14, 30, 0)

    def test_empty(self):
        assert from_appsheet_time("") is None

    def test_invalid(self):
        assert from_appsheet_time("invalid") is None
