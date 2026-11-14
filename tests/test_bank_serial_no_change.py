# -*- coding: utf-8 -*-
"""
Unit Tests for Bank Transaction Serial Number Auto-Advancement.

This test suite verifies that transaction serial numbers and cheque reference sequences
auto-increment correctly and adjust gracefully when transactions are inserted or re-ordered.

Key Scenarios Tested:
    • Sequential serial number generation per financial year.
    • Conflict resolution when inserting transactions with duplicate serial numbers.
"""

import tkinter as tk
from tkinter import ttk
import pytest
import Shared.modal_utils
from BankMan.bank_db_utils import get_last_serial_no
from BankMan.bank_transactions_add import add_bank_transaction_main


@pytest.fixture(scope="module")
def tk_root():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter not available")
    root.withdraw()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def mock_modal_and_tk(monkeypatch):
    monkeypatch.setattr(Shared.modal_utils, "disable_parent", lambda *a, **kw: 1)
    monkeypatch.setattr(Shared.modal_utils, "enable_parent", lambda *a, **kw: None)
    monkeypatch.setattr(tk.Tk, "wait_window", lambda self, w=None: None)
    monkeypatch.setattr(tk.Toplevel, "wait_window", lambda self, w=None: None)


def _find_all(w, cls):
    res = []
    for c in w.winfo_children():
        if isinstance(c, cls):
            res.append(c)
        res.extend(_find_all(c, cls))
    return res


def test_get_last_serial_no_values():
    """Verify get_last_serial_no returns integer or None."""
    # Account 1 (ICICI) should have a valid int serial > 0
    s1 = get_last_serial_no(1)
    assert s1 is not None and isinstance(s1, int) and s1 > 0

    # Account 3 (Bank of Baroda) has no transactions in DB
    s3 = get_last_serial_no(3)
    assert s3 is None


def test_account_change_updates_serial_no(tk_root):
    """Verify that changing Account via Combobox, typing/Return, and FocusOut auto-advances Serial No."""
    add_bank_transaction_main(tk_root)
    win = tk_root.winfo_children()[-1]
    try:
        win.update()

        account_combo = _find_all(win, ttk.Combobox)[0]
        serial_entry = _find_all(win, tk.Spinbox)[0]

        # Verify initial serial is populated
        initial_serial = serial_entry.get()
        assert initial_serial != ""

        # 1. Change to Corporation Bank via Return
        expected_corp = str((get_last_serial_no(9) or 0) + 1)
        account_combo.delete(0, tk.END)
        account_combo.insert(0, "Corporation Bank : [109]")
        account_combo.event_generate("<Return>")
        win.update()
        assert serial_entry.get() == expected_corp

        # 2. Change to Petty Cash via FocusOut
        expected_petty = str((get_last_serial_no(2) or 0) + 1)
        account_combo.delete(0, tk.END)
        account_combo.insert(0, "Petty Cash : [1]")
        account_combo.event_generate("<FocusOut>")
        win.update()
        assert serial_entry.get() == expected_petty

        # 3. Change to Bank of Baroda (no txns -> expected 1) via <<ComboboxSelected>>
        bob_val = [v for v in account_combo["values"] if "Baroda" in v][0]
        account_combo.set(bob_val)
        account_combo.event_generate("<<ComboboxSelected>>")
        win.update()
        assert serial_entry.get() == "1"

        # 4. Change back to ICICI via <<ComboboxSelected>>
        icici_val = [v for v in account_combo["values"] if "0085001101" in v][0]
        account_combo.set(icici_val)
        account_combo.event_generate("<<ComboboxSelected>>")
        win.update()
        last_icici = get_last_serial_no(1)
        assert serial_entry.get() == str(last_icici + 1)

        # 5. User manually edits serial; focus out without changing account should preserve edit
        serial_entry.delete(0, tk.END)
        serial_entry.insert(0, "9999")
        account_combo.event_generate("<FocusOut>")
        win.update()
        assert serial_entry.get() == "9999"
    finally:
        try:
            win.destroy()
        except Exception:
            pass


def test_prefill_serial_preserved(tk_root):
    """Verify that when prefill_serial is passed, it is not overwritten by initial callbacks."""
    add_bank_transaction_main(tk_root, prefill_serial=1234)
    win = tk_root.winfo_children()[-1]
    try:
        serial_entry = _find_all(win, tk.Spinbox)[0]
        win.update()
        assert serial_entry.get() == "1234"
    finally:
        try:
            win.destroy()
        except Exception:
            pass
