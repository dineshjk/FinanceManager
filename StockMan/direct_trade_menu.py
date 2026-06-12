# -*- coding: utf-8 -*-
# StockMan/direct_trade_menu.py


"""Direct trading modal for IPOs, Rights and Allotments."""

import tkinter as tk
from typing import Any

from .rights import rights
from Shared.globals import logger
from Shared.dialog_utils import show_colorful_info
from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from .ipo import ipo
from .primary_offer_remove import remove_primary_offer


def _info(parent: Any, title: str, message: str) -> None:
    """Helper wrapper for informational dialogs."""
    show_colorful_info(parent, title, message)


def show_direct_trade_menu_modal(
    parent: Any, come_back_index: int | None = None
) -> None:
    """Show modal containing direct trade actions
    (IPO/Right/Allotment/Remove).
    """
    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        modal_win.destroy()

    buttons = [
        {
            "text": "IPO Subscription",
            "hotkey": "I",
            "command": lambda: ipo(parent=modal_win),
        },
        {
            "text": "Rights Issue",
            "hotkey": "R",
            "command": lambda: rights(parent=modal_win),
        },
        {
            "text": "Remove Offer",
            "hotkey": "O",
            "command": lambda: remove_primary_offer(parent=modal_win),
        },
        {"text": "Previous Menu", "hotkey": "X", "command": close_modal},
    ]

    menu_config = {
        "title": "Direct Trading",
        "geometry": "360x350",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#f7f7e6",
        "buttons": buttons,
        "padx": 40,
        "pady": 5,
        "come_back_index": come_back_index,
    }

    modal_win, _ = create_menu_window(menu_config)
    push_window(modal_win, parent)
    parent.wait_window(modal_win)
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        logger.debug("parent.grab_set skipped: parent destroyed.")
    enable_parent(modal_id)
