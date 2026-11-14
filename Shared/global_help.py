# -*- coding: utf-8 -*-
# Shared/global_help.py

"""Global Help Center & Universal System Documentation Registry.

This module defines the master documentation, workflow explanations,
keyboard shortcut cheat sheets, and architectural directory for the entire
Universal Finance Manager suite. It is invoked globally across all windows
via the `Ctrl+F1` shortcut or through the main dashboard.

Key Responsibilities:
    • Central Documentation Hub: Contains the complete guide lines
      (`global_guide_text`) explaining project philosophy, offline privacy,
      FIFO accounting, and synchronization.
    • Comprehensive Module Directory: Catalogues every module across
      StockMan, BankMan, Shared, and scripts, outlining which component
      is responsible for what functionality.
    • Multi-Sheet Workflow Documentation: Explains the automated pipeline
      connecting trade entry to AI advice status reconciliation,
      'StockMan_Portfolio.xlsx' multi-sheet export, and background
      Google Drive cloud backup.
    • Interactive FAQ: Houses `global_faq_data` answering critical user
      questions regarding inter-module cash-flow links, startup sync prompts,
      and shortcut navigation.
    • Interactive Module Directory Tab: Injects a dedicated, searchable,
      category-filtered notebook tab into the help viewer displaying all
      modules and their responsibilities.

Key Functions:
    • `show_global_help(parent=None)`: Launches the standardized Global
      Help Center modal window using `Shared.help_utils.show_standard_help`,
      preventing duplicate instances.
"""

import tkinter as tk
from tkinter import ttk
from Shared.help_utils import show_standard_help

