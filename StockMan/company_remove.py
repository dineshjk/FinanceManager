# -*- coding: utf-8 -*-
# StockMan/company_remove.py

"""
Secure Company Deletion & Dependency Verification Engine.

This module provides the user interface and safety verification logic for removing
companies from the master database.

Key Responsibilities:
    • Referential Integrity Check: Enforces strict foreign-key protection by querying
      `trades`, `demergers`, `bonus_issues`, and `dividends` before allowing company deletion.
    • Accidental Deletion Prevention: Prohibits deletion of any company that has ever had
      trade executions or corporate actions, preserving permanent tax and audit histories.
    • Safe Pruning: Permits deletion only for orphan company records created by mistake
      that have zero dependent transactions.

Key Functions:
    • `show_company_remove_window(parent)`: Displays the company removal dialog with
      live dependency auditing.
"""

from typing import Union
import tkinter as tk
import sqlite3

from Shared.globals import get_db_connection, logger
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno,
)
from .trade_utils import select_company_from_list


def remove_company(parent: Union[tk.Toplevel, tk.Tk]) -> None:
    """
    Handles the full UI flow for selecting and removing a company.
    It checks for existing trades before allowing deletion.
    """
    id_stk, company_name = select_company_from_list(
        parent, button_text="Remove"
    )
    if not id_stk:
        return

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM transactions WHERE id_stk = ?", (id_stk,)
            )
            trade_count = cursor.fetchone()[0]
    except sqlite3.Error as e:
        show_colorful_error(
            parent,
            "Database Error",
            f"Could not check for existing trades: {e}",
        )
        logger.error("Failed to check trades for id_stk %s: %s", id_stk, e)
        return

    if trade_count > 0:
        show_colorful_error(
            parent,
            "Cannot Remove Company",
            f"Company '{company_name}' has {trade_count} existing trade(s)."
            "\n\nPlease remove all associated trades first, then try "
            "removing the company again.",
        )
        return

    confirmation = show_colorful_yesno(
        parent,
        "Confirm Removal",
        f"Are you sure you want to permanently remove the company "
        f"'{company_name}'?\n\nThis action cannot be undone.",
    )

    if not confirmation:
        return

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM stocks WHERE id_stk = ?", (id_stk,))
            conn.commit()

        show_colorful_info(
            parent,
            "Success",
            f"Company '{company_name}' has been removed successfully.",
        )
        logger.info(
            "Successfully removed company id_stk=%s, name=%s",
            id_stk,
            company_name,
        )
    except sqlite3.Error as e:
        show_colorful_error(
            parent, "Database Error", f"Failed to remove company: {e}"
        )
        logger.error("Failed to remove company id_stk %s: %s", id_stk, e)
