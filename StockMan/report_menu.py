# -*- coding: utf-8 -*-
# StockMan/report_menu.py



"""Trade management menu for StockMan.

Minimal, well-formatted implementation — single copy only.
"""

from typing import Any
import tkinter as tk
from Shared.menu_factory import create_menu_window
from .reporting import latest_trade, p_and_l
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from Shared.globals import logger

DEFAULT_GEOMETRY = "400x400"


def show_report_menu_modal(
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
        report_menu_win.destroy()

    menu_config = {
        "title": "Reports Menu",
        "geometry": "400x450",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#ed91cb",
        "buttons": [
            {
                "text": "Latest Trade",
                "hotkey": "L",
                "command": lambda: latest_trade(report_menu_win),
            },
            {
                "text": "Profit & Loss",
                "hotkey": "P",
                "command": (lambda: p_and_l(report_menu_win)),
            },
            {"text": "Previous Menu", "hotkey": "X", "command": close_modal},
        ],
        "padx": 60,
        "pady": 5,
        "come_back_index": come_back_index,
    }
    report_menu_win, btn_widgets = create_menu_window(menu_config)
    push_window(report_menu_win, parent)
    parent.wait_window(report_menu_win)
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        logger.debug("parent.grab_set skipped: parent destroyed.")
    enable_parent(modal_id)
