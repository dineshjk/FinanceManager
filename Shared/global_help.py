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
    "2. System Menu Hierarchy & Module Responsibilities",
    "• Universal Finance Dashboard (Root)",
    "  • StockMan (Equity Portfolio & Market Intelligence)",
    "    - Company Management: Register stock tickers, ISINs, sectors, market caps, and company metadata.",
    "    - Trade Management: Record secondary and primary trades (ICICI Direct, Zerodha Contract Notes, Direct/IPOs, Sell FIFO). Automatically calls 'update_portfolio_excel()' and matches open AI advice upon every trade save, update, or delete.",
    "    - Corporate Actions: Record dividends, stock splits, bonuses, mergers, and demergers with exact cost-basis adjustments.",
    "    - Maintenance: Update current market prices (CMP), verify database integrity, and run SQLite backups.",
    "    - Reports & Analytics: Capital gains statements (realized & unrealized), holding summaries, sector allocations, and XIRR performance metrics.",
    "    - Watchlist & Alerts: Monitor target buy/sell prices, scan for technical momentum signals, and generate the daily AI Pick of the Day.",
    "    - Advice Tracking: Track AI 'Pick of the Day' advice, monitor execution status ('Fully Followed', 'Partially Followed', 'Not Followed'), record execution dates, and export multi-sheet portfolio summaries.",
    "    - Drive Sync Engine: Synchronizes portfolio data and advice logs to Google Drive upon morning first run (prompted) and in the background whenever trades or advice change.",
    "    - Transfer Data: Calculate and export discrepant holding data for shares transferred from ICICI Direct to Zerodha.",
    "  • BankMan (Banking & Cash Flow)",
    "    - Bank & Account Master: Manage bank accounts, card accounts, and overdraft limits.",
    "    - Passbook (Income/Expense/Transfer): Double-entry recording for income, expenses, and inter-account transfers.",
    "    - Sub-Ledgers: Fixed Deposits (FDs), Credit Cards, Loans, and Public Provident Fund (PPF).",
    "    - Budgets: Monthly expenditure budgets and variance tracking.",
    "  • MFMan & InsMan (Mutual Funds & Insurance)",
    "    - MFMan: Systematic Investment Plans (SIPs), lump-sum folios, and NAV valuation.",
    "    - InsMan: Term life, health, and vehicle insurance policies with premium reminder schedules.",
    "",
    "3. Inter-Module Workflow & Automated Synchronization",
    "• Trade Entry to Advice Matching: When you execute and record a trade in Trade Management (ICICI or Zerodha), the engine automatically checks 'advice_log' for open advice matching the stock and action (e.g. 'Buy 30 HDFCBANK'). If matched, it marks the status as 'Fully Followed' (or 'Partially Followed' for partial quantities) with today's execution date.",
    "• Automated Excel Export: Saving, editing, or deleting a trade immediately calls 'update_portfolio_excel()', generating 'StockMan_Portfolio.xlsx' with two sheets: 'Portfolio' (holdings & CMP) and 'Advice_Log' (full advice audit trail).",
    "• Google Drive Cloud Sync: Every portfolio Excel regeneration initiates an asynchronous background upload to Google Drive without blocking the user interface.",
    "• Bank Reconciliation: Stock trades and corporate actions generate computed bank ledger entries in BankMan, ensuring total net worth reconciliation.",
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
    ),
    (
        "Q3: Which modules carry out which tasks for Advice Tracking and Excel Sync?",
        "A: Watchlist scans identify the daily AI 'Pick of the Day'. Advice Tracking records recommendations and execution statuses. Trade Management executes buy/sell trades, auto-matches open advice in the Advice Log, and immediately calls 'update_portfolio_excel()'. The Drive Sync engine uploads the dual-sheet workbook to Google Drive in the background."
    ),
    (
        "Q4: Does trading automatically update 'StockMan_Portfolio.xlsx'?",
        "A: Yes! Whenever a trade is added (ICICI or Zerodha), updated, or deleted, Trade Management automatically calls 'update_portfolio_excel()', which refreshes the Excel file with both 'Portfolio' and 'Advice_Log' sheets and uploads it to Google Drive."
    ),
    (
        "Q5: How does the startup first-run cycle work?",
        "A: Each morning on the first run of the day, StockMan prompts you to download latest stock prices and upload 'StockMan_Portfolio.xlsx' to Google Drive. The cycle resets daily at 8:00 AM."
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
