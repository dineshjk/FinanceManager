import importlib
import sys
from pathlib import Path
import pytest

# Ensure project root importable
tests_dir = Path(__file__).resolve().parent
project_root = tests_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

company_add = importlib.import_module("StockMan.company_add")
db_setup = importlib.import_module("StockMan.stock_database_setup")


def test_add_company_db_duplicate_raises_validation_error(tmp_path):
    db_path = tmp_path / "test_db.sqlite"
    # Ensure create_database uses our tmp path
    db_setup.STOCK_DB_PATH = str(db_path)  # type: ignore[attr-defined]
    db_setup.create_database(None)

    # First insertion should succeed
    ok, _ = company_add.add_company_db(
        "TST", "IN0000000000", "Test Co", "TST", "Test", 10.0, 0.01, 1, 0
    )
    assert ok

    # Second insertion with same stock code/ISIN should raise ValidationError
    valmod = importlib.import_module("StockMan.validation_utils")
    with pytest.raises(valmod.ValidationError):
        company_add.add_company_db(
            "TST",
            "IN0000000000",
            "Test Co 2",
            "TST2",
            "Test",
            10.0,
            0.01,
            1,
            0,
        )
