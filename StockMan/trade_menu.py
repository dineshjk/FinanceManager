# -*- coding: utf-8 -*-
# StockMan/trade_menu.py

"""Trade management menu for StockMan.

Minimal, well-formatted implementation — single copy only.
"""

from typing import Any
import tkinter as tk
from Shared.menu_factory import create_menu_window
from .trade_add import add_trade
from .trade_manager import show_trade_manager
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from .direct_trade_menu import show_direct_trade_menu_modal
from .trade_from_file import trade_entry_from_file
from .sell_management import show_sell_management_modal
from Shared.globals import logger

DEFAULT_GEOMETRY = "400x400"


def show_trade_menu_modal(
    parent: Any, come_back_index: int | None = None
) -> None:
    """Show the trade menu as a modal window.

    The function builds a simple button configuration and uses the menu
    factory to display a modal window. Parent window is disabled while
    the modal is active.
    """
    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        modal_win.destroy()

    menu_config = {
        "title": "Trade Menu",
        "geometry": "400x400",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#ead2e4",
        "buttons": [
            {
                "text": "Add Trade",
                "hotkey": "A",
                "command": lambda: add_trade(modal_win),
            },
            {
                "text": "Direct Trading (IPO/Rights)",
                "hotkey": "D",
                "command": (
                    lambda: show_direct_trade_menu_modal(
                        modal_win, come_back_index
                    )
                ),
            },
            {
                "text": "Manage / Edit / Remove",
                "hotkey": "M",
                "command": lambda: show_trade_manager(modal_win),
            },
            {
                "text": "Sell Management (FIFO)",
                "hotkey": "S",
                "command": lambda: show_sell_management_modal(modal_win),
            },
            {
                "text": "Import Trades",
                "hotkey": "I",
                "command": lambda: trade_entry_from_file(
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
