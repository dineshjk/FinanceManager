import importlib
import sys
from pathlib import Path
import sqlite3

# tempfile not needed; tmp_path fixture provides a temp folder


# Ensure project root is importable
tests_dir = Path(__file__).resolve().parent
project_root = tests_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

db_setup = importlib.import_module("StockMan.stock_database_setup")
globals_mod = importlib.import_module("Shared.globals")


def test_db_rejects_malformed_trd_dt(tmp_path):
    db_path = tmp_path / "test_db.sqlite"
    # create database
    # Ensure the package-level STOCK_DB_PATH is the tmp DB so create_database
    # actually creates the schema where we expect
    # Ensure both the globals module and database_setup point to our tmp DB
    # so the schema is created there (get_db_connection reads globals.STOCK_DB_PATH).
    globals_mod.STOCK_DB_PATH = str(db_path)
    db_setup.STOCK_DB_PATH = str(db_path)
    db_setup.create_database(None)

    # Attempt to insert into transactions with malformed date that should
    # fail the CHECK constraint (DB-level enforcement)
    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.cursor()
        # Create a minimal stock and contract so FK constraints are satisfied
        cur.execute(
            (
                "INSERT INTO stocks (company_name, stk_code, short_name, "
                "isin) VALUES (?, ?, ?, ?)"
            ),
            ("Tst", "TST", "TST", "IN0000000000"),
        )
        conn.commit()
        cur.execute("SELECT id_stk FROM stocks WHERE stk_code = ?", ("TST",))
        id_stk = cur.fetchone()[0]

        # Try to insert an invalid date into transactions
        try:
            cur.execute(
                (
                    "INSERT INTO transactions (id_stk, trd_dt, qty_trd, "
                    "net_amt_trd, trade_type_trd) VALUES (?, ?, ?, ?, 'BUY')"
                ),
                (id_stk, "2025-02-30", 10, 100.0),
            )
            conn.commit()
            assert False, "Expected IntegrityError due to malformed trd_dt"
        except sqlite3.IntegrityError:
            # Expected path: DB CHECK prevents insertion
            pass
