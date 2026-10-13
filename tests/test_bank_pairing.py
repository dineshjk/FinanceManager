# -*- coding: utf-8 -*-
"""Unit tests for bank transaction pairing logic and modal."""

import sqlite3
import pytest
from BankMan.bank_db_utils import (
    get_transactions_for_pairing,
    add_bank_transaction_v2,
    get_db_connection,
    BANK_DB_PATH,
)


def test_get_transactions_for_pairing_includes_row_96():
    """Verify that row 96 is returned in eligible pairing list for account 1."""
    rows = get_transactions_for_pairing(account_id=1, account_filter_mode="ALL")
    trans_ids = [r[0] for r in rows]
    assert 96 in trans_ids

    # Check row 96 data
    row_96 = next(r for r in rows if r[0] == 96)
    assert row_96[0] == 96  # trans_id
    assert row_96[7] == "INCOME"  # entry_type
    assert row_96[6] == 450.0  # deposit_amount


def test_get_transactions_for_pairing_same_account_filter():
    """Verify SAME account filter includes row 96 (account 1)."""
    rows = get_transactions_for_pairing(account_id=1, account_filter_mode="SAME")
    trans_ids = [r[0] for r in rows]
    assert 96 in trans_ids
    # All returned rows must have account_id == 1 (index 9)
    for r in rows:
        assert r[9] == 1


def test_get_transactions_for_pairing_other_account_filter():
    """Verify OTHER account filter excludes account 1 rows."""
    rows = get_transactions_for_pairing(account_id=1, account_filter_mode="OTHER")
    trans_ids = [r[0] for r in rows]
    assert 96 not in trans_ids
    for r in rows:
        assert r[9] != 1


def test_get_transactions_for_pairing_exclude_self():
    """Verify that exclude_trans_id prevents self-pairing."""
    rows = get_transactions_for_pairing(account_id=1, exclude_trans_id=96)
    trans_ids = [r[0] for r in rows]
    assert 96 not in trans_ids


def test_get_transactions_for_pairing_includes_already_paired_116_and_96():
    """Verify that already-paired rows (96 and 116) are present in 'ALL' pair status filter."""
    rows = get_transactions_for_pairing(account_id=1, pair_status_filter="ALL")
    trans_ids = [r[0] for r in rows]
    assert 96 in trans_ids
    assert 116 in trans_ids

    # Find row 116 and verify its pair_id column (index 8) is 96
    row_116 = next(r for r in rows if r[0] == 116)
    assert row_116[8] == 96

    # Find row 96 and verify its pair_id column (index 8) is 116
    row_96 = next(r for r in rows if r[0] == 96)
    assert row_96[8] == 116


def test_add_bank_transaction_reciprocal_linking(tmp_path):
    """Verify add_bank_transaction_v2 bidirectionally links pair_id."""
    test_db = str(tmp_path / "test_bank.db")
    with sqlite3.connect(test_db) as conn:
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute(
            """
            CREATE TABLE bank_transactions (
                trans_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                serial_no INTEGER,
                value_date TEXT,
                trans_date TEXT,
                cheque_no TEXT,
                bank_desc TEXT,
                user_desc TEXT,
                withdrawal_amount REAL,
                deposit_amount REAL,
                balance_after REAL,
                pair_id INTEGER,
                bh_id INTEGER,
                module_type TEXT,
                module_ref_id INTEGER,
                entry_type TEXT
            )
            """
        )
        # Insert target transaction (e.g. trans_id 10)
        conn.execute(
            """
            INSERT INTO bank_transactions (
                trans_id, account_id, value_date, trans_date, bank_desc,
                withdrawal_amount, deposit_amount, balance_after, pair_id, entry_type
            ) VALUES (10, 1, '2026-01-01', '2026-01-01', 'Cheque Deposit', 0.0, 500.0, 500.0, NULL, 'INCOME')
            """
        )
        conn.commit()

    # Monkeypatch BANK_DB_PATH
    import BankMan.bank_db_utils as bdu
    orig_path = bdu.BANK_DB_PATH
    bdu.BANK_DB_PATH = test_db
    try:
        data = {
            "account_id": 1,
            "serial_no": 1,
            "value_date": "2026-01-01",
            "trans_date": "2026-01-01",
            "withdrawal_amount": 25.0,
            "deposit_amount": 0.0,
            "balance_after": 475.0,
            "pair_id": 10,
            "entry_type": "EXPENSE",
            "bank_desc": "Collection charges",
        }
        new_id = add_bank_transaction_v2(data)

        # Check that new transaction has pair_id = 10
        with sqlite3.connect(test_db) as conn:
            cur = conn.cursor()
            cur.execute("SELECT pair_id FROM bank_transactions WHERE trans_id = ?", (new_id,))
            assert cur.fetchone()[0] == 10

            # Check reciprocal linking: trans_id 10 must now have pair_id = new_id!
            cur.execute("SELECT pair_id FROM bank_transactions WHERE trans_id = 10")
            assert cur.fetchone()[0] == new_id
    finally:
        bdu.BANK_DB_PATH = orig_path


