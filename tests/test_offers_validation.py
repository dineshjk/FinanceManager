import importlib
import sys
from pathlib import Path
import pytest

# Ensure project root is importable
tests_dir = Path(__file__).resolve().parent
project_root = tests_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

offers = importlib.import_module("StockMan.offers")
db_setup = importlib.import_module("StockMan.stock_database_setup")
valmod = importlib.import_module("StockMan.validation_utils")


def test_add_ipo_invalid_date_raises(tmp_path):
    db_path = tmp_path / "test_db.sqlite"
    db_setup.STOCK_DB_PATH = str(db_path)
    db_setup.create_database(None)

    # Using invalid date should raise ValidationError
    with pytest.raises(valmod.ValidationError):
        offers.add_ipo(1, "IPO X", open_dt="2025-02-30")


def test_add_rights_invalid_date_raises(tmp_path):
    db_path = tmp_path / "test_db2.sqlite"
    db_setup.STOCK_DB_PATH = str(db_path)
    db_setup.create_database(None)

    with pytest.raises(valmod.ValidationError):
        offers.add_rights_issue(1, "Rights Y", allotment_dt="not-a-date")
