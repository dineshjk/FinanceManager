import sqlite3

# Add project root to the Python path
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from StockMan.trade_from_file import import_transaction


def _create_schema(cur: sqlite3.Cursor) -> None:
    # Minimal schema for contracts, transactions, exchange_orders
    cur.execute(
        """
        CREATE TABLE contracts (
            cont_no INTEGER PRIMARY KEY,
            trd_dt TEXT,
            settle_no INTEGER,
            settle_dt TEXT,
            no_of_trades INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE transactions (
            id_trd INTEGER PRIMARY KEY AUTOINCREMENT,
            cont_no INTEGER,
            trd_dt TEXT,
            company_name TEXT,
            trade_type_trd TEXT,
            id_stk INTEGER,
            qty_trd INTEGER,
            wap_unit_trd REAL,
            brok_unit_trd REAL,
            net_amt_trd REAL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE exchange_orders (
            id_eo INTEGER PRIMARY KEY AUTOINCREMENT,
            id_trd INTEGER,
            ord_no INTEGER,
            ord_dt TEXT,
            trd_no INTEGER,
            qty_eo INTEGER,
            rate_eo REAL,
            brok_unit_eo REAL,
            net_rate_eo REAL,
            net_total_eo REAL
        )
        """
    )


def test_import_transaction_commits_and_fk_and_lastrowid(tmp_path):
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_file))

    try:
        cur = conn.cursor()
        _create_schema(cur)

        # Prepare a transaction dict with a single exchange_order
        tx = {
            "cont_no": 123,
            "trd_dt": "2025-01-01",
            "company_name": "UNITTEST CO",
            "trade_type_trd": "BUY",
            "id_stk": 1,
            "qty_trd": 100,
            "wap_unit_trd": 50.0,
            "brok_unit_trd": 5.0,
            "net_amt_trd": 5000.0,
            "exchange_orders": [
                {
                    "ord_no": 1,
                    "ord_dt": "2025-01-01",
                    "trd_no": 1,
                    "qty_eo": 100,
                    "rate_eo": 50.0,
                    "brok_unit_eo": 5.0,
                    "net_rate_eo": 50.0,
                    "net_total_eo": 5000.0,
                }
            ],
        }

        # Ensure foreign_keys is off initially for the test; import_transaction
        # should set PRAGMA foreign_keys = ON on the provided connection
        cur.execute("PRAGMA foreign_keys = OFF")
        cur.execute("PRAGMA foreign_keys")
        before = cur.fetchone()[0]
        assert before == 0

        ok = import_transaction(conn, tx)
        assert ok is True

        # After import_transaction runs on this connection, PRAGMA should be ON
        cur.execute("PRAGMA foreign_keys")
        after = cur.fetchone()[0]
        assert after == 1

        # Check that a transaction was inserted
        cur.execute("SELECT id_trd, cont_no, company_name FROM transactions")
        tr = cur.fetchone()
        assert tr is not None
        id_trd = tr[0]
        assert tr[1] == 123
        assert tr[2] == "UNITTEST CO"

        # Check exchange_orders reference the inserted transaction
        cur.execute(
            "SELECT id_trd FROM exchange_orders WHERE id_trd = ?", (id_trd,)
        )
        eo = cur.fetchone()
        assert eo is not None
        assert eo[0] == id_trd

    finally:
        conn.close()


def test_import_transaction_rejects_invalid_payload_and_rolls_back(tmp_path):
    db_file = tmp_path / "test_invalid.db"
    conn = sqlite3.connect(str(db_file))

    try:
        cur = conn.cursor()
        _create_schema(cur)

        ok = import_transaction(
            conn,
            {
                "cont_no": 123,
                "trd_dt": "2025-02-30",
                "company_name": "UNITTEST CO",
                "trade_type_trd": "BUY",
                "id_stk": 1,
                "qty_trd": 100,
                "exchange_orders": [],
            },
        )

        assert ok is False
        cur.execute("SELECT COUNT(*) FROM transactions")
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT COUNT(*) FROM contracts")
        assert cur.fetchone()[0] == 0
    finally:
        conn.close()


def test_import_transaction_replay_updates_existing_rows(tmp_path):
    db_file = tmp_path / "test_replay.db"
    conn = sqlite3.connect(str(db_file))

    try:
        cur = conn.cursor()
        _create_schema(cur)

        original_tx = {
            "cont_no": 123,
            "trd_dt": "2025-01-01",
            "company_name": "UNITTEST CO",
            "trade_type_trd": "BUY",
            "id_stk": 1,
            "qty_trd": 100,
            "wap_unit_trd": 50.0,
            "brok_unit_trd": 5.0,
            "net_amt_trd": 5000.0,
            "exchange_orders": [
                {
                    "ord_no": 1,
                    "ord_dt": "2025-01-01",
                    "trd_no": 1,
                    "qty_eo": 100,
                    "rate_eo": 50.0,
                    "brok_unit_eo": 5.0,
                    "net_rate_eo": 50.0,
                    "net_total_eo": 5000.0,
                }
            ],
        }
        replay_tx = {
            **original_tx,
            "qty_trd": 120,
            "wap_unit_trd": 55.0,
            "net_amt_trd": 6600.0,
            "exchange_orders": [
                {
                    "ord_no": 1,
                    "ord_dt": "2025-01-01",
                    "trd_no": 2,
                    "qty_eo": 120,
                    "rate_eo": 55.0,
                    "brok_unit_eo": 6.0,
                    "net_rate_eo": 55.0,
                    "net_total_eo": 6600.0,
                }
            ],
        }

        assert import_transaction(conn, original_tx) is True
        assert import_transaction(conn, replay_tx) is True

        cur.execute("SELECT COUNT(*) FROM transactions")
        assert cur.fetchone()[0] == 1

        cur.execute(
            "SELECT qty_trd, wap_unit_trd, net_amt_trd FROM transactions"
        )
        transaction_row = cur.fetchone()
        assert transaction_row == (120, 55.0, 6600.0)

        cur.execute("SELECT COUNT(*) FROM exchange_orders")
        assert cur.fetchone()[0] == 1

        cur.execute(
            "SELECT trd_no, qty_eo, rate_eo, net_total_eo FROM exchange_orders"
        )
        order_row = cur.fetchone()
        assert order_row == (2, 120, 55.0, 6600.0)
    finally:
        conn.close()


def test_import_transaction_rejects_exchange_order_qty_mismatch(tmp_path):
    db_file = tmp_path / "test_qty_mismatch.db"
    conn = sqlite3.connect(str(db_file))

    try:
        cur = conn.cursor()
        _create_schema(cur)

        ok = import_transaction(
            conn,
            {
                "cont_no": 123,
                "trd_dt": "2025-01-01",
                "company_name": "UNITTEST CO",
                "trade_type_trd": "BUY",
                "id_stk": 1,
                "qty_trd": 100,
                "exchange_orders": [
                    {
                        "ord_no": 1,
                        "ord_dt": "2025-01-01",
                        "trd_no": 1,
                        "qty_eo": 60,
                        "rate_eo": 50.0,
                    },
                    {
                        "ord_no": 2,
                        "ord_dt": "2025-01-01",
                        "trd_no": 2,
                        "qty_eo": 30,
                        "rate_eo": 50.0,
                    },
                ],
            },
        )

        assert ok is False
        cur.execute("SELECT COUNT(*) FROM contracts")
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT COUNT(*) FROM transactions")
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT COUNT(*) FROM exchange_orders")
        assert cur.fetchone()[0] == 0
    finally:
        conn.close()
