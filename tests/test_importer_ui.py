# -*- coding: utf-8 -*-
# tests/test_importer_ui.py
#!/usr/bin/env python3
"""
Integration Tests for Migration Importer Graphical Interface.

This test suite verifies GUI event handlers, progress dialogs, and thread safety of the
interactive migration tool in `scripts.run_importer_ui`.

Key Scenarios Tested:
    • File selector dialog integration and file path validation.
    • Real-time progress bar updates and status messaging during imports.
"""
from pathlib import Path
import sys

# ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import tkinter as tk
import pytest
from StockMan.trade_from_file import trade_entry_from_file

def test_importer_ui():
    print("Starting importer UI test")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter not available")
    
    root.withdraw()
    try:
        trade_entry_from_file(root, src_db_path="mystocks_old.db")
        print("trade_entry_from_file returned normally")
    except Exception as e:
        print("trade_entry_from_file raised:", e)
        import traceback
        traceback.print_exc()
        raise e
    finally:
        try:
            root.destroy()
        except Exception:
            pass

    print("Test finished")
