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
