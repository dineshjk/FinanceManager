# -*- coding: utf-8 -*-
# tests/test_reporting_investment_stats.py
import pytest

from StockMan.helpers import calculate_investment_summary_stats


def test_calculate_investment_summary_stats_tracks_overall_totals():
    stats = calculate_investment_summary_stats(
        investment_rows=[
            (1, "2024-04-10", 100.0),
            (2, "2024-08-15", 50.0),
        ],
        disinvestment_rows=[(1, "2024-06-01", 50.0)],
    )

    overall = stats["overall"]
    year_stats = stats["yearly"]["FY 2024-25"]

    assert overall["total_investment"] == pytest.approx(150.0)
    assert overall["total_disinvestment"] == pytest.approx(50.0)
    assert overall["max_invested"] == pytest.approx(100.0)
    assert overall["min_invested"] == pytest.approx(0.0)
    assert overall["largest_investment"] == pytest.approx(100.0)
    assert overall["largest_disinvestment"] == pytest.approx(50.0)

    assert year_stats["total_investment"] == pytest.approx(150.0)
    assert year_stats["total_disinvestment"] == pytest.approx(50.0)
    assert year_stats["max_invested"] == pytest.approx(100.0)
    assert year_stats["min_invested"] == pytest.approx(0.0)


def test_calculate_investment_summary_stats_groups_same_trade_event():
    stats = calculate_investment_summary_stats(
        investment_rows=[
            (10, "2024-04-01", 60.0),
            (10, "2024-04-01", 40.0),
            (11, "2024-07-01", 50.0),
        ],
        disinvestment_rows=[
            (20, "2024-09-01", 30.0),
            (20, "2024-09-01", 70.0),
        ],
    )

    overall = stats["overall"]
    year_stats = stats["yearly"]["FY 2024-25"]

    assert overall["total_investment"] == pytest.approx(150.0)
    assert overall["largest_investment"] == pytest.approx(100.0)
    assert overall["total_disinvestment"] == pytest.approx(100.0)
    assert overall["largest_disinvestment"] == pytest.approx(100.0)
    assert year_stats["largest_investment"] == pytest.approx(100.0)
    assert year_stats["largest_disinvestment"] == pytest.approx(100.0)


def test_calculate_investment_summary_stats_carries_opening_balance_into_year():
    stats = calculate_investment_summary_stats(
        investment_rows=[
            (1, "2023-03-15", 100.0),
            (2, "2023-05-01", 50.0),
        ],
        disinvestment_rows=[(1, "2024-01-10", 80.0)],
    )

    fy_2022 = stats["yearly"]["FY 2022-23"]
    fy_2023 = stats["yearly"]["FY 2023-24"]

    assert fy_2022["max_invested"] == pytest.approx(100.0)
    assert fy_2022["min_invested"] == pytest.approx(0.0)

    assert fy_2023["total_investment"] == pytest.approx(50.0)
    assert fy_2023["total_disinvestment"] == pytest.approx(80.0)
    assert fy_2023["max_invested"] == pytest.approx(150.0)
    assert fy_2023["min_invested"] == pytest.approx(70.0)


def test_calculate_investment_summary_stats_handles_empty_inputs():
    stats = calculate_investment_summary_stats([], [])

    assert stats["overall"] == {
        "total_investment": 0.0,
        "total_disinvestment": 0.0,
        "max_invested": 0.0,
        "min_invested": 0.0,
        "largest_investment": 0.0,
        "largest_disinvestment": 0.0,
    }
    assert stats["yearly"] == {}


