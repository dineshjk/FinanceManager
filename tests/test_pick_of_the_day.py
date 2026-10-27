# -*- coding: utf-8 -*-
# tests/test_pick_of_the_day.py

"""Tests for Pick of the Day AI analysis feature."""

import sqlite3
import tkinter as tk
import pytest
from unittest.mock import MagicMock, patch

from StockMan import ai_analyzer
from StockMan.watchlist_menu import show_watchlist
from Shared.globals import STOCK_DB_PATH


def test_get_pick_of_the_day_advice_no_key():
    with patch.object(ai_analyzer, "get_api_key", return_value=None):
        msg = ai_analyzer.get_pick_of_the_day_advice("Holdings Test Summary", api_key=None)
        assert "[System] No Gemini API key found" in msg


def test_get_pick_of_the_day_advice_disabled():
    with patch.object(ai_analyzer, "AI_AVAILABLE", False):
        msg = ai_analyzer.get_pick_of_the_day_advice("Holdings Test Summary", api_key="dummy_key")
        assert "AI Analysis is disabled" in msg


def test_get_pick_of_the_day_advice_prompt_and_client():
    mock_response = MagicMock()
    mock_response.text = "# Pick of the Day Report\nWinner: MOCK1"

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(ai_analyzer.genai, "Client", return_value=mock_client):
        test_summary = "1 | MOCK1 | MOCK1.NS | Mock Enterprises | Industrial | 100 | ₹1,000.00 | ₹100,000.00 | 10.00%"
        result = ai_analyzer.get_pick_of_the_day_advice(test_summary, api_key="dummy_api_key")

        assert result == "# Pick of the Day Report\nWinner: MOCK1"
        assert mock_client.models.generate_content.called

        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        assert call_kwargs["model"] == "gemini-3.1-pro-preview"

        prompt = call_kwargs["contents"]
        # Verify verbatim standing instructions
        assert "Role: Elite Institutional Equity Research Analyst & Portfolio Strategist." in prompt
        assert "Task: Conduct an exhaustive, data-driven daily analysis of my entire tracked stock universe" in prompt
        assert "Fundamental Quality & Balance Sheet Health (18 Points)" in prompt
        assert "Growth Runway & Earnings Momentum (18 Points)" in prompt
        assert "Valuation & Margin of Safety (18 Points)" in prompt
        assert "Catalysts, Limelight News & Brokerage Upgrades (10 Points)" in prompt
        assert "Downside Risks & Vulnerabilities (15 Points)" in prompt
        assert "Sector Tailwinds & Relative Sector Performance (10 Points)" in prompt
        assert "Technical & Market Regime Context (5 Points)" in prompt
        assert "Portfolio Fit & Sector Weight Balance (6 Points)" in prompt
        assert "Pick of the Day" in prompt
        assert "Market Limelight & Special Situation Spotlight" in prompt
        assert "Complete Stock Universe Ranking Table" in prompt
        # Verify injected holdings summary
        assert test_summary in prompt

        # Verify Google Search Grounding tool is present
        config = call_kwargs["config"]
        assert hasattr(config, "tools")
        assert hasattr(config, "thinking_config")


def test_get_pick_of_the_day_advice_fallback_on_quota():
    mock_client = MagicMock()

    # First call (gemini-2.5-flash) raises 429 quota error
    # Second call (gemini-1.5-flash) succeeds
    mock_flash_response = MagicMock()
    mock_flash_response.text = "# Pick of the Day (1.5 Flash Fallback)"

    def side_effect(*args, **kwargs):
        if kwargs.get("model") == "gemini-3.1-pro-preview":
            raise Exception("429 Resource has been exhausted (quota limit)")
        return mock_flash_response

    mock_client.models.generate_content.side_effect = side_effect

    with patch.object(ai_analyzer.genai, "Client", return_value=mock_client):
        result = ai_analyzer.get_pick_of_the_day_advice("Holdings Summary", api_key="dummy_key")
        assert result == "# Pick of the Day (1.5 Flash Fallback)"


