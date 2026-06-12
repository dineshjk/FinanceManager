# -*- coding: utf-8 -*-
# scripts/importer_cli.py
r"""Importer CLI: preview (dry-run) or commit imports from a legacy DB into the
app DB.

Usage:
    python scripts/importer_cli.py --src data/mystocks_old.db --action preview
    python scripts/importer_cli.py --src data/mystocks_old.db --action commit

The preview runs all imports inside a rollback and reports counts. The commit
creates a timestamped backup of the app DB and then performs the imports.
"""

from __future__ import annotations

import argparse
import shutil
import datetime
import os
import runpy
import sqlite3
from typing import Tuple

from StockMan.trade_from_file import (
    _fetch_source_transactions,
    import_transaction,
)
from Shared.globals import STOCK_DB_PATH


def run_cli(src: str, action: str) -> Tuple[int, int]:
    """Run preview or commit import from src into STOCK_DB_PATH.

    Returns (imported_count, failed_count).
    """
    src = os.path.abspath(src)
    if not os.path.exists(src):
        raise FileNotFoundError(f"Source DB not found: {src}")

    rows = _fetch_source_transactions(src)
    total = len(rows)
    print(f"Found {total} transactions in source DB: {src}")

    if action == "preview":
        imported = 0
        failed = 0
        with sqlite3.connect(STOCK_DB_PATH) as conn:
            try:
                conn.execute("BEGIN")
            except Exception:
                pass
            for tx in rows:
                ok = import_transaction(conn, tx)
                if ok:
                    imported += 1
                else:
                    failed += 1
            try:
                conn.rollback()
            except Exception:
                pass

        # keep this line shorter for linters by avoiding a long f-string
        print("Preview complete: would import", imported, "would fail", failed)
        return imported, failed

    if action == "commit":
        # backup (build path without a very long f-string to satisfy linters)
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        bak = STOCK_DB_PATH + ".pre_import_bak." + ts
        print("Creating backup:", bak)
        shutil.copy2(STOCK_DB_PATH, bak)

        imported = 0
        failed = 0
        with sqlite3.connect(STOCK_DB_PATH) as conn:
            for tx in rows:
                ok = import_transaction(conn, tx)
                if ok:
                    imported += 1
                else:
                    failed += 1

        print("Commit complete:", imported, "imported,", failed, "failed")
        # Run audit script to regenerate CSV (best-effort)
        audit_dir = os.path.dirname(__file__)
        audit_script = os.path.join(audit_dir, "importer_audit.py")
        try:
            print("Running importer audit to regenerate data/import_audit.csv")
            runpy.run_path(audit_script, run_name="__main__")
        except Exception:
            print("Failed to run audit script (non-fatal)")
        return imported, failed

    raise ValueError("Unknown action: " + action)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--src", required=True, help="Path to legacy SQLite DB")
    p.add_argument(
        "--action",
        choices=["preview", "commit"],
        default="preview",
    )
    args = p.parse_args()
    try:
        imported, failed = run_cli(args.src, args.action)
        print("Finished:", imported, "imported,", failed, "failed")
    except Exception as exc:
        print("Error during run:", exc)


if __name__ == "__main__":
    main()
