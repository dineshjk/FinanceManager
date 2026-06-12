#!/usr/bin/env python3
"""Repair deterministic link fields in an existing StockMan database."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def main() -> int:
    script_path = Path(__file__).resolve()
    repo_root = script_path.parent.parent
    workspace_parent = repo_root.parent
    if str(workspace_parent) not in sys.path:
        sys.path.insert(0, str(workspace_parent))

    db_setup = importlib.import_module("StockMan.stock_database_setup")
    globals_mod = importlib.import_module("Shared.globals")

    target_path = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else Path(db_setup.STOCK_DB_PATH).resolve()
    )

    globals_mod.STOCK_DB_PATH = str(target_path)
    db_setup.STOCK_DB_PATH = str(target_path)

    result = db_setup.run_schema_migrations()
    repairs = result.get("repaired", {})
    unresolved = result.get("unresolved", {})

    changed = {name: count for name, count in repairs.items() if count > 0}
    remaining = {name: count for name, count in unresolved.items() if count > 0}
    print(f"Database: {target_path}")
    if changed:
        print("Link repairs applied:")
        for name, count in changed.items():
            print(f" - {name}: {count}")
    else:
        print("No link repairs were needed.")
    if remaining:
        print("Unresolved links after verification:")
        for name, count in remaining.items():
            print(f" - {name}: {count}")
    else:
        print("Verification passed with no unresolved links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