def test_all_stocks_db_query():
    """Verify that the database query extracts all stocks from 'stocks' table."""
    with sqlite3.connect(STOCK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.stk_code, s.company_name, s.ticker, s.sector, s.curr_avg_price,
                   (s.buy_qty - s.sell_qty) AS current_qty
            FROM stocks s
            ORDER BY ((s.buy_qty - s.sell_qty) * s.curr_avg_price) DESC, s.stk_code ASC
        """)
        rows = cursor.fetchall()
        assert len(rows) > 0
        has_holding = False
        has_watchlist = False
        for r in rows:
            stk_code, name, ticker, sector, curr_avg, qty = r
            assert len(stk_code) > 0
            if qty and qty > 0 and curr_avg and curr_avg > 0:
                has_holding = True
            else:
                has_watchlist = True
        assert has_holding
        assert has_watchlist


def test_watchlist_pick_of_the_day_button_exists():
    """Verify that the Pick of the Day button is instantiated with correct properties in watchlist UI."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available")

    root.withdraw()

    found_button = {}

    def mock_wait_window(win):
        def find_buttons(w):
            res = []
            if isinstance(w, tk.Button):
                res.append(w)
            for c in w.winfo_children():
                res.extend(find_buttons(c))
            return res

        buttons = find_buttons(win)
        for b in buttons:
            txt = b.cget("text")
            if "Pick of the Day" in txt:
                found_button["text"] = txt
                found_button["bg"] = b.cget("bg")
                found_button["cmd"] = b.cget("command")
        win.destroy()

    root.wait_window = mock_wait_window

    try:
        show_watchlist(root)
    finally:
        try:
            root.destroy()
        except Exception:
            pass

    assert "text" in found_button
    assert "⭐ Pick of the Day" in found_button["text"]
    assert found_button["bg"] == "#e11d48"


def test_clean_pick_of_the_day_response_formats_section_0_and_cleans_citations():
    """Verify that clean_pick_of_the_day_response formats section 0, removes citations, and preserves holdings."""
    sample_raw = """0. Based on the latest available market data as of October 21, 2026, the current total market value is ₹1,000,000.00.

**Holdings with Stale or Missing Data:**
*   **MOCK1.NS (Mock Enterprises Limited):** Current Price of ₹1,000.00 is as of October 1, 2026. [cite: 4 of prev batch]
*   **MOCK2.NS (Mock Global Limited):** Unlisted in India. [cite: 2 of prev batch]

**Current Portfolio Holdings and Valuation (as of October 21, 2026):**

| No. | Ticker | Company Name | Sector | Holding Qty | Avg Cost (INR) | Total Cost Basis (INR) | Current Price (INR) | Current Value (INR) | Weight % |
|---|---|---|---|---|---|---|---|---|---|
| 1 | MOCK1.NS | Mock Enterprises Limited | Industrial | 100 | ₹1,000.00 | ₹100,000.00 | ₹1,050.00 | ₹105,000.00 | 10.50% |

## 1. Market Snapshot
Market is consolidating near highs.

## 2. Pick of the Day: Winner Deep-Dive
Winner is MOCK1.NS with score 91.

## 3. Full Portfolio Ranking Table
| Rank | Ticker | Company Name | Score /100 | Action | Key Positive | Key Risk |
| :---: | :--- | :--- | :---: | :---: | :--- | :--- |
| 1 | MOCK1.NS | Mock Enterprises | 91 | ADD | Strong order book. [cite: 1] | Execution delays. [cite: 2] |

## 6. Sources & Data Freshness Audit
Exchange disclosures and audited reports.
"""

    cleaned = ai_analyzer.clean_pick_of_the_day_response(sample_raw)

    # 1. Clean report should start with Title and Section 0 header
    assert cleaned.startswith("# 🏆 Daily Pick of the Day")
    assert "## 0. Current Portfolio Holdings & Valuation Baseline" in cleaned

    # 2. Citations must be stripped
    assert "[cite:" not in cleaned

    # 3. Valuation table and subsequent sections must be preserved
    assert "Current Portfolio Holdings and Valuation" in cleaned
    assert "## 1. Market Snapshot" in cleaned
    assert "## 2. Pick of the Day: Winner Deep-Dive" in cleaned
    assert "## 3. Full Portfolio Ranking Table" in cleaned
    assert "MOCK1.NS" in cleaned


def test_pick_of_the_day_with_available_cash_injected():
    """Verify that available_cash is properly formatted and injected into the Gemini prompt."""
    mock_response = MagicMock()
    mock_response.text = "# Pick of the Day Report\nWinner: MOCK1\nCash: ₹1,50,000.00"

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(ai_analyzer.genai, "Client", return_value=mock_client):
        test_summary = "1 | MOCK1 | MOCK1.NS | Mock Enterprises | Industrial | 100 | ₹1,000.00 | ₹100,000.00 | 10.00%"
        result = ai_analyzer.get_pick_of_the_day_advice(
            test_summary,
            available_cash=150000.0,
            api_key="dummy_api_key"
        )

        assert mock_client.models.generate_content.called
        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        prompt = call_kwargs["contents"]

        assert "INVESTOR'S AVAILABLE CASH FOR NEW CAPITAL: ₹150,000.00" in prompt
        assert "MANDATORY CASH DEPLOYMENT & SIZING INSTRUCTIONS:" in prompt
        assert "Sizing Pick of the Day:" in prompt
        assert "Portfolio Assessment:" in prompt


