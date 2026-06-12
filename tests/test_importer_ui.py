#!/usr/bin/env python3
"""Programmatic test runner for the importer UI.

This opens a hidden Tk root, calls trade_entry_from_file() with auto_close=True
so the modal loads and then closes automatically. It prints status to stdout
so we can see if any exceptions occurred.
"""
from pathlib import Path
import sys

# ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import tkinter as tk
from StockMan.trade_from_file import trade_entry_from_file

print("Starting importer UI test")
root = tk.Tk()
root.withdraw()
try:
    trade_entry_from_file(root, src_db_path="mystocks_old.db", auto_close=True)
    print("trade_entry_from_file returned normally")
except Exception as e:
    print("trade_entry_from_file raised:", e)
    import traceback

    traceback.print_exc()
finally:
    try:
        root.destroy()
    except Exception:
        pass

print("Test finished")
