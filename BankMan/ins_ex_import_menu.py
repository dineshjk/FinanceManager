# -*- coding: utf-8 -*-
# BankMan/ins_ex_import_menu.py

"""
Insurance Batch Import & Export Navigation Menu.

This module builds the sub-menu for transferring insurance master policies and premium logs.

Key Responsibilities:
    • Navigation Hub: Provides choices to transfer policy profiles and payment histories.

Key Functions:
    • `show_ins_ex_import_menu(parent)`: Spawns the insurance import/export menu.
"""

from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from .ins_ex_import import export_ins, import_ins
from .ins_transactions_ex_import import (
    export_ins_transactions,
    import_ins_transactions,
)

# ---------------------------------------------------------------------------
# Export sub-menu
# ---------------------------------------------------------------------------


def show_ins_export_menu(parent, come_back_index=None):
    """Sub-menu: Insurance → Export."""

    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        menu_window.destroy()

    menu_config = {
        "title": "Export — Insurance",
        "geometry": "400x300",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#d9b3f5",
        "buttons": [
            {
                "text": "Insurance Master",
                "hotkey": "M",
                "command": lambda: export_ins(menu_window),
            },
            {
                "text": "Insurance Transactions",
                "hotkey": "T",
                "command": lambda: export_ins_transactions(menu_window),
            },
            {
                "text": "Previous Menu",
                "hotkey": "P",
                "command": close_modal,
            },
        ],
        "padx": 60,
        "pady": 5,
        "come_back_index": come_back_index,
    }

    menu_window, _ = create_menu_window(menu_config)
    menu_window.protocol("WM_DELETE_WINDOW", close_modal)

    push_window(menu_window, parent)
    parent.wait_window(menu_window)
    try:
        parent.grab_set()
    except Exception:
        pass
    enable_parent(modal_id)


# ---------------------------------------------------------------------------
# Import sub-menu
# ---------------------------------------------------------------------------


def show_ins_import_menu(parent, come_back_index=None):
    """Sub-menu: Insurance → Import."""

    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        menu_window.destroy()

    menu_config = {
        "title": "Import — Insurance",
        "geometry": "400x300",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#f5d9a0",
        "buttons": [
            {
                "text": "Insurance Master",
                "hotkey": "M",
                "command": lambda: import_ins(menu_window),
            },
            {
                "text": "Insurance Transactions",
                "hotkey": "T",
                "command": lambda: import_ins_transactions(menu_window),
            },
            {
                "text": "Previous Menu",
                "hotkey": "P",
                "command": close_modal,
            },
        ],
        "padx": 60,
        "pady": 5,
        "come_back_index": come_back_index,
    }

    menu_window, _ = create_menu_window(menu_config)
    menu_window.protocol("WM_DELETE_WINDOW", close_modal)

    push_window(menu_window, parent)
    parent.wait_window(menu_window)
    try:
        parent.grab_set()
    except Exception:
        pass
    enable_parent(modal_id)