def test_chain_and_multi_pairing(tmp_path):
    """Verify that multiple transactions (n_2 -> n_1 and n_3 -> n_2) maintain their pairings."""
    test_db = str(tmp_path / "test_chain.db")
    with sqlite3.connect(test_db) as conn:
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute(
            """
            CREATE TABLE bank_transactions (
                trans_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                serial_no INTEGER,
                value_date TEXT,
                trans_date TEXT,
                cheque_no TEXT,
                bank_desc TEXT,
                user_desc TEXT,
                withdrawal_amount REAL,
                deposit_amount REAL,
                balance_after REAL,
                pair_id INTEGER,
                bh_id INTEGER,
                module_type TEXT,
                module_ref_id INTEGER,
                entry_type TEXT
            )
            """
        )
        # n_1: Cheque deposit #96
        conn.execute(
            """
            INSERT INTO bank_transactions (
                trans_id, account_id, value_date, trans_date, bank_desc,
                withdrawal_amount, deposit_amount, balance_after, pair_id, entry_type
            ) VALUES (96, 1, '2026-01-01', '2026-01-01', 'Realised Chq #569839', 0.0, 450.0, 450.0, NULL, 'INCOME')
            """
        )
        conn.commit()

    import BankMan.bank_db_utils as bdu
    orig_path = bdu.BANK_DB_PATH
    bdu.BANK_DB_PATH = test_db
    try:
        # Step 1: Add n_2 (collection charges) paired to 96
        data_n2 = {
            "account_id": 1,
            "value_date": "2026-01-01",
            "trans_date": "2026-01-01",
            "withdrawal_amount": 56.0,
            "deposit_amount": 0.0,
            "balance_after": 394.0,
            "pair_id": 96,
            "entry_type": "EXPENSE",
            "bank_desc": "Colln + ST Chgs 569839",
        }
        id_n2 = add_bank_transaction_v2(data_n2)

        # 96 and n2 are now reciprocally paired
        with sqlite3.connect(test_db) as conn:
            cur = conn.cursor()
            cur.execute("SELECT pair_id FROM bank_transactions WHERE trans_id = ?", (id_n2,))
            assert cur.fetchone()[0] == 96
            cur.execute("SELECT pair_id FROM bank_transactions WHERE trans_id = 96")
            assert cur.fetchone()[0] == id_n2

        # Step 2: Add n_3 (tax reversal) paired to n_2 (id_n2)
        data_n3 = {
            "account_id": 1,
            "value_date": "2026-01-02",
            "trans_date": "2026-01-02",
            "withdrawal_amount": 0.0,
            "deposit_amount": 1.03,
            "balance_after": 395.03,
            "pair_id": id_n2,
            "entry_type": "INCOME",
            "bank_desc": "REV EXCESS SER TAX 569839",
        }
        id_n3 = add_bank_transaction_v2(data_n3)

        # n_3 points to n_2, while n_2's link to 96 is NOT overwritten!
        with sqlite3.connect(test_db) as conn:
            cur = conn.cursor()
            cur.execute("SELECT pair_id FROM bank_transactions WHERE trans_id = ?", (id_n3,))
            assert cur.fetchone()[0] == id_n2

            cur.execute("SELECT pair_id FROM bank_transactions WHERE trans_id = ?", (id_n2,))
            assert cur.fetchone()[0] == 96  # Still points to 96!

            cur.execute("SELECT pair_id FROM bank_transactions WHERE trans_id = 96")
            assert cur.fetchone()[0] == id_n2  # Still points to n_2!

        # Step 3: Add n_4 paired directly to 96
        data_n4 = {
            "account_id": 1,
            "value_date": "2026-01-03",
            "trans_date": "2026-01-03",
            "withdrawal_amount": 0.0,
            "deposit_amount": 5.0,
            "balance_after": 400.03,
            "pair_id": 96,
            "entry_type": "INCOME",
            "bank_desc": "Bonus Credit for 569839",
        }
        id_n4 = add_bank_transaction_v2(data_n4)

        with sqlite3.connect(test_db) as conn:
            cur = conn.cursor()
            cur.execute("SELECT pair_id FROM bank_transactions WHERE trans_id = ?", (id_n4,))
            assert cur.fetchone()[0] == 96

            # 96 still points to n2
            cur.execute("SELECT pair_id FROM bank_transactions WHERE trans_id = 96")
            assert cur.fetchone()[0] == id_n2
    finally:
        bdu.BANK_DB_PATH = orig_path


def test_show_pair_select_modal_ui():
    """Verify show_pair_select_modal launches, displays rows including 96, and selects correctly."""
    import tkinter as tk
    from BankMan.bank_transactions_add import show_pair_select_modal

    root = tk.Tk()
    root.withdraw()

    pair_id_var = tk.StringVar(value="")
    dummy_btn = tk.Button(root, text="Submit")

    show_pair_select_modal(
        win=root,
        account_id=1,
        pair_id_var=pair_id_var,
        on_escape=lambda e: None,
        submit_button=dummy_btn,
        exclude_trans_id=None,
        current_pair_id=None,
    )

    # Find the opened modal
    toplevels = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]
    assert len(toplevels) == 1
    modal = toplevels[0]

    # Find the Treeview
    from tkinter import ttk
    trees = [w for w in modal.winfo_children() if isinstance(w, tk.Frame)]
    # Look inside frames for Treeview
    tree = None
    for frame in modal.winfo_children():
        for child in frame.winfo_children():
            if isinstance(child, ttk.Treeview):
                tree = child
                break
        if tree:
            break

    assert tree is not None
    children = tree.get_children()
    assert len(children) > 0

    # Verify row 96 is present in the tree
    found_96 = False
    for item in children:
        vals = tree.item(item, "values")
        if vals and str(vals[0]) == "96":
            found_96 = True
            tree.selection_set(item)
            break

    assert found_96, "Trans ID 96 should be present in the modal treeview"

    # Find Select button and invoke it
    # Find btn_row frame
    select_btn = None
    for frame in modal.winfo_children():
        for child in frame.winfo_children():
            if isinstance(child, tk.Button) and "Select" in child.cget("text"):
                select_btn = child
                break
        if select_btn:
            break

    assert select_btn is not None
    select_btn.invoke()

    # Verify pair_id_var has been set to '96'
    assert pair_id_var.get() == "96"

    root.destroy()

