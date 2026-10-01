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
from Shared.help_utils import show_standard_help

DEFAULT_GEOMETRY = "400x400"

def _get_report_menu_help_data():
    guide_lines = [
        "This menu generates insights into your portfolio performance and trading history.",
        "",
        "• Latest Trade: View your most recent transactions to quickly verify your data entry.",
        "• Profit & Loss: Generate detailed realized P&L statements for tax reporting and performance tracking."
    ]
    faq_data = [
        (
            "Q: Do these reports include real-time market prices?",
            "A: The Profit & Loss report is based on *realized* gains and losses from your actual Sell transactions. To view *unrealized* gains based on current prices, ensure you have updated the Current Market Price (CMP) via the 'Maintenance' menu."
        )
    ]
    return guide_lines, faq_data


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
    
    def _show_help(e=None):
        guide, faq = _get_report_menu_help_data()
        show_standard_help(
            parent=report_menu_win,
            title="Reports Menu Help",
            guide_lines=guide,
            faq_data=faq
        )
        
    # Explicitly enforce Escape key to close modal and return to parent
    report_menu_win.bind("<Escape>", lambda e: close_modal())
    
    # The bitmask 0x0004 strictly checks for the Control key to prevent double-triggering global help
    report_menu_win.bind("<F1>", lambda e: None if getattr(e, "state", 0) & 0x0004 else _show_help(e))

    push_window(report_menu_win, parent)
    parent.wait_window(report_menu_win)
    try:
        if parent.winfo_exists():
            try:
                parent.grab_set()
            except Exception:
                pass
    except tk.TclError:
        logger.debug("parent.grab_set skipped: parent destroyed.")
    enable_parent(modal_id)