SYSTEM_MODULE_CATALOG = [
    (
        "finance_dashboard.py",
        "Root & Dashboard",
        (
            "Master application launcher and central navigation "
            "dashboard. Initializes root Tkinter window, binds "
            "universal shortcuts (Ctrl+F1 for Global Help, F1 for Local "
            "Help, X/Escape to exit), loads custom wallpaper from "
            "'Pics/dashboard_bg.jpg' or fallback theme, and launches "
            "StockMan, BankMan, MFMan, and InsMan."
        ),
    ),
    (
        "StockMan/stocks.py",
        "StockMan: Core",
        (
            "Main GUI entry point and root window for Stock Portfolio "
            "Management. Hosts live benchmark indices (NIFTY 50, "
            "SENSEX), navigation buttons, status bar, and evaluates "
            "morning first-run prompts (Google Drive sync and CMP "
            "updates)."
        ),
    ),
    (
        "StockMan/stock_database_setup.py",
        "StockMan: Database",
        (
            "Defines the complete SQLite schema for StockMan ('stocks', "
            "'trades', 'demergers', 'advice_log', 'computed_bank', "
            "'actual_bank'), foreign- key constraints, triggers, and "
            "performance B-tree indexes."
        ),
    ),
    (
        "StockMan/data_manager.py",
        "StockMan: Database",
        (
            "Database access and transaction isolation layer. Manages "
            "SQLite connection pooling, WAL mode, foreign keys, and "
            "safe transaction commits."
        ),
    ),
    (
        "StockMan/database_setup_old.py",
        "StockMan: Database",
        (
            "Legacy schema definition preserved for backward "
            "compatibility, migration testing, and historical database "
            "parity auditing."
        ),
    ),
    (
        "StockMan/rollback_manager.py",
        "StockMan: Engine",
        (
            "Centralized trade deletion and database rollback engine. "
            "Reverses executed trades, unwinds FIFO sell allocations, "
            "restores original purchase lots, and removes linked bank "
            "entries safely."
        ),
    ),
    (
        "StockMan/company_add.py",
        "StockMan: Companies",
        (
            "Form for registering new listed companies. Captures "
            "ticker, company name, ISIN, exchange (NSE/BSE), sector, "
            "and market cap tier with uniqueness and Yahoo Finance "
            "formatting validation."
        ),
    ),
    (
        "StockMan/company_update.py",
        "StockMan: Companies",
        (
            "Company master record editor. Modifies company names, "
            "sectors, market caps, and ticker symbols while "
            "safeguarding referential integrity."
        ),
    ),
    (
        "StockMan/company_remove.py",
        "StockMan: Companies",
        (
            "Secure company deletion dialog. Checks foreign keys across "
            "trades, dividends, and corporate actions, preventing "
            "deletion of traded companies."
        ),
    ),
    (
        "StockMan/company_bulk_entry.py",
        "StockMan: Companies",
        (
            "High-throughput multi-row data entry grid for rapidly "
            "entering or spreadsheet-pasting multiple companies in a "
            "single batch session."
        ),
    ),
    (
        "StockMan/company_ex_import.py",
        "StockMan: Companies",
        (
            "Bulk CSV and Excel import/export engine for company master "
            "records with deduplication."
        ),
    ),
    (
        "StockMan/company_menu.py",
        "StockMan: Companies",
        (
            "Navigation sub-menu for all Company Management operations "
            "(Add, Update, Bulk, Remove, Import/Export)."
        ),
    ),
    (
        "StockMan/trade_add.py",
        "StockMan: Trades",
        (
            "Primary manual trade entry form for ICICI Direct and "
            "standard brokers. Captures buys/sells, brokerages, STT, "
            "and taxes. Automatically correlates open AI advice and "
            "triggers Excel export with Google Drive cloud sync."
        ),
    ),
    (
        "StockMan/trade_add_zerodha.py",
        "StockMan: Trades",
        (
            "Specialized trade entry form for Zerodha contract notes. "
            "Computes discount broker charges, STT, turnover fees, GST, "
            "and bifurcates trades while auto-updating advice logs and "
            "Google Drive."
        ),
    ),
    (
        "StockMan/sell_management.py",
        "StockMan: Trades",
        (
            "Core First-In-First-Out (FIFO) sell order executor and "
            "overselling prevention guardian. Calculates available "
            "sellable shares, rejects orders exceeding holdings, and "
            "tags purchase lots for tax filing."
        ),
    ),
    (
        "StockMan/trade_manager.py",
        "StockMan: Trades",
        (
            "Interactive transaction log and holding review table with "
            "search, filtering, and safe transaction rollback triggers."
        ),
    ),
    (
        "StockMan/trade_update.py",
        "StockMan: Trades",
        (
            "Trade record modification dialog. Adjusts trade dates, "
            "quantities, and prices while recomputing downstream FIFO "
            "lot allocations."
        ),
    ),
    (
        "StockMan/trade_from_file.py",
        "StockMan: Trades",
        (
            "Broker contract note and statement file parser. Ingests "
            "CSV/Excel reports from brokers, validates rows, and "
            "commits trades in bulk."
        ),
    ),
    (
        "StockMan/trade_utils.py",
        "StockMan: Trades",
        (
            "Trade mathematics toolkit. Centralizes formulas for "
            "brokerage, STT, stamp duty, exchange turnover fees, SEBI "
            "charges, GST, and net settlement prices."
        ),
    ),
    (
        "StockMan/trade_menu.py",
        "StockMan: Trades",
        (
            "Navigation menu for Trade Management operations (Standard "
            "Entry, Zerodha Entry, Primary Market, File Import, "
            "Review/Rollback)."
        ),
    ),
    (
        "StockMan/export_trades.py",
        "StockMan: Trades",
        (
            "Multi-format trade and ledger exporter. Generates Excel "
            "and CSV summaries formatted for tax audits and filing "
            "under Schedule 112A / 111A."
        ),
    ),
    (
        "StockMan/transfer_data.py",
        "StockMan: Trades",
        (
            "Inter-broker share transfer reconciliation tool (e.g. "
            "ICICI to Zerodha). Recalculates cost bases and exports "
            "discrepancy files for broker portals."
        ),
    ),
    (
        "StockMan/ipo.py",
        "StockMan: Corporate",
        (
            "Primary market Initial Public Offering (IPO) application "
            "and allotment recorder. Tracks applied bids, allotments, "
            "refunds, and converts shares to active holdings."
        ),
    ),
    (
        "StockMan/offers.py",
        "StockMan: Corporate",
        (
            "Primary market Offer for Sale (OFS), buyback tender "
            "offers, and secondary allotment manager."
        ),
    ),
    (
        "StockMan/rights.py",
        "StockMan: Corporate",
        (
            "Rights issue subscription and entitlement recorder. Tracks "
            "call money disbursements and conversion into fully paid "
            "shares."
        ),
    ),
    (
        "StockMan/primary_offer_remove.py",
        "StockMan: Corporate",
        (
            "Administrative tool to clean up unallotted or rejected "
            "IPO/OFS applications safely."
        ),
    ),
    (
        "StockMan/direct_trade_menu.py",
        "StockMan: Corporate",
        (
            "Navigation menu for primary market investments (IPOs, "
            "Rights Issues, Offers for Sale)."
        ),
    ),
    (
        "StockMan/dividend.py",
        "StockMan: Corporate",
        (
            "Corporate dividend accounting module. Records cash "
            "dividends, calculates per-share yields, and creates "
            "matching ledger entries in BankMan."
        ),
    ),
    (
        "StockMan/split_entry.py",
        "StockMan: Corporate",
        (
            "Corporate action handler for stock splits and "
            "consolidations. Multiplies share counts and adjusts "
            "purchase prices while preserving invested capital."
        ),
    ),
    (
        "StockMan/bonus_entry.py",
        "StockMan: Corporate",
        (
            "Corporate action handler for bonus share issues. Allocates "
            "bonus shares and dilutes cost basis across historical buy "
            "lots."
        ),
    ),
    (
        "StockMan/merger_entry.py",
        "StockMan: Corporate",
        (
            "Corporate merger and amalgamation processor. Replaces "
            "merged company holdings with acquirer shares according to "
            "swap ratios, carrying forward cost basis."
        ),
    ),
    (
        "StockMan/demerger_entry.py",
        "StockMan: Corporate",
        (
            "Corporate demerger cost-basis apportionment engine. "
            "Apportions cost basis between parent and spun-off entity, "
            "creating spun-off company masters automatically."
        ),
    ),
    (
        "StockMan/corp_manager.py",
        "StockMan: Corporate",
        (
            "Corporate action review screen. Displays historical "
            "corporate actions with search and safe rollback execution."
        ),
    ),
    (
        "StockMan/corpo_menu.py",
        "StockMan: Corporate",
        (
            "Central navigation menu for all Corporate Actions "
            "(Dividends, Splits, Bonuses, Mergers, Demergers, Review)."
        ),
    ),
    (
        "StockMan/ai_analyzer.py",
        "StockMan: Intelligence",
        (
            "Google Gemini LLM analysis engine. Uses a multi-tier model "
            "cascade to generate fundamental analysis, portfolio "
            "advice, and the daily 'Pick of the Day'."
        ),
    ),
    (
        "StockMan/advice_tracker.py",
        "StockMan: Intelligence",
        (
            "AI recommendation audit and execution tracker. Logs "
            "recommendations into 'advice_log', tracks statuses ('Fully "
            "Followed', 'Partially Followed', 'Not Followed'), auto- "
            "matches trades, and exports dual- sheet "
            "'StockMan_Portfolio.xlsx'."
        ),
    ),
    (
        "StockMan/scanner.py",
        "StockMan: Intelligence",
        (
            "Technical market scanner. Evaluates 14-day RSI, 20/50/200 "
            "DMA trends, and volume breakouts on watched tickers via "
            "live yfinance market data."
        ),
    ),
    (
        "StockMan/watchlist_menu.py",
        "StockMan: Intelligence",
        (
            "Watchlist and price alerts dashboard. Displays live market "
            "quotes, 52-week highs/lows, target buy/sell prices, and "
            "triggers technical scans."
        ),
    ),
    (
        "StockMan/watchlist_from_file.py",
        "StockMan: Intelligence",
        (
            "Watchlist file parser. Ingests external stock lists and "
            "broker watchlists into user tracking lists."
        ),
    ),
    (
        "StockMan/reporting.py",
        "StockMan: Reporting",
        (
            "Financial reporting calculation engine. Computes FIFO STCG "
            "(Section 111A), LTCG (Section 112A with Grandfathering), "
            "portfolio valuations, and XIRR."
        ),
    ),
    (
        "StockMan/reporting_utils.py",
        "StockMan: Reporting",
        (
            "Reporting helpers and data extractors. Resolves fiscal "
            "year intervals, extracts master ledgers, and computes "
            "dividend yields and portfolio statistics."
        ),
    ),
    (
        "StockMan/report_menu.py",
        "StockMan: Reporting",
        (
            "Central financial reports menu (Capital Gains, Holdings, "
            "Sector Allocation, Dividend Statements)."
        ),
    ),
    (
        "StockMan/drive_sync.py",
        "StockMan: Cloud Sync",
        (
            "Google Drive background sync engine. Manages OAuth2 "
            "tokens, executes non-blocking background "
            "uploads/downloads, prompts daily morning sync, and syncs "
            "portfolio workbooks."
        ),
    ),
    (
        "StockMan/maint_menu.py",
        "StockMan: Maintenance",
        (
            "Maintenance and administration menu (Live CMP updates, "
            "SQLite VACUUM, PRAGMA integrity checks, database backups, "
            "manual cloud sync)."
        ),
    ),
    (
        "StockMan/date_utils.py",
        "StockMan: Helpers",
        (
            "Financial date calculation toolkit. Handles ISO "
            "formatting, Indian financial years (FY 2024-25), and "
            "calendar day holding duration arithmetic."
        ),
    ),
    (
        "StockMan/helpers.py",
        "StockMan: Helpers",
        (
            "Auxiliary utilities for Indian currency formatting "
            "(Lakhs/Crores), string sanitization, and safe type "
            "casting."
        ),
    ),
    (
        "StockMan/validation_utils.py",
        "StockMan: Helpers",
        (
            "StockMan trade validation and constraint error "
            "translation."
        ),
    ),
    (
        "BankMan/banks.py",
        "BankMan: Core",
        (
            "BankMan central navigation window and subsystem launchpad. "
            "Hosts buttons for Master Records, Data Entry, Transaction "
            "Review, and Statement Import/Export."
        ),
    ),
    (
        "BankMan/bank_database_setup.py",
        "BankMan: Database",
        (
            "Master SQLite schema definition for BankMan ('banks', "
            "'accounts', 'budget_head', 'bank_transactions', sub- "
            "ledgers), check constraints, and triggers."
        ),
    ),
    (
        "BankMan/bank_db_utils.py",
        "BankMan: Database",
        (
            "Core database operations and balance calculation engine. "
            "Recomputes chronological running balances across accounts "
            "and manages double- entry transfers."
        ),
    ),
    (
        "BankMan/banks_add.py",
        "BankMan: Banking",
        (
            "Form for registering new banking institutions (name, "
            "branch, IFSC prefix, MICR) in the 'banks' table."
        ),
    ),
    (
        "BankMan/bank_edit.py",
        "BankMan: Banking",
        (
            "Bank master profile editor. Modifies branch, IFSC code, "
            "and contact details."
        ),
    ),
    (
        "BankMan/banks_ex_import.py",
        "BankMan: Banking",
        (
            "Bulk CSV/Excel importer and exporter for bank master "
            "profiles."
        ),
    ),
    (
        "BankMan/accounts_add.py",
        "BankMan: Banking",
        (
            "Bank account registration form. Captures account number, "
            "bank, account type (Savings, Current, Overdraft), and "
            "opening balance."
        ),
    ),
    (
        "BankMan/accounts_edit.py",
        "BankMan: Banking",
        (
            "Bank account profile editor. Modifies nicknames, overdraft "
            "limits, and account types."
        ),
    ),
    (
        "BankMan/manage_bank.py",
        "BankMan: Banking",
        (
            "Bank and account management dashboard. Displays real-time "
            "aggregated running balances across all institutions."
        ),
    ),
    (
        "BankMan/budget_head_add.py",
        "BankMan: Budgets",
        (
            "Form for creating two-tier hierarchical income and expense "
            "budget categories with monthly planned expenditure limits."
        ),
    ),
    (
        "BankMan/budget_head_edit.py",
        "BankMan: Budgets",
        (
            "Budget category editor and hierarchy manager. Modifies "
            "category names and budget limits."
        ),
    ),
    (
        "BankMan/budget_head_ex_import.py",
        "BankMan: Budgets",
        "Budget category CSV/Excel importer and exporter.",
    ),
    (
        "BankMan/manage_bh.py",
        "BankMan: Budgets",
        (
            "Hierarchical Treeview manager for organizing budget "
            "categories and tracking planned monthly expenditures."
        ),
    ),
    (
        "BankMan/bank_transactions_add.py",
        "BankMan: Passbook",
        (
            "Primary double-entry bank passbook transaction entry form "
            "(Income, Expense, and Inter-Account Transfers) with live "
            "running balance recalculation."
        ),
    ),
    (
        "BankMan/bank_transaction_edit.py",
        "BankMan: Passbook",
        (
            "Passbook transaction editor and reversal dialog. Modifies "
            "entries and recalculates subsequent chronological balances "
            "across affected accounts."
        ),
    ),
    (
        "BankMan/bank_import_excel.py",
        "BankMan: Passbook",
        (
            "Bank statement Excel importer. Maps statement columns, "
            "auto- categorizes payee keywords, and rejects duplicate "
            "transactions."
        ),
    ),
    (
        "BankMan/bank_data_entry_menu.py",
        "BankMan: Passbook",
        (
            "Navigation menu for bank transaction data entry, statement "
            "import, and passbook management."
        ),
    ),
    (
        "BankMan/fd_master_add.py",
        "BankMan: Fixed Deposits",
        (
            "Form for registering Fixed Deposit contracts (principal, "
            "interest rate, tenure, compounding, maturity value) with "
            "automatic bank passbook linking."
        ),
    ),
    (
        "BankMan/fd_master_edit.py",
        "BankMan: Fixed Deposits",
        (
            "Fixed Deposit contract editor. Modifies interest rates, "
            "tenures, and contract statuses."
        ),
    ),
    (
        "BankMan/fd_transactions_add.py",
        "BankMan: Fixed Deposits",
        (
            "FD interest credit and TDS transaction form. Deposits net "
            "interest into linked savings accounts via polymorphic "
            "links."
        ),
    ),
    (
        "BankMan/manage_fd.py",
        "BankMan: Fixed Deposits",
        (
            "Fixed Deposit portfolio dashboard and maturity tracker "
            "with renewal alerts."
        ),
    ),
    (
        "BankMan/cc_master_add.py",
        "BankMan: Credit Cards",
        (
            "Credit card contract registration form (card nickname, "
            "credit limit, billing cycle date, payment due date, linked "
            "bank account)."
        ),
    ),
    (
        "BankMan/cc_master_edit.py",
        "BankMan: Credit Cards",
        (
            "Credit card contract editor. Modifies credit limits, "
            "billing dates, and card statuses."
        ),
    ),
    (
        "BankMan/cc_transactions_add.py",
        "BankMan: Credit Cards",
        (
            "Credit card purchase and statement payment entry form with "
            "polymorphic links to bank passbooks."
        ),
    ),
    (
        "BankMan/cc_transactions_edit.py",
        "BankMan: Credit Cards",
        "Credit card transaction editor and reversal interface.",
    ),
    (
        "BankMan/rewards_points_add.py",
        "BankMan: Credit Cards",
        (
            "Credit card reward points tracker. Logs points earned, "
            "expiry dates, and cash-back redemptions."
        ),
    ),
    (
        "BankMan/manage_cc.py",
        "BankMan: Credit Cards",
        (
            "Credit card portfolio dashboard. Monitors utilized limits, "
            "available credit, and upcoming payment due dates."
        ),
    ),
    (
        "BankMan/loan_master_add.py",
        "BankMan: Loans",
        (
            "Form for registering loan contracts (sanction amount, "
            "interest rate, tenure, EMI schedule, linked bank account)."
        ),
    ),
    (
        "BankMan/loan_master_edit.py",
        "BankMan: Loans",
        (
            "Loan contract editor. Updates floating interest rates and "
            "tenures."
        ),
    ),
    (
        "BankMan/loan_transactions_add.py",
        "BankMan: Loans",
        (
            "Loan EMI repayment form. Bifurcates installments into "
            "principal and interest components and debits linked bank "
            "accounts."
        ),
    ),
    (
        "BankMan/loan_transactions_edit.py",
        "BankMan: Loans",
        "Loan repayment transaction editor and reversal dialog.",
    ),
    (
        "BankMan/manage_loan.py",
        "BankMan: Loans",
        (
            "Debt and loan portfolio dashboard. Tracks outstanding "
            "principal balances and aggregated monthly EMI liabilities."
        ),
    ),
    (
        "BankMan/ppf_master_add.py",
        "BankMan: PPF",
        (
            "Public Provident Fund account registration form "
            "(subscriber, account number, 15-year maturity schedule)."
        ),
    ),
    (
        "BankMan/ppf_master_edit.py",
        "BankMan: PPF",
        (
            "PPF master account editor. Updates subscriber details and "
            "account parameters."
        ),
    ),
    (
        "BankMan/ppf_transactions_add.py",
        "BankMan: PPF",
        (
            "PPF subscription deposit and annual interest credit form "
            "with annual ₹1,50,000 Section 80C threshold tracking."
        ),
    ),
    (
        "BankMan/manage_ppf.py",
        "BankMan: PPF",
        "PPF dashboard and tax exemption contribution monitor.",
    ),
    (
        "BankMan/ins_master_add.py",
        "BankMan: Insurance",
        (
            "Insurance policy registration form (Term Life, Health, "
            "Motor, sum assured, premium amount, payment schedule, "
            "nominee)."
        ),
    ),
    (
        "BankMan/ins_master_edit.py",
        "BankMan: Insurance",
        (
            "Insurance policy editor. Updates coverage amounts and "
            "premium schedules."
        ),
    ),
    (
        "BankMan/ins_transactions_add.py",
        "BankMan: Insurance",
        (
            "Insurance premium payment and claim settlement form with "
            "automated bank passbook debits."
        ),
    ),
    (
        "BankMan/manage_ins.py",
        "BankMan: Insurance",
        (
            "Insurance portfolio dashboard with policy renewal and "
            "premium due alerts. Also serves as InsMan subsystem "
            "launcher."
        ),
    ),
    (
        "BankMan/mf_master_add.py",
        "BankMan: Mutual Funds",
        (
            "Mutual Fund folio registration form (folio number, AMC, "
            "scheme name, SIP mandate, linked bank account)."
        ),
    ),
    (
        "BankMan/mf_master_edit.py",
        "BankMan: Mutual Funds",
        (
            "Mutual Fund folio editor. Modifies scheme descriptions and "
            "SIP amounts."
        ),
    ),
    (
        "BankMan/mf_transactions_add.py",
        "BankMan: Mutual Funds",
        (
            "Mutual Fund investment and redemption form (purchase NAV, "
            "units, gross amount) with passbook linking."
        ),
    ),
    (
        "BankMan/manage_mf.py",
        "BankMan: Mutual Funds",
        (
            "Mutual Fund portfolio dashboard and SIP manager. Also "
            "serves as MFMan subsystem launcher."
        ),
    ),
    (
        "BankMan/data_entry_menu.py",
        "BankMan: Navigation",
        (
            "Master data entry navigation menu for all banking and sub- "
            "ledger instruments."
        ),
    ),
    (
        "BankMan/manage_master_menu.py",
        "BankMan: Navigation",
        (
            "Master configuration menu for banks, accounts, categories, "
            "and sub- ledger contracts."
        ),
    ),
    (
        "BankMan/manage_transactions_menu.py",
        "BankMan: Navigation",
        (
            "Master transaction review and audit menu across all "
            "banking instruments."
        ),
    ),
    (
        "BankMan/import_menu.py",
        "BankMan: Navigation",
        (
            "Central import hub for ingesting statements across all "
            "sub-ledgers."
        ),
    ),
    (
        "BankMan/export_menu.py",
        "BankMan: Navigation",
        (
            "Central export hub for generating financial spreadsheets "
            "across all accounts."
        ),
    ),
    (
        "Shared/global_help.py",
        "Shared: Help",
        (
            "Master Global Help Center (Ctrl+F1). Hosts system "
            "architecture guides, workflows, shortcuts, FAQs, and the "
            "interactive Module Directory."
        ),
    ),
    (
        "Shared/help_utils.py",
        "Shared: Help",
        (
            "Standardized multi-tab help window builder "
            "('show_standard_help') with General Guide, paginated FAQ "
            "navigation, and custom notebook tabs."
        ),
    ),
    (
        "Shared/window_manager.py",
        "Shared: Windows",
        (
            "Centralized LIFO window hierarchy stack. Manages modal "
            "nesting, suppresses parent Escape bubbling, and unwinds "
            "window focus safely."
        ),
    ),
    (
        "Shared/modal_utils.py",
        "Shared: Windows",
        (
            "Modal window lifecycle manager. Disables parent windows, "
            "enforces mouse/keyboard grab, and restores parent "
            "interactivity and focus upon closure."
        ),
    ),
    (
        "Shared/menu_factory.py",
        "Shared: Windows",
        (
            "Universal declarative menu generator for Tkinter windows "
            "with hotkey bindings and background wallpaper support."
        ),
    ),
    (
        "Shared/dialog_sizing.py",
        "Shared: Dialogs",
        (
            "Dynamic layout and geometry calculator. Determines optimal "
            "dialog dimensions based on content volume, ensuring action "
            "buttons remain visible."
        ),
    ),
    (
        "Shared/dialog_utils.py",
        "Shared: Dialogs",
        (
            "Styled replacement dialogs for standard message boxes "
            "(show_info_dialog, show_error_dialog, "
            "show_confirmation_dialog)."
        ),
    ),
    (
        "Shared/gui_utils.py",
        "Shared: UI Utils",
        (
            "Comprehensive UI toolkit: button hover animations, Enter- "
            "key focus progression, date spinners (+/- keys), tree "
            "sorting, and error flashing."
        ),
    ),
    (
        "Shared/gui_progressive.py",
        "Shared: UI Utils",
        (
            "Non-blocking progressive search / autocomplete typeahead "
            "for ttk.Combobox widgets across large datasets."
        ),
    ),
    (
        "Shared/style_utils.py",
        "Shared: Styling",
        (
            "Centralized ttk style presets and theme configurations "
            "across application widgets."
        ),
    ),
    (
        "Shared/globals.py",
        "Shared: Core",
        (
            "System-wide constants, database paths ('stocks.db', "
            "'bank.db'), color themes (UI_THEME, BANK_UI_THEME), and "
            "fonts."
        ),
    ),
    (
        "Shared/google_drive_sync.py",
        "Shared: Cloud",
        (
            "Unified cloud synchronization adapter and proxy module "
            "delegating to StockMan.drive_sync."
        ),
    ),
    (
        "Shared/network_utils.py",
        "Shared: Network",
        (
            "Network resolution optimizer helper prioritizing IPv4 over "
            "IPv6 on Windows to eliminate DNS timeout stalls when "
            "contacting cloud APIs."
        ),
    ),
    (
        "Shared/validation_utils.py",
        "Shared: Validation",
        (
            "Reusable validation routines for currency amounts, decimal "
            "precision, and positive numbers."
        ),
    ),
    (
        "scripts/importer_cli.py",
        "Scripts & Tools",
        (
            "Command-line interface for running automated contract note "
            "and legacy database migrations headlessly."
        ),
    ),
    (
        "scripts/importer_audit.py",
        "Scripts & Tools",
        (
            "Post-migration audit tool verifying relational integrity, "
            "trade quantities, and ledger balancing."
        ),
    ),
    (
        "scripts/compare_legacy_live.py",
        "Scripts & Tools",
        (
            "Database parity auditor comparing record counts, balances, "
            "and corporate actions between legacy and live databases."
        ),
    ),
    (
        "scripts/repair_transactions_from_eos.py",
        "Scripts & Tools",
        (
            "Database repair utility reconstructing missing foreign "
            "keys and correcting running balances from End-of-Statement "
            "snapshots."
        ),
    ),
    (
        "scripts/run_importer_ui.py",
        "Scripts & Tools",
        (
            "Tkinter graphical front-end for executing data migrations "
            "interactively."
        ),
    ),
    (
        "scripts/inspect_legacy_tx.py",
        "Scripts & Tools",
        (
            "Diagnostic inspector dumping raw transaction records and "
            "polymorphic keys from legacy database files."
        ),
    ),
]