def test_head_to_head_comparison_prompt_mandates_full_sentences():
    """Verify that the prompt explicitly mandates full sentences for Head-to-Head table parameters."""
    mock_response = MagicMock()
    mock_response.text = "# Pick of the Day Report"
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(ai_analyzer.genai, "Client", return_value=mock_client):
        ai_analyzer.get_pick_of_the_day_advice("Universe Summary", api_key="dummy_key")
        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        prompt = call_kwargs["contents"]

        assert "Head-to-Head Comparison Table (Winner vs Top Runner-Up)" in prompt
        assert "Action & Entry: Provide complete, actionable guidance" in prompt
        assert "Core Thesis: Provide complete, articulate sentences" in prompt
        assert "MANDATORY REQUIREMENT: Provide complete, articulate, and informative sentences for every cell in the Head-to-Head Comparison Table" in prompt


def test_ai_model_cascade_order_and_cache_fallback():
    """Verify that models are tried in exact requested order: 3.1 Pro -> 3.8 Flash -> 4 Argon -> Free -> Cache."""
    from StockMan.ai_analyzer import AI_MODEL_CASCADE
    assert AI_MODEL_CASCADE[0] == "gemini-3.1-pro-preview"
    assert "gemini-3.8-flash" in AI_MODEL_CASCADE
    assert "gemini-4-argon" in AI_MODEL_CASCADE
    
    # 3.8 Flash must come before 4 Argon
    assert AI_MODEL_CASCADE.index("gemini-3.8-flash") < AI_MODEL_CASCADE.index("gemini-4-argon")
    # 3.1 Pro Preview must come before 3.8 Flash
    assert AI_MODEL_CASCADE.index("gemini-3.1-pro-preview") < AI_MODEL_CASCADE.index("gemini-3.8-flash")


def test_pick_of_the_day_modal_renders_massive_report_with_multiple_tables_and_edu_notes():
    """Verify that open_pick_of_the_day_modal renders multiple tables, educational callouts, and resets viewport."""
    from StockMan import drive_sync

    massive_report = """# 🏆 Daily Pick of the Day Intelligence Report

## Market Snapshot

| Sector | Value | Weight | Status | Advice |
| :--- | :--- | :--- | :--- | :--- |
| Defense | ₹500,000 | 50% | OVER-INVESTED | Stop deployment |
| Banking | ₹100,000 | 10% | UNDER-INVESTED | Priority sector |

## Technical Analysis & Educational Guide

**Educational Note — Relative Strength Index (RSI):**
The RSI is a momentum oscillator measured on a scale of 0 to 100.

**Moving Averages (50 DMA & 200 DMA):**
The 50 DMA acts as intermediate support while the 200 DMA defines structural trend.

## Technical Indicators Table

| Ticker | CMP | 50 DMA | 200 DMA | RSI | Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| HDFC | 1,730 | 1,680 | 1,590 | 58.4 | BUY |
| INFY | 1,840 | 1,810 | 1,650 | 52.1 | HOLD |

## Securities Lending & Borrowing (SLB) Opportunities

| Stock | Eligible Qty | Yield | Status |
| :--- | :--- | :--- | :--- |
| HAL | 150 | 5.2% | ACCUMULATE |
| BEL | 300 | 4.8% | HOLD |

## Upcoming IPOs

| IPO | Price | Lot | Rating |
| :--- | :--- | :--- | :--- |
| EnergyCorp | 450 | 30 | BUY |
"""

    root = tk.Tk()
    root.withdraw()

    with patch.object(
        drive_sync,
        "get_local_pick_of_the_day",
        return_value=(massive_report, "test_report.md", "2026-10-25 18:00"),
    ):
        def mock_wait_window(win):
            for child in win.winfo_children():
                for sub in child.winfo_children():
                    if isinstance(sub, tk.Button) and "Pick of the Day" in sub.cget("text"):
                        sub.invoke()
                        break
            win.destroy()

        root.wait_window = mock_wait_window
        try:
            show_watchlist(root)
        finally:
            try:
                root.destroy()
            except Exception:
                pass
