# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\trade_utils.py

"""
trade_utils.py
--------------

Shared utility functions for trade and company management in the StockMan application.
This module centralizes common logic to avoid code duplication.

"""

from datetime import datetime
from typing import Union
import tkinter as tk
from tkinter import ttk
import sqlite3

from Shared.globals import get_db_connection, logger
from Shared.dialog_utils import show_colorful_info, show_colorful_error
from Shared.gui_utils import universal_tree_sort


def _parse_iso_trade_date(date_str: str):
    """Parse a YYYY-MM-DD date string to a date object."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _build_entitled_lots(
    transaction_rows,
    record_dt: str,
    entitled_qty: int,
):
    """Return entitled open lots at the dividend record date."""
    if entitled_qty <= 0:
        return None

    record_date = _parse_iso_trade_date(record_dt)
    if record_date is None:
        return None

    open_lots: list[dict[str, float | int | object]] = []
    for trd_dt, trade_type, qty_trd, net_amt_trd in transaction_rows:
        trade_date = _parse_iso_trade_date(trd_dt)
        if trade_date is None or trade_date >= record_date:
            continue

        qty = int(qty_trd or 0)
        net_amt = float(net_amt_trd or 0.0)
        if qty <= 0:
            continue

        if trade_type == "BUY":
            cost_per_share = net_amt / qty
            open_lots.append(
                {
                    "trade_date": trade_date,
                    "qty": qty,
                    "cost_per_share": cost_per_share,
                }
            )
            continue

        if trade_type != "SELL":
            continue

        qty_to_match = qty
        while qty_to_match > 0 and open_lots:
            first_lot = open_lots[0]
            reduction_qty = min(qty_to_match, int(first_lot["qty"]))
            first_lot["qty"] = int(first_lot["qty"]) - reduction_qty
            qty_to_match -= reduction_qty
            if int(first_lot["qty"]) == 0:
                open_lots.pop(0)

        if qty_to_match > 0:
            return None

    outstanding_qty = sum(int(lot["qty"]) for lot in open_lots)
    if outstanding_qty < entitled_qty or outstanding_qty <= 0:
        return None

    allocation_ratio = entitled_qty / outstanding_qty
    entitled_lots = []
    for lot in open_lots:
        allocated_qty = int(lot["qty"]) * allocation_ratio
        if allocated_qty <= 0:
            continue
        entitled_lots.append(
            {
                "trade_date": lot["trade_date"],
                "allocated_qty": allocated_qty,
                "cost_per_share": float(lot["cost_per_share"]),
            }
        )
    return entitled_lots


def calculate_dividend_return_percent(
    transaction_rows,
    record_dt: str,
    entitled_qty: int,
    gross_dividend_amount: float,
) -> float | None:
    """Calculate dividend return as a percent of entitled invested amount.

    The eligible lots are determined from holdings outstanding before the
    dividend record date using FIFO sell matching.

    If the entitled quantity differs from the outstanding quantity snapshot,
    the open lots are scaled proportionally to the entitled quantity.
    """
    if entitled_qty <= 0 or gross_dividend_amount <= 0:
        return None

    entitled_lots = _build_entitled_lots(
        transaction_rows, record_dt, entitled_qty
    )
    if entitled_lots is None:
        return None

    entitled_investment = 0.0
    for lot in entitled_lots:
        lot_cost = float(lot["allocated_qty"]) * float(lot["cost_per_share"])
        entitled_investment += lot_cost

    if entitled_investment <= 0:
        return None

    return gross_dividend_amount * 100.0 / entitled_investment


def calculate_annualized_dividend_yield(
    transaction_rows,
    record_dt: str,
    credit_dt: str,
    entitled_qty: int,
    gross_dividend_amount: float,
) -> float | None:
    """Calculate annualized dividend yield using lot-weighted capital-days."""
    if gross_dividend_amount <= 0:
        return None

    entitled_lots = _build_entitled_lots(
        transaction_rows, record_dt, entitled_qty
    )
    if entitled_lots is None:
        return None

    record_date = _parse_iso_trade_date(record_dt)
    credit_date = _parse_iso_trade_date(credit_dt)
    if record_date is None or credit_date is None or credit_date < record_date:
        return None

    capital_day_cost = 0.0
    for lot in entitled_lots:
        holding_days = (credit_date - lot["trade_date"]).days
        if holding_days <= 0:
            continue
        lot_cost = float(lot["allocated_qty"]) * float(lot["cost_per_share"])
        capital_day_cost += lot_cost * holding_days

    if capital_day_cost <= 0:
        return None

    return gross_dividend_amount * 365.0 * 100.0 / capital_day_cost


def calculate_dividend_holding_days(
    transaction_rows,
    record_dt: str,
    credit_dt: str,
    entitled_qty: int,
) -> float | None:
    """Calculate lot-cost-weighted holding days for an entitled dividend."""
    entitled_lots = _build_entitled_lots(
        transaction_rows, record_dt, entitled_qty
    )
    if entitled_lots is None:
        return None

    record_date = _parse_iso_trade_date(record_dt)
    credit_date = _parse_iso_trade_date(credit_dt)
    if record_date is None or credit_date is None or credit_date < record_date:
        return None

    total_cost = 0.0
    capital_day_cost = 0.0
    for lot in entitled_lots:
        holding_days = (credit_date - lot["trade_date"]).days
        if holding_days <= 0:
            continue
        lot_cost = float(lot["allocated_qty"]) * float(lot["cost_per_share"])
        total_cost += lot_cost
        capital_day_cost += lot_cost * holding_days

    if total_cost <= 0 or capital_day_cost <= 0:
        return None

    return capital_day_cost / total_cost


def compute_dividend_return_percent(
    id_stk: int,
    record_dt: str,
    entitled_qty: int,
    gross_dividend_amount: float,
    cursor: sqlite3.Cursor | None = None,
) -> float | None:
    """Fetch transactions for a stock and compute dividend return percent."""

    def _compute(cur: sqlite3.Cursor) -> float | None:
        cur.execute(
            """
            SELECT trd_dt, trade_type_trd, qty_trd, net_amt_trd
            FROM transactions
            WHERE id_stk = ? AND trd_dt < ?
            ORDER BY trd_dt ASC, id_trd ASC
            """,
            (id_stk, record_dt),
        )
        return calculate_dividend_return_percent(
            cur.fetchall(),
            record_dt,
            entitled_qty,
            gross_dividend_amount,
        )

    try:
        if cursor is not None:
            return _compute(cursor)

        with get_db_connection() as conn:
            return _compute(conn.cursor())
    except sqlite3.Error as exc:
        logger.error(
            "Failed to compute dividend return percent for stock %s: %s",
            id_stk,
            exc,
        )
        return None


def compute_dividend_annualized_yield(
    id_stk: int,
    record_dt: str,
    credit_dt: str,
    entitled_qty: int,
    gross_dividend_amount: float,
    cursor: sqlite3.Cursor | None = None,
) -> float | None:
    """Fetch transactions for a stock and compute annualized dividend yield."""

    def _compute(cur: sqlite3.Cursor) -> float | None:
        cur.execute(
            """
            SELECT trd_dt, trade_type_trd, qty_trd, net_amt_trd
            FROM transactions
            WHERE id_stk = ? AND trd_dt < ?
            ORDER BY trd_dt ASC, id_trd ASC
            """,
            (id_stk, record_dt),
        )
        return calculate_annualized_dividend_yield(
            cur.fetchall(),
            record_dt,
            credit_dt,
            entitled_qty,
            gross_dividend_amount,
        )

    try:
        if cursor is not None:
            return _compute(cursor)

        with get_db_connection() as conn:
            return _compute(conn.cursor())
    except sqlite3.Error as exc:
        logger.error(
            "Failed to compute dividend annualized yield for stock %s: %s",
            id_stk,
            exc,
        )
        return None


def compute_dividend_holding_days(
    id_stk: int,
    record_dt: str,
    credit_dt: str,
    entitled_qty: int,
    cursor: sqlite3.Cursor | None = None,
) -> float | None:
    """Fetch transactions for a stock and compute weighted holding days."""

    def _compute(cur: sqlite3.Cursor) -> float | None:
        cur.execute(
            """
            SELECT trd_dt, trade_type_trd, qty_trd, net_amt_trd
            FROM transactions
            WHERE id_stk = ? AND trd_dt < ?
            ORDER BY trd_dt ASC, id_trd ASC
            """,
            (id_stk, record_dt),
        )
        return calculate_dividend_holding_days(
            cur.fetchall(),
            record_dt,
            credit_dt,
            entitled_qty,
        )

    try:
        if cursor is not None:
            return _compute(cursor)

        with get_db_connection() as conn:
            return _compute(conn.cursor())
    except sqlite3.Error as exc:
        logger.error(
            "Failed to compute dividend holding days for stock %s: %s",
            id_stk,
            exc,
        )
        return None


def process_allotment(id_allot: int, cursor=None) -> None:
    """
    Generates the corresponding contract, transaction, and bank entries
    for a successful primary offer allotment.
    """
    import datetime

    def _execute_logic(cur):
        # 1. Fetch the allotment and related offer/stock details
        cur.execute(
            """
            SELECT o.id_stk, o.allotted_qty, o.allotted_amt, o.allotment_dt,
                   o.exchange, s.company_name, o.tx_id, o.id_comp_bt
            FROM offer_allotments o
            JOIN stocks s ON o.id_stk = s.id_stk
            WHERE o.id_allot = ?
        """,
            (id_allot,),
        )

        row = cur.fetchone()
        if not row:
            return

        (
            id_stk,
            allotted_qty,
            allotted_amt,
            allotment_dt,
            exchange,
            company_name,
            tx_id,
            id_comp_bt,
        ) = row

        # 2. Only process if shares were allotted and no transaction exists yet
        if allotted_qty > 0 and tx_id is None:
            cont_no = f"PO_{id_allot}"
            settle_no = int(f"111{id_allot}")
            a_dt = (
                allotment_dt
                if allotment_dt
                else datetime.date.today().strftime("%Y-%m-%d")
            )
            price = allotted_amt / allotted_qty if allotted_qty > 0 else 0

            # Insert Contract
            cur.execute(
                """
                INSERT INTO contracts (cont_no, trd_dt, settle_no, settle_dt, no_of_trades, net_amt_cont, net_amt_cont_applicable)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    cont_no,
                    a_dt,
                    settle_no,
                    a_dt,
                    1,
                    allotted_amt,
                    allotted_amt,
                ),
            )

            # Insert Transaction
            cur.execute(
                """
                INSERT INTO transactions (
                    id_stk, cont_no, trd_dt, company_name, trade_type_trd, exchange,
                    qty_trd, wap_unit_trd, price_lot_trd, net_amt_trd, net_amt_trd_applicable, note_trd
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    id_stk,
                    cont_no,
                    a_dt,
                    company_name,
                    "BUY",
                    exchange or "NSE",
                    allotted_qty,
                    price,
                    allotted_amt,
                    allotted_amt,
                    allotted_amt,
                    "Primary Offer Allotment",
                ),
            )
            new_tx_id = cur.lastrowid

            # Insert Bank Record
            if id_comp_bt is None:
                cur.execute(
                    """
                    INSERT INTO computed_bank (
                        cont_no,
                        comp_bt_dt,
                        comp_bt_type,
                        comp_bt_amt,
                        comp_bt_amt_applicable,
                        comp_bt_desc
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        cont_no,
                        a_dt,
                        "DEBIT",
                        allotted_amt,
                        allotted_amt,
                        "Primary Offer Allotment",
                    ),
                )
                id_comp_bt = cur.lastrowid

            # Update Allotment Links
            cur.execute(
                """
                UPDATE offer_allotments
                SET tx_id = ?, cont_no = ?, id_comp_bt = ?
                WHERE id_allot = ?
            """,
                (new_tx_id, cont_no, id_comp_bt, id_allot),
            )

    # Execute using the provided cursor, or open a new connection if none provided
    try:
        if cursor:
            _execute_logic(cursor)
        else:
            with get_db_connection() as conn:
                cur = conn.cursor()
                _execute_logic(cur)
                conn.commit()
    except Exception as e:
        logger.error(
            "Failed to process allotment %s: %s",
            id_allot,
            e,
            exc_info=True,
        )
        raise


