# -*- coding: utf-8 -*-
# StockMan/corpo_menu.py


"""
Corporate Actions management menu window for
the Stock Portfolio Management System.

Provides access to:
- Add Corporate Action
- Update Corporate Action
- Remove Corporate Action
- Previous Menu
"""

import tkinter as tk
from typing import Union

from .corp_manager import show_corp_manager
from .dividend import add_dividend
from .bonus_entry import bonus_shares
from .split_entry import add_split_share  # <--- NEW IMPORT
from .merger_entry import add_merger
from .demerger_entry import add_demerger
from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from Shared.help_utils import show_standard_help

DEFAULT_GEOMETRY = "400x400"


# def show_update_corp_menu(menu=None, button=None):
#     """
#     Show the Update Corporate Menu as a modal window (using menu_factory)
#     and restore main button state.
#     """

#     parent = menu
#     main_buttons = getattr(parent, "_main_menu_buttons", [])
#     idx = 0
#     if parent is not None:
#         focused = parent.focus_get()
#         try:
#             idx = main_buttons.index(focused)
#         except ValueError:
#             pass

#     show_update_corp_menu_modal(parent, come_back_index=idx)


# def show_remove_corp_menu(parent, button=None):
#     """Show info dialog for Remove Corporate Action."""
#     show_colorful_info(
#         parent, "Remove Corporate Action", "Remove Corporate Action clicked!"
#     )


def show_add_corp_menu(menu=None, button=None):
    """
    Show the Add Corporate Menu as a modal window (using menu_factory)
    and restore main button state.
    """

    parent = menu
    main_buttons = getattr(parent, "_main_menu_buttons", [])
    idx = 0
    if parent is not None:
        focused = parent.focus_get()
        try:
            idx = main_buttons.index(focused)
        except ValueError:
            pass

    show_add_corp_menu_modal(parent, come_back_index=idx)


def _get_add_corp_help_data():
    guide = [
        "Choose the specific type of corporate event declared by the company.",
        "• Dividend: Record standard cash payouts.",
        "• Bonus Issue: Record free additional shares given to current shareholders.",
        "• Share Split: Record a face-value split that increases your quantity and reduces your average price.",
        "• Merger / Demerger: Restructure holdings when a company amalgamates or spins off a new entity."
    ]
    faq = [(
        "Q: How do I handle Fractional Shares during a split or bonus?",
        "A: If a corporate action results in fractional shares, record only the whole shares here. The company will eventually cash out the fractional remainder directly to your bank account, which you should log manually."
    )]
    return guide, faq

def show_add_corp_menu_modal(
    parent: Union[tk.Tk, tk.Toplevel], come_back_index: int | None = None
) -> None:
    """Show the Add Corporate Action menu as a modal window.

    The function builds a simple button configuration and uses the menu
    factory to display a modal window. Parent window is disabled while
    the modal is active.
    """
    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        add_corp_win.destroy()

    menu_config = {
        "title": "Add Corporate Actions Menu",
        "geometry": DEFAULT_GEOMETRY,
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#bfec5e",  # Light green for modal
        "buttons": [
            {
                "text": "Dividend",
                "hotkey": "D",
                "command": lambda: add_dividend(add_corp_win),
            },
            {
                "text": "Bonus Issue",
                "hotkey": "B",
                "command": lambda: bonus_shares(add_corp_win),
            },
            {
                "text": "Share Split",
                "hotkey": "S",
                "command": lambda: add_split_share(add_corp_win),
            },
            {
                "text": "Merger",
                "hotkey": "M",
                "command": lambda: add_merger(add_corp_win),
            },
            {
                "text": "Demerger",
                "hotkey": "G",
                "command": lambda: add_demerger(add_corp_win),
            },
            {
                "text": "Previous Menu",
                "hotkey": "X",
                "command": close_modal,
            },
        ],
        "padx": 60,
        "pady": 5,
        "come_back_index": come_back_index,
    }
    add_corp_win, _ = create_menu_window(menu_config)
    
    def _show_add_help(e=None):
        guide, faq = _get_add_corp_help_data()
        show_standard_help(add_corp_win, "Add Corporate Action Help", guide, faq)
    add_corp_win.bind("<F1>", lambda e: None if getattr(e, "state", 0) & 0x0004 else _show_add_help(e))

    push_window(add_corp_win, parent)
    parent.wait_window(add_corp_win)
    try:
        parent.grab_set()
    except Exception:
        pass
    enable_parent(modal_id)


