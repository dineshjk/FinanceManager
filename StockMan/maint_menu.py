# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\maint_menu.py


"""Maintenance menu for StockMan."""

from typing import Any
import tkinter as tk
from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from .trade_from_file import trade_entry_from_file
from .watchlist_from_file import import_watchlist_from_file
from .export_trades import export_trades
from Shared.globals import logger
from Shared.dialog_utils import show_colorful_info

DEFAULT_GEOMETRY = "400x300"


def show_maint_menu_modal(
    parent: Any, come_back_index: int | None = None
) -> None:
    """Show the maintenance menu as a modal window.

    The function builds a simple button configuration and uses the menu
    factory to display a modal window. Parent window is disabled while
    the modal is active.
    """
    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        modal_win.destroy()

    menu_config = {
        "title": "Maintenance Menu",
        "geometry": DEFAULT_GEOMETRY,
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#d4e1f5",  # A light blue/grey color
        "buttons": [
            {
                "text": "Export Trades",
                "hotkey": "E",
                "command": lambda: export_trades(modal_win),
            },
            {
                "text": "Import Trades",
                "hotkey": "I",
                "command": lambda: trade_entry_from_file(
                    modal_win, src_db_path="mystocks_old.db"
                ),
            },
            {
                "text": "Import Watchlist",
                "hotkey": "W",
                "command": lambda: import_watchlist_from_file(
                    modal_win, src_db_path="mystocks_old.db"
                ),
            },
            {"text": "Previous Menu", "hotkey": "X", "command": close_modal},
        ],
        "padx": 60,
        "pady": 5,
        "come_back_index": come_back_index,
    }
    modal_win, btn_widgets = create_menu_window(menu_config)
    push_window(modal_win, parent)
    parent.wait_window(modal_win)
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        logger.debug("parent.grab_set skipped: parent destroyed.")
    enable_parent(modal_id)


# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\maint_menu.py ends here