global_guide_text = [
    "Welcome to the Universal Finance Manager Master Documentation.",
    "",
    (
        "================================================================== "
        "==== =========="
    ),
    "1. PROJECT AIM & PHILOSOPHY",
    (
        "================================================================== "
        "==== =========="
    ),
    (
        "The Universal Finance Manager is a comprehensive, privacy-first "
        "desktop application designed"
    ),
    (
        "to centralize and automate complex personal finance tracking. "
        "Built using Python, Tkinter,"
    ),
    (
        "and SQLite, it operates as a secure offline ledger with powerful "
        "analytical capabilities."
    ),
    (
        "The primary aim is to bridge the gap between fragmented financial "
        "services by unifying bank"
    ),
    (
        "cash flows, equity portfolios, mutual funds, and insurance "
        "policies into a single, mathematically"
    ),
    "rigorous ecosystem.",
    "",
    (
        "The system is defined by its strict data integrity rules: "
        "preventing overselling, enforcing"
    ),
    (
        "First-In-First-Out (FIFO) capital gains accounting, maintaining "
        "exact corporate action"
    ),
    (
        "cost-basis transfers, and automatically reconciling stock market "
        "trades with bank account"
    ),
    (
        "balances. It leverages real-time market data (yfinance) and AI- "
        "driven insights to transition"
    ),
    "from a static ledger into an active portfolio advisory tool.",
    "",
    (
        "================================================================== "
        "==== =========="
    ),
    "2. SYSTEM ARCHITECTURE & SUBSYSTEM BLUEPRINT",
    (
        "================================================================== "
        "==== =========="
    ),
    "The application is structured into four primary layers:",
    (
        "  1. Universal Dashboard (Root): Master launchpad "
        "(finance_dashboard.py) coordinating all subsystems."
    ),
    (
        "  2. StockMan Subsystem: Complete equity portfolio management, "
        "multi- broker trade execution,"
    ),
    (
        "     FIFO tax accounting, corporate actions (splits, bonuses, "
        "mergers, demergers), AI market"
    ),
    (
        "     scanners, automated dual-sheet Excel exports, and Google "
        "Drive background synchronization."
    ),
    (
        "  3. BankMan Subsystem: Double-entry cash flow ledger, bank "
        "accounts, hierarchical budget"
    ),
    (
        "     heads, running balance recalculations, and specialist sub- "
        "ledgers (Fixed Deposits, Credit"
    ),
    "     Cards, Loans, PPF, Insurance, Mutual Funds).",
    (
        "  4. Shared Subsystem: Cross-cutting UI toolkit, modal lifecycle "
        "management, dynamic dialog"
    ),
    (
        "     sizing, LIFO window stacks, network optimizers, and cloud "
        "sync adapters."
    ),
    "",
    (
        "================================================================== "
        "==== =========="
    ),
    "3. WHICH MODULE IS DOING WHAT: COMPLETE DIRECTORY",
    (
        "================================================================== "
        "==== =========="
    ),
    "A. ROOT APPLICATION & DASHBOARD",
    (
        "  • finance_dashboard.py: Root launcher initializing Tkinter root "
        "window, setting up master"
    ),
    (
        "    navigation buttons (StockMan, BankMan, MFMan, InsMan), binding "
        "global shortcuts (Ctrl+F1,"
    ),
    (
        "    F1, X/Escape), and dynamically rendering custom wallpaper from "
        "Pics/dashboard_bg.jpg."
    ),
    "",
    "B. STOCKMAN SUBSYSTEM (EQUITY PORTFOLIO & INTELLIGENCE)",
    "  • Core & Navigation:",
    (
        "    - StockMan/stocks.py: Main entry point for StockMan; hosts "
        "live market indices (NIFTY 50,"
    ),
    "      SENSEX), status bar, and morning first-run sync prompts.",
    (
        "    - StockMan/stock_database_setup.py: SQLite schema "
        "initialization defining tables ('stocks',"
    ),
    (
        "      'trades', 'demergers', 'advice_log', 'computed_bank', "
        "'actual_bank'), triggers, and indices."
    ),
    (
        "    - StockMan/data_manager.py: Connection management, WAL mode, "
        "and atomic query execution."
    ),
    (
        "    - StockMan/rollback_manager.py: High-integrity trade deletion "
        "and database rollback engine."
    ),
    "  • Company Management:",
    (
        "    - StockMan/company_add.py: Form for adding listed companies "
        "with ticker, ISIN, and sector validation."
    ),
    (
        "    - StockMan/company_update.py: Editor for modifying company "
        "profiles without breaking foreign keys."
    ),
    (
        "    - StockMan/company_remove.py: Secure company deletion module "
        "preventing deletion of traded stocks."
    ),
    (
        "    - StockMan/company_bulk_entry.py: High-throughput batch grid "
        "for rapid multi-company ingestion."
    ),
    (
        "    - StockMan/company_ex_import.py: CSV/Excel export and import "
        "engine for company master tables."
    ),
    (
        "    - StockMan/company_menu.py: Navigation menu for all Company "
        "Management operations."
    ),
    "  • Trade Execution & Accounting:",
    (
        "    - StockMan/trade_add.py: Primary trade entry form for ICICI "
        "Direct & standard brokers. Auto-correlates"
    ),
    (
        "      open AI advice, updates 'StockMan_Portfolio.xlsx', and "
        "triggers Google Drive cloud sync."
    ),
    (
        "    - StockMan/trade_add_zerodha.py: Form optimized for Zerodha "
        "contract notes, handling discount broker"
    ),
    (
        "      fees, GST, STT, and trade bifurcation with automatic advice "
        "matching and cloud sync."
    ),
    (
        "    - StockMan/sell_management.py: FIFO sell execution engine and "
        "overselling prevention guardian."
    ),
    (
        "    - StockMan/trade_manager.py: Interactive trade history review "
        "table with rollback triggers."
    ),
    (
        "    - StockMan/trade_update.py: Trade editor modifying records and "
        "re- sequencing downstream FIFO lots."
    ),
    (
        "    - StockMan/trade_from_file.py: Broker contract note statement "
        "parser (CSV/Excel)."
    ),
    (
        "    - StockMan/trade_utils.py: Financial formulas for brokerage, "
        "STT, stamp duty, turnover fees, and GST."
    ),
    (
        "    - StockMan/trade_menu.py: Navigation sub-menu for Trade "
        "Management operations."
    ),
    (
        "    - StockMan/export_trades.py: Multi-format trade exporter for "
        "Income Tax Schedules 112A / 111A."
    ),
    (
        "    - StockMan/transfer_data.py: Inter-broker share transfer "
        "reconciliation (e.g. ICICI to Zerodha)."
    ),
    "  • Corporate Actions:",
    (
        "    - StockMan/dividend.py: Dividend recorder calculating yields "
        "and crediting BankMan passbooks."
    ),
    (
        "    - StockMan/split_entry.py: Stock split processor multiplying "
        "share counts and adjusting costs."
    ),
    (
        "    - StockMan/bonus_entry.py: Bonus share issue processor "
        "expanding share counts and diluting costs."
    ),
    (
        "    - StockMan/merger_entry.py: Merger swap processor replacing "
        "merged shares with acquirer shares."
    ),
    (
        "    - StockMan/demerger_entry.py: Demerger engine apportioning "
        "cost basis and creating spun-off entities."
    ),
    (
        "    - StockMan/corp_manager.py: Corporate action review table with "
        "safe rollback integration."
    ),
    "    - StockMan/corpo_menu.py: Navigation menu for Corporate Actions.",
    "  • Primary Market:",
    (
        "    - StockMan/ipo.py: IPO bid and allotment recorder, "
        "transferring allotted shares to holdings."
    ),
    (
        "    - StockMan/offers.py: Primary market Offer for Sale (OFS) and "
        "buyback tender offer manager."
    ),
    (
        "    - StockMan/rights.py: Rights issue entitlement, call money "
        "payment, and share conversion manager."
    ),
    (
        "    - StockMan/primary_offer_remove.py: Administrative tool to "
        "safely delete unallotted bids."
    ),
    (
        "    - StockMan/direct_trade_menu.py: Navigation menu for primary "
        "market offerings."
    ),
    "  • Intelligence, Advice & Scanners:",
    (
        "    - StockMan/ai_analyzer.py: Gemini LLM analysis engine with "
        "multi- tier model cascade."
    ),
    (
        "    - StockMan/advice_tracker.py: AI advice audit and status "
        "tracker ('Fully Followed', 'Partially"
    ),
    (
        "      Followed', 'Not Followed'), auto-matching trades and "
        "generating dual-sheet portfolio workbooks."
    ),
    (
        "    - StockMan/scanner.py: Technical market scanner evaluating "
        "14-day RSI and moving average breakouts."
    ),
    (
        "    - StockMan/watchlist_menu.py: Watchlist dashboard with live "
        "market quotes and target alerts."
    ),
    (
        "    - StockMan/watchlist_from_file.py: Watchlist importer for "
        "external ticker lists."
    ),
    "  • Reporting & Maintenance:",
    (
        "    - StockMan/reporting.py: Financial reporting engine computing "
        "FIFO STCG, LTCG, and XIRR."
    ),
    (
        "    - StockMan/reporting_utils.py: Analytical helpers, fiscal year "
        "resolvers, and ledger formatters."
    ),
    "    - StockMan/report_menu.py: Central financial reports menu.",
    (
        "    - StockMan/drive_sync.py: Asynchronous Google Drive cloud sync "
        "engine and startup workflow."
    ),
    (
        "    - StockMan/maint_menu.py: Maintenance menu (CMP updates, "
        "SQLite VACUUM, backups, integrity checks)."
    ),
    (
        "    - StockMan/date_utils.py: Fiscal year boundary math, ISO date "
        "formatting, and holding period math."
    ),
    (
        "    - StockMan/helpers.py: Indian currency formatters "
        "(Lakhs/Crores) and string sanitizers."
    ),
    (
        "    - StockMan/validation_utils.py: StockMan trade validation and "
        "constraint error translation."
    ),
    "",
    "C. BANKMAN SUBSYSTEM (BANKING, PASSBOOK & SUB-LEDGERS)",
    "  • Core & Navigation:",
    (
        "    - BankMan/banks.py: Main entry point for the BankMan banking "
        "ecosystem."
    ),
    (
        "    - BankMan/bank_database_setup.py: SQLite schema for banks, "
        "accounts, budgets, and sub-ledgers."
    ),
    (
        "    - BankMan/bank_db_utils.py: Core CRUD operations and "
        "chronological running balance recalculations."
    ),
    "  • Bank & Account Master:",
    (
        "    - BankMan/banks_add.py: Registration form for financial "
        "institutions and banks."
    ),
    "    - BankMan/bank_edit.py: Bank master profile editor.",
    (
        "    - BankMan/banks_ex_import.py: CSV/Excel export and import "
        "engine for bank masters."
    ),
    (
        "    - BankMan/accounts_add.py: Bank account registration form "
        "(Savings, Current, Overdraft)."
    ),
    "    - BankMan/accounts_edit.py: Bank account profile editor.",
    (
        "    - BankMan/manage_bank.py: Bank and account overview dashboard "
        "with real-time running balances."
    ),
    "  • Budgeting & Categories:",
    (
        "    - BankMan/budget_head_add.py: Form for creating hierarchical "
        "income and expense categories."
    ),
    (
        "    - BankMan/budget_head_edit.py: Budget category editor and "
        "hierarchy manager."
    ),
    (
        "    - BankMan/budget_head_ex_import.py: Budget category CSV/Excel "
        "importer and exporter."
    ),
    (
        "    - BankMan/manage_bh.py: Expandable Treeview manager for budget "
        "categories and expenditure limits."
    ),
    "  • Passbook / Core Transactions:",
    (
        "    - BankMan/bank_transactions_add.py: Primary double-entry "
        "passbook transaction entry form."
    ),
    (
        "    - BankMan/bank_transaction_edit.py: Passbook transaction "
        "editor with automated balance recalculation."
    ),
    (
        "    - BankMan/bank_import_excel.py: Bank statement spreadsheet "
        "importer with keyword auto-categorization."
    ),
    (
        "    - BankMan/bank_data_entry_menu.py: Navigation menu for bank "
        "transaction data entry."
    ),
    "  • Specialist Sub-Ledgers:",
    (
        "    - Fixed Deposits: BankMan/fd_master_add.py, "
        "BankMan/fd_master_edit.py, BankMan/fd_transactions_add.py,"
    ),
    (
        "      BankMan/manage_fd.py (Maturity tracker and interest credit "
        "recorder)."
    ),
    (
        "    - Credit Cards: BankMan/cc_master_add.py, "
        "BankMan/cc_master_edit.py, BankMan/cc_transactions_add.py,"
    ),
    (
        "      BankMan/rewards_points_add.py, BankMan/manage_cc.py (Billing "
        "cycle monitor and rewards tracker)."
    ),
    (
        "    - Loans & Debt: BankMan/loan_master_add.py, "
        "BankMan/loan_master_edit.py, BankMan/loan_transactions_add.py,"
    ),
    (
        "      BankMan/manage_loan.py (Principal and interest amortization "
        "tracker and EMI liability monitor)."
    ),
    (
        "    - Public Provident Fund: BankMan/ppf_master_add.py, "
        "BankMan/ppf_master_edit.py,"
    ),
    (
        "      BankMan/ppf_transactions_add.py, BankMan/manage_ppf.py "
        "(Annual Section 80C threshold monitor)."
    ),
    (
        "    - Insurance: BankMan/ins_master_add.py, "
        "BankMan/ins_master_edit.py, BankMan/ins_transactions_add.py,"
    ),
    (
        "      BankMan/manage_ins.py (Policy portfolio dashboard and "
        "renewal due alerts; InsMan launcher)."
    ),
    (
        "    - Mutual Funds: BankMan/mf_master_add.py, "
        "BankMan/mf_master_edit.py, BankMan/mf_transactions_add.py,"
    ),
    (
        "      BankMan/manage_mf.py (Folio portfolio dashboard and SIP "
        "mandate manager; MFMan launcher)."
    ),
    "  • Navigation Menus:",
    (
        "    - BankMan/data_entry_menu.py: Top-level data entry hub for all "
        "banking instruments."
    ),
    (
        "    - BankMan/manage_master_menu.py: Master configuration menu for "
        "accounts and financial products."
    ),
    (
        "    - BankMan/manage_transactions_menu.py: Master transaction "
        "review and audit menu."
    ),
    (
        "    - BankMan/import_menu.py: Central import hub for ingesting "
        "statements across all sub-ledgers."
    ),
    (
        "    - BankMan/export_menu.py: Central export hub for generating "
        "financial spreadsheets."
    ),
    "",
    "D. SHARED INFRASTRUCTURE SUBSYSTEM",
    (
        "  • Shared/global_help.py: Master Global Help Center (Ctrl+F1), "
        "architecture guides, and module catalog."
    ),
    (
        "  • Shared/help_utils.py: Reusable multi-tab help window builder "
        "with interactive FAQ viewer."
    ),
    (
        "  • Shared/window_manager.py: Global LIFO window hierarchy stack "
        "and parent Escape suppression manager."
    ),
    (
        "  • Shared/modal_utils.py: Modal window lifecycle manager (parent "
        "disablement, grab, and focus restoration)."
    ),
    (
        "  • Shared/menu_factory.py: Declarative menu window generator for "
        "Tkinter/ttk navigation menus."
    ),
    (
        "  • Shared/dialog_sizing.py: Mathematical dialog sizing engine "
        "ensuring action buttons remain visible."
    ),
    (
        "  • Shared/dialog_utils.py: Styled alert, error, and confirmation "
        "modal dialog replacements."
    ),
    (
        "  • Shared/gui_utils.py: UI animations, hover effects, date "
        "spinners (+/-), and tree column sorting."
    ),
    (
        "  • Shared/gui_progressive.py: Progressive autocomplete / live- "
        "search combobox helpers."
    ),
    (
        "  • Shared/style_utils.py: Centralized ttk style presets and theme "
        "configurations."
    ),
    (
        "  • Shared/globals.py: Global constants, database paths "
        "('stocks.db', 'bank.db'), color themes, and fonts."
    ),
    (
        "  • Shared/google_drive_sync.py: Cross-module Google Drive cloud "
        "synchronization adapter."
    ),
    (
        "  • Shared/network_utils.py: Network resolution optimizer "
        "prioritizing IPv4 over IPv6 on Windows."
    ),
    (
        "  • Shared/validation_utils.py: Input validation routines for "
        "financial data entry."
    ),
    "",
    "E. SCRIPTS & MIGRATION SUITE",
    (
        "  • scripts/importer_cli.py: Headless CLI runner for contract note "
        "and legacy database migrations."
    ),
    (
        "  • scripts/importer_audit.py: Post-migration audit tool verifying "
        "relational integrity and ledger balances."
    ),
    (
        "  • scripts/compare_legacy_live.py: Parity auditor comparing "
        "legacy vs live database records."
    ),
    (
        "  • scripts/repair_transactions_from_eos.py: Data repair script "
        "reconstructing links from EOS snapshots."
    ),
    (
        "  • scripts/run_importer_ui.py: Graphical front-end for running "
        "data migrations interactively."
    ),
    (
        "  • scripts/inspect_legacy_tx.py: Diagnostic tool inspecting raw "
        "legacy transaction records."
    ),
    "",
    (
        "================================================================== "
        "==== =========="
    ),
    "4. INTER-MODULE WORKFLOW & AUTOMATED SYNCHRONIZATION",
    (
        "================================================================== "
        "==== =========="
    ),
    "• Trade Entry to Advice Matching:",
    (
        "  When you record a trade in StockMan (trade_add.py or "
        "trade_add_zerodha.py), the engine"
    ),
    (
        "  automatically queries 'advice_log' for open recommendations "
        "matching the ticker and action."
    ),
    (
        "  If matched, it marks the status as 'Fully Followed' (or "
        "'Partially Followed' for partial quantities)"
    ),
    "  with the exact trade execution date.",
    "",
    "• Automated Portfolio Excel Export & Cloud Backup:",
    (
        "  Saving, updating, or deleting any trade immediately triggers "
        "advice_tracker.update_portfolio_excel(),"
    ),
    (
        "  regenerating 'StockMan_Portfolio.xlsx' with two sheets: "
        "'Portfolio' (active holdings and CMP) and"
    ),
    (
        "  'Advice_Log' (full advice audit trail). The engine then "
        "initiates an asynchronous background upload"
    ),
    "  to Google Drive via StockMan.drive_sync without blocking the UI.",
    "",
    "• Bank Passbook Reconciliation:",
    (
        "  Stock trades, dividend receipts, credit card bill payments, and "
        "FD interest payouts automatically"
    ),
    (
        "  generate matching double-entry cash flow records in BankMan, "
        "ensuring complete net worth alignment."
    ),
    "",
    (
        "================================================================== "
        "==== =========="
    ),
    "5. GLOBAL NAVIGATION & SHORTCUTS",
    (
        "================================================================== "
        "==== =========="
    ),
    (
        "• Ctrl + F1: Global Help - Opens this master documentation and "
        "interactive Module Directory."
    ),
    (
        "• F1: Local Help - Opens contextual, screen-specific instructions "
        "for the current active window."
    ),
    (
        "• Escape: Cancel / Close - Closes modal dialogs safely and unwinds "
        "parent window focus."
    ),
    (
        "• Enter: Advance Focus - Rapidly moves focus to the next input "
        "field in forms."
    ),
    (
        "• Ctrl + Enter: Execute / Save - Bypasses remaining fields to "
        "trigger primary Save actions."
    ),
    (
        "• '+' / '-' (Date Spinners): Increments or decrements dates by 1 "
        "day on any date input field."
    ),
    (
        "• Column Header Click: Sorts Treeview columns naturally "
        "(alphanumeric or numeric order)."
    ),
]