def select_trade_from_list(
    parent_win: Union[tk.Toplevel, tk.Tk],
    title: str,
    bg_color: str,
    heading_bg: str,
    button_text: str = "Select",
    include_zero_net: bool = False,
) -> int | None:
    """
    Displays a modal window to select a trade from a list.

    Returns:
        The selected trade's id_trd, or None if no trade was selected.
    """
    selected_trade_id = [None]

    # --- Colors ---
    odd_row_bg = "#f0f9ff"
    even_row_bg = "white"
    select_btn_bg = "#22c55e"
    select_btn_active_bg = "#16a34a"
    select_btn_focus_bg = "#2563eb"
    cancel_btn_bg = "#ef4444"
    cancel_btn_active_bg = "#b91c1c"

    sel_win = tk.Toplevel(parent_win)
    sel_win.title(title)
    sel_win.geometry("950x550")
    sel_win.configure(bg=bg_color)
    sel_win.transient(parent_win)
    sel_win.grab_set()

    style = ttk.Style(sel_win)
    style.theme_use("clam")
    style.configure(
        "Treeview.Heading",
        background=heading_bg,
        foreground="white",
        font=("Helvetica", 12, "bold"),
    )
    style.configure("Treeview", rowheight=30, font=("Helvetica", 11))

    tree_frame = ttk.Frame(sel_win, padding="10")
    tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

    cols = ("ID", "Date", "Contract", "Company", "Type", "Qty", "Net Amount")
    tree = ttk.Treeview(tree_frame, columns=cols, show="headings")

    for col in cols:
        tree.heading(col, text=col, command=lambda _c=col: universal_tree_sort(tree, _c, False))
        tree.column(col, width=120, anchor="center")
    tree.column("ID", width=60, anchor="e")
    tree.column("Company", width=250, anchor="w")
    tree.column("Net Amount", width=140, anchor="e")

    tree.tag_configure("oddrow", background=odd_row_bg)
    tree.tag_configure("evenrow", background=even_row_bg)

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if include_zero_net:
                query = """
                    SELECT t.id_trd, t.trd_dt, t.cont_no, s.company_name, t.trade_type_trd, t.qty_trd, t.net_amt_trd
                    FROM transactions t JOIN stocks s ON t.id_stk = s.id_stk
                    ORDER BY t.trd_dt DESC, t.id_trd DESC
                """
            else:
                query = """
                    SELECT t.id_trd, t.trd_dt, t.cont_no, s.company_name, t.trade_type_trd, t.qty_trd, t.net_amt_trd
                    FROM transactions t JOIN stocks s ON t.id_stk = s.id_stk
                    WHERE t.net_amt_trd IS NOT NULL AND t.net_amt_trd != 0
                    ORDER BY t.trd_dt DESC, t.id_trd DESC
                """

            cursor.execute(query)
            for i, row in enumerate(cursor.fetchall()):
                tree.insert(
                    "",
                    "end",
                    values=row,
                    tags=("oddrow" if i % 2 else "evenrow",),
                )
    except sqlite3.Error as e:
        show_colorful_error(
            sel_win, "Database Error", f"Could not fetch trades: {e}"
        )
        sel_win.destroy()
        return None

    scrollbar = ttk.Scrollbar(
        tree_frame, orient="vertical", command=tree.yview
    )
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    btn_frame = tk.Frame(sel_win, bg=bg_color)
    btn_frame.pack(fill="x", padx=10, pady=(0, 10))

    def on_select():
        selected_item = tree.focus()
        if selected_item:
            selected_trade_id[0] = tree.item(selected_item)["values"][0]
            sel_win.destroy()

    def on_cancel(_event=None):
        sel_win.destroy()

    def on_select_focus_in(_event):
        select_btn.config(bg=select_btn_focus_bg)

    def on_select_focus_out(_event):
        select_btn.config(bg=select_btn_bg)

    def on_cancel_focus_in(_event):
        cancel_btn.config(bg=select_btn_focus_bg)

    def on_cancel_focus_out(_event):
        cancel_btn.config(bg=cancel_btn_bg)

    cancel_btn = tk.Button(
        btn_frame,
        text="Cancel",
        command=on_cancel,
        bg=cancel_btn_bg,
        fg="white",
        activebackground=cancel_btn_active_bg,
        font=("Helvetica", 12, "bold"),
        relief="raised",
        bd=2,
        padx=10,
    )
    cancel_btn.pack(side="right", padx=5)

    select_btn = tk.Button(
        btn_frame,
        text=button_text,
        command=on_select,
        bg=select_btn_bg,
        fg="white",
        activebackground=select_btn_active_bg,
        font=("Helvetica", 12, "bold"),
        relief="raised",
        bd=2,
        padx=10,
    )
    select_btn.pack(side="right", padx=5)

    tree.bind("<Double-1>", lambda e: on_select())
    tree.bind("<Return>", lambda e: on_select())
    sel_win.bind("<Escape>", on_cancel)
    select_btn.bind("<FocusIn>", on_select_focus_in)
    select_btn.bind("<FocusOut>", on_select_focus_out)
    cancel_btn.bind("<FocusIn>", on_cancel_focus_in)
    cancel_btn.bind("<FocusOut>", on_cancel_focus_out)

    children = tree.get_children()
    if children:
        tree.focus(children[0])
        tree.selection_set(children[0])
    tree.focus_set()

    parent_win.wait_window(sel_win)
    return selected_trade_id[0]


