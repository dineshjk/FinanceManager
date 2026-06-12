# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\sell_management.py

"""
sell_management.py
------------------

Central FIFO sell-management UI for StockMan.

Provides a two-mode workflow:
  - All Stocks: rebuild FIFO allocations for every stock with SELL trades.
  - Select Stock(s): let the user pick one or more stocks, then rebuild.

Entry point: ``show_sell_management_modal(parent)``
"""

from typing import Union
import tkinter as tk

from Shared.globals import logger
from Shared.dialog_utils import (
    show_colorful_error,
    show_colorful_info,
    show_colorful_yesno,
)
from .trade_utils import (
    rebuild_sell_allocations,
    select_stocks_for_sell_management,
)
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window

# ---------------------------------------------------------------------------
# Result summary dialog
# ---------------------------------------------------------------------------


def _show_result_summary(
    parent_win: Union[tk.Toplevel, tk.Tk],
    result: dict,
) -> None:
    """Display a scrollable summary of rebuild outcomes."""
    processed = result.get("processed", [])
    failed = result.get("failed", [])

    win_bg = "#f0fdf4"
    win = tk.Toplevel(parent_win)
    win.title("Sell Management – Result Summary")
    win.geometry("700x480")
    win.configure(bg=win_bg)
    win.transient(parent_win)
    win.grab_set()

    # Header
    header_text = (
        f"Completed: {len(processed)} stock(s) rebuilt successfully"
        + (f", {len(failed)} failed." if failed else ".")
    )
    tk.Label(
        win,
        text=header_text,
        bg=win_bg,
        font=("Helvetica", 13, "bold"),
        fg="#15803d" if not failed else "#b45309",
        wraplength=660,
        justify="left",
    ).pack(anchor="w", padx=14, pady=(12, 4))

    # Scrollable text area
    frame = tk.Frame(win, bg=win_bg)
    frame.pack(fill="both", expand=True, padx=14, pady=(0, 8))

    sb = tk.Scrollbar(frame)
    sb.pack(side="right", fill="y")

    text = tk.Text(
        frame,
        font=("Courier New", 11),
        bg="white",
        relief="solid",
        bd=1,
        yscrollcommand=sb.set,
        state="normal",
        wrap="word",
    )
    text.pack(side="left", fill="both", expand=True)
    sb.config(command=text.yview)

    if processed:
        text.insert("end", "──── Rebuilt Successfully ────\n", "heading")
        for row in processed:
            text.insert(
                "end",
                f"  ✓  {row['company_name']}"
                f"  |  {row['sells_rebuilt']} SELL trade(s)"
                f"  |  {row['lots_matched']} lot(s) matched\n",
                "ok",
            )

    if failed:
        text.insert("end", "\n──── Failed ────\n", "heading")
        for row in failed:
            name = row.get("company_name") or "(unknown)"
            text.insert(
                "end",
                f"  ✗  {name}  –  {row['error']}\n",
                "err",
            )

    text.tag_configure(
        "heading", font=("Helvetica", 11, "bold"), foreground="#1e40af"
    )
    text.tag_configure("ok", foreground="#15803d")
    text.tag_configure("err", foreground="#b91c1c")
    text.config(state="disabled")

    ok_btn = tk.Button(
        win,
        text="OK",
        command=win.destroy,
        bg="#22c55e",
        fg="white",
        activebackground="#16a34a",
        font=("Helvetica", 12, "bold"),
        relief="raised",
        bd=2,
        padx=20,
    )
    ok_btn.pack(pady=(0, 14))
    ok_btn.focus_set()
    win.bind("<Return>", lambda _e: win.destroy())
    win.bind("<Escape>", lambda _e: win.destroy())

    parent_win.wait_window(win)


# ---------------------------------------------------------------------------
# Mode selection dialog
# ---------------------------------------------------------------------------