global_faq_data = [
    (
        "Q1: How do I access module-specific help vs global help?",
        (
            "A: Press F1 inside any active window to view contextual "
            "help specific to that screen. Press Ctrl+F1 from any "
            "window in the application to open this Global Help "
            "Center."
        ),
    ),
    (
        "Q2: Which module is doing what across the StockMan subsystem?",
        (
            "A: In StockMan:\n"
            "• stocks.py: Root launcher and index bar.\n"
            "• stock_database_setup.py: Schema, triggers, and "
            "indices.\n"
            "• company_add.py, company_update.py, company_menu.py: "
            "Company metadata management.\n"
            "• trade_add.py & trade_add_zerodha.py: Trade execution, "
            "fee calculation, advice matching, and Excel sync.\n"
            "• sell_management.py: FIFO order execution and "
            "overselling prevention guardian.\n"
            "• rollback_manager.py: Cascading trade and corporate "
            "action deletion engine.\n"
            "• dividend.py, split_entry.py, bonus_entry.py, "
            "merger_entry.py, demerger_entry.py: Corporate actions.\n"
            "• ai_analyzer.py: Gemini LLM analysis engine with multi- "
            "tier model cascade.\n"
            "• advice_tracker.py: Recommendation tracking, trade "
            "matching, and dual-sheet Excel generation.\n"
            "• reporting.py: FIFO STCG/LTCG capital gains statements "
            "and portfolio valuations.\n"
            "• drive_sync.py: Google Drive background cloud sync "
            "engine."
        ),
    ),
    (
        "Q3: Which module is doing what across the BankMan subsystem?",
        (
            "A: In BankMan:\n"
            "• banks.py: Central launcher for the banking ecosystem.\n"
            "• bank_database_setup.py & bank_db_utils.py: Relational "
            "schema, CRUD, and running balance recalculations.\n"
            "• banks_add.py, accounts_add.py, manage_bank.py: Banks "
            "and bank accounts overview.\n"
            "• budget_head_add.py & manage_bh.py: Hierarchical "
            "income/expense categories and monthly limits.\n"
            "• bank_transactions_add.py & bank_transaction_edit.py: "
            "Double- entry passbook ledger.\n"
            "• bank_import_excel.py: Bank statement spreadsheet "
            "importer.\n"
            "• fd_*, cc_*, loan_*, ppf_*, ins_*, mf_*: Specialized "
            "sub-ledgers for Fixed Deposits, Credit Cards, Loans, "
            "PPF, Insurance, and Mutual Funds."
        ),
    ),
    (
        "Q4: Which module is doing what across the Shared subsystem?",
        (
            "A: In Shared:\n"
            "• global_help.py & help_utils.py: Multi-tab help "
            "windows, FAQ viewer, and module directory.\n"
            "• window_manager.py & modal_utils.py: LIFO modal window "
            "hierarchy, parent disablement, and focus unwinding.\n"
            "• menu_factory.py: Declarative menu generator with "
            "hotkey binding.\n"
            "• dialog_sizing.py & dialog_utils.py: Content-aware "
            "dialog sizing and styled replacement dialogs.\n"
            "• gui_utils.py & gui_progressive.py: UI animations, date "
            "spinners (+/-), tree sorting, and autocomplete "
            "comboboxes.\n"
            "• google_drive_sync.py: Generic cloud synchronization "
            "adapter.\n"
            "• network_utils.py: IPv4 prioritization eliminating "
            "Windows DNS timeout stalls.\n"
            "• globals.py: Centralized paths, themes (UI_THEME, "
            "BANK_UI_THEME), and fonts."
        ),
    ),
    (
        "Q5: How do StockMan and BankMan interact?",
        (
            "A: StockMan and BankMan share double-entry cash flow "
            "data. When you execute stock trades or receive corporate "
            "dividends in StockMan, computed bank records are "
            "generated and linked to actual BankMan passbook "
            "accounts. In addition, BankMan sub-ledger transactions "
            "(such as FD interest payouts, loan repayments, and "
            "credit card payments) debit or credit linked bank "
            "accounts automatically."
        ),
    ),
    (
        (
            "Q6: Does trading automatically update 'StockMan_Portfolio.xlsx' "
            "and Google Drive?"
        ),
        (
            "A: Yes! Whenever a trade is added (ICICI or Zerodha), "
            "updated, or deleted, Trade Management automatically "
            "calls advice_tracker.update_portfolio_excel(), which "
            "refreshes the Excel workbook with both 'Portfolio' "
            "(active holdings) and 'Advice_Log' (full advice audit "
            "trail) sheets and initiates an asynchronous background "
            "upload to Google Drive via drive_sync.py."
        ),
    ),
    (
        "Q7: How does the startup first-run cycle work?",
        (
            "A: Each morning on the first run of the day, StockMan "
            "prompts you to download latest stock prices (CMP) and "
            "upload 'StockMan_Portfolio.xlsx' to Google Drive. The "
            "startup prompt cycle resets daily at 8:00 AM."
        ),
    ),
    (
        "Q8: What tools exist for database repairs, audits, and rollbacks?",
        (
            "A: The application provides:\n"
            "• rollback_manager.py: Reverses trades and corporate "
            "actions while restoring FIFO buy lots.\n"
            "• scripts/importer_audit.py & "
            "scripts/compare_legacy_live.py: Audits database parity "
            "and balances.\n"
            "• scripts/repair_transactions_from_eos.py: Repairs "
            "missing foreign keys and running balance drift.\n"
            "• maint_menu.py: Runs SQLite PRAGMA integrity_check, "
            "VACUUM rebuilds, and timestamped backups."
        ),
    ),
]