def test_yearly_passbook_multi_year_hisaab_continuity():
    from StockMan.reporting_utils import build_yearly_passbook_data

    # Scenario:
    # 2022-05-10: Buy 1,00,000 (FY 2022-23)
    # 2023-01-15: Sell 40,000 cost basis for 45,000 (P&L 5,000) (FY 2022-23)
    # FY 2022-23 closing investment should be: 1,00,000 - 40,000 = 60,000
    #
    # FY 2023-24 opening investment on 01-Apr-2023 should be 60,000!
    # 2023-07-20: Buy 50,000 (FY 2023-24)
    # 2023-11-10: Dividend 3,000 (FY 2023-24)
    # FY 2023-24 closing investment should be: 60,000 + 50,000 = 1,10,000
    #
    # FY 2024-25 opening investment on 01-Apr-2024 should be 1,10,000!
    # 2024-06-15: Sell 60,000 cost basis for 70,000 (P&L 10,000)
    # FY 2024-25 closing investment should be: 1,10,000 - 60,000 = 50,000
    mock_events = {
        "buys": [
            (1, "2022-05-10", "INFY.NS", 100000.0),
            (2, "2023-07-20", "TCS.NS", 50000.0),
        ],
        "sells": [
            (3, "2023-01-15", "INFY.NS", 45000.0, 40000.0, 45000.0, 5000.0, 1000000.0),
            (4, "2024-06-15", "TCS.NS", 70000.0, 60000.0, 70000.0, 10000.0, 2000000.0),
        ],
        "dividends": [
            (1, "2023-11-10", "TCS.NS", 3000.0),
        ],
    }

    res = build_yearly_passbook_data(mock_events)

    # Check FY 2022-23 ledger
    fy_22 = res["fy_ledgers"]["FY 2022-23"]["rows"]
    assert fy_22[0][0] == "2022-04-01"
    assert "Opening Investment" in fy_22[0][1]
    assert fy_22[0][6] == "0.00"  # Opening Investment
    # Closing row for FY 2022-23
    assert fy_22[-1][0] == "2023-03-31"
    assert "Closing Investment" in fy_22[-1][1]
    assert fy_22[-1][6] == "60,000.00"  # Closing: 100,000 - 40,000 = 60,000

    # Check FY 2023-24 ledger: Opening on 01-Apr-2023 must be 60,000.00!
    fy_23 = res["fy_ledgers"]["FY 2023-24"]["rows"]
    assert fy_23[0][0] == "2023-04-01"
    assert "Opening Investment" in fy_23[0][1]
    assert fy_23[0][4] == "60,000.00"
    assert fy_23[0][6] == "60,000.00"  # EXACTLY carried forward!
    # Closing row for FY 2023-24
    assert fy_23[-1][0] == "2024-03-31"
    assert "Closing Investment" in fy_23[-1][1]
    assert fy_23[-1][6] == "110,000.00"  # 60,000 + 50,000 = 110,000

    # Check FY 2024-25 ledger: Opening on 01-Apr-2024 must be 1,10,000.00!
    fy_24 = res["fy_ledgers"]["FY 2024-25"]["rows"]
    assert fy_24[0][0] == "2024-04-01"
    assert "Opening Investment" in fy_24[0][1]
    assert fy_24[0][4] == "110,000.00"
    assert fy_24[0][6] == "110,000.00"  # EXACTLY carried forward!
    # Closing row for FY 2024-25: 110,000 - 60,000 = 50,000.00
    assert fy_24[-1][0] == "2025-03-31"
    assert "Closing Investment" in fy_24[-1][1]
    assert fy_24[-1][6] == "50,000.00"

    # Check summary table has each year's opening and closing balancing out
    summary_map = {r[0]: r for r in res["hisaab_summary_rows"]}
    # FY 2022-23: Opening 0, Added 100k, Disinv 40k, Closing 60k
    assert summary_map["FY 2022-23"][2] == "0.00"
    assert summary_map["FY 2022-23"][3] == "100,000.00"
    assert summary_map["FY 2022-23"][4] == "40,000.00"
    assert summary_map["FY 2022-23"][5] == "60,000.00"

    # FY 2023-24: Opening 60k, Added 50k, Disinv 0, Closing 110k
    assert summary_map["FY 2023-24"][2] == "60,000.00"
    assert summary_map["FY 2023-24"][3] == "50,000.00"
    assert summary_map["FY 2023-24"][4] == "0.00"
    assert summary_map["FY 2023-24"][5] == "110,000.00"

    # FY 2024-25: Opening 110k, Added 0, Disinv 60k, Closing 50k
    assert summary_map["FY 2024-25"][2] == "110,000.00"
    assert summary_map["FY 2024-25"][3] == "0.00"
    assert summary_map["FY 2024-25"][4] == "60,000.00"
    assert summary_map["FY 2024-25"][5] == "50,000.00"


def test_yearly_passbook_filtered_by_fy():
    from StockMan.reporting_utils import build_yearly_passbook_data

    mock_events = {
        "buys": [
            (1, "2023-06-01", "INFY.NS", 50000.0),
            (2, "2024-06-01", "TCS.NS", 75000.0),
        ],
        "sells": [],
        "dividends": [],
    }

    # Filter to FY 2024-25
    res = build_yearly_passbook_data(mock_events, selected_fy="FY 2024-25")
    assert len(res["hisaab_summary_rows"]) == 1
    row = res["hisaab_summary_rows"][0]
    assert row[0] == "FY 2024-25"
    assert row[2] == "50,000.00"  # Opening carried forward from FY 2023-24!
    assert row[3] == "75,000.00"  # Added in FY 2024-25
    assert row[5] == "125,000.00"  # Closing at year end

