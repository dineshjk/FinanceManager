# -*- coding: utf-8 -*-
# StockMan/trade_menu.py

"""Trade management menu for StockMan.

Minimal, well-formatted implementation — single copy only.
"""

from typing import Any
import tkinter as tk
from Shared.menu_factory import create_menu_window
from .trade_add import add_trade
from .trade_add_zerodha import add_trade_zerodha
from .trade_manager import show_trade_manager
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from .direct_trade_menu import show_direct_trade_menu_modal
from .trade_from_file import trade_entry_from_file
from .sell_management import show_sell_management_modal
from Shared.globals import logger
from Shared.help_utils import show_standard_help

DEFAULT_GEOMETRY = "400x450"

def _get_trade_menu_help_data():
    guide_lines = [
        "This menu is your central hub for recording and managing your stock transactions.",
        "",
        "• Add Trade (ICICI / Auto): Log your standard secondary market buy and sell orders.",
        "• Add Trade (Zerodha): Log your secondary market buy and sell orders from Zerodha.",
        "• Direct Trading: Record primary market transactions like IPO allotments and Rights issues.",
        "• Manage / Edit / Remove: View your trade ledger, and safely delete or edit historical transactions.",
        "• Sell Management (FIFO): Process sell orders using the First-In, First-Out accounting method.",
        "• Import Trades: Batch import historical trades from a legacy database or file."
    ]
    faq_data = [
        (
            "Q: Why are there different buttons for ICICI and Zerodha?",
            "A: Each broker has slightly different contract note structures and charge calculations. The specific buttons ensure accurate calculation of brokerage, STT, and other statutory charges based on the exact platform you used."
        ),
        (
            "Q: What does Sell Management (FIFO) do?",
            "A: To calculate capital gains accurately, sold shares must be matched against specific past purchase lots. The system uses FIFO (First-In, First-Out) to ensure the oldest shares are always 'sold' first for tax reporting purposes."
        )
    ]
    return guide_lines, faq_data


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
        "geometry": "400x450",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#ead2e4",
        "buttons": [
            {
                "text": "Add Trade (ICICI / Auto)",
                "hotkey": "A",
                "command": lambda: add_trade(modal_win),
            },
            {
                "text": "Add Trade (Zerodha)",
                "hotkey": "Z",
                "command": lambda: add_trade_zerodha(modal_win),
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
    
    def _show_help(e=None):
        if e and (getattr(e, "state", 0) & 0x0004):
            return  # Let global handler process Ctrl+F1
        guide, faq = _get_trade_menu_help_data()
        show_standard_help(
            parent=modal_win,
            title="Trade Menu Help",
            guide_lines=guide,
            faq_data=faq
        )
    modal_win.bind("<F1>", _show_help)

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
