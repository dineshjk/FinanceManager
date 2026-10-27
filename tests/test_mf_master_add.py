# -*- coding: utf-8 -*-
# tests/test_mf_master_add.py

"""Unit and integration tests for Add MF Master UI and database helpers."""

import sqlite3
import tkinter as tk
from tkinter import ttk
import pytest

from BankMan.bank_db_utils import (
    get_distinct_mf_amc_names,
    get_distinct_mf_rta_names,
    get_distinct_mf_folio_numbers,
    db_add_mf_master,
)
from BankMan.mf_master_add import (
    _get_combined_rta_names,
    add_mf_master_main,
    _DEFAULT_RTAS,
)
from Shared.globals import BANK_DB_PATH


def test_get_distinct_mf_amc_names():
    names = get_distinct_mf_amc_names()
    assert isinstance(names, list)
    # Check that items are non-empty strings and sorted case-insensitively
    assert all(isinstance(n, str) and n.strip() for n in names)
    assert names == sorted(names, key=str.casefold)


def test_get_distinct_mf_rta_names():
    rtas = get_distinct_mf_rta_names()
    assert isinstance(rtas, list)
    assert all(isinstance(r, str) and r.strip() for r in rtas)
    assert rtas == sorted(rtas, key=str.casefold)


def test_get_distinct_mf_folio_numbers():
    folios = get_distinct_mf_folio_numbers()
    assert isinstance(folios, list)
    assert all(isinstance(f, str) and f.strip() for f in folios)
    assert folios == sorted(folios, key=str.casefold)


def test_get_combined_rta_names():
    combined = _get_combined_rta_names()
    assert isinstance(combined, list)
    # All default RTAs should be in combined list
    for default_rta in _DEFAULT_RTAS:
        assert default_rta in combined
    # DB RTAs should also be in combined list
    db_rtas = get_distinct_mf_rta_names()
    for db_rta in db_rtas:
        assert db_rta in combined
    # No duplicates
    assert len(combined) == len(set(combined))


def test_db_add_and_distinct_reflection():
    """Test adding a new record and verifying that distinct queries include it."""
    with sqlite3.connect(BANK_DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT ac_id FROM accounts LIMIT 1;")
        row = cur.fetchone()
        assert row is not None
        ac_id = row[0]

    test_amc = "ZZZ Test AMC Unique"
    test_rta = "ZZZ Custom RTA"
    test_folio = "FOLIO-TEST-UNIQUE-999"
    test_scheme = "ZZZ Test Scheme Growth"

    data = {
        "account_id": ac_id,
        "amc_name": test_amc,
        "rta_name": test_rta,
        "folio_number": test_folio,
        "scheme_name": test_scheme,
        "is_active": 1,
    }
    new_id = db_add_mf_master(data)
    assert new_id is not None

    try:
        amc_list = get_distinct_mf_amc_names()
        assert test_amc in amc_list

        rta_list = get_distinct_mf_rta_names()
        assert test_rta in rta_list

        folio_list = get_distinct_mf_folio_numbers()
        assert test_folio in folio_list

        combined_rtas = _get_combined_rta_names()
        assert test_rta in combined_rtas
    finally:
        with sqlite3.connect(BANK_DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM mf_master WHERE mf_master_id = ?", (new_id,))
            conn.commit()


def test_add_mf_master_ui_comboboxes():
    """Verify that Add MF Master dialog creates comboboxes populated with existing DB data and allows new values."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available")

    root.withdraw()

    captured_combos = {}

    def mock_wait_window(win):
        # Recursively find all widgets
        def find_widgets(w):
            res = [w]
            for child in w.winfo_children():
                res.extend(find_widgets(child))
            return res

        all_widgets = find_widgets(win)
        comboboxes = [w for w in all_widgets if isinstance(w, ttk.Combobox)]
        # We expect 4 comboboxes: Account, AMC, RTA, Folio
        assert len(comboboxes) == 4, f"Expected 4 Comboboxes, got {len(comboboxes)}"

        account_cb, amc_cb, rta_cb, folio_cb = comboboxes

        db_amcs = tuple(get_distinct_mf_amc_names())
        db_rtas = tuple(_get_combined_rta_names())
        db_folios = tuple(get_distinct_mf_folio_numbers())

        assert amc_cb["values"] == db_amcs
        assert rta_cb["values"] == db_rtas
        assert folio_cb["values"] == db_folios

        # Verify entering new values (not in list) works
        new_amc_val = "Brand New Custom AMC"
        amc_cb.set(new_amc_val)
        assert amc_cb.get() == new_amc_val

        new_rta_val = "Brand New Custom RTA"
        rta_cb.set(new_rta_val)
        assert rta_cb.get() == new_rta_val

        new_folio_val = "NEW-FOLIO-12345"
        folio_cb.set(new_folio_val)
        assert folio_cb.get() == new_folio_val

        captured_combos["amc"] = amc_cb
        captured_combos["rta"] = rta_cb
        captured_combos["folio"] = folio_cb

        win.destroy()

    root.wait_window = mock_wait_window

    try:
        add_mf_master_main(root)
    finally:
        try:
            root.destroy()
        except Exception:
            pass

    assert "amc" in captured_combos
    assert "rta" in captured_combos
    assert "folio" in captured_combos
