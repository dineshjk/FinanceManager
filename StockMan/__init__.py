# -*- coding: utf-8 -*-
# StockMan/__init__.py

"""
StockMan Package Initialization.
Exposes key components, utilities, and GUI factories for the portfolio manager.
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
    "apply_dark_entry_theme",
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
]
