# -*- coding: utf-8 -*-
"""Tests for income_tax table, helpers, and bank transaction integration."""

import os
import sqlite3
import pytest

from BankMan.bank_db_utils import (
    calculate_fy_ay,
    infer_tax_section,
    add_bank_transaction_v2,
    db_update_bank_transaction,
    get_income_tax_for_trans,
)
from BankMan.bank_database_setup import setup_bankman_database
from Shared.globals import BANK_DB_PATH


def test_calculate_fy_ay():
    # After March (e.g. June)
    fy, ay = calculate_fy_ay("2026-06-15")
    assert fy == "2026-27"
    assert ay == "2027-28"

    # Before April (e.g. February)
    fy, ay = calculate_fy_ay("2026-02-10")
    assert fy == "2025-26"
    assert ay == "2026-27"

    # Edge: April 1
    fy, ay = calculate_fy_ay("2026-04-01")
    assert fy == "2026-27"
    assert ay == "2027-28"

    # Edge: March 31
    fy, ay = calculate_fy_ay("2026-03-31")
    assert fy == "2025-26"
    assert ay == "2026-27"


def test_infer_tax_section():
    assert infer_tax_section(is_direct_it=True, is_deposit=False) == "DIRECT_TAX"
    assert infer_tax_section(is_direct_it=True, is_deposit=True) == "REFUND"
    assert infer_tax_section("Fixed Deposit Interest") == "194A"
    assert infer_tax_section("Savings Bank Interest") == "194A"
    assert infer_tax_section("Dividend from TCS") == "194"
    assert infer_tax_section("Pension") == "192"
    assert infer_tax_section("Miscellaneous Income") == "TDS"


def test_income_tax_transaction_flow():
    # Fetch an existing account_id from database
    with sqlite3.connect(BANK_DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT ac_id FROM accounts LIMIT 1;")
        row = cur.fetchone()
        assert row is not None, "At least one account must exist"
        ac_id = row[0]

    # 1. Add income with TDS (Net Deposit: 900, TDS: 100)
    data = {
        "account_id": ac_id,
        "serial_no": "TEST-IT-01",
        "value_date": "2026-06-15",
        "trans_date": "2026-06-15",
        "cheque_no": None,
        "bank_desc": "Dividend TCS Net Credit",
        "user_desc": "Dividend received net of TDS",
        "withdrawal_amount": 0.0,
        "deposit_amount": 900.0,
        "balance_after": 10900.0,
        "pair_id": None,
        "bh_id": None,
        "bh_name": "Dividend",
        "module_type": "NONE",
        "master_id": None,
        "entry_type": "INCOME",
        "is_direct_it": False,
        "tds_amount": 100.0,
        "tax_section": "194",
    }
    trans_id = add_bank_transaction_v2(data)
    assert trans_id is not None

    try:
        # Verify bank_transactions row
        with sqlite3.connect(BANK_DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT deposit_amount FROM bank_transactions WHERE trans_id = ?", (trans_id,))
            assert cur.fetchone()[0] == 900.0

        # Verify linked income_tax row
        tax_rec = get_income_tax_for_trans(trans_id)
        assert tax_rec is not None
        assert tax_rec["trans_id"] == trans_id
        assert tax_rec["tax_amount"] == 100.0
        assert tax_rec["refund_amount"] == 0.0
        assert tax_rec["financial_year"] == "2026-27"
        assert tax_rec["assessment_year"] == "2027-28"
        assert tax_rec["tax_section"] == "194"
        assert tax_rec["source_type"] == "BANK"

        # 2. Update transaction (change TDS from 100 to 150)
        cascades = db_update_bank_transaction(
            trans_id,
            serial_no="TEST-IT-01",
            value_date="2026-06-15",
            trans_date="2026-06-15",
            cheque_no=None,
            bank_desc="Dividend TCS Net Credit",
            user_desc="Dividend received net of TDS",
            withdrawal_amount=0.0,
            deposit_amount=900.0,
            balance_after=10900.0,
            pair_id=None,
            bh_id=None,
            module_type="NONE",
            module_ref_id=None,
            entry_type="INCOME",
            old_withdrawal=0.0,
            old_deposit=900.0,
            old_trans_date="2026-06-15",
            old_pair_id=None,
            old_module_type="NONE",
            old_module_ref_id=None,
            account_id=ac_id,
            is_direct_it=False,
            tds_amount=150.0,
            tax_section="194",
        )
        assert cascades.get("tax_updated") is True

        tax_rec = get_income_tax_for_trans(trans_id)
        assert tax_rec is not None
        assert tax_rec["tax_amount"] == 150.0

        # 3. Update transaction to clear TDS (set TDS to 0)
        cascades = db_update_bank_transaction(
            trans_id,
            serial_no="TEST-IT-01",
            value_date="2026-06-15",
            trans_date="2026-06-15",
            cheque_no=None,
            bank_desc="Dividend TCS Net Credit",
            user_desc="Dividend received net of TDS",
            withdrawal_amount=0.0,
            deposit_amount=900.0,
            balance_after=10900.0,
            pair_id=None,
            bh_id=None,
            module_type="NONE",
            module_ref_id=None,
            entry_type="INCOME",
            old_withdrawal=0.0,
            old_deposit=900.0,
            old_trans_date="2026-06-15",
            old_pair_id=None,
            old_module_type="NONE",
            old_module_ref_id=None,
            account_id=ac_id,
            is_direct_it=False,
            tds_amount=0.0,
            tax_section=None,
        )
        assert cascades.get("tax_removed") is True

        tax_rec = get_income_tax_for_trans(trans_id)
        assert tax_rec is None

    finally:
        # Cleanup test transaction
        with sqlite3.connect(BANK_DB_PATH) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("DELETE FROM bank_transactions WHERE trans_id = ?", (trans_id,))
            conn.commit()


def test_direct_it_transactions():
    with sqlite3.connect(BANK_DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT ac_id FROM accounts LIMIT 1;")
        ac_id = cur.fetchone()[0]

    # Direct Tax Payment (Challan Paid: 5000 withdrawal)
    data = {
        "account_id": ac_id,
        "serial_no": "TEST-IT-02",
        "value_date": "2026-09-15",
        "trans_date": "2026-09-15",
        "cheque_no": None,
        "bank_desc": "Advance Tax Paid ITD",
        "user_desc": "Advance Tax Q2",
        "withdrawal_amount": 5000.0,
        "deposit_amount": 0.0,
        "balance_after": 50000.0,
        "pair_id": None,
        "bh_id": None,
        "module_type": "NONE",
        "master_id": None,
        "entry_type": "EXPENSE",
        "is_direct_it": True,
        "tds_amount": 0.0,
        "tax_section": "DIRECT_TAX",
    }
    trans_id = add_bank_transaction_v2(data)

    try:
        tax_rec = get_income_tax_for_trans(trans_id)
        assert tax_rec is not None
        assert tax_rec["tax_amount"] == 5000.0
        assert tax_rec["refund_amount"] == 0.0
        assert tax_rec["tax_section"] == "DIRECT_TAX"
        assert tax_rec["financial_year"] == "2026-27"
    finally:
        with sqlite3.connect(BANK_DB_PATH) as conn:
            conn.execute("DELETE FROM bank_transactions WHERE trans_id = ?", (trans_id,))
            conn.commit()
