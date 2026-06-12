#!/usr/bin/env python3
"""Audit the import by comparing the backup DB with the current live DB.

Produces a JSON report listing, for each legacy transaction, whether the
contract existed before, whether the transaction existed before, and which
exchange_orders were added.
"""

from pathlib import Path
import os
import sys
import json
from datetime import datetime

import sqlite3

LEGACY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "mystocks_old.db")


def find_latest_backup():
    # locate data dir from project STOCK_DB_PATH at runtime
    from Shared.globals import STOCK_DB_PATH

    DATA_DIR = Path(STOCK_DB_PATH).resolve().parent
    candidates = sorted(DATA_DIR.glob("mystocks.db.bak.*"))
    if not candidates:
        return None
    return str(candidates[-1])


def rows_for_contract(conn, cont_no):
    cur = conn.cursor()
    cur.execute("SELECT * FROM contracts WHERE cont_no = ?", (cont_no,))
    cols = [c[0] for c in cur.description] if cur.description else []
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def txs_for_contract(conn, cont_no):
    cur = conn.cursor()
    cur.execute("SELECT * FROM transactions WHERE cont_no = ?", (cont_no,))
    cols = [c[0] for c in cur.description] if cur.description else []
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def eos_for_trd(conn, id_trd):
    cur = conn.cursor()
    cur.execute("SELECT * FROM exchange_orders WHERE id_trd = ?", (id_trd,))
    cols = [c[0] for c in cur.description] if cur.description else []
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def audit():
    # ensure project root is importable and import project modules locally
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT))
    from StockMan.trade_from_file import _fetch_source_transactions
    from Shared.globals import STOCK_DB_PATH

    DATA_DIR = Path(STOCK_DB_PATH).resolve().parent

    if not os.path.exists(LEGACY):
        print("Legacy DB not found at", LEGACY)
        return

    backup = find_latest_backup()
    if not backup:
        print("No backup found in data directory:", DATA_DIR)
        return

    print("Using backup:", backup)
    print("Using live DB:", STOCK_DB_PATH)

    legacy_rows = _fetch_source_transactions(LEGACY)

    conn_bak = sqlite3.connect(backup)
    conn_now = sqlite3.connect(STOCK_DB_PATH)

    report = {
        # timezone-aware timestamp
        "generated_at": datetime.now().astimezone().isoformat(),
        "legacy_path": LEGACY,
        "backup_path": backup,
        "live_path": STOCK_DB_PATH,
        "entries": [],
    }

    for tx in legacy_rows:
        cont = tx.get("cont_no")
        entry = {
            "cont_no": cont,
            "company_name": tx.get("company_name"),
            "legacy_src_id": tx.get("src_id_trd"),
            "contract_in_backup": False,
            "contract_in_live": False,
            "transactions_in_backup": [],
            "transactions_in_live": [],
            "exchange_orders_new": [],
        }

        # contracts
        bak_contracts = rows_for_contract(conn_bak, cont)
        now_contracts = rows_for_contract(conn_now, cont)
        entry["contract_in_backup"] = len(bak_contracts) > 0
        entry["contract_in_live"] = len(now_contracts) > 0

        # transactions
        bak_txs = txs_for_contract(conn_bak, cont)
        now_txs = txs_for_contract(conn_now, cont)
        entry["transactions_in_backup"] = bak_txs
        entry["transactions_in_live"] = now_txs

        # For each live tx that matches a legacy-by-ord pairs, find new EO rows
        # Collect ord_no/ord_dt tuples from backup and live, then diff
        bak_eos = set()
        for b in bak_txs:
            bak_list = eos_for_trd(conn_bak, b["id_trd"])
            for e in bak_list:
                bak_eos.add((e["ord_no"], e["ord_dt"]))
        live_eos = set()
        # map live id_trd -> list
        for n in now_txs:
            nlist = eos_for_trd(conn_now, n["id_trd"])
            for e in nlist:
                live_eos.add((e["ord_no"], e["ord_dt"]))
        new_eos = []
        for o, d in sorted(live_eos - bak_eos):
            new_eos.append({"ord_no": o, "ord_dt": d})
        entry["exchange_orders_new"] = new_eos

        report["entries"].append(entry)

    # write report
    out = Path(DATA_DIR) / (
        "import_audit_" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".json"
    )
    with out.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    print("Audit written to:", out)


if __name__ == "__main__":
    audit()