def select_company_from_list(
    parent_win: Union[tk.Toplevel, tk.Tk], button_text: str = "Select"
) -> tuple[int | None, str | None]:
    """
    Displays a modal window to select a company from a list.

    Returns:
        A tuple containing the selected company's (id_stk, company_name),
        or (None, None) if no company was selected.
    """
    selected_company = [None, None]
    win_bg = "#fff5f5"
    tree_heading_bg = "#991b1b"
    odd_row_bg = "#fee2e2"
    even_row_bg = "white"
    select_btn_bg = "#ef4444"
    select_btn_active_bg = "#b91c1c"
    select_btn_focus_bg = "#2563eb"  # Blue
    cancel_btn_bg = "#6b7280"

    sel_win = tk.Toplevel(parent_win)
    sel_win.title("Select Company to Remove")
    sel_win.geometry("750x500")
    sel_win.configure(bg=win_bg)
    sel_win.transient(parent_win)
    sel_win.grab_set()

    style = ttk.Style(sel_win)
    style.theme_use("clam")
    style.configure(
        "Treeview.Heading",
        background=tree_heading_bg,
        foreground="white",
        font=("Helvetica", 12, "bold"),
    )
    style.configure("Treeview", rowheight=30, font=("Helvetica", 11))

    tree_frame = ttk.Frame(sel_win, padding="10")
    tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

    cols = ("ID", "Company Name", "ISIN")
    tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
    for col, text in [("ID", "ID"), ("Company Name", "Company Name"), ("ISIN", "ISIN")]:
        tree.heading(col, text=text, command=lambda _c=col: universal_tree_sort(tree, _c, False))
    tree.column("ID", width=60, anchor="e")
    tree.column("Company Name", width=400, anchor="w")
    tree.column("ISIN", width=150, anchor="center")

    tree.tag_configure("oddrow", background=odd_row_bg)
    tree.tag_configure("evenrow", background=even_row_bg)

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id_stk, company_name, isin FROM stocks ORDER BY company_name ASC"
            )
            for i, row in enumerate(cursor.fetchall()):
                tree.insert(
                    "",
                    "end",
                    values=row,
                    tags=("oddrow" if i % 2 else "evenrow",),
                )
    except sqlite3.Error as e:
        show_colorful_error(
            sel_win, "Database Error", f"Could not fetch companies: {e}"
        )
        sel_win.destroy()
        return None, None

    scrollbar = ttk.Scrollbar(
        tree_frame, orient="vertical", command=tree.yview
    )
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    btn_frame = tk.Frame(sel_win, bg=win_bg)
    btn_frame.pack(fill="x", padx=10, pady=(0, 10))

    def on_select():
        selected_item = tree.focus()
        if selected_item:
            values = tree.item(selected_item)["values"]
            selected_company[0] = values[0]
            selected_company[1] = values[1]
            sel_win.destroy()

    def on_cancel(_event=None):
        sel_win.destroy()

    def on_select_focus_in(_event):
        select_btn.config(bg=select_btn_focus_bg)

    def on_select_focus_out(_event):
        select_btn.config(bg=select_btn_bg)

    def on_cancel_focus_in(_event):
        cancel_btn.config(bg=select_btn_focus_bg)

    def on_cancel_focus_out(_event):
        cancel_btn.config(bg=cancel_btn_bg)

    cancel_btn = tk.Button(
        btn_frame,
        text="Cancel",
        command=on_cancel,
        bg=cancel_btn_bg,
        fg="white",
        activebackground="#4b5563",
        font=("Helvetica", 12, "bold"),
        relief="raised",
        bd=2,
        padx=10,
    )
    cancel_btn.pack(side="right", padx=5)

    select_btn = tk.Button(
        btn_frame,
        text=button_text,
        command=on_select,
        bg=select_btn_bg,
        fg="white",
        activebackground=select_btn_active_bg,
        font=("Helvetica", 12, "bold"),
        relief="raised",
        bd=2,
        padx=10,
    )
    select_btn.pack(side="right", padx=5)

    tree.bind("<Double-1>", lambda e: on_select())
    tree.bind("<Return>", lambda e: on_select())
    sel_win.bind("<Escape>", on_cancel)
    select_btn.bind("<FocusIn>", on_select_focus_in)
    select_btn.bind("<FocusOut>", on_select_focus_out)
    cancel_btn.bind("<FocusIn>", on_cancel_focus_in)
    cancel_btn.bind("<FocusOut>", on_cancel_focus_out)

    children = tree.get_children()
    if children:
        tree.focus(children[0])
        tree.selection_set(children[0])
    tree.focus_set()

    parent_win.wait_window(sel_win)
    return selected_company[0], selected_company[1]


