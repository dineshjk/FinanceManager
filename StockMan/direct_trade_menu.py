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

from Shared.help_utils import show_standard_help

def _get_direct_trade_help_data():
    guide_lines = [
        "This menu handles primary market transactions rather than standard secondary market trades.",
        "",
        "• IPO Subscription: Record Initial Public Offering allotments directly into your portfolio.",
        "• Rights Issue: Log shares acquired through corporate Rights issues.",
        "• Remove Offer: Delete incorrectly logged primary market transactions."
    ]
    faq_data = [
        (
            "Q: Do these trades use contract notes?",
            "A: No, primary market transactions like IPOs and Rights issues bypass standard broker contract notes and are credited directly to your demat account. Therefore, they do not require Brokerage, STT, or Exchange charges to be logged here."
        )
    ]
    return guide_lines, faq_data



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
    
    def _show_help(e=None):
        guide, faq = _get_direct_trade_help_data()
        show_standard_help(
            parent=modal_win,
            title="Direct Trading Help",
            guide_lines=guide,
            faq_data=faq
        )
        
    # Explicitly enforce Escape key to close modal and return to parent
    modal_win.bind("<Escape>", lambda e: close_modal())
    
    # The bitmask 0x0004 strictly checks for the Control key to prevent double-triggering global help
    modal_win.bind("<F1>", lambda e: None if getattr(e, "state", 0) & 0x0004 else _show_help(e))

    push_window(modal_win, parent)
    parent.wait_window(modal_win)
    try:
        if parent.winfo_exists():
            try:
                parent.grab_set()
            except Exception:
                pass
    except tk.TclError:
        logger.debug("parent.grab_set skipped: parent destroyed.")
    enable_parent(modal_id)
