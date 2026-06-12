from datetime import datetime
import sqlite3

import pytest

from StockMan.trade_utils import (
    calculate_annualized_dividend_yield,
    calculate_dividend_return_percent,
    compute_dividend_annualized_yield,
    compute_dividend_return_percent,
)


def _days_between(start_date: str, end_date: str) -> int:
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    return (end - start).days


def test_calculate_dividend_return_percent_single_lot():
    rows = [("2024-01-01", "BUY", 10, 1000.0)]

    result = calculate_dividend_return_percent(
        rows,
        record_dt="2024-06-01",
        entitled_qty=10,
        gross_dividend_amount=50.0,
    )

    expected = 50.0 * 100.0 / 1000.0
    assert result == pytest.approx(expected)


def test_calculate_annualized_dividend_yield_single_lot():
    rows = [("2024-01-01", "BUY", 10, 1000.0)]

    result = calculate_annualized_dividend_yield(
        rows,
        record_dt="2024-06-01",
        credit_dt="2024-06-30",
        entitled_qty=10,
        gross_dividend_amount=50.0,
    )

    expected = (
        50.0
        * 365.0
        * 100.0
        / (1000.0 * _days_between("2024-01-01", "2024-06-30"))
    )
    assert result == pytest.approx(expected)


def test_calculate_dividend_return_percent_multiple_lots():
    rows = [
        ("2024-01-01", "BUY", 5, 500.0),
        ("2024-03-01", "BUY", 5, 600.0),
    ]

    result = calculate_dividend_return_percent(
        rows,
        record_dt="2024-06-01",
        entitled_qty=10,
        gross_dividend_amount=55.0,
    )

    expected = 55.0 * 100.0 / (500.0 + 600.0)
    assert result == pytest.approx(expected)


def test_calculate_dividend_return_percent_partial_sell_before_record():
    rows = [
        ("2024-01-01", "BUY", 10, 1000.0),
        ("2024-02-01", "BUY", 10, 1200.0),
        ("2024-04-01", "SELL", 12, 1500.0),
    ]

    result = calculate_dividend_return_percent(
        rows,
        record_dt="2024-06-01",
        entitled_qty=8,
        gross_dividend_amount=40.0,
    )

    remaining_cost = (1200.0 / 10.0) * 8.0
    expected = 40.0 * 100.0 / remaining_cost
    assert result == pytest.approx(expected)


def test_calculate_dividend_return_percent_includes_zero_cost_lots():
    rows = [
        ("2024-01-01", "BUY", 8, 800.0),
        ("2024-03-01", "BUY", 2, 0.0),
    ]

    result = calculate_dividend_return_percent(
        rows,
        record_dt="2024-06-01",
        entitled_qty=10,
        gross_dividend_amount=50.0,
    )

    expected = 50.0 * 100.0 / 800.0
    assert result == pytest.approx(expected)


def test_compute_dividend_return_percent_uses_record_snapshot():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE transactions (
            id_trd INTEGER PRIMARY KEY AUTOINCREMENT,
            id_stk INTEGER NOT NULL,
            trd_dt TEXT NOT NULL,
            trade_type_trd TEXT NOT NULL,
            qty_trd INTEGER NOT NULL,
            net_amt_trd REAL NOT NULL
        )
        """
    )
    cur.executemany(
        """
        INSERT INTO transactions (id_stk, trd_dt, trade_type_trd, qty_trd, net_amt_trd)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (1, "2024-01-01", "BUY", 10, 1000.0),
            (1, "2024-06-15", "SELL", 10, 1200.0),
        ],
    )

    result = compute_dividend_return_percent(
        id_stk=1,
        record_dt="2024-06-01",
        entitled_qty=10,
        gross_dividend_amount=50.0,
        cursor=cur,
    )

    expected = 50.0 * 100.0 / 1000.0
    assert result == pytest.approx(expected)

    conn.close()


def test_compute_dividend_annualized_yield_uses_record_snapshot():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE transactions (
            id_trd INTEGER PRIMARY KEY AUTOINCREMENT,
            id_stk INTEGER NOT NULL,
            trd_dt TEXT NOT NULL,
            trade_type_trd TEXT NOT NULL,
            qty_trd INTEGER NOT NULL,
            net_amt_trd REAL NOT NULL
        )
        """
    )
    cur.executemany(
        """
        INSERT INTO transactions (id_stk, trd_dt, trade_type_trd, qty_trd, net_amt_trd)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (1, "2024-01-01", "BUY", 10, 1000.0),
            (1, "2024-06-15", "SELL", 10, 1200.0),
        ],
    )

    result = compute_dividend_annualized_yield(
        id_stk=1,
        record_dt="2024-06-01",
        credit_dt="2024-06-30",
        entitled_qty=10,
        gross_dividend_amount=50.0,
        cursor=cur,
    )

    expected = (
        50.0
        * 365.0
        * 100.0
        / (1000.0 * _days_between("2024-01-01", "2024-06-30"))
    )
    assert result == pytest.approx(expected)

    conn.close()


def test_calculate_dividend_return_percent_ignores_credit_date():
    rows = [("2025-01-01", "BUY", 2, 2000.0)]

    result = calculate_dividend_return_percent(
        rows,
        record_dt="2025-09-16",
        entitled_qty=2,
        gross_dividend_amount=16.0,
    )

    expected = 16.0 * 100.0 / 2000.0
    assert result == pytest.approx(expected)