def revert_sell_allocation(
    sell_trd_id: int,
    cursor: sqlite3.Cursor | None = None,
    poke: bool = True,
    raise_on_error: bool = False,
) -> bool:
    """
    Reverts the sell allocation for a given sell transaction.
    """

    def _execute(cur: sqlite3.Cursor) -> None:
        cur.execute(
            "SELECT buy_id_trd, sell_qty FROM sell_records WHERE sell_id_trd = ?",
            (sell_trd_id,),
        )
        allocations = cur.fetchall()

        if not allocations:
            return

        for buy_id_trd, sold_qty in allocations:
            cur.execute(
                "UPDATE transactions SET sold_qty = sold_qty - ? WHERE id_trd = ?",
                (sold_qty, buy_id_trd),
            )

        cur.execute(
            "DELETE FROM sell_records WHERE sell_id_trd = ?",
            (sell_trd_id,),
        )

    try:
        if cursor is not None:
            _execute(cursor)
            logger.info(
                "Reverted sell allocation for sell_trd_id: %s", sell_trd_id
            )
            return True

        with get_db_connection() as conn:
            local_cursor = conn.cursor()
            _execute(local_cursor)
            conn.commit()
            logger.info(
                "Reverted sell allocation for sell_trd_id: %s", sell_trd_id
            )
            return True
    except sqlite3.Error as e:
        if poke:
            show_colorful_error(
                None,
                "Revert Sell Error",
                f"Failed to revert sell allocation: {e}",
            )
        logger.error(
            "Failed to revert sell allocation for sell_trd_id: %s. Error: %s",
            sell_trd_id,
            e,
        )
        if raise_on_error:
            raise ValueError(
                f"Failed to revert sell allocation for trade {sell_trd_id}: {e}"
            ) from e
        return False


