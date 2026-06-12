# -*- coding: utf-8 -*-
# tests/test_reporting_utils.py
from datetime import date
import sqlite3
from datetime import datetime

import pytest

from StockMan.reporting_utils import (
    assemble_detail_tree_data,
    assemble_position_quantity_metrics,
    build_capital_stats_tree_rows,
    build_current_holdings_header_values,
    build_current_holdings_row,
    build_detail_header_fragments,
    build_grand_summary_row,
    build_intraday_analysis_lines,
    build_live_market_snapshot,
    build_detail_corp_tree_rows,
    build_detail_existing_action_keys,
    build_detail_ledger_display_rows,
    build_detail_ledger_tree_rows,
    build_detail_dividend_tree_rows,
    build_detail_position_overview_fragments,
    build_master_existing_action_keys,
    build_master_corp_tree_rows,
    build_master_dividend_tree_rows,
    build_master_ledger_display_rows,
    build_online_action_entries,
    build_pooled_cost_reality_summary,
    build_online_corp_action_rows,
    build_report_value_fragments,
    build_realized_pnl_report_fragments,
    build_stock_tree_initial_row,
    build_stock_tree_update_row,
    build_summary_selection_fragments,
    accumulate_live_position_metrics,
    build_summary_tree_rows,
    compute_current_position_metrics,
    compute_intraday_price_bounds,
    compute_intraday_vwap_analysis,
    compute_portfolio_header_totals,
    fetch_and_filter_online_corp_actions,
    fetch_detail_dividend_total,
    fetch_detail_investment_summary,
    fetch_holding_bounds,
    fetch_detail_timeline_rows,
    build_detail_corp_action_records,
    build_detail_dividend_display_data,
    build_master_corp_action_records,
    build_master_dividend_display_data,
    build_realized_pnl_rows,
    build_reality_pnl_rows,
    build_xirr_cashflows,
    build_portfolio_summary,
    compute_position_xirr,
    fetch_detail_bonus_rows,
    fetch_detail_dividend_source_rows,
    fetch_detail_ledger_rows,
    fetch_position_cashflow_rows,
    fetch_realized_detail_rows,
    fetch_report_stock_rows,
    fetch_yearly_realized_amount,
    fetch_detail_split_rows,
    fetch_master_bonus_rows,
    fetch_master_dividend_source_rows,
    fetch_master_ledger_rows,
    fetch_master_split_rows,
    has_corporate_action_history,
    format_dividend_value_with_yield,
    get_financial_years,
    initialize_stock_data_cache,
    resolve_optional_date_filters,
    resolve_reporting_period,
    resolve_intraday_chart_window,
    resolve_action_window,
    xirr,
    xnpv,
)


