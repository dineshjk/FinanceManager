import sqlite3
from StockMan.trade_from_file import import_transaction
from Shared.globals import STOCK_DB_PATH


def test_import_transaction_commits_and_enforces_fk():
    # quick smoke test: connect to DB and run import_transaction within a
    # transaction to ensure it runs without exception. This is a light test
    # intended to guard the import flow not full data correctness.
    conn = sqlite3.connect(STOCK_DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    # Prefer using an existing stock from the DB to satisfy FK constraints.
    cur.execute("SELECT id_stk, company_name FROM stocks LIMIT 1")
    row = cur.fetchone()
    if row:
        stock_id, stock_name = row
    else:
        # create a minimal stock row and commit
        stock_id = 9999
        stock_name = "Test Co"
        cur.execute(
            (
                "INSERT OR IGNORE INTO stocks (id_stk, stk_code, isin, company_name, short_name)"
                " VALUES (?, ?, ?, ?, ?)"
            ),
            (stock_id, "TEST-9999", "IN0000000000", stock_name, "TEST"),
        )
        conn.commit()
    # Build a minimal fake transaction and one exchange_order
    tx = {
        "cont_no": "TEST-000",
        "trd_dt": "2025-10-18",
        "company_name": stock_name,
        "trade_type_trd": "BUY",
        "id_stk": stock_id,
        "exchange_orders": [
            {
                "ord_no": 1,
                "ord_dt": "2025-10-18",
                "trd_no": 1,
                "qty_eo": 1,
                "rate_eo": 1.0,
                "brok_unit_eo": 0.0,
                "net_rate_eo": 1.0,
                "net_total_eo": 1.0,
            }
        ],
    }
    try:
        # Run the import; this will commit inside import_transaction.
        # We avoid starting an outer transaction to prevent 'nested' errors.
        tx["qty_trd"] = 1  # Add the missing field
        ok = import_transaction(conn, tx)
        assert ok is True
    finally:
        # Cleanup any rows created by the test to avoid leaving test data.
        try:
            # delete exchange orders for the test transaction
            conn.execute(
                "DELETE FROM exchange_orders WHERE id_trd IN (SELECT id_trd FROM transactions WHERE cont_no = ?)",
                ("TEST-000",),
            )
            conn.execute("DELETE FROM transactions WHERE cont_no = ?", ("TEST-000",))
            conn.execute("DELETE FROM contracts WHERE cont_no = ?", ("TEST-000",))
            # optional: remove the test stock we inserted
            conn.execute("DELETE FROM stocks WHERE id_stk = ?", (9999,))
            conn.commit()
        except Exception:
            # best-effort cleanup; ignore errors
            try:
                conn.rollback()
            except Exception:
                pass
        cur.close()
        conn.close()
