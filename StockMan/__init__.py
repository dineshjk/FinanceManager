# -*- coding: utf-8 -*-
# StockMan/__init__.py

"""
StockMan - Equity Portfolio & Market Intelligence Subsystem.

This package provides a comprehensive, privacy-first equity investment management
system. It handles stock registrations, multi-broker trade executions (ICICI Direct,
Zerodha), strict First-In-First-Out (FIFO) capital gains accounting, corporate action
cost basis transfers (splits, bonuses, mergers, demergers), AI-powered market analysis
via Google Gemini, technical momentum scanners, and automated multi-sheet portfolio
exports with background Google Drive cloud synchronization.

Core Subsystem Modules:
    • Master Data: `company_add`, `company_update`, `company_bulk_entry`, `company_menu`.
    • Trade Processing: `trade_add`, `trade_add_zerodha`, `trade_update`, `sell_management`.
    • Corporate Actions: `dividend`, `split_entry`, `bonus_entry`, `merger_entry`, `demerger_entry`.
    • Intelligence & AI: `ai_analyzer`, `advice_tracker`, `scanner`, `watchlist_menu`.
    • Persistence & Engine: `stock_database_setup`, `corp_manager`, `rollback_manager`, `reporting`.
"""

# --- Globals & Database ---
from Shared.globals import (
    STOCK_APP_TITLE,
    BANK_APP_TITLE,
    UNIVERSAL_APP_TITLE,
    get_db_connection,
    logger,
)

# --- GUI & Styling Utilities ---
from Shared.style_utils import apply_style, ensure_ttk_style, STYLE_CONFIGS
from Shared.menu_factory import create_menu_window
from Shared.gui_utils import format_hotkey_label
from Shared.gui_progressive import progressive_selection
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno,
)

from Shared.gui_utils import (
    # ... your other gui_utils imports ...
    apply_entry_theme,
)

# --- Core Domain & Trade Utilities ---
from .trade_utils import (
    select_trade_from_list,
    select_company_from_list,
    revert_sell_allocation,
    manage_sell,
    compute_avg_price,
)
from .company_menu import (
    add_company,
    update_company,
    bulk_entry_company,
    show_company_menu_modal,
)
from .company_remove import remove_company
from .watchlist_menu import show_watchlist

# --- Corporate Actions ---
from .dividend import add_dividend
from .bonus_entry import bonus_shares
from .merger_entry import add_merger
from .rights import rights
from .split_entry import add_split_share

# --- General Utilities ---
from .date_utils import (
    next_working_day,
    previous_working_day,
    is_working_day,
    format_date_for_display,
    parse_date_from_string,
)
from .validation_utils import show_validation_error, ValidationError
from .helpers import list_all_id_stk, universal_tree_sort
from .stock_database_setup import create_stockman_database
from .transfer_data import (
    calculate_transfer_data,
    export_transfer_data_to_excel,
    generate_and_export_transfer_data,
    export_transfer_data_gui,
)
from .drive_sync import (
    update_portfolio_excel,
    export_portfolio_excel,
    build_portfolio_dataframe,
    fetch_live_cmp,
    get_drive_service,
    upload_portfolio_to_drive,
    download_latest_pick_of_the_day,
    sync_two_way_pipeline,
    get_local_pick_of_the_day,
    run_startup_sequence,
    adjust_cash_for_trade,
    adjust_cash_for_trades,
    update_available_cash_in_excel,
)
from .advice_tracker import (
    show_advice_tracker,
    parse_advice_from_pick_of_the_day,
    auto_update_advice_from_pick_of_the_day,
    sync_all_pending_pick_of_the_day_advices,
)

# Define explicitly what this package exports
__all__ = [
    # Globals
    "STOCK_APP_TITLE",
    "BANK_APP_TITLE",
    "UNIVERSAL_APP_TITLE",
    "get_db_connection",
    "logger",
    # GUI
    "apply_style",
    "ensure_ttk_style",
    "STYLE_CONFIGS",
    "create_menu_window",
    "format_hotkey_label",
    "progressive_selection",
    "show_colorful_info",
    "show_colorful_error",
    "show_colorful_yesno",
    "apply_entry_theme",
    # Domain
    "select_trade_from_list",
    "select_company_from_list",
    "revert_sell_allocation",
    "manage_sell",
    "compute_avg_price",
    "add_company",
    "update_company",
    "remove_company",
    "bulk_entry_company",
    "show_company_menu_modal",
    "show_watchlist",
    # Corporate Actions
    "add_dividend",
    "bonus_shares",
    "add_merger",
    "rights",
    "add_split_share",
    # Utilities
    "list_all_id_stk",
    "universal_tree_sort",
    "create_stockman_database",
    "next_working_day",
    "previous_working_day",
    "is_working_day",
    "format_date_for_display",
    "parse_date_from_string",
    "show_validation_error",
    "ValidationError",
    # Transfer Data
    "calculate_transfer_data",
    "export_transfer_data_to_excel",
    "generate_and_export_transfer_data",
    "export_transfer_data_gui",
    # Portfolio Excel Export & Google Drive Pipeline
    "update_portfolio_excel",
    "export_portfolio_excel",
    "build_portfolio_dataframe",
    "fetch_live_cmp",
    "get_drive_service",
    "upload_portfolio_to_drive",
    "download_latest_pick_of_the_day",
    "sync_two_way_pipeline",
    "get_local_pick_of_the_day",
    "run_startup_sequence",
    "adjust_cash_for_trade",
    "adjust_cash_for_trades",
    "update_available_cash_in_excel",
    # Advice Tracking
    "show_advice_tracker",
    "parse_advice_from_pick_of_the_day",
    "auto_update_advice_from_pick_of_the_day",
    "sync_all_pending_pick_of_the_day_advices",
]