def manage_sell(
    sell_trd_id: int,
    poke: bool = True,
    cursor: sqlite3.Cursor | None = None,
    raise_on_error: bool = False,
) -> bool:
    """
    Handles sell transaction logic using FIFO matching.
    Args:
        sell_trd_id: ID of the sell transaction in transactions table
        poke: If True, shows UI message boxes. If False, runs silently.
    """
    connection: sqlite3.Connection | None = None
    active_cursor: sqlite3.Cursor | None = cursor
    owns_connection = cursor is None

    try:
        if owns_connection:
            connection = get_db_connection()
            active_cursor = connection.cursor()

        if active_cursor is None:
            return False

        # Fetch sell transaction details
        active_cursor.execute(
            """
            SELECT id_stk, trd_dt, qty_trd, net_amt_trd
            FROM transactions
            WHERE id_trd = ? AND trade_type_trd = 'SELL'
        """,
            (sell_trd_id,),
        )
        row = active_cursor.fetchone()
        if not row:
            message = (
                f"Sell transaction id_trd={sell_trd_id} not found "
                "or not a SELL."
            )
            if poke:
                show_colorful_error(None, "Sell Error", message)
            if raise_on_error:
                raise ValueError(message)
            return False
        # Mapping id_stk -> id_stk, trd_dt -> sell_dt,
        # qty_trd -> sell_qty, net_amt_trd -> tot_sell_value
        id_stk, sell_dt, sell_qty, tot_sell_value = row
        if sell_qty <= 0:
            message = "Sell quantity must be positive."
            if poke:
                show_colorful_error(None, "Sell Error", message)
            if raise_on_error:
                raise ValueError(message)
            return False

        avg_sell_price = tot_sell_value / sell_qty if sell_qty else 0.0

        # Check available shares
        active_cursor.execute(
            """
            SELECT SUM(qty_trd - sold_qty)
            FROM transactions
            WHERE id_stk = ? AND trade_type_trd = 'BUY' AND trd_dt <= ?
        """,
            (id_stk, sell_dt),
        )
        available_qty = active_cursor.fetchone()[0] or 0
        if sell_qty > available_qty:
            message = (
                f"Cannot sell {sell_qty} shares. "
                f"Only {available_qty} shares available."
            )
            if poke:
                show_colorful_error(None, "Sell Error", message)
            if raise_on_error:
                raise ValueError(message)
            return False

        # Get buy transactions with qty_open > 0, FIFO order,
        # and trd_dt <= sell_dt
        active_cursor.execute(
            """
            SELECT id_trd, trd_dt, net_amt_trd, qty_trd, sold_qty
            FROM transactions
            WHERE id_stk = ?
              AND trade_type_trd = 'BUY'
              AND qty_trd > sold_qty
              AND trd_dt <= ?
            ORDER BY trd_dt ASC
        """,
            (id_stk, sell_dt),
        )
        remaining_qty = sell_qty
        for (
            buy_id,
            buy_dt,
            buy_price,
            buy_qty,
            sold_qty,
        ) in active_cursor.fetchall():
            qty_open = buy_qty - sold_qty
            matched_qty = min(remaining_qty, qty_open)
            if matched_qty <= 0:
                continue

            buy_value = (buy_price / buy_qty) * matched_qty
            sell_value = avg_sell_price * matched_qty
            pnl = sell_value - buy_value
            # Log computed PnL for audit purposes (keeps variable used)
            logger.debug("Matched qty %s: pnl=%s", matched_qty, pnl)

            # Update the buy trade's sold_qty
            active_cursor.execute(
                "UPDATE transactions SET sold_qty = sold_qty + ? WHERE id_trd = ?",
                (matched_qty, buy_id),
            )

            # Record the detailed mapping
            active_cursor.execute(
                """
                INSERT INTO sell_records (
                    sell_id_trd, buy_id_trd, id_stk, sell_qty,
                    buy_dt, buy_value, sell_dt, sell_value
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    sell_trd_id,
                    buy_id,
                    id_stk,
                    matched_qty,
                    buy_dt,
                    buy_value,
                    sell_dt,
                    sell_value,
                ),
            )

            if poke:
                show_colorful_info(
                    None,
                    "Shares Sold",
                    f"Sold {matched_qty} shares from trade ID {buy_id}",
                )

            remaining_qty -= matched_qty
            if remaining_qty <= 0:
                break

        if remaining_qty > 0:
            message = (
                f"SELL trade {sell_trd_id} could not be fully allocated. "
                f"Unmatched qty: {remaining_qty}."
            )
            if poke:
                show_colorful_error(None, "Sell Error", message)
            if raise_on_error:
                raise ValueError(message)
            return False

        if owns_connection and connection is not None:
            connection.commit()
            # Keep backward-compatible behavior for standalone calls.
            compute_avg_price(id_stk, "SELL", poke=poke)

            if poke:
                show_colorful_info(
                    None,
                    "Sell Update",
                    (
                        f"All {sell_qty} shares from sell transaction "
                        f"{sell_trd_id} allocated successfully."
                    ),
                )

        return True
    except (sqlite3.Error, ValueError) as e:
        if owns_connection and connection is not None:
            connection.rollback()
        if poke:
            show_colorful_error(None, "Sell Error", str(e))
        if raise_on_error:
            raise
        return False
    finally:
        if owns_connection and connection is not None:
            connection.close()


def enforce_no_oversell_for_stock(cursor: sqlite3.Cursor, id_stk: int) -> dict:
    """
    Rebuild FIFO allocations for one stock inside the current transaction.

    Raises ValueError if any SELL cannot be fully matched to BUY inventory.
    The caller is responsible for commit/rollback.
    """
    if id_stk is None:
        raise ValueError("id_stk is required for no-over-sell enforcement")
    return _rebuild_sell_allocation_for_stock(cursor, id_stk)


def compute_avg_price(stock_id, trade_type_trd=None, poke: bool = True):
    """
    Compute the average price of a stock based on its trades.
    Compute Current Average Price,
            Disinvestment Amount,
            Realized Profit Loss Amount

    Args:
        stock_id: ID of the stock to compute average price for
        poke: If True, shows UI message boxes. If False, runs silently.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get all buy trades for the stock
            cursor.execute(
                """
                SELECT net_amt_trd, qty_trd, sold_qty FROM transactions
                WHERE id_stk = ? AND trade_type_trd = 'BUY'
            """,
                (stock_id,),
            )
            trades = cursor.fetchall()

            if not trades:
                if poke:
                    show_colorful_info(
                        None,
                        "No Buy Trades",
                        f"No buy trades found for stock ID {stock_id}.",
                    )
                return

            # Compute withdrawn amount and current investment skipping any
            # malformed rows (e.g., qty_trd == 0) to avoid ZeroDivisionError.
            withdrawn_amt = 0.0
            total_current_invest = 0.0
            total_current_qty = 0
            for net_amt_trd, qty_trd, sold_qty in trades:
                try:
                    if not qty_trd:
                        # Skip rows with zero quantity (invalid/edge-case)
                        try:
                            logger.debug(
                                "compute_avg_price: skipping trade with qty_trd=0 for stock_id=%s",
                                stock_id,
                            )
                        except Exception:
                            pass
                        continue
                    withdrawn_amt += (net_amt_trd / qty_trd) * sold_qty
                    total_current_invest += (net_amt_trd / qty_trd) * (
                        qty_trd - sold_qty
                    )
                    total_current_qty += qty_trd - sold_qty
                except Exception:
                    try:
                        logger.debug(
                            "compute_avg_price: skipping malformed row %s for stock %s",
                            (net_amt_trd, qty_trd, sold_qty),
                            stock_id,
                        )
                    except Exception:
                        pass
            if trade_type_trd == "SELL":
                if poke:
                    show_colorful_info(
                        None,
                        "Amount Recovered",
                        f"Total amount recovered from sold shares: "
                        f"{withdrawn_amt:.4f}",
                    )

            if total_current_qty == 0:
                if poke:
                    show_colorful_info(
                        None,
                        "No Quantity",
                        "No quantity available to compute average price.",
                    )
                avg_price = 0.0
            else:
                avg_price = total_current_invest / total_current_qty
                if poke:
                    show_colorful_info(
                        None,
                        "Average Price",
                        f"Average price for stock ID {stock_id}: {avg_price:.4f}",
                    )

            cursor.execute(
                "SELECT sum(net_amt_trd) FROM transactions "
                "WHERE id_stk = ? AND trade_type_trd = 'SELL'",
                (stock_id,),
            )
            amts = cursor.fetchone()
            sell_amt = amts[0] if amts and amts[0] is not None else 0.0
            if sell_amt < withdrawn_amt:
                oh_no = (
                    f"There seems to be a loss {sell_amt} is less than "
                    f"disinvestment amount {withdrawn_amt}."
                )
                if poke:
                    show_colorful_error(None, "Loss Detected", oh_no)

            cursor.execute(
                """
                UPDATE stocks
                SET curr_avg_price = ?, disinvestment_amt = ?,
                rpnl_amt = sell_amt - ?
                WHERE id_stk = ?
            """,
                (avg_price, withdrawn_amt, withdrawn_amt, stock_id),
            )
            conn.commit()

    except sqlite3.Error as e:
        if poke:
            show_colorful_error(
                None, "Error", f"Error computing average price: {e}"
            )

    if poke:
        show_colorful_info(
            None,
            "Update Complete",
            "Average, disinvestment and rpnl inserted/updated.",
        )
    return


def fetch_holding_on_date(id_stk: int, target_date_str: str) -> int:
    """Calculates holding quantity on or before a specific date."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT SUM(
                    CASE
                        WHEN trade_type_trd = 'BUY' THEN qty_trd
                        ELSE -qty_trd
                    END
                )
                FROM transactions
                WHERE id_stk = ? AND trd_dt < ?
                """,
                (id_stk, target_date_str),
            )
            result = cursor.fetchone()[0]
            return int(result) if result else 0
    except sqlite3.Error as e:
        logger.error("DB Error in fetch_holding_on_date: %s", e)
        return 0


