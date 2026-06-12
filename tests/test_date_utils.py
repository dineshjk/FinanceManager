import importlib
import sys
from pathlib import Path
import pytest

# Ensure project parent is on sys.path so 'StockMan' package can be imported
tests_dir = Path(__file__).resolve().parent
# parent of the StockMan package (project root)
project_root = tests_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

date_utils = importlib.import_module("StockMan.date_utils")


def test_is_valid_iso_date():
    assert date_utils.is_valid_iso_date("2025-10-11")
    assert not date_utils.is_valid_iso_date("2025-02-30")
    assert not date_utils.is_valid_iso_date("2025-13-01")
    assert not date_utils.is_valid_iso_date("not-a-date")


def test_normalize_iso_date_with_various_inputs():
    from datetime import date, datetime

    assert date_utils.normalize_iso_date(date(2025, 10, 11)) == "2025-10-11"
    assert (
        date_utils.normalize_iso_date(datetime(2025, 10, 11, 12, 0))
        == "2025-10-11"
    )
    assert date_utils.normalize_iso_date("2025-10-11") == "2025-10-11"
    assert date_utils.normalize_iso_date("2025-02-30") is None
    assert date_utils.normalize_iso_date(None) is None


def test_validate_iso_date_or_raise():
    assert date_utils.validate_iso_date_or_raise("2025-10-11") == "2025-10-11"
    with pytest.raises(ValueError):
        date_utils.validate_iso_date_or_raise(
            "2025-02-30", field_name="testdate"
        )