def _create_reporting_source_schema(conn):
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE stocks (
            id_stk INTEGER PRIMARY KEY,
            short_name TEXT NOT NULL,
            company_name TEXT DEFAULT '',
            ticker TEXT DEFAULT '',
            current_qty REAL DEFAULT 0,
            rpnl_amt REAL DEFAULT 0,
            curr_investment_amt REAL DEFAULT 0,
            total_investment_amt REAL DEFAULT 0,
            disinvestment_amt REAL DEFAULT 0,
            sector TEXT DEFAULT NULL
        );
        CREATE TABLE transactions (
            id_trd INTEGER PRIMARY KEY,
            id_stk INTEGER NOT NULL,
            cont_no TEXT NOT NULL,
            trd_dt TEXT NOT NULL,
            trade_type_trd TEXT NOT NULL,
            qty_trd INTEGER NOT NULL,
            wap_unit_trd REAL,
            net_amt_trd REAL NOT NULL
        );
        CREATE TABLE contracts (
            cont_no TEXT PRIMARY KEY,
            settle_dt TEXT NOT NULL
        );
        CREATE TABLE dividends (
            id_div INTEGER PRIMARY KEY,
            id_stk INTEGER NOT NULL,
            record_dt TEXT NOT NULL,
            credit_dt TEXT NOT NULL,
            div_type TEXT NOT NULL,
            entitled_qty INTEGER NOT NULL,
            per_share_amt REAL NOT NULL DEFAULT 0.0,
            gross_amt REAL NOT NULL,
            net_amt REAL NOT NULL,
            tds_amt REAL NOT NULL
        );
        CREATE TABLE splits (
            id_split INTEGER PRIMARY KEY,
            id_stk INTEGER NOT NULL,
            ex_dt TEXT NOT NULL,
            old_fv REAL NOT NULL,
            new_fv REAL NOT NULL
        );
        CREATE TABLE bonus_issues (
            id_bonus INTEGER PRIMARY KEY,
            id_stk INTEGER NOT NULL,
            ex_dt TEXT NOT NULL,
            ratio_old INTEGER NOT NULL,
            ratio_new INTEGER NOT NULL
        );
        CREATE TABLE sell_records (
            id_sell INTEGER PRIMARY KEY,
            id_stk INTEGER NOT NULL,
            buy_dt TEXT NOT NULL,
            sell_dt TEXT NOT NULL,
            buy_value REAL NOT NULL,
            sell_value REAL NOT NULL,
            sell_qty INTEGER NOT NULL,
            pnl_amt REAL NOT NULL,
            holding_days INTEGER NOT NULL
        );
        """
    )
    conn.commit()


def test_get_financial_years_returns_descending_financial_year_labels():
    conn = sqlite3.connect(":memory:")
    try:
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE transactions (id_trd INTEGER PRIMARY KEY, trd_dt TEXT)"
        )
        cur.executemany(
            "INSERT INTO transactions (trd_dt) VALUES (?)",
            [("2023-03-31",), ("2023-04-01",), ("2025-01-15",)],
        )

        assert get_financial_years(conn) == [
            "FY 2024-25",
            "FY 2023-24",
            "FY 2022-23",
        ]
    finally:
        conn.close()


def test_fetch_report_stock_rows_returns_all_or_filtered_rows():
    conn = sqlite3.connect(":memory:")
    try:
        _create_reporting_source_schema(conn)
        cur = conn.cursor()
        cur.executemany(
            "INSERT INTO stocks (id_stk, short_name, company_name, ticker) VALUES (?, ?, ?, ?)",
            [
                (1, "AAA", "Alpha Ltd", "AAA.NS"),
                (2, "BBB", "Beta Ltd", "BBB.NS"),
            ],
        )

        assert [row[0] for row in fetch_report_stock_rows(cur)] == [1, 2]
        assert [row[0] for row in fetch_report_stock_rows(cur, [2])] == [2]
    finally:
        conn.close()


def test_fetch_yearly_realized_amount_returns_zero_when_missing():
    conn = sqlite3.connect(":memory:")
    try:
        _create_reporting_source_schema(conn)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sell_records (id_stk, buy_dt, sell_dt, buy_value, sell_value, sell_qty, pnl_amt, holding_days) VALUES (1, '2024-01-01', '2024-05-01', 100.0, 120.0, 1, 20.0, 121)"
        )

        assert fetch_yearly_realized_amount(
            cur, 1, "2024-04-01", "2025-03-31"
        ) == pytest.approx(20.0)
        assert fetch_yearly_realized_amount(
            cur, 1, "2025-04-01", "2026-03-31"
        ) == pytest.approx(0.0)
    finally:
        conn.close()


def test_fetch_position_cashflow_rows_applies_optional_date_filters():
    conn = sqlite3.connect(":memory:")
    try:
        _create_reporting_source_schema(conn)
        cur = conn.cursor()
        cur.executemany(
            "INSERT INTO transactions (id_stk, cont_no, trd_dt, trade_type_trd, qty_trd, net_amt_trd) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (1, "C1", "2024-04-10", "BUY", 1, 100.0),
                (1, "C2", "2024-06-10", "SELL", 1, 130.0),
                (1, "C3", "2025-04-10", "BUY", 1, 140.0),
            ],
        )

        purchases, sells = fetch_position_cashflow_rows(
            cur,
            1,
            "2024-04-01",
            "2025-03-31",
        )

        assert purchases == [("2024-04-10", 100.0)]
        assert sells == [("2024-06-10", 130.0)]
    finally:
        conn.close()


def test_xnpv_rejects_mismatched_cashflow_lengths():
    with pytest.raises(ValueError):
        xnpv(0.1, [-100.0, 110.0], [date(2024, 1, 1)])


def test_xirr_returns_expected_rate_for_simple_cashflow():
    result = xirr(
        [-1000.0, 1100.0],
        [date(2024, 1, 1), date(2025, 1, 1)],
    )

    assert result == pytest.approx(0.0997135859)


def test_build_xirr_cashflows_includes_live_position_when_requested():
    amounts, dates = build_xirr_cashflows(
        purchase_rows=[("2024-01-01", 1000.0)],
        sell_rows=[("2024-06-01", 200.0)],
        current_qty=5,
        current_price=100.0,
        include_live_position=True,
        valuation_date=date(2024, 12, 31),
    )

    assert amounts == [-1000.0, 200.0, 500.0]
    assert dates == [
        date(2024, 1, 1),
        date(2024, 6, 1),
        date(2024, 12, 31),
    ]


def test_compute_position_xirr_returns_none_without_mixed_cashflows():
    assert (
        compute_position_xirr(
            purchase_rows=[("2024-01-01", 1000.0)],
            sell_rows=[],
            include_live_position=False,
        )
        is None
    )


def test_compute_position_xirr_uses_live_position_for_open_holding():
    result = compute_position_xirr(
        purchase_rows=[("2024-01-01", 1000.0)],
        sell_rows=[],
        current_qty=10,
        current_price=110.0,
        include_live_position=True,
        valuation_date=date(2025, 1, 1),
    )

    assert result == pytest.approx(0.0997135859)


def test_format_dividend_value_with_yield_handles_unavailable_metrics():
    assert format_dividend_value_with_yield(1250.0, None, float("inf")) == (
        "₹1,250.00 | Return unavailable | Annualized unavailable"
    )


def test_format_dividend_value_with_yield_formats_both_metrics():
    assert format_dividend_value_with_yield(1250.0, 3.456, 6.789) == (
        "₹1,250.00 | Ret 3.46% | Ann 6.79% p.a."
    )


def test_build_portfolio_summary_aggregates_realized_tax_and_opportunity():
    summary = build_portfolio_summary(
        sell_rows=[
            ("2024-06-10", "2023-05-01", 200.0, 10, 1000.0, 1),
            ("2024-11-10", "2024-08-01", -50.0, 5, 450.0, 2),
        ],
        investment_rows=[("2024-04-05", 300.0), ("2023-02-01", 999.0)],
        dividend_rows=[("2024-08-01", 40.0), ("1900-01-01", 99.0)],
        stock_prices={1: 120.0, 2: 80.0},
        capital_gains_tax_rates=lambda _date: (0.15, 0.1),
    )

    assert summary == {
        "FY 2024-25": {
            "inv": pytest.approx(300.0),
            "pnl": pytest.approx(150.0),
            "pat": pytest.approx(130.0),
            "div": pytest.approx(40.0),
            "miss_profit": pytest.approx(200.0),
            "save_loss": pytest.approx(50.0),
        }
    }


def test_build_portfolio_summary_preserves_realized_year_gate():
    summary = build_portfolio_summary(
        sell_rows=[],
        investment_rows=[("2024-04-05", 300.0)],
        dividend_rows=[("2024-08-01", 40.0)],
        stock_prices={},
        capital_gains_tax_rates=lambda _date: (0.15, 0.1),
    )

    assert summary == {}


def test_fetch_master_query_helpers_respect_date_filters():
    conn = sqlite3.connect(":memory:")
    try:
        _create_reporting_source_schema(conn)
        cur = conn.cursor()
        cur.executemany(
            "INSERT INTO stocks (id_stk, short_name, ticker) VALUES (?, ?, ?)",
            [(1, "AAA", "AAA.NS"), (2, "BBB", "")],
        )
        cur.executemany(
            "INSERT INTO transactions (id_trd, id_stk, cont_no, trd_dt, trade_type_trd, qty_trd, net_amt_trd) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (1, 1, "C1", "2024-05-01", "BUY", 10, 1000.0),
                (2, 2, "C2", "2023-05-01", "SELL", 4, 500.0),
            ],
        )
        cur.executemany(
            "INSERT INTO dividends (id_div, id_stk, record_dt, credit_dt, div_type, entitled_qty, per_share_amt, gross_amt, net_amt, tds_amt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    1,
                    1,
                    "2024-05-10",
                    "2024-05-20",
                    "FINAL",
                    10,
                    5.0,
                    50.0,
                    45.0,
                    5.0,
                ),
                (
                    2,
                    2,
                    "2023-05-10",
                    "2023-05-20",
                    "FINAL",
                    4,
                    4.5,
                    20.0,
                    18.0,
                    2.0,
                ),
            ],
        )
        cur.executemany(
            "INSERT INTO splits (id_split, id_stk, ex_dt, old_fv, new_fv) VALUES (?, ?, ?, ?, ?)",
            [(1, 1, "2024-06-01", 10.0, 5.0), (2, 2, "2023-06-01", 10.0, 2.0)],
        )
        cur.executemany(
            "INSERT INTO bonus_issues (id_bonus, id_stk, ex_dt, ratio_old, ratio_new) VALUES (?, ?, ?, ?, ?)",
            [(1, 1, "2024-07-01", 1, 1), (2, 2, "2023-07-01", 2, 1)],
        )
        conn.commit()

        assert fetch_master_ledger_rows(cur, "2024-04-01", "2025-03-31") == [
            ("C1", "AAA.NS", "2024-05-01", "BUY", 10, None, 1000.0)
        ]
        assert fetch_master_dividend_source_rows(
            cur, "2024-04-01", "2025-03-31"
        ) == [
            (
                "AAA.NS",
                1,
                "2024-05-10",
                "2024-05-20",
                "FINAL",
                10,
                5.0,
                50.0,
                45.0,
                5.0,
            )
        ]
        assert fetch_master_split_rows(cur, "2024-04-01", "2025-03-31") == [
            ("AAA.NS", "2024-06-01", 10.0, 5.0)
        ]
        assert fetch_master_bonus_rows(cur, "2024-04-01", "2025-03-31") == [
            ("AAA.NS", "2024-07-01", 1, 1)
        ]
    finally:
        conn.close()


def test_fetch_detail_query_helpers_return_stock_scoped_rows():
    conn = sqlite3.connect(":memory:")
    try:
        _create_reporting_source_schema(conn)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO stocks (id_stk, short_name, ticker) VALUES (1, 'AAA', '')"
        )
        cur.execute(
            "INSERT INTO contracts (cont_no, settle_dt) VALUES ('C1', '2024-05-03')"
        )
        cur.execute(
            "INSERT INTO transactions (id_trd, id_stk, cont_no, trd_dt, trade_type_trd, qty_trd, net_amt_trd) VALUES (1, 1, 'C1', '2024-05-01', 'BUY', 10, 1000.0)"
        )
        cur.execute(
            "INSERT INTO dividends (id_div, id_stk, record_dt, credit_dt, div_type, entitled_qty, gross_amt, net_amt, tds_amt) VALUES (1, 1, '2024-05-10', '2024-05-20', 'FINAL', 10, 50.0, 45.0, 5.0)"
        )
        cur.execute(
            "INSERT INTO splits (id_split, id_stk, ex_dt, old_fv, new_fv) VALUES (1, 1, '2024-06-01', 10.0, 5.0)"
        )
        cur.execute(
            "INSERT INTO bonus_issues (id_bonus, id_stk, ex_dt, ratio_old, ratio_new) VALUES (1, 1, '2024-07-01', 1, 1)"
        )
        conn.commit()

        assert fetch_detail_ledger_rows(
            cur, 1, "2024-04-01", "2025-03-31"
        ) == [("2024-05-03", "BUY", 10, 1000.0)]
        assert fetch_detail_dividend_source_rows(
            cur, 1, "2024-04-01", "2025-03-31"
        ) == [("2024-05-10", "2024-05-20", "FINAL", 10, 50.0, 45.0, 5.0)]
        assert fetch_detail_split_rows(cur, 1, "2024-04-01", "2025-03-31") == [
            ("2024-06-01", 10.0, 5.0)
        ]
        assert fetch_detail_bonus_rows(cur, 1, "2024-04-01", "2025-03-31") == [
            ("2024-07-01", 1, 1)
        ]
    finally:
        conn.close()


def test_fetch_realized_detail_rows_respects_date_filter():
    conn = sqlite3.connect(":memory:")
    try:
        _create_reporting_source_schema(conn)
        cur = conn.cursor()
        cur.executemany(
            "INSERT INTO sell_records (id_sell, id_stk, buy_dt, sell_dt, buy_value, sell_value, sell_qty, pnl_amt, holding_days) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    1,
                    1,
                    "2024-01-01",
                    "2024-05-01",
                    1000.0,
                    1200.0,
                    10,
                    200.0,
                    121,
                ),
                (
                    2,
                    1,
                    "2023-01-01",
                    "2023-05-01",
                    500.0,
                    600.0,
                    5,
                    100.0,
                    120,
                ),
            ],
        )
        conn.commit()

        assert fetch_realized_detail_rows(
            cur, 1, "2024-04-01", "2025-03-31"
        ) == [(1000.0, 121, 200.0, 10, 1200.0, "2024-05-01")]
    finally:
        conn.close()


def test_fetch_detail_investment_summary_supports_yearly_and_all_time():
    conn = sqlite3.connect(":memory:")
    try:
        _create_reporting_source_schema(conn)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO stocks (id_stk, short_name, ticker, total_investment_amt, disinvestment_amt) VALUES (1, 'AAA', '', 1500.0, 400.0)"
        )
        cur.executemany(
            "INSERT INTO transactions (id_trd, id_stk, cont_no, trd_dt, trade_type_trd, qty_trd, net_amt_trd) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (1, 1, "C1", "2024-05-01", "BUY", 10, 1000.0),
                (2, 1, "C2", "2023-05-01", "BUY", 5, 500.0),
            ],
        )
        cur.executemany(
            "INSERT INTO sell_records (id_sell, id_stk, buy_dt, sell_dt, buy_value, sell_value, sell_qty, pnl_amt, holding_days) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    1,
                    1,
                    "2024-01-01",
                    "2024-05-01",
                    600.0,
                    800.0,
                    6,
                    200.0,
                    121,
                ),
            ],
        )
        conn.commit()

        assert fetch_detail_investment_summary(
            cur, 1, "2024-04-01", "2025-03-31"
        ) == (1000.0, 600.0)
        assert fetch_detail_investment_summary(cur, 1) == (1500.0, 400.0)
    finally:
        conn.close()


def test_fetch_detail_timeline_rows_and_corp_action_presence():
    conn = sqlite3.connect(":memory:")
    try:
        _create_reporting_source_schema(conn)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO contracts (cont_no, settle_dt) VALUES ('C1', '2024-05-03')"
        )
        cur.execute(
            "INSERT INTO transactions (id_trd, id_stk, cont_no, trd_dt, trade_type_trd, qty_trd, net_amt_trd) VALUES (1, 1, 'C1', '2024-05-01', 'BUY', 10, 1000.0)"
        )
        cur.execute(
            "INSERT INTO bonus_issues (id_bonus, id_stk, ex_dt, ratio_old, ratio_new) VALUES (1, 1, '2024-07-01', 1, 1)"
        )
        conn.commit()

        assert fetch_detail_timeline_rows(cur, 1) == [
            ("2024-05-03", "BUY", 10, 1000.0)
        ]
        assert has_corporate_action_history(cur, 1) is True
        assert has_corporate_action_history(cur, 2) is False
    finally:
        conn.close()


def test_fetch_holding_bounds_returns_none_without_transactions():
    conn = sqlite3.connect(":memory:")
    try:
        _create_reporting_source_schema(conn)
        cur = conn.cursor()
        assert fetch_holding_bounds(cur, 1) is None
    finally:
        conn.close()


def test_fetch_holding_bounds_returns_min_and_max_dates():
    conn = sqlite3.connect(":memory:")
    try:
        _create_reporting_source_schema(conn)
        cur = conn.cursor()
        cur.executemany(
            "INSERT INTO transactions (id_trd, id_stk, cont_no, trd_dt, trade_type_trd, qty_trd, net_amt_trd) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (1, 1, "C1", "2024-05-01", "BUY", 10, 1000.0),
                (2, 1, "C2", "2024-06-01", "SELL", 2, 250.0),
            ],
        )
        conn.commit()

        assert fetch_holding_bounds(cur, 1) == ("2024-05-01", "2024-06-01")
    finally:
        conn.close()


def test_resolve_action_window_applies_filters_and_open_position_now():
    result = resolve_action_window(
        "2024-05-01",
        "2024-06-01",
        current_qty=5,
        filter_start=datetime(2024, 5, 15),
        filter_end=datetime(2024, 5, 20),
        now=datetime(2024, 7, 1),
    )

    assert result == (datetime(2024, 5, 15), datetime(2024, 5, 20))


def test_resolve_action_window_returns_none_for_disjoint_range():
    assert (
        resolve_action_window(
            "2024-05-01",
            "2024-06-01",
            current_qty=0,
            filter_start=datetime(2024, 7, 1),
            filter_end=datetime(2024, 7, 2),
        )
        is None
    )


def test_build_pooled_cost_reality_summary_calculates_pooled_metrics():
    result = build_pooled_cost_reality_summary(
        [
            ("2024-01-01", "BUY", 10, 1000.0),
            ("2024-02-01", "BUY", 10, 1200.0),
            ("2024-03-01", "SELL", 5, 700.0),
        ],
        current_price=150.0,
    )

    assert result["qty"] == pytest.approx(15.0)
    assert result["invested"] == pytest.approx(1650.0)
    assert result["disinvested"] == pytest.approx(550.0)
    assert result["realized_pnl"] == pytest.approx(150.0)
    assert result["unrealized_pnl"] == pytest.approx(600.0)
    assert result["total_pnl"] == pytest.approx(750.0)
    assert result["avg_price"] == pytest.approx(110.0)
    assert result["sells"][0]["days"] == 60


def test_build_online_corp_action_rows_formats_master_rows_and_dedupes():
    rows, updated_keys = build_online_corp_action_rows(
        [
            ("20-05-2024", 45.0, 0.0),
            ("01-06-2024", 0.0, 2.0),
        ],
        {("20-05-2024", "AAA.NS", "Dividend")},
        display_name="AAA.NS",
    )

    assert rows == [
        (
            "AAA.NS",
            "01-06-2024",
            "Stock Split",
            "Ratio 2.0",
            "Yahoo! Finance",
        )
    ]
    assert ("20-05-2024", "AAA.NS", "Dividend") in updated_keys
    assert ("01-06-2024", "AAA.NS", "Stock Split") in updated_keys


def test_build_online_corp_action_rows_formats_detail_rows():
    rows, updated_keys = build_online_corp_action_rows(
        [("20-05-2024", 45.0, 3.0)],
        set(),
    )

    assert rows == [
        ("20-05-2024", "Dividend", "₹45.00", "Yahoo! Finance"),
        ("20-05-2024", "Stock Split", "Ratio 3.0", "Yahoo! Finance"),
    ]
    assert ("20-05-2024", "Dividend") in updated_keys
    assert ("20-05-2024", "Stock Split") in updated_keys


def test_build_online_action_entries_normalizes_iterrows_data():
    rows = build_online_action_entries(
        [
            ("2024-05-20", {"Dividends": 45.0, "Stock Splits": 0.0}),
            ("2024-06-01", {"Dividends": 0.0, "Stock Splits": 2.0}),
        ],
        date_formatter=lambda value: f"fmt:{value}",
    )

    assert rows == [
        ("fmt:2024-05-20", 45.0, 0.0),
        ("fmt:2024-06-01", 0.0, 2.0),
    ]


def test_build_master_existing_action_keys_normalizes_master_records():
    result = build_master_existing_action_keys(
        [
            ("2024-05-20", "AAA.NS", "Dividend (FINAL)", "₹45.00", "₹5.00"),
            ("2024-06-01", "AAA.NS", "Stock Split", "Ratio 2.0", "-"),
        ],
        date_formatter=lambda value: f"fmt:{value}",
    )

    assert result == {
        ("fmt:2024-05-20", "AAA.NS", "Dividend"),
        ("fmt:2024-06-01", "AAA.NS", "Stock Split"),
    }


def test_build_detail_existing_action_keys_normalizes_detail_records():
    result = build_detail_existing_action_keys(
        [
            {
                "date": "2024-05-20",
                "nature": "Dividend (FINAL)",
                "val": "₹45.00",
                "tds": "₹5.00",
            },
            {
                "date": "2024-06-01",
                "nature": "Stock Split",
                "val": "Ratio 2.0",
                "tds": "-",
            },
        ],
        date_formatter=lambda value: f"fmt:{value}",
    )

    assert result == {
        ("fmt:2024-05-20", "Dividend"),
        ("fmt:2024-06-01", "Stock Split"),
    }


def test_build_detail_ledger_display_rows_tracks_running_balances():
    rows = build_detail_ledger_display_rows(
        [
            ("2024-05-03", "BUY", 10, 1000.0),
            ("2024-05-10", "BUY", 5, 600.0),
            ("2024-05-20", "SELL", 6, 900.0),
            ("2024-05-30", "SELL", 9, 1400.0),
        ]
    )

    assert rows == [
        (
            "2024-05-03",
            0,
            "+10",
            10,
            pytest.approx(1000.0),
            pytest.approx(100.0),
        ),
        (
            "2024-05-10",
            10,
            "+5",
            15,
            pytest.approx(1600.0),
            pytest.approx(106.6666666667),
        ),
        (
            "2024-05-20",
            15,
            "-6",
            9,
            pytest.approx(960.0),
            pytest.approx(106.6666666667),
        ),
        ("2024-05-30", 9, "-9", 0, pytest.approx(0.0), pytest.approx(0.0)),
    ]


def test_build_master_ledger_display_rows_formats_action_and_date():
    rows = build_master_ledger_display_rows(
        [
            ("C1", "AAA.NS", "2024-05-03", "BUY", 10, 100.0, 1000.0),
            ("C2", "AAA.NS", "2024-05-20", "SELL", 4, None, None),
        ],
        date_formatter=lambda value: f"fmt:{value}",
    )

    assert rows == [
        (
            "C1",
            "AAA.NS",
            "fmt:2024-05-03",
            "BUY",
            "Credit",
            "10",
            "\u20b9100.00",
            "\u20b91,000.00",
        ),
        ("C2", "AAA.NS", "fmt:2024-05-20", "SELL", "Debit", "4", "-", "-"),
    ]


def test_build_master_corp_tree_rows_formats_dates_for_tree():
    rows = build_master_corp_tree_rows(
        [
            ("2024-05-20", "AAA.NS", "Dividend", "₹45.00", "₹5.00"),
            ("2024-06-01", "AAA.NS", "Stock Split", "Ratio 2.0", "-"),
        ],
        date_formatter=lambda value: f"fmt:{value}",
    )

    assert rows == [
        ("AAA.NS", "fmt:2024-05-20", "Dividend", "₹45.00", "₹5.00"),
        ("AAA.NS", "fmt:2024-06-01", "Stock Split", "Ratio 2.0", "-"),
    ]


def test_build_master_dividend_tree_rows_returns_summary_and_details():
    result = build_master_dividend_tree_rows(
        {
            "dividend_records": [
                ("AAA.NS", "20-05-2024", "10", "₹4.50", "₹1,000.00", "₹45.00", "5.00%", "7.50%")
            ],
            "total_entitled_qty": 10.0,
            "total_invested_amount": 1000.0,
            "total_net_amount": 45.0,
        }
    )

    assert result == {
        "summary_row": (
            "TOTAL",
            "-",
            "10",
            "-",
            "₹1,000.00",
            "₹45.00",
            "-",
            "-",
        ),
        "detail_rows": [
            ("AAA.NS", "20-05-2024", "10", "₹4.50", "₹1,000.00", "₹45.00", "5.00%", "7.50%")
        ],
    }


def test_build_master_dividend_tree_rows_omits_summary_without_detail_rows():
    result = build_master_dividend_tree_rows(
        {
            "dividend_records": [],
            "total_entitled_qty": 0.0,
            "total_invested_amount": 0.0,
            "total_net_amount": 0.0,
        }
    )

    assert result == {"summary_row": None, "detail_rows": []}


def test_build_detail_ledger_tree_rows_formats_detail_tree_values():
    rows = build_detail_ledger_tree_rows(
        [
            ("2024-05-03", 0, "+10", 10, 1000.0, 100.0),
            ("2024-05-20", 10, "-4", 6, 600.0, 100.0),
        ],
        date_formatter=lambda value: f"fmt:{value}",
    )

    assert rows == [
        ("fmt:2024-05-03", "0", "+10", "10", "1,000.00", "100.00"),
        ("fmt:2024-05-20", "10", "-4", "6", "600.00", "100.00"),
    ]


def test_build_detail_corp_tree_rows_formats_dates_for_tree():
    rows = build_detail_corp_tree_rows(
        [
            {
                "date": "2024-05-20",
                "nature": "Dividend (FINAL)",
                "val": "₹45.00",
                "tds": "₹5.00",
            }
        ],
        date_formatter=lambda value: f"fmt:{value}",
    )

    assert rows == [("fmt:2024-05-20", "Dividend (FINAL)", "₹45.00", "₹5.00")]


def test_build_detail_dividend_tree_rows_returns_summary_and_details():
    result = build_detail_dividend_tree_rows(
        {
            "dividend_records": [
                (
                    "AAA.NS",
                    "10",
                    "₹1,000.00",
                    "₹45.00",
                    "5.00%",
                    "7.50%",
                    "110.0",
                )
            ],
            "total_entitled_qty": 10.0,
            "total_invested_amount": 1000.0,
            "total_net_amount": 45.0,
        }
    )

    assert result == {
        "summary_row": (
            "TOTAL",
            "10",
            "₹1,000.00",
            "₹45.00",
            "-",
            "-",
            "-",
        ),
        "detail_rows": [
            (
                "AAA.NS",
                "10",
                "₹1,000.00",
                "₹45.00",
                "5.00%",
                "7.50%",
                "110.0",
            )
        ],
    }


def test_build_detail_dividend_tree_rows_omits_summary_without_rows():
    result = build_detail_dividend_tree_rows(
        {
            "dividend_records": [],
            "total_entitled_qty": 0.0,
            "total_invested_amount": 0.0,
            "total_net_amount": 0.0,
        }
    )

    assert result == {"summary_row": None, "detail_rows": []}


def test_build_detail_position_overview_fragments_formats_comparison_block():
    fragments = build_detail_position_overview_fragments(
        total_investment=1000.0,
        disinvestment_amount=250.0,
        current_invested_amount=750.0,
        buy_qty=10.0,
        sell_qty=4.0,
        current_qty=6.0,
        avg_price=125.0,
        current_price=150.0,
        reality_summary={
            "disinvested": 200.0,
            "invested": 800.0,
            "qty": 6.0,
            "avg_price": 133.3333,
        },
    )

    assert fragments[0][1] == "subheader"
    assert "Income Tax (IT)" in fragments[0][0]
    assert "Reality (Pooled)" in fragments[0][0]
    assert any(
        text
        == "  Total Bought Quantity:                       10  |                10\n"
        and tag == "normal"
        for text, tag in fragments
    )
    assert any(
        text
        == "  Current Quantity:                             6  |                 6\n"
        and tag == "normal"
        for text, tag in fragments
    )
    assert any(
        text == "          133.33\n" and tag == "positive"
        for text, tag in fragments
    )


def test_build_detail_position_overview_fragments_omits_price_lines_for_empty_position():
    fragments = build_detail_position_overview_fragments(
        total_investment=1000.0,
        disinvestment_amount=1000.0,
        current_invested_amount=0.0,
        buy_qty=10.0,
        sell_qty=10.0,
        current_qty=0.0,
        avg_price=0.0,
        current_price=150.0,
        reality_summary={
            "disinvested": 1000.0,
            "invested": 0.0,
            "qty": 0.0,
            "avg_price": 0.0,
        },
    )

    assert not any(
        "Average Price per Share:" in text
        or "Current Market Price (CMP):" in text
        for text, _tag in fragments
    )


def test_compute_intraday_vwap_analysis_returns_series_and_summary():
    result = compute_intraday_vwap_analysis(
        [
            (110.0, 90.0, 100.0, 10.0),
            (130.0, 110.0, 120.0, 30.0),
        ]
    )

    assert result is not None
    assert result["vwap_values"][0] == pytest.approx(100.0)
    assert result["vwap_values"][1] == pytest.approx(115.0)
    assert result["current_price"] == pytest.approx(120.0)
    assert result["current_vwap"] == pytest.approx(115.0)


def test_assemble_detail_tree_data_gathers_and_formats_all_stock_details():
    conn = sqlite3.connect(":memory:")
    try:
        _create_reporting_source_schema(conn)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO stocks (id_stk, short_name, ticker) VALUES (1, 'AAA', '')"
        )
        cur.execute(
            "INSERT INTO contracts (cont_no, settle_dt) VALUES ('C1', '2024-05-03')"
        )
        cur.execute(
            "INSERT INTO transactions (id_trd, id_stk, cont_no, trd_dt, trade_type_trd, qty_trd, net_amt_trd) VALUES (1, 1, 'C1', '2024-05-01', 'BUY', 10, 1000.0)"
        )
        cur.execute(
            "INSERT INTO dividends (id_div, id_stk, record_dt, credit_dt, div_type, entitled_qty, gross_amt, net_amt, tds_amt) VALUES (1, 1, '2024-05-10', '2024-05-20', 'FINAL', 10, 50.0, 45.0, 5.0)"
        )
        cur.execute(
            "INSERT INTO splits (id_split, id_stk, ex_dt, old_fv, new_fv) VALUES (1, 1, '2024-06-01', 10.0, 5.0)"
        )
        cur.execute(
            "INSERT INTO bonus_issues (id_bonus, id_stk, ex_dt, ratio_old, ratio_new) VALUES (1, 1, '2024-07-01', 1, 1)"
        )
        cur.execute(
            "INSERT INTO sell_records (id_sell, id_stk, buy_dt, sell_dt, buy_value, sell_value, sell_qty, pnl_amt, holding_days) VALUES (1, 1, '2024-01-01', '2024-05-01', 100.0, 120.0, 1, 20.0, 121)"
        )
        conn.commit()

        result = assemble_detail_tree_data(
            cur,
            1,
            "AAA Inc",
            150.0,
            capital_gains_tax_rates=lambda _d: (0.15, 0.10),
            dividend_metric_resolver=lambda *args: (5.0, 10.0, 180),
        )

        assert result["ledger_tree_rows"] == [
            ("2024-05-03", "0", "+10", "10", "1,000.00", "100.00")
        ]
        assert result["dividend_tree_rows_data"]["detail_rows"] == [
            (
                "AAA Inc",
                "10",
                "₹1,000.00",
                "₹45.00",
                "5.00%",
                "10.00%",
                "180.0",
            )
        ]
        assert result["corp_tree_rows"] == [
            (
                "2024-05-20",
                "Dividend (FINAL)",
                "₹45.00 | Ret 5.00% | Ann 10.00% p.a.",
                "₹5.00",
            ),
            ("2024-06-01", "Stock Split", "Ratio 10.0:5.0", "-"),
            ("2024-07-01", "Bonus Issue", "Ratio 1 for 1", "-"),
        ]
        assert len(result["realized_rows"]) == 1
        assert result["realized_rows"][0]["pnl"] == 20.0
        assert result["realized_rows"][0]["pat"] == 17.0
        assert result["reality_summary"]["qty"] == 10.0
    finally:
        conn.close()


def test_compute_intraday_vwap_analysis_returns_none_for_empty_input():
    assert compute_intraday_vwap_analysis([]) is None


def test_compute_intraday_price_bounds_adds_one_percent_padding():
    result = compute_intraday_price_bounds(
        [100.0, 120.0],
        [105.0, 115.0],
        current_price=120.0,
    )

    assert result == (98.8, 121.2)


def test_resolve_intraday_chart_window_uses_market_hours():
    start_time, end_time = resolve_intraday_chart_window(
        [datetime(2024, 5, 20, 10, 5)]
    )

    assert start_time == datetime(2024, 5, 20, 9, 15)
    assert end_time == datetime(2024, 5, 20, 15, 30)


def test_resolve_intraday_chart_window_returns_none_for_empty_values():
    assert resolve_intraday_chart_window([]) is None


def test_build_intraday_analysis_lines_formats_summary_and_guide():
    lines = build_intraday_analysis_lines(
        current_price=120.0,
        current_vwap=115.0,
        trend="BULLISH 🟢",
        delta_pct=4.35,
    )

    assert lines[0] == "Current Price : ₹120.00\n"
    assert lines[1] == "Intraday VWAP : ₹115.00\n"
    assert "Trend Status  : BULLISH 🟢 (Delta: +4.35%)" in lines[2]
    assert any("CHART LEGEND & ANALYSIS GUIDE" in line for line in lines)


def test_build_current_holdings_row_formats_values_and_profit_tag():
    result = build_current_holdings_row(
        {
            "ticker": "AAA.NS",
            "qty": 10,
            "price": 120.0,
            "unrealized": 200.0,
            "realized": 50.0,
        },
        avg_price=100.0,
        cost=1000.0,
    )

    assert result == {
        "values": (
            "AAA.NS",
            10,
            "100.00 (₹100.00)",
            "1,000.00 (₹1,000.00)",
            "120.00",
            "200.00 (+20.00%) [₹200.00 (+20.00%)]",
            "50.00",
        ),
        "tag": "profit",
    }


def test_build_current_holdings_header_values_formats_strings_and_color():
    result = build_current_holdings_header_values(
        total_invested=1000.0,
        total_value=1250.0,
        total_unrealized=250.0,
        total_realized=75.0,
        total_invested_ex_stt=1000.0,
    )
    assert result == {
        "invested": "Current Cost Basis: ₹1,000.00 (₹1,000.00)",
        "value": "Live Market Value: ₹1,250.00",
        "unrealized": "Unrealized Gain/Loss: ₹250.00 (+25.00%) [₹250.00 (+25.00%)]",
        "unrealized_color": "#27ae60",
        "realized": "Realized Gain/Loss: ₹75.00",
    }


def test_build_summary_tree_rows_formats_years_and_all_years_totals():
    result = build_summary_tree_rows(
        {
            "FY 2024-25": {
                "inv": 1000.0,
                "pnl": 100.0,
                "pat": 80.0,
                "div": 20.0,
                "miss_profit": 5.0,
                "save_loss": 0.0,
            },
            "FY 2023-24": {
                "inv": 500.0,
                "pnl": 50.0,
                "pat": 40.0,
                "div": 10.0,
                "miss_profit": 0.0,
                "save_loss": 3.0,
            },
        }
    )

    assert result["yearly_rows"][0][0] == "FY 2024-25"
    assert result["summary_row"] == (
        "ALL YEARS",
        "1,500.00",
        "150.00",
        "120.00",
        "30.00",
        "150.00",
        "5.00",
        "3.00",
    )


def test_build_capital_stats_tree_rows_formats_summary_and_sorted_years():
    result = build_capital_stats_tree_rows(
        {
            "overall": {
                "total_investment": 1500.0,
                "total_disinvestment": 600.0,
                "max_invested": 900.0,
                "min_invested": 100.0,
                "largest_investment": 700.0,
                "largest_disinvestment": 300.0,
            },
            "yearly": {
                "FY 2023-24": {
                    "total_investment": 500.0,
                    "total_disinvestment": 200.0,
                    "max_invested": 300.0,
                    "min_invested": 50.0,
                    "largest_investment": 250.0,
                    "largest_disinvestment": 120.0,
                },
                "FY 2024-25": {
                    "total_investment": 1000.0,
                    "total_disinvestment": 400.0,
                    "max_invested": 600.0,
                    "min_invested": 100.0,
                    "largest_investment": 450.0,
                    "largest_disinvestment": 180.0,
                },
            },
        },
        financial_year_sort_key=lambda label: label,
    )

    assert result["summary_row"] == (
        "ALL YEARS",
        "1,500.00",
        "600.00",
        "900.00",
        "100.00",
        "700.00",
        "300.00",
    )
    assert result["yearly_rows"][0][0] == "FY 2024-25"


def test_build_stock_tree_initial_row_formats_fetching_state():
    result = build_stock_tree_initial_row(
        display_name="AAA.NS",
        realized=125.0,
        is_yearly=False,
        current_qty=10,
    )

    assert result == (
        "AAA.NS",
        "125.00",
        "Fetching...",
        "125.00",
        "Calculating...",
    )


def test_build_stock_tree_update_row_formats_unrealized_and_xirr():
    result = build_stock_tree_update_row(
        display_name="AAA.NS",
        realized=125.0,
        total=300.0,
        unrealized=175.0,
        xirr_rate=0.1234,
        show_unrealized=True,
    )

    assert result == (
        "AAA.NS",
        "125.00",
        "175.00",
        "300.00",
        "12.34%",
    )


def test_build_grand_summary_row_formats_with_and_without_unrealized():
    assert build_grand_summary_row(grand_realized=125.0) == (
        "🏆 GRAND SUMMARY",
        "125.00",
        "-",
        "125.00",
        "-",
    )
    assert build_grand_summary_row(
        grand_realized=125.0,
        grand_unrealized=50.0,
    ) == (
        "🏆 GRAND SUMMARY",
        "125.00",
        "50.00",
        "175.00",
        "-",
    )


def test_resolve_reporting_period_for_all_years():
    assert resolve_reporting_period("All Years") == (False, None, None)


def test_resolve_reporting_period_for_financial_year():
    assert resolve_reporting_period("FY 2024-25") == (
        True,
        "2024-04-01",
        "2025-03-31",
    )


def test_resolve_optional_date_filters_returns_datetimes_when_present():
    assert resolve_optional_date_filters("2024-04-01", "2025-03-31") == (
        datetime(2024, 4, 1),
        datetime(2025, 3, 31),
    )


def test_resolve_optional_date_filters_returns_none_for_missing_values():
    assert resolve_optional_date_filters(None, None) == (None, None)


def test_build_detail_header_fragments_includes_live_data_for_all_years_view():
    result = build_detail_header_fragments(
        {
            "short_name": "AAA",
            "company_name": "Alpha Ltd",
            "ticker": "AAA.NS",
            "price": 123.45,
            "low52": 100.0,
            "high52": 150.0,
        },
        is_yearly=False,
    )

    assert result[0] == (f"{'='*75}\n", "normal")
    assert result[1] == ("Stock: AAA (Alpha Ltd)\n", "header")
    assert result[2] == (
        "Ticker: AAA.NS | Live Price: ₹123.45\n",
        "subheader",
    )
    assert result[3] == (
        "52-Week Range: ₹100.00 - ₹150.00\n",
        "italic",
    )


def test_build_detail_header_fragments_omits_live_section_for_yearly_view():
    result = build_detail_header_fragments(
        {
            "short_name": "AAA",
            "company_name": "Alpha Ltd",
            "ticker": "AAA.NS",
            "price": 123.45,
            "low52": 100.0,
            "high52": 150.0,
        },
        is_yearly=True,
    )

    assert result == [
        (f"{'='*75}\n", "normal"),
        ("Stock: AAA (Alpha Ltd)\n", "header"),
        (f"{'='*75}\n\n", "normal"),
    ]


def test_build_summary_selection_fragments_returns_header_and_message():
    result = build_summary_selection_fragments()

    assert result[0] == ("Portfolio Summary\n\n", "header")
    assert "Select an individual stock" in result[1][0]
    assert result[1][1] == "normal"


def test_build_live_market_snapshot_handles_missing_and_invalid_values():
    result = build_live_market_snapshot(
        None,
        {"yearHigh": "150.5", "yearLow": None},
    )

    assert result == {"price": 0.0, "high52": 150.5, "low52": 0.0}


def test_build_live_market_snapshot_uses_close_price_and_defaults():
    result = build_live_market_snapshot(123.45)

    assert result == {"price": 123.45, "high52": 0.0, "low52": 0.0}


def test_build_realized_pnl_rows_calculates_pat_and_opportunity():
    rows = build_realized_pnl_rows(
        [(1000.0, 200, 150.0, 10, 1200.0, "2024-05-01")],
        current_price=140.0,
        capital_gains_tax_rates=lambda _date: (0.15, 0.1),
    )

    assert rows == [
        {
            "cost": 1000.0,
            "qty": 10,
            "days": 200,
            "pnl": 150.0,
            "pat": pytest.approx(127.5),
            "opportunity_delta": pytest.approx(200.0),
        }
    ]


def test_build_reality_pnl_rows_handles_missing_live_price():
    rows = build_reality_pnl_rows(
        [
            {
                "cost": 100.0,
                "qty": 2,
                "days": 10,
                "pnl": 5.0,
                "sell_value": 110.0,
            }
        ],
        current_price=0.0,
    )

    assert rows == [
        {
            "cost": 100.0,
            "qty": 2,
            "days": 10,
            "pnl": 5.0,
            "opportunity_delta": None,
        }
    ]


def test_build_detail_dividend_display_data_formats_rows_and_totals():
    result = build_detail_dividend_display_data(
        [("2024-05-10", "2024-05-20", "FINAL", 10, 50.0, 45.0, 5.0)],
        display_name="AAA.NS",
        metric_resolver=lambda *_args: (5.0, 7.5, 110.0),
    )

    assert result["corp_records"] == [
        {
            "date": "2024-05-20",
            "nature": "Dividend (FINAL)",
            "val": "₹45.00 | Ret 5.00% | Ann 7.50% p.a.",
            "tds": "₹5.00",
        }
    ]
    assert result["dividend_records"] == [
        ("AAA.NS", "10", "₹1,000.00", "₹45.00", "5.00%", "7.50%", "110.0")
    ]
    assert result["total_entitled_qty"] == pytest.approx(10.0)
    assert result["total_invested_amount"] == pytest.approx(1000.0)
    assert result["total_net_amount"] == pytest.approx(45.0)


def test_build_master_dividend_display_data_formats_rows_and_totals():
    result = build_master_dividend_display_data(
        [
            (
                "AAA.NS",
                1,
                "2024-05-10",
                "2024-05-20",
                "FINAL",
                10,
                4.50,
                50.0,
                45.0,
                5.0,
            )
        ],
        metric_resolver=lambda *_args: (5.0, 7.5),
    )

    assert result["corp_records"] == [
        (
            "2024-05-20",
            "AAA.NS",
            "Dividend (FINAL)",
            "₹45.00 | Ret 5.00% | Ann 7.50% p.a.",
            "₹5.00",
        )
    ]
    assert result["dividend_records"] == [
        ("AAA.NS", "20-05-2024", "10", "₹4.50", "₹1,000.00", "₹45.00", "5.00%", "7.50%")
    ]
    assert result["total_entitled_qty"] == pytest.approx(10.0)
    assert result["total_invested_amount"] == pytest.approx(1000.0)
    assert result["total_net_amount"] == pytest.approx(45.0)


def test_build_master_corp_action_records_merges_and_sorts_rows():
    result = build_master_corp_action_records(
        dividend_corp_records=[
            (
                "2024-05-20",
                "AAA.NS",
                "Dividend (FINAL)",
                "₹45.00 | Ret 5.00% | Ann 7.50% p.a.",
                "₹5.00",
            )
        ],
        split_rows=[("AAA.NS", "2024-06-01", 10.0, 5.0)],
        bonus_rows=[("AAA.NS", "2024-04-15", 1, 1)],
    )

    assert result == [
        ("2024-04-15", "AAA.NS", "Bonus Issue", "Ratio 1 for 1", "-"),
        (
            "2024-05-20",
            "AAA.NS",
            "Dividend (FINAL)",
            "₹45.00 | Ret 5.00% | Ann 7.50% p.a.",
            "₹5.00",
        ),
        ("2024-06-01", "AAA.NS", "Stock Split", "Ratio 10.0:5.0", "-"),
    ]


def test_build_detail_corp_action_records_merges_and_sorts_rows():
    result = build_detail_corp_action_records(
        dividend_corp_records=[
            {
                "date": "2024-05-20",
                "nature": "Dividend (FINAL)",
                "val": "₹45.00 | Ret 5.00% | Ann 7.50% p.a.",
                "tds": "₹5.00",
            }
        ],
        split_rows=[("2024-06-01", 10.0, 5.0)],
        bonus_rows=[("2024-04-15", 1, 1)],
    )

    assert result == [
        {
            "date": "2024-04-15",
            "nature": "Bonus Issue",
            "val": "Ratio 1 for 1",
            "tds": "-",
        },
        {
            "date": "2024-05-20",
            "nature": "Dividend (FINAL)",
            "val": "₹45.00 | Ret 5.00% | Ann 7.50% p.a.",
            "tds": "₹5.00",
        },
        {
            "date": "2024-06-01",
            "nature": "Stock Split",
            "val": "Ratio 10.0:5.0",
            "tds": "-",
        },
    ]


def test_build_report_value_fragments_formats_comparison_line():
    assert build_report_value_fragments(
        "Realized Profit/Loss:",
        125.0,
        -50.0,
    ) == [
        ("  Realized Profit/Loss:          ", "normal"),
        ("          125.00", "positive"),
        ("  |  ", "normal"),
        ("          -50.00\n", "negative"),
    ]


def test_build_realized_pnl_report_fragments_formats_sections_and_notes():
    fragments = build_realized_pnl_report_fragments(
        [
            {
                "cost": 1000.0,
                "qty": 10,
                "days": 120,
                "pnl": 150.0,
                "pat": 127.5,
                "opportunity_delta": 200.0,
            }
        ],
        reality_rows=[
            {
                "cost": 900.0,
                "qty": 10,
                "days": 120,
                "pnl": 250.0,
                "opportunity_delta": None,
            }
        ],
    )

    assert fragments[0] == (
        "\nRealized Profit/Loss Breakdown (FIFO):\n",
        "subheader",
    )
    assert any(
        text == "\nRealized Profit/Loss Breakdown (Reality - Pooled Cost):\n"
        and tag == "subheader"
        for text, tag in fragments
    )
    assert fragments[-2][1] == "italic"
    assert fragments[-1][1] == "italic"


def test_build_realized_pnl_report_fragments_handles_empty_rows():
    assert build_realized_pnl_report_fragments([]) == [
        ("  No realized gain/loss details available.\n", "normal")
    ]
