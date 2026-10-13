# -*- coding: utf-8 -*-
"""Tests for nullable FD master fields (interest_rate, maturity_dt) and FD TDS payout breakdown."""

import sqlite3
import pytest

from BankMan.bank_db_utils import (
    db_add_fd_master,
    get_fd_principal,
    add_bank_transaction_v2,
    get_income_tax_for_trans,
    get_all_fd_masters_for_display,
)
from Shared.globals import BANK_DB_PATH


def test_fd_master_nullable_fields():
    with sqlite3.connect(BANK_DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT ac_id FROM accounts LIMIT 1;")
        row = cur.fetchone()
        assert row is not None, "At least one account must exist"
        ac_id = row[0]

    # 1. Add FD master with NULL interest_rate and NULL maturity_dt
    fd_data = {
        "account_id": ac_id,
        "fd_number": "TEST-FD-NULL-01",
        "principal_amount": 500000.0,
        "interest_rate": None,
        "open_dt": "2018-11-09",
        "maturity_dt": None,
        "is_active": 1,
    }
    fd_id = db_add_fd_master(fd_data)
    assert fd_id is not None

    try:
        # Verify stored values in db
        with sqlite3.connect(BANK_DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT principal_amount, interest_rate, maturity_dt, is_active FROM fd_master WHERE fd_master_id = ?",
                (fd_id,),
            )
            rec = cur.fetchone()
            assert rec[0] == 500000.0
            assert rec[1] is None
            assert rec[2] is None
            assert rec[3] == 1

            # Update FD master keeping them NULL
            cur.execute(
                """
                UPDATE fd_master
                SET principal_amount = ?, interest_rate = ?, maturity_dt = ?
                WHERE fd_master_id = ?
                """,
                (550000.0, None, None, fd_id),
            )
            conn.commit()

            cur.execute(
                "SELECT principal_amount, interest_rate, maturity_dt FROM fd_master WHERE fd_master_id = ?",
                (fd_id,),
            )
            rec2 = cur.fetchone()
            assert rec2[0] == 550000.0
            assert rec2[1] is None
            assert rec2[2] is None

        # Verify get_all_fd_masters_for_display handles None gracefully
        display_fds = get_all_fd_masters_for_display()
        matching = [r for r in display_fds if r[0] == fd_id]
        assert len(matching) == 1
        # row[5] is interest_rate
        assert matching[0][5] is None

    finally:
        with sqlite3.connect(BANK_DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM fd_master WHERE fd_master_id = ?", (fd_id,))
            conn.commit()


def test_fd_interest_with_tds_transaction_flow():
    with sqlite3.connect(BANK_DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT ac_id FROM accounts LIMIT 1;")
        row = cur.fetchone()
        assert row is not None, "At least one account must exist"
        ac_id = row[0]

    # Create an active FD of 500,000
    fd_data = {
        "account_id": ac_id,
        "fd_number": "TEST-FD-TDS-02",
        "principal_amount": 500000.0,
        "interest_rate": 7.0,
        "open_dt": "2018-11-09",
        "maturity_dt": None,
        "is_active": 1,
    }
    fd_id = db_add_fd_master(fd_data)
    assert fd_id is not None

    try:
        # Initial principal should be 500000.0
        initial_p = get_fd_principal(fd_id)
        assert initial_p == 500000.0

        # Now simulate bank interest credit:
        # Deposit: 5890.0, TDS: 1672.0, Gross Interest = 7562.0, Principal component = 0.0
        deposit_val = 5890.0
        tds_val = 1672.0
        gross_val = round(deposit_val + tds_val, 2)  # 7562.0
        p_comp = 0.0
        i_comp = gross_val

        tx_data = {
            "account_id": ac_id,
            "serial_no": "TEST-FD-TX-01",
            "value_date": "2019-02-09",
            "trans_date": "2019-02-11",
            "cheque_no": None,
            "bank_desc": "FD Interest Payout",
            "user_desc": "Quarterly interest with TDS",
            "withdrawal_amount": 0.0,
            "deposit_amount": deposit_val,
            "balance_after": 25000.0,
            "pair_id": None,
            "bh_id": None,
            "bh_name": "Fixed Deposit Interest",
            "module_type": "FD",
            "master_id": fd_id,
            "entry_type": "INCOME",
            "is_direct_it": False,
            "tds_amount": tds_val,
            "tax_section": "194A",
            # FD subledger kwargs:
            "fd_saving": 0.0,
            "fd_withdrawal": round(p_comp + i_comp, 2),
            "fd_principal": p_comp,
            "fd_int": i_comp,
        }
        trans_id = add_bank_transaction_v2(tx_data)
        assert trans_id is not None

        try:
            # 1. Check bank_transactions row
            with sqlite3.connect(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT deposit_amount, module_type, module_ref_id FROM bank_transactions WHERE trans_id = ?",
                    (trans_id,),
                )
                bt_row = cur.fetchone()
                assert bt_row[0] == 5890.0
                assert bt_row[1] == "FD"
                fd_trans_id = bt_row[2]
                assert fd_trans_id is not None

                # 2. Check fd_transactions row
                cur.execute(
                    "SELECT fd_saving, fd_withdrawal, fd_principal, fd_int FROM fd_transactions WHERE fd_trans_id = ?",
                    (fd_trans_id,),
                )
                ft_row = cur.fetchone()
                assert ft_row[0] == 0.0
                assert ft_row[1] == 7562.0  # Gross payout
                assert ft_row[2] == 0.0     # Principal untouched
                assert ft_row[3] == 7562.0  # Gross interest

            # 3. Check income_tax linked entry
            tax_rec = get_income_tax_for_trans(trans_id)
            assert tax_rec is not None
            assert tax_rec["tax_amount"] == 1672.0
            assert tax_rec["tax_section"] == "194A"
            assert tax_rec["financial_year"] == "2018-19"
            assert tax_rec["assessment_year"] == "2019-20"

            # 4. Check FD principal remains intact (500,000.0)
            remaining_p = get_fd_principal(fd_id)
            assert remaining_p == 500000.0

        finally:
            with sqlite3.connect(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM bank_transactions WHERE trans_id = ?", (trans_id,))
                cur.execute("DELETE FROM income_tax WHERE trans_id = ?", (trans_id,))
                cur.execute("DELETE FROM fd_transactions WHERE fd_master_id = ?", (fd_id,))
                conn.commit()

    finally:
        with sqlite3.connect(BANK_DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM fd_master WHERE fd_master_id = ?", (fd_id,))
            conn.commit()
