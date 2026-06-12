# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\helpers.py

"""
This file provides the following helper functions.
- list_all_id_stk: Returns a list of all stock IDs.
"""

import sqlite3
import tkinter as tk
from tkinter import ttk
from datetime import datetime, date
from typing import Union
import typing as _t

# Project-specific imports
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno,
)
from Shared.globals import get_db_connection

from Shared.globals import logger


def list_all_id_stk(parent: Union[tk.Toplevel, tk.Tk]) -> _t.List[int]:
    """Returns a list of `id_stk` integers from the current DB path.

    This function connects directly to the current database and returns
    all id_stk values from the stocks table.
    """
    ids: _t.List[int] = []
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id_stk FROM stocks ORDER BY company_name ASC"
            )
            for (row,) in cursor.fetchall():
                ids.append(int(row))
    except sqlite3.Error as exc:
        show_colorful_error(parent, "DB Error", f"Failed to read: {exc}")
        logger.exception("list_all_id_stk: DB error %s", exc)
        return []
    return ids


def universal_tree_sort(tree: ttk.Treeview, col: str, reverse: bool) -> None:
    """A generic sorter that handles Strings, Currency, Percentages, and DD-MM-YYYY dates."""
    data_list = [
        (tree.set(child, col), child)
        for child in tree.get_children("")
        if "summary" not in tree.item(child, "tags") and child != "SUMMARY"
    ]

    def convert_type(val_tuple):
        val = str(val_tuple[0]).strip()
        # Handle empty/loading states
        if val in ("N/A", "-", "", "TBD", "Fetching...", "Calculating..."):
            return float("-inf") if reverse else float("inf")

        # Strip currency and formatting
        clean_val = (
            val.split("(")[0]
            .replace(",", "")
            .replace("₹", "")
            .replace("%", "")
            .strip()
        )

        # Check if it's a DD-MM-YYYY date
        if (
            len(clean_val) == 10
            and clean_val[2] == "-"
            and clean_val[5] == "-"
        ):
            try:
                return datetime.strptime(clean_val, "%d-%m-%Y").timestamp()
            except ValueError:
                pass

        # Try numeric, fallback to string
        try:
            return float(clean_val)
        except ValueError:
            return val.lower()

    data_list.sort(key=convert_type, reverse=reverse)

    for index, (val, child) in enumerate(data_list):
        tree.move(child, "", index)

    tree.heading(
        col,
        command=lambda _col=col: universal_tree_sort(tree, _col, not reverse),
    )


def financial_year_label(value_date: date) -> str:
    """Return the Apr-Mar financial year label for a date."""
    start_year = (
        value_date.year if value_date.month >= 4 else value_date.year - 1
    )
    return f"FY {start_year}-{str(start_year + 1)[-2:]}"


def financial_year_sort_key(fy_label: str) -> int:
    """Return the starting year for a financial-year label."""
    return int(fy_label.split(" ")[1].split("-")[0])


def _new_investment_stats_bucket(
    opening_balance: float = 0.0,
) -> dict[str, float]:
    return {
        "total_investment": 0.0,
        "total_disinvestment": 0.0,
        "max_invested": opening_balance,
        "min_invested": opening_balance,
        "largest_investment": 0.0,
        "largest_disinvestment": 0.0,
    }


def calculate_investment_summary_stats(
    investment_rows: _t.Iterable[tuple[_t.Any, str, float]],
    disinvestment_rows: _t.Iterable[tuple[_t.Any, str, float]],
) -> dict[str, _t.Any]:
    """Aggregate invested-capital totals and running-balance extremes.

    `investment_rows` and `disinvestment_rows` are expected to contain
    `(event_id, date_text, amount)` tuples. Disinvestment amounts represent
    capital withdrawn on a cost basis, so they reduce the running invested
    balance without overstating withdrawals after profitable exits.
    Rows with the same `(event_id, date_text)` are treated as a single
    one-time event so that "largest" metrics reflect a full trade event.
    """
    events: list[dict[str, _t.Any]] = []
    grouped_investments: dict[tuple[int, str], float] = {}
    grouped_disinvestments: dict[tuple[int, str], float] = {}

    for event_id, date_text, amount in investment_rows:
        if not date_text or amount is None or amount <= 0:
            continue
        group_key = (int(event_id or 0), date_text)
        grouped_investments[group_key] = grouped_investments.get(
            group_key, 0.0
        ) + float(amount)

    for (event_id, date_text), amount in grouped_investments.items():
        event_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        events.append(
            {
                "date": event_date,
                "order": 0,
                "event_id": event_id,
                "investment": amount,
                "disinvestment": 0.0,
                "delta": amount,
                "fy": financial_year_label(event_date),
            }
        )

    for event_id, date_text, amount in disinvestment_rows:
        if not date_text or amount is None or amount <= 0:
            continue
        group_key = (int(event_id or 0), date_text)
        grouped_disinvestments[group_key] = grouped_disinvestments.get(
            group_key, 0.0
        ) + float(amount)

    for (event_id, date_text), amount in grouped_disinvestments.items():
        event_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        events.append(
            {
                "date": event_date,
                "order": 1,
                "event_id": event_id,
                "investment": 0.0,
                "disinvestment": amount,
                "delta": -amount,
                "fy": financial_year_label(event_date),
            }
        )

    events.sort(
        key=lambda event: (event["date"], event["order"], event["event_id"])
    )

    overall = _new_investment_stats_bucket()
    yearly: dict[str, dict[str, float]] = {}
    running_balance = 0.0

    for event in events:
        fy_label = event["fy"]
        year_bucket = yearly.setdefault(
            fy_label, _new_investment_stats_bucket(running_balance)
        )

        investment_amount = event["investment"]
        disinvestment_amount = event["disinvestment"]

        if investment_amount:
            overall["total_investment"] += investment_amount
            overall["largest_investment"] = max(
                overall["largest_investment"], investment_amount
            )
            year_bucket["total_investment"] += investment_amount
            year_bucket["largest_investment"] = max(
                year_bucket["largest_investment"], investment_amount
            )

        if disinvestment_amount:
            overall["total_disinvestment"] += disinvestment_amount
            overall["largest_disinvestment"] = max(
                overall["largest_disinvestment"], disinvestment_amount
            )
            year_bucket["total_disinvestment"] += disinvestment_amount
            year_bucket["largest_disinvestment"] = max(
                year_bucket["largest_disinvestment"], disinvestment_amount
            )

        running_balance += event["delta"]
        overall["max_invested"] = max(overall["max_invested"], running_balance)
        overall["min_invested"] = min(overall["min_invested"], running_balance)
        year_bucket["max_invested"] = max(
            year_bucket["max_invested"], running_balance
        )
        year_bucket["min_invested"] = min(
            year_bucket["min_invested"], running_balance
        )

    return {"overall": overall, "yearly": yearly}


# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\helpers.py ends here