# ---------------------------------------------------------------------------
# Central FIFO sell-allocation rebuild
# ---------------------------------------------------------------------------


def _rebuild_sell_allocation_for_stock(
    cursor: sqlite3.Cursor, id_stk: int
) -> dict:
    """
    Rebuild FIFO sell allocations from scratch for one stock.

    Steps (all within the caller's transaction):
      1. Reset sold_qty = 0 on every BUY trade for this stock.
      2. Delete all sell_records rows for this stock.
      3. Re-run FIFO matching for every SELL trade in chronological order.
      4. Raise ValueError if any SELL cannot be fully matched (caller rolls back).

    Returns a summary dict with keys:
      ``sells_rebuilt`` - number of SELL trades processed
      ``lots_matched``  - total sell_records rows inserted
    """
    # -- step 1: clear accumulated sold_qty on BUY rows --
    cursor.execute(
        "UPDATE transactions SET sold_qty = 0 WHERE id_stk = ? AND trade_type_trd = 'BUY'",
        (id_stk,),
    )

    # -- step 2: wipe existing allocation records for this stock --
    cursor.execute("DELETE FROM sell_records WHERE id_stk = ?", (id_stk,))

    # -- step 3: fetch SELL trades in strict chronological order --
    cursor.execute(
        """
        SELECT id_trd, trd_dt, qty_trd, net_amt_trd
        FROM transactions
        WHERE id_stk = ? AND trade_type_trd = 'SELL'
        ORDER BY trd_dt ASC, id_trd ASC
        """,
        (id_stk,),
    )
    sell_trades = cursor.fetchall()

    sells_rebuilt = 0
    lots_matched = 0

    for sell_id, sell_dt, sell_qty, tot_sell_value in sell_trades:
        if sell_qty <= 0:
            continue

        avg_sell_price = (tot_sell_value / sell_qty) if sell_qty else 0.0

        # check available BUY inventory up to sell date
        cursor.execute(
            """
            SELECT COALESCE(SUM(qty_trd - sold_qty), 0)
            FROM transactions
            WHERE id_stk = ? AND trade_type_trd = 'BUY' AND trd_dt <= ?
            """,
            (id_stk, sell_dt),
        )
        available = cursor.fetchone()[0] or 0
        if sell_qty > available:
            raise ValueError(
                f"SELL trade id_trd={sell_id} on {sell_dt} requires {sell_qty} shares "
                f"but only {available} are available from BUY trades on or before that date."
            )

        # FIFO: match against BUY lots oldest-first
        cursor.execute(
            """
            SELECT id_trd, trd_dt, net_amt_trd, qty_trd, sold_qty
            FROM transactions
            WHERE id_stk = ? AND trade_type_trd = 'BUY'
              AND qty_trd > sold_qty AND trd_dt <= ?
            ORDER BY trd_dt ASC, id_trd ASC
            """,
            (id_stk, sell_dt),
        )
        remaining = sell_qty
        for buy_id, buy_dt, buy_price, buy_qty, sold_qty in cursor.fetchall():
            if remaining <= 0:
                break
            qty_open = buy_qty - sold_qty
            matched = min(remaining, qty_open)
            if matched <= 0:
                continue

            buy_value = (buy_price / buy_qty) * matched
            sell_value = avg_sell_price * matched

            cursor.execute(
                "UPDATE transactions SET sold_qty = sold_qty + ? WHERE id_trd = ?",
                (matched, buy_id),
            )
            cursor.execute(
                """
                INSERT INTO sell_records
                    (sell_id_trd, buy_id_trd, id_stk, sell_qty,
                     buy_dt, buy_value, sell_dt, sell_value)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sell_id,
                    buy_id,
                    id_stk,
                    matched,
                    buy_dt,
                    buy_value,
                    sell_dt,
                    sell_value,
                ),
            )
            remaining -= matched
            lots_matched += 1

        if remaining > 0:
            # Should never reach here given the availability check above,
            # but guard defensively.
            raise ValueError(
                f"SELL trade id_trd={sell_id}: could not fully allocate "
                f"{sell_qty} shares ({remaining} unmatched)."
            )

        sells_rebuilt += 1

    return {"sells_rebuilt": sells_rebuilt, "lots_matched": lots_matched}


def rebuild_sell_allocations(
    stock_ids: list[int] | None = None,
) -> dict:
    """
    Central FIFO sell-allocation reconciler.

    Rebuilds sell allocations from scratch for each requested stock inside
    an isolated per-stock transaction. On failure for one stock the
    transaction is rolled back and that stock is recorded as failed;
    processing continues for the remaining stocks.

    Args:
        stock_ids: List of ``id_stk`` values to process, or ``None`` to
                   process every stock that has at least one SELL trade.

    Returns a dict with:
      ``processed`` - list of dicts, one per succeeded stock
                      (keys: id_stk, company_name, sells_rebuilt, lots_matched)
      ``failed``    - list of dicts, one per failed stock
                      (keys: id_stk, company_name, error)
    """
    processed: list[dict] = []
    failed: list[dict] = []

    try:
        with get_db_connection() as meta_conn:
            meta_cursor = meta_conn.cursor()

            if stock_ids is None:
                # All stocks that have at least one SELL trade
                meta_cursor.execute("""
                    SELECT DISTINCT t.id_stk, s.company_name
                    FROM transactions t
                    JOIN stocks s ON s.id_stk = t.id_stk
                    WHERE t.trade_type_trd = 'SELL'
                    ORDER BY s.company_name ASC
                    """)
            else:
                if not stock_ids:
                    return {"processed": [], "failed": []}
                placeholders = ",".join("?" * len(stock_ids))
                meta_cursor.execute(
                    f"""
                    SELECT DISTINCT t.id_stk, s.company_name
                    FROM transactions t
                    JOIN stocks s ON s.id_stk = t.id_stk
                    WHERE t.trade_type_trd = 'SELL'
                      AND t.id_stk IN ({placeholders})
                    ORDER BY s.company_name ASC
                    """,
                    stock_ids,
                )

            targets = meta_cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(
            "rebuild_sell_allocations: failed to fetch stock list: %s", e
        )
        return {
            "processed": [],
            "failed": [
                {"id_stk": None, "company_name": None, "error": str(e)}
            ],
        }

    for id_stk, company_name in targets:
        try:
            with get_db_connection() as conn:
                conn.execute("PRAGMA foreign_keys = ON;")
                cursor = conn.cursor()
                summary = _rebuild_sell_allocation_for_stock(cursor, id_stk)
                conn.commit()

            # Recompute portfolio averages for this stock (silent)
            compute_avg_price(id_stk, poke=False)

            processed.append(
                {
                    "id_stk": id_stk,
                    "company_name": company_name,
                    "sells_rebuilt": summary["sells_rebuilt"],
                    "lots_matched": summary["lots_matched"],
                }
            )
            logger.info(
                "rebuild_sell_allocations: rebuilt stock %s (%s): %d sells, %d lots",
                id_stk,
                company_name,
                summary["sells_rebuilt"],
                summary["lots_matched"],
            )
        except (sqlite3.Error, ValueError) as e:
            failed.append(
                {
                    "id_stk": id_stk,
                    "company_name": company_name,
                    "error": str(e),
                }
            )
            logger.error(
                "rebuild_sell_allocations: failed for stock %s (%s): %s",
                id_stk,
                company_name,
                e,
            )

    return {"processed": processed, "failed": failed}


def select_stocks_for_sell_management(
    parent_win: Union[tk.Toplevel, tk.Tk],
) -> list[int] | None:
    """
    Modal multi-select Treeview showing stocks with SELL trades.

    Columns: Company, ISIN, Current Qty, SELL Trades
    Returns a list of selected ``id_stk`` values, or ``None`` if cancelled.
    """
    selected_ids: list[int] = []
    win_bg = "#f0fdf4"
    heading_bg = "#15803d"
    odd_row_bg = "#dcfce7"
    even_row_bg = "white"
    select_btn_bg = "#22c55e"
    select_btn_active_bg = "#16a34a"
    select_btn_focus_bg = "#2563eb"
    cancel_btn_bg = "#6b7280"

    sel_win = tk.Toplevel(parent_win)
    sel_win.title("Select Stock(s) for Sell Management")
    sel_win.geometry("820x500")
    sel_win.configure(bg=win_bg)
    sel_win.transient(parent_win)
    sel_win.grab_set()

    style = ttk.Style(sel_win)
    style.theme_use("clam")
    style.configure(
        "Treeview.Heading",
        background=heading_bg,
        foreground="white",
        font=("Helvetica", 12, "bold"),
    )
    style.configure("Treeview", rowheight=30, font=("Helvetica", 11))

    info_lbl = tk.Label(
        sel_win,
        text="Hold Ctrl or Shift to select multiple stocks.",
        bg=win_bg,
        font=("Helvetica", 11, "italic"),
        fg="#374151",
    )
    info_lbl.pack(anchor="w", padx=14, pady=(8, 0))

    tree_frame = ttk.Frame(sel_win, padding="10")
    tree_frame.pack(fill="both", expand=True, padx=10, pady=4)

    cols = ("id_stk", "Company", "ISIN", "Current Qty", "SELL Trades")
    tree = ttk.Treeview(
        tree_frame, columns=cols, show="headings", selectmode="extended"
    )
    for col, text in [
        ("id_stk", "ID"),
        ("Company", "Company"),
        ("ISIN", "ISIN"),
        ("Current Qty", "Curr Qty"),
        ("SELL Trades", "SELL Trades"),
    ]:
        tree.heading(col, text=text, command=lambda _c=col: universal_tree_sort(tree, _c, False))
    tree.column("id_stk", width=50, anchor="e")
    tree.column("Company", width=320, anchor="w")
    tree.column("ISIN", width=140, anchor="center")
    tree.column("Current Qty", width=90, anchor="e")
    tree.column("SELL Trades", width=110, anchor="e")

    tree.tag_configure("oddrow", background=odd_row_bg)
    tree.tag_configure("evenrow", background=even_row_bg)

    # id_stk is hidden in col 0 of values — we read it back on submit
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.id_stk, s.company_name, s.isin,
                       s.current_qty,
                       COUNT(t.id_trd) AS sell_count
                FROM stocks s
                JOIN transactions t ON t.id_stk = s.id_stk
                WHERE t.trade_type_trd = 'SELL'
                GROUP BY s.id_stk
                ORDER BY s.company_name ASC
                """)
            for i, row in enumerate(cursor.fetchall()):
                tree.insert(
                    "",
                    "end",
                    values=row,
                    tags=("oddrow" if i % 2 else "evenrow",),
                )
    except sqlite3.Error as e:
        show_colorful_error(
            sel_win, "Database Error", f"Could not fetch stocks: {e}"
        )
        sel_win.destroy()
        return None

    scrollbar = ttk.Scrollbar(
        tree_frame, orient="vertical", command=tree.yview
    )
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    btn_frame = tk.Frame(sel_win, bg=win_bg)
    btn_frame.pack(fill="x", padx=10, pady=(0, 10))

    cancelled = [False]

    def on_select():
        items = tree.selection()
        if not items:
            show_colorful_error(
                sel_win, "No Selection", "Please select at least one stock."
            )
            return
        for item in items:
            selected_ids.append(tree.item(item)["values"][0])
        sel_win.destroy()

    def on_cancel(_event=None):
        cancelled[0] = True
        sel_win.destroy()

    def on_select_focus_in(_e):
        select_btn.config(bg=select_btn_focus_bg)

    def on_select_focus_out(_e):
        select_btn.config(bg=select_btn_bg)

    def on_cancel_focus_in(_e):
        cancel_btn.config(bg=select_btn_focus_bg)

    def on_cancel_focus_out(_e):
        cancel_btn.config(bg=cancel_btn_bg)

    cancel_btn = tk.Button(
        btn_frame,
        text="Cancel",
        command=on_cancel,
        bg=cancel_btn_bg,
        fg="white",
        activebackground="#4b5563",
        font=("Helvetica", 12, "bold"),
        relief="raised",
        bd=2,
        padx=10,
    )
    cancel_btn.pack(side="right", padx=5)

    select_btn = tk.Button(
        btn_frame,
        text="Select",
        command=on_select,
        bg=select_btn_bg,
        fg="white",
        activebackground=select_btn_active_bg,
        font=("Helvetica", 12, "bold"),
        relief="raised",
        bd=2,
        padx=10,
    )
    select_btn.pack(side="right", padx=5)

    tree.bind("<Return>", lambda e: on_select())
    sel_win.bind("<Escape>", on_cancel)
    select_btn.bind("<FocusIn>", on_select_focus_in)
    select_btn.bind("<FocusOut>", on_select_focus_out)
    cancel_btn.bind("<FocusIn>", on_cancel_focus_in)
    cancel_btn.bind("<FocusOut>", on_cancel_focus_out)

    children = tree.get_children()
    if children:
        tree.focus(children[0])
        tree.selection_set(children[0])
    tree.focus_set()

    parent_win.wait_window(sel_win)
    return None if cancelled[0] else selected_ids


# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\trade_utils.py ends here