# def show_update_corp_menu_modal(
#     parent: Union[tk.Tk, tk.Toplevel], come_back_index: int | None = None
# ) -> None:
#     """Show the Update Corporate Action menu as a modal window.

#     The function builds a simple button configuration and uses the menu
#     factory to display a modal window. Parent window is disabled while
#     the modal is active.
#     """
#     modal_id = disable_parent(parent)

#     def close_modal() -> None:
#         pop_window()
#         update_corp_win.destroy()

#     menu_config = {
#         "title": "Update Corporate Actions Menu",
#         "geometry": DEFAULT_GEOMETRY,
#         "style": "Menu.TButton",
#         "parent": parent,
#         "modal": True,
#         "bg": "#bfec5e",  # Light green for modal
#         "buttons": [
#             {
#                 "text": "Update Dividend",
#                 "hotkey": "D",
#                 "command": lambda: update_dividend(update_corp_win),
#             },
#             {
#                 "text": "Update Bonus Share",
#                 "hotkey": "B",
#                 "command": lambda: bonus_shares(update_corp_win, edit_id=selected_id),
#             },
#             {
#                 "text": "Update Split Share",
#                 "hotkey": "S",
#                 "command": lambda: update_split_share(update_corp_win),
#             },
#             {
#                 "text": "Update Merger Action",  # <--- ADD THIS BLOCK
#                 "hotkey": "M",
#                 "command": lambda: update_merger(update_corp_win),
#             },
#             {
#                 "text": "Update Demerger Action",  # <--- ADD THIS BLOCK
#                 "hotkey": "D",
#                 "command": lambda: update_demerger(update_corp_win),
#             },
#             {
#                 "text": "Previous Menu",
#                 "hotkey": "P",
#                 "command": close_modal,
#             },
#         ],
#         "padx": 60,
#         "pady": 5,
#         "come_back_index": come_back_index,
#     }
#     update_corp_win, _ = create_menu_window(menu_config)
#     push_window(update_corp_win, parent)
#     parent.wait_window(update_corp_win)
#     parent.grab_set()
#     enable_parent(modal_id)


def _get_corp_hub_help_data():
    guide = [
        "This is your primary hub for managing corporate events that affect your portfolio structure.",
        "• Add Corporate Action: Open the sub-menu to record a Dividend, Bonus, Split, or Merger.",
        "• Demerger: A direct shortcut to record a corporate spin-off.",
        "• Manage / Edit / Remove: Open the Manager grid to review, edit, or delete historical corporate actions."
    ]
    faq = [(
        "Q: Do these actions automatically update my portfolio balance?",
        "A: Yes! When you log a Bonus or Split here, the system automatically adjusts your holding quantity and average purchase price in your reports."
    )]
    return guide, faq


def show_corporate_menu_modal(parent, come_back_index=None):
    """Show the corporate actions management menu as a modal window.

    Uses the menu_factory system. Optionally accepts
    come_back_index to restore focus to the next button in parent.
    """
    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        corp_win.destroy()

    menu_config = {
        "title": "Corporate Actions Menu",
        "geometry": DEFAULT_GEOMETRY,
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#917aec",  # Light purple for modal
        "buttons": [
            {
                "text": "Add Corporate Action",
                "hotkey": "A",
                "command": lambda: show_add_corp_menu(corp_win),
            },
            {
                "text": "Demerger",
                "hotkey": "D",
                "command": lambda: add_demerger(corp_win),
            },
            {
                "text": "Manage / Edit / Remove",
                "hotkey": "M",
                "command": lambda: show_corp_manager(corp_win),
            },
            {
                "text": "Previous Menu",
                "hotkey": "X",
                "command": close_modal,
            },
        ],
        "padx": 60,
        "pady": 5,
        "come_back_index": come_back_index,
    }
    corp_win, _ = create_menu_window(menu_config)
    
    def _show_hub_help(e=None):
        guide, faq = _get_corp_hub_help_data()
        show_standard_help(corp_win, "Corporate Actions Hub Help", guide, faq)
    corp_win.bind("<F1>", lambda e: None if getattr(e, "state", 0) & 0x0004 else _show_hub_help(e))

    push_window(corp_win, parent)
    parent.wait_window(corp_win)
    try:
        parent.grab_set()
    except Exception:
        pass
    enable_parent(modal_id)
