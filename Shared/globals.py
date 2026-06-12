# -*- coding: utf-8 -*-
# File: FinanceManager/StockMan/globals.py
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\Shared\globals.py

"""
Global constants, configurations, and standardized messages for the Stock Portfolio Management application.
"""

import os
import logging
import sqlite3
from datetime import date
from contextlib import contextmanager
from typing import Generator

# =============================================================================
# 1. PATHS & APPLICATION INFO (Restored from Original)
# =============================================================================
# PROJECT_ROOT evaluates to: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STOCK_DB_PATH = os.path.join(PROJECT_ROOT, "data", "mystocks.db")
BANK_DB_PATH = os.path.join(PROJECT_ROOT, "data", "mybanks.db")

# Assuming market_data belongs in the StockMan folder
DATA_DIR = os.path.join(PROJECT_ROOT, "Shared", "market_data")

LOG_DIR = os.path.join(PROJECT_ROOT, "log")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "stock_portfolio.log")

STOCK_APP_TITLE = "Stock Portfolio Management"
BANK_APP_TITLE = "Bank Account Management"
UNIVERSAL_APP_TITLE = "Universal Finance Manager"
STOCK_APP_VERSION = "1.0"
BANK_APP_VERSION = "1.0"

# =============================================================================
# 2. FINANCIAL CONSTANTS & FUNCTIONS (Restored from Original)
# =============================================================================
ETCN = 0.0000297
ETCB = 0.0000375
BROK = 0.0022
GST = 0.18
SEBI = 0.000001
STT = 0.001
IPFT = 0.000001


def get_etc(trade_date: date, exchange: str) -> float:
    """Returns the Exchange Transaction Charge (ETC)."""
    if not isinstance(trade_date, date):
        raise TypeError("trade_date must be a datetime.date object")

    exchange = exchange.upper()
    if exchange not in ("NSE", "BSE"):
        raise ValueError("Exchange must be 'NSE' or 'BSE'")

    if trade_date <= date(2023, 3, 31):
        return 0.0000345 + IPFT if exchange == "NSE" else 0.0000375 + IPFT
    elif date(2023, 4, 1) <= trade_date <= date(2024, 9, 30):
        return 0.0000325 + IPFT if exchange == "NSE" else 0.0000375 + IPFT
    elif trade_date >= date(2024, 10, 1):
        return 0.0000297 + IPFT if exchange == "NSE" else 0.0000375 + IPFT

    raise ValueError(f"Could not determine ETC rate for date {trade_date}")


def get_capital_gains_tax_rates(sell_date: date) -> tuple[float, float]:
    """Returns the applicable (STCG_rate, LTCG_rate)."""
    if sell_date >= date(2024, 7, 23):
        return 0.20, 0.125  # STCG 20%, LTCG 12.5%
    else:
        return 0.15, 0.10  # STCG 15%, LTCG 10%


class ValidationError(Exception):
    """Custom exception for validation errors."""


# =============================================================================
# 3. UI AND THEMING (New Milestone 1 Additions)
# =============================================================================
DATE_FMT_UI = "dd-mm-yyyy"
DATE_FMT_DB = "%Y-%m-%d"

UI_THEME = {
    # Raw Color Palette
    "dark_slate": "#1e293b",
    "charcoal": "#334155",
    "slate_light": "#475569",
    "gold": "#FFD700",
    "white": "#ffffff",
    "red_alert": "#ef4444",
    # Header Colors (Added to resolve KeyError)
    "bg_header": "#1e293b",
    "fg_header": "#ffffff",
    # ---------------------------------------------------------
    # The Single Source of Truth for Input Fields (trade_add model)
    # ---------------------------------------------------------
    "bg_input": "black",
    "fg_input": "yellow",
    "bg_readonly": "black",
    "fg_readonly": "yellow",
    "bg_disabled": "black",
    "fg_disabled": "yellow",
    "bg_hover": "#8a1e62",  # Purple
    "fg_hover": "#FFD700",  # Bright Yellow
    "bg_focus": "red",
    "fg_focus": "yellow",
    "bg_select": "blue",  # Text selection background
    "bg_error": "#ffcccc",  # Validation flash background
    # Standardized Fonts
    "font_main": ("Helvetica", 14, "bold"),
    "font_bold": ("Helvetica", 14, "bold"),
    "font_title": ("Helvetica", 16, "bold"),
}

MSG = {
    "succ_saved": "{} entry recorded successfully for {}.",
    "succ_prompt_next": "Do you want to add another {} entry?",
    "err_invalid_comp": "Please select a valid company from the list.",
    "err_positive_num": "Ensure all ratios and quantities are valid positive numbers.",
    "err_no_holding": "You do not currently hold any shares of {} on the selected date.",
    "err_invalid_date": "Please ensure all selected dates are chronologically valid.",
    "err_limit_reached": "Maximum of {} entries allowed per transaction.",
    "err_db_save": "Database error: Failed to save the record. Details: {}",
    "err_db_fetch": "Database error: Failed to fetch data. Details: {}",
    "icon_success": "✅",
    "icon_error": "❌",
    "icon_warning": "⚠️",
    "icon_info": "ℹ️",
}

# =============================================================================
# 4. LOGGING & DATABASE CONNECTION (Merged)
# =============================================================================
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename=LOG_PATH,
)
logger = logging.getLogger("StockMan")


@contextmanager
def get_db_connection(
    db_path: str = STOCK_DB_PATH,
) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
    except sqlite3.Error as e:
        logger.error("Database error connecting to %s: %s", db_path, e, exc_info=True)
        raise
    finally:
        if conn:
            conn.close()
