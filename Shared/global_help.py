# -*- coding: utf-8 -*-
# Shared/global_help.py

from Shared.help_utils import show_standard_help

global_guide_text = [
    "Welcome to the Universal Finance Manager Master Documentation.",
    "",
    "1. Project Aim & Philosophy",
    "The Universal Finance Manager is a comprehensive, privacy-first desktop application designed to centralize and automate complex personal finance tracking. Built using Python, Tkinter, and SQLite, it operates as a secure offline ledger with powerful online analytical capabilities. The primary aim is to bridge the gap between fragmented financial services by unifying bank cash flows, equity portfolios, mutual funds, and insurance policies into a single, mathematically rigorous ecosystem.",
    "The system is defined by its strict data integrity rules: preventing overselling, enforcing First-In-First-Out (FIFO) capital gains accounting, maintaining exact corporate action cost-basis transfers, and automatically reconciling stock market trades with bank account balances. It leverages real-time market data (yfinance) and AI-driven insights to transition from a static ledger into an active portfolio advisory tool.",
    "",
    "2. System Menu Hierarchy",
    "• Universal Finance Dashboard (Root)",
    "  • StockMan (Equity Portfolio)",
    "    - Company Management",
    "    - Trade Management (ICICI, Zerodha, IPOs, Sell FIFO, Ledger)",
    "    - Corporate Actions (Dividends, Bonus, Splits, Mergers, Demergers)",
    "    - Reports & Watchlist (Analytics, AI Scans)",
    "  • BankMan (Banking & Cash Flow)",
    "    - Bank & Account Master",
    "    - Passbook (Income/Expense/Transfer)",
    "    - Sub-Ledgers (FDs, Credit Cards, Loans, PPF)",
    "    - Budgets",
    "  • MFMan & InsMan (Mutual Funds & Insurance)",
    "",
    "3. Core Module Overviews",
    "• StockMan: The flagship equity tracking engine. Calculates exact broker levies, tracks live market prices, computes XIRR, and automates complex corporate actions ensuring the historical cost-basis remains mathematically perfect for Capital Gains tax reporting.",
    "• BankMan: A robust double-entry accounting ledger. Tracks standard income/expenses while offering dedicated sub-ledgers. Every financial outflow or inflow from StockMan automatically mirrors in BankMan, ensuring total net worth reconciliation.",
    "• MFMan & InsMan: Dedicated modules for tracking SIPs, lump-sum mutual funds, and recurring insurance premium obligations.",
    "• AI & Analytics Engine: Uses live market data to generate intraday VWAP charts, scan for technical momentum triggers, and query AI models for institutional broker advice.",
    "",
    "4. Global Navigation & Shortcuts",
    "• F1: Local Module Help - Opens a contextual, module-specific guide explaining the current screen's fields and rules.",
    "• Ctrl + F1: Global Help - Opens this overarching system guide from any window.",
    "• F2: Session Summary - Opens a quick-view grid of all data entries made during the current active session.",
    "• Escape: Cancel / Rollback - Safely aborts the current operation, closes the window, and rolls back unsaved partial entries to protect database integrity.",
    "• Enter: Advance Focus - Rapidly moves the cursor to the next logical input field.",
    "• Ctrl + Enter: Execute / Save - Bypasses remaining fields to immediately trigger the primary Save/Execute action.",
    "• Tab / Shift+Tab: UI Navigation - Cycles focus forward or backward through all interactive widgets."
]

global_faq_data = [
    (
        "Q1: How do I access module-specific help vs global help?",
        "A: Press F1 inside any active window to get help specific to that screen. Press Ctrl+F1 from anywhere to open this Global Help window."
    ),
    (
        "Q2: How do StockMan and BankMan interact?",
        "A: They share cash-flow data. When you trade or receive dividends in StockMan, computed and actual bank ledgers are generated. BankMan links its passbook entries to these StockMan ledgers to ensure 100% reconciliation."
    )
]

def show_global_help(parent=None):
    """Launch the Global Help Center accessible via Ctrl+F1."""
    if hasattr(parent, "_global_help_open") and parent._global_help_open:
        return
    if parent:
        parent._global_help_open = True

    show_standard_help(
        parent=parent,
        title="Global Help Center",
        guide_lines=global_guide_text,
        faq_data=global_faq_data
    )