def _add_module_directory_tab(notebook):
    """Inject an interactive 'Module Directory' tab into help notebook."""
    tab_modules = tk.Frame(notebook, bg="#f8fafc", padx=10, pady=10)
    notebook.add(tab_modules, text="Module Directory")

    # Search & Filter Bar
    filter_bar = tk.Frame(tab_modules, bg="#f8fafc")
    filter_bar.pack(fill="x", pady=(0, 8))

    tk.Label(
        filter_bar,
        text="Filter Modules:",
        font=("Helvetica", 11, "bold"),
        bg="#f8fafc",
        fg="#0f172a",
    ).pack(side="left", padx=(0, 6))

    search_var = tk.StringVar()
    search_entry = tk.Entry(
        filter_bar,
        textvariable=search_var,
        font=("Helvetica", 11),
        bg="white",
        fg="#0f172a",
        bd=1,
        relief="solid",
    )
    search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

    tk.Label(
        filter_bar,
        text="Category:",
        font=("Helvetica", 10, "bold"),
        bg="#f8fafc",
        fg="#475569",
    ).pack(side="left", padx=(0, 4))

    categories = [
        "All Categories",
        "Root & Dashboard",
        "StockMan",
        "BankMan",
        "Shared",
        "Scripts & Tools",
    ]
    category_combo = ttk.Combobox(
        filter_bar,
        values=categories,
        state="readonly",
        width=18,
        font=("Helvetica", 10),
    )
    category_combo.current(0)
    category_combo.pack(side="right")

    # Main Split Container
    paned = ttk.PanedWindow(tab_modules, orient="vertical")
    paned.pack(fill="both", expand=True)

    # Upper Frame: Treeview Table
    tree_frame = tk.Frame(paned, bg="#f8fafc")
    paned.add(tree_frame, weight=3)

    cols = ("module", "category", "summary")
    tree = ttk.Treeview(
        tree_frame, columns=cols, show="headings", selectmode="browse"
    )
    tree.heading("module", text="Module / Python File")
    tree.heading("category", text="Subsystem / Category")
    tree.heading("summary", text="Responsibilities (What it does)")

    tree.column("module", width=220, minwidth=160, anchor="w")
    tree.column("category", width=160, minwidth=120, anchor="w")
    tree.column("summary", width=460, minwidth=280, anchor="w")

    vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    tree_frame.rowconfigure(0, weight=1)
    tree_frame.columnconfigure(0, weight=1)

    # Lower Frame: Detailed Description Pane
    detail_frame = tk.LabelFrame(
        paned,
        text="Selected Module Details",
        font=("Helvetica", 10, "bold"),
        bg="#f8fafc",
        fg="#0f172a",
        padx=8,
        pady=6,
    )
    paned.add(detail_frame, weight=1)

    detail_text = tk.Text(
        detail_frame,
        wrap="word",
        bg="#ffffff",
        fg="#1e293b",
        font=("Helvetica", 11),
        bd=1,
        relief="solid",
        padx=6,
        pady=6,
        height=4,
    )
    detail_text.pack(fill="both", expand=True)
    detail_text.insert(
        "1.0",
        "Select any module in the table above to view its "
        "detailed responsibilities.",
    )
    detail_text.config(state="disabled")

    # Populate & Filter Functionality
    def refresh_tree(*_args):
        selected_cat = category_combo.get()
        query = search_var.get().strip().lower()

        tree.delete(*tree.get_children())
        for path, cat, desc in SYSTEM_MODULE_CATALOG:
            # Category match
            if selected_cat != "All Categories":
                if (
                    selected_cat == "StockMan"
                    and not cat.startswith("StockMan")
                ):
                    continue
                if (
                    selected_cat == "BankMan"
                    and not cat.startswith("BankMan")
                ):
                    continue
                if (
                    selected_cat == "Shared"
                    and not cat.startswith("Shared")
                ):
                    continue
                if (
                    selected_cat not in ("StockMan", "BankMan", "Shared")
                    and selected_cat != cat
                ):
                    continue

            # Query match
            if query:
                searchable = f"{path} {cat} {desc}".lower()
                if query not in searchable:
                    continue

            # Short summary for table
            short_summary = desc.split(". ")[0] + "."
            tree.insert("", "end", values=(path, cat, short_summary))

    def on_tree_select(_event):
        selected = tree.selection()
        if not selected:
            return
        item = tree.item(selected[0])
        path = item["values"][0]

        # Find full description
        full_desc = ""
        full_cat = ""
        for p, c, d in SYSTEM_MODULE_CATALOG:
            if p == path:
                full_desc = d
                full_cat = c
                break

        detail_text.config(state="normal")
        detail_text.delete("1.0", "end")
        detail_text.insert("end", f"Module: {path}\n", "heading")
        detail_text.insert("end", f"Category: {full_cat}\n\n", "subheading")
        detail_text.insert("end", full_desc, "body")
        detail_text.tag_configure(
            "heading", font=("Helvetica", 11, "bold"), foreground="#0f172a"
        )
        detail_text.tag_configure(
            "subheading",
            font=("Helvetica", 10, "italic"),
            foreground="#0284c7",
        )
        detail_text.tag_configure(
            "body", font=("Helvetica", 11), foreground="#334155"
        )
        detail_text.config(state="disabled")

    tree.bind("<<TreeviewSelect>>", on_tree_select)
    search_var.trace_add("write", refresh_tree)
    category_combo.bind("<<ComboboxSelected>>", refresh_tree)

    refresh_tree()


def show_global_help(parent=None):
    """
    Launch the Global Help Center accessible via Ctrl+F1.

    Opens a comprehensive tabbed dialog containing the General Guide, the
    interactive Module Directory, and the FAQ.
    """
    if hasattr(parent, "_global_help_open") and parent._global_help_open:
        return None
    if parent:
        parent._global_help_open = True

    return show_standard_help(
        parent=parent,
        title="Global Help Center",
        guide_lines=global_guide_text,
        faq_data=global_faq_data,
        extra_tabs_callback=_add_module_directory_tab,
    )
