# -*- coding: utf-8 -*-
"""Unit tests for balance recalculation on intermediate date entries and account recompute."""

import sqlite3
import pytest
from BankMan.bank_db_utils import (
    add_bank_transaction_v2,
    get_balance_before_date,
    recalculate_account_balances,
    recalculate_all_accounts_balances,
    BANK_DB_PATH,
)
import BankMan.bank_db_utils as bdu


@pytest.fixture
def test_db_setup(tmp_path):
    """Create a temporary test database with accounts and bank_transactions schema."""
    test_db = str(tmp_path / "test_finance.db")
    with sqlite3.connect(test_db) as conn:
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute(
            """
            CREATE TABLE accounts (
                ac_id INTEGER PRIMARY KEY AUTOINCREMENT,
                b_id INTEGER,
                open_dt TEXT,
                ac_number TEXT,
                type TEXT,
                curr_balance REAL DEFAULT 0.0,
                curr_balance_dt TEXT,
                is_joint INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )
            """
        )
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
                withdrawal_amount REAL DEFAULT 0.0,
                deposit_amount REAL DEFAULT 0.0,
                balance_after REAL DEFAULT 0.0,
                pair_id INTEGER,
                bh_id INTEGER,
                module_type TEXT,
                module_ref_id INTEGER,
                entry_type TEXT
            )
            """
        )
        # Account 1: Bank Account, opening balance 10000.0 on 2008-04-01
        conn.execute(
            "INSERT INTO accounts (ac_id, b_id, open_dt, ac_number, type, curr_balance, curr_balance_dt) "
            "VALUES (1, 1, '2008-04-01', 'ICICI001', 'SAVINGS', 10000.0, '2008-04-01')"
        )
        # Account 2: Petty Cash, opening balance 1000.0 on 2008-04-01
        conn.execute(
            "INSERT INTO accounts (ac_id, b_id, open_dt, ac_number, type, curr_balance, curr_balance_dt) "
            "VALUES (2, 4, '2008-04-01', 'CASH001', 'CURRENT', 1000.0, '2008-04-01')"
        )
        conn.commit()

    orig_path = bdu.BANK_DB_PATH
    bdu.BANK_DB_PATH = test_db
    yield test_db
    bdu.BANK_DB_PATH = orig_path


def test_get_balance_before_date_opening_balance(test_db_setup):
    """When no transactions exist, balance before date is the account's opening balance."""
    bal = get_balance_before_date(account_id=2, trans_date="2008-04-15")
    assert bal == 1000.0


def test_get_balance_before_date_with_prior_transactions(test_db_setup):
    """When prior transactions exist, get_balance_before_date returns the most recent balance."""
    with sqlite3.connect(test_db_setup) as conn:
        conn.execute(
            """
            INSERT INTO bank_transactions (trans_id, account_id, trans_date, withdrawal_amount, deposit_amount, balance_after)
            VALUES (1, 2, '2008-04-05', 0.0, 500.0, 1500.0)
            """
        )
        conn.execute(
            """
            INSERT INTO bank_transactions (trans_id, account_id, trans_date, withdrawal_amount, deposit_amount, balance_after)
            VALUES (2, 2, '2008-04-20', 200.0, 0.0, 1300.0)
            """
        )
        conn.commit()

    # Before 2008-04-01 -> opening balance
    assert get_balance_before_date(2, "2008-04-01") == 1000.0

    # On 2008-04-10 (intermediate between 05 and 20) -> 1500.0
    assert get_balance_before_date(2, "2008-04-10") == 1500.0

    # On 2008-04-25 (after 20) -> 1300.0
    assert get_balance_before_date(2, "2008-04-25") == 1300.0