def _show_mode_selection(
    parent_win: Union[tk.Toplevel, tk.Tk],
) -> str | None:
    """
    Ask the user whether to process all stocks or select specific ones.

    Returns ``"all"``, ``"select"``, or ``None`` (cancelled).
    """
    choice = [None]
    win_bg = "#fefce8"

    mode_win = tk.Toplevel(parent_win)
    mode_win.title("Sell Management – Choose Mode")
    mode_win.geometry("460x220")
    mode_win.configure(bg=win_bg)
    mode_win.resizable(False, False)
    mode_win.transient(parent_win)
    mode_win.grab_set()

    tk.Label(
        mode_win,
        text="FIFO Sell Management",
        bg=win_bg,
        font=("Helvetica", 15, "bold"),
        fg="#92400e",
    ).pack(pady=(18, 4))

    tk.Label(
        mode_win,
        text="Rebuild sell allocations for:",
        bg=win_bg,
        font=("Helvetica", 12),
        fg="#374151",
    ).pack(pady=(0, 12))

    btn_frame = tk.Frame(mode_win, bg=win_bg)
    btn_frame.pack(pady=4)

    def pick(val):
        choice[0] = val
        mode_win.destroy()

    tk.Button(
        btn_frame,
        text="All Stocks",
        width=18,
        command=lambda: pick("all"),
        bg="#f59e0b",
        fg="white",
        activebackground="#d97706",
        font=("Helvetica", 12, "bold"),
        relief="raised",
        bd=2,
    ).grid(row=0, column=0, padx=8)

    tk.Button(
        btn_frame,
        text="Select Stock(s)",
        width=18,
        command=lambda: pick("select"),
        bg="#3b82f6",
        fg="white",
        activebackground="#2563eb",
        font=("Helvetica", 12, "bold"),
        relief="raised",
        bd=2,
    ).grid(row=0, column=1, padx=8)

    tk.Button(
        mode_win,
        text="Cancel",
        width=12,
        command=mode_win.destroy,
        bg="#6b7280",
        fg="white",
        activebackground="#4b5563",
        font=("Helvetica", 11),
        relief="raised",
        bd=2,
    ).pack(pady=(14, 0))

    mode_win.bind("<Escape>", lambda _e: mode_win.destroy())
    parent_win.wait_window(mode_win)
    return choice[0]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def show_sell_management_modal(
    parent: Union[tk.Toplevel, tk.Tk],
) -> None:
    """
    Full sell-management workflow.

    1. Show mode selector (All / Select).
    2. For Select mode, show multi-stock picker.
    3. Confirm before running.
    4. Execute rebuild and display summary.
    """
    modal_id = disable_parent(parent)

    try:
        mode = _show_mode_selection(parent)
        if mode is None:
            return

        stock_ids: list[int] | None = None  # None → all stocks

        if mode == "select":
            stock_ids = select_stocks_for_sell_management(parent)
            if stock_ids is None:  # user cancelled picker
                return
            if not stock_ids:
                show_colorful_error(
                    parent,
                    "No Stocks Selected",
                    "No stocks were selected. Operation cancelled.",
                )
                return

        # Confirmation prompt
        if stock_ids is None:
            confirm_msg = (
                "This will rebuild FIFO sell allocations for ALL stocks "
                "that have SELL trades.\n\n"
                "The operation is safe and transactional per stock, but may "
                "take a moment for large portfolios.\n\n"
                "Proceed?"
            )
        else:
            names_preview = ", ".join(str(sid) for sid in stock_ids[:5])
            if len(stock_ids) > 5:
                names_preview += f" … (+{len(stock_ids) - 5} more)"
            confirm_msg = (
                f"Rebuild FIFO sell allocations for {len(stock_ids)} "
                f"selected stock(s) [{names_preview}]?\n\n"
                "Proceed?"
            )

        if not show_colorful_yesno(
            parent, "Confirm Sell Management", confirm_msg
        ):
            return

        logger.info(
            "sell_management: starting rebuild, mode=%s, stock_ids=%s",
            mode,
            stock_ids,
        )

        result = rebuild_sell_allocations(stock_ids)

        logger.info(
            "sell_management: done – %d processed, %d failed",
            len(result["processed"]),
            len(result["failed"]),
        )

        _show_result_summary(parent, result)

    finally:
        enable_parent(modal_id)


# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\sell_management.py ends here
