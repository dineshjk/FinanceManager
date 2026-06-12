# -*- coding: utf-8 -*-
# tests/inspect_db.py
#!/usr/bin/env python3
"""Inspect a SQLite DB: list tables and row counts for key tables."""
import os
import sqlite3
import sys


def inspect(path: str) -> None:
    if not os.path.exists(path):
        print(f"DB not found: {path}")
        return
    print(f"Inspecting DB: {path}")
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
    except sqlite3.Error as e:
        print(f"Failed to open DB: {e}")
        return
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        if not tables:
            print("No tables found in DB.")
            return
        print("Tables:")
        for t in tables:
            print(f" - {t}")
        print("")
        for t in ("transactions", "exchange_orders"):
            if t in tables:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {t}")
                    cnt = cur.fetchone()[0]
                except sqlite3.Error as e:
                    cnt = f"error: {e}"
                print(f"{t}: {cnt}")
            else:
                print(f"{t}: (not present)")
    finally:
        conn.close()


if __name__ == "__main__":
    # default legacy path next to current DB
    module_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(module_dir)
    default = os.path.join(repo_root, "..", "data", "mystocks_old.db")
    path = sys.argv[1] if len(sys.argv) > 1 else default
    inspect(os.path.abspath(path))