def test_add_transaction_intermediate_date_adjusts_downstream(test_db_setup):
    """Adding a transaction on an intermediate date adjusts all following balances for that account."""
    # Existing transactions on 2008-04-05 and 2008-06-10
    with sqlite3.connect(test_db_setup) as conn:
        conn.execute(
            """
            INSERT INTO bank_transactions (trans_id, account_id, trans_date, withdrawal_amount, deposit_amount, balance_after)
            VALUES (1, 2, '2008-04-05', 0.0, 2000.0, 3000.0)
            """
        )
        conn.execute(
            """
            INSERT INTO bank_transactions (trans_id, account_id, trans_date, withdrawal_amount, deposit_amount, balance_after)
            VALUES (2, 2, '2008-06-10', 500.0, 0.0, 2500.0)
            """
        )
        conn.commit()

    # Now an intermediate transaction is entered on 2008-05-15 (deposit 1000 into Petty Cash)
    tx_data = {
        "account_id": 2,
        "serial_no": 3,
        "value_date": "2008-05-15",
        "trans_date": "2008-05-15",
        "withdrawal_amount": 0.0,
        "deposit_amount": 1000.0,
        "balance_after": 4000.0,  # 3000 + 1000
        "bank_desc": "Cash from Bank of Baroda",
        "entry_type": "TRANSFER",
    }
    new_id = add_bank_transaction_v2(tx_data)
    assert tx_data.get("downstream_adjusted") == 1

    # Verify balances in DB:
    with sqlite3.connect(test_db_setup) as conn:
        cur = conn.cursor()
        # Row 1 (2008-04-05) should be unchanged at 3000.0
        cur.execute("SELECT balance_after FROM bank_transactions WHERE trans_id = 1")
        assert cur.fetchone()[0] == 3000.0

        # Row new_id (2008-05-15) should be 4000.0
        cur.execute("SELECT balance_after FROM bank_transactions WHERE trans_id = ?", (new_id,))
        assert cur.fetchone()[0] == 4000.0

        # Row 2 (2008-06-10) should have been adjusted by +1000.0 -> 2500 + 1000 = 3500.0
        cur.execute("SELECT balance_after FROM bank_transactions WHERE trans_id = 2")
        assert cur.fetchone()[0] == 3500.0


def test_intermediate_transaction_does_not_affect_other_accounts(test_db_setup):
    """Downstream adjustment is strictly scoped to the same account_id."""
    with sqlite3.connect(test_db_setup) as conn:
        # Account 1 has transaction on 2008-06-01
        conn.execute(
            """
            INSERT INTO bank_transactions (trans_id, account_id, trans_date, withdrawal_amount, deposit_amount, balance_after)
            VALUES (10, 1, '2008-06-01', 0.0, 5000.0, 15000.0)
            """
        )
        # Account 2 has transaction on 2008-06-01
        conn.execute(
            """
            INSERT INTO bank_transactions (trans_id, account_id, trans_date, withdrawal_amount, deposit_amount, balance_after)
            VALUES (20, 2, '2008-06-01', 0.0, 500.0, 1500.0)
            """
        )
        conn.commit()

    # Enter intermediate transaction on 2008-05-01 for Account 2
    tx_data = {
        "account_id": 2,
        "value_date": "2008-05-01",
        "trans_date": "2008-05-01",
        "withdrawal_amount": 200.0,
        "deposit_amount": 0.0,
        "balance_after": 800.0,
        "entry_type": "EXPENSE",
    }
    add_bank_transaction_v2(tx_data)

    with sqlite3.connect(test_db_setup) as conn:
        cur = conn.cursor()
        # Account 1 row should be completely untouched!
        cur.execute("SELECT balance_after FROM bank_transactions WHERE trans_id = 10")
        assert cur.fetchone()[0] == 15000.0

        # Account 2 row on 2008-06-01 should be adjusted by -200 -> 1500 - 200 = 1300.0
        cur.execute("SELECT balance_after FROM bank_transactions WHERE trans_id = 20")
        assert cur.fetchone()[0] == 1300.0


def test_recalculate_account_balances(test_db_setup):
    """recalculate_account_balances fixes out-of-order or broken running balances."""
    # Opening balance of Account 2 is 1000.0
    with sqlite3.connect(test_db_setup) as conn:
        # Row 1: +500 -> expected 1500.0, but stored as 9999.0 (corrupted)
        conn.execute(
            """
            INSERT INTO bank_transactions (trans_id, account_id, trans_date, withdrawal_amount, deposit_amount, balance_after)
            VALUES (1, 2, '2008-04-10', 0.0, 500.0, 9999.0)
            """
        )
        # Row 2: -200 -> expected 1300.0, stored as 8888.0
        conn.execute(
            """
            INSERT INTO bank_transactions (trans_id, account_id, trans_date, withdrawal_amount, deposit_amount, balance_after)
            VALUES (2, 2, '2008-05-10', 200.0, 0.0, 8888.0)
            """
        )
        conn.commit()

    res = recalculate_account_balances(2)
    assert res["account_id"] == 2
    assert res["total_rows"] == 2
    assert res["rows_updated"] == 2
    assert res["opening_balance"] == 1000.0
    assert res["final_balance"] == 1300.0

    with sqlite3.connect(test_db_setup) as conn:
        cur = conn.cursor()
        cur.execute("SELECT trans_id, balance_after FROM bank_transactions WHERE account_id = 2 ORDER BY trans_id")
        rows = cur.fetchall()
        assert rows == [(1, 1500.0), (2, 1300.0)]
