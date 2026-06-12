# -*- coding: utf-8 -*-
# BankMan/fd_ex_import_menu.py

"""
Fixed Deposit Export / Import sub-menus for the BankMan application.
Each function opens a 3-button sub-menu (Master | Transactions | Back).
"""

from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from .fd_ex_import import export_fd, import_fd
from .fd_transactions_ex_import import export_fd_transactions, import_fd_transactions

# ---------------------------------------------------------------------------
# Export sub-menu
# ---------------------------------------------------------------------------


def show_fd_export_menu(parent, come_back_index=None):
    """Sub-menu: Fixed Deposit → Export."""

    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        menu_window.destroy()

    menu_config = {
        "title": "Export — Fixed Deposit",
        "geometry": "400x300",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#d9b3f5",
        "buttons": [
            {
                "text": "Fixed Deposit Master",
                "hotkey": "M",
                "command": lambda: export_fd(menu_window),
            },
            {
                "text": "Fixed Deposit Transactions",
                "hotkey": "T",
                "command": lambda: export_fd_transactions(menu_window),
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
    parent.grab_set()
    enable_parent(modal_id)


# ---------------------------------------------------------------------------
# Import sub-menu
# ---------------------------------------------------------------------------


def show_fd_import_menu(parent, come_back_index=None):
    """Sub-menu: Fixed Deposit → Import."""

    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        menu_window.destroy()

    menu_config = {
        "title": "Import — Fixed Deposit",
        "geometry": "400x300",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#f5d9a0",
        "buttons": [
            {
                "text": "Fixed Deposit Master",
                "hotkey": "M",
                "command": lambda: import_fd(menu_window),
            },
            {
                "text": "Fixed Deposit Transactions",
                "hotkey": "T",
                "command": lambda: import_fd_transactions(menu_window),
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
    parent.grab_set()
    enable_parent(modal_id)
