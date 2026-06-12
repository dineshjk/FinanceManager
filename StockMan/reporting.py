# -*- coding: utf-8 -*-
# StockMan/reporting.py


"""
Show various financial reports.
"""

from typing import Union
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from datetime import datetime
import sqlite3
import threading  # <-- NEW
import concurrent.futures
import matplotlib
import os
import csv
from tkinter import filedialog

matplotlib.use("TkAgg")  # Tells matplotlib to render inside Tkinter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

try:  # <-- NEW
    import yfinance as yf
except ImportError:
    yf = None

from Shared.globals import (
    logger,
    get_db_connection,
    get_capital_gains_tax_rates,
)

from Shared.dialog_utils import show_colorful_error, show_colorful_info
from .date_utils import format_date_for_display
from Shared.gui_utils import bind_tooltip, setup_footer_tooltip
from .helpers import (
    calculate_investment_summary_stats,
    financial_year_sort_key,
    universal_tree_sort,
)
from Shared.modal_utils import disable_parent, enable_parent
from .reporting_utils import (
    build_allocation_tree_rows,
    build_intraday_analysis_lines,
    build_capital_stats_tree_rows,
    build_current_holdings_header_values,
    build_current_holdings_row,
    build_detail_header_fragments,
    build_live_market_snapshot,
    build_detail_corp_tree_rows,
    build_detail_existing_action_keys,
    build_detail_ledger_display_rows,
    build_detail_ledger_tree_rows,
    build_detail_dividend_tree_rows,
    build_detail_position_overview_fragments,
    build_master_existing_action_keys,
    build_master_corp_tree_rows,
    build_master_dividend_tree_rows,
    build_master_ledger_display_rows,
    build_online_action_entries,
    build_online_corp_action_rows,
    build_pooled_cost_reality_summary,
    build_report_value_fragments,
    build_realized_pnl_report_fragments,
    build_grand_summary_row,
    build_stock_tree_initial_row,
    build_stock_tree_update_row,
    build_summary_selection_fragments,
    build_summary_tree_rows,
    compute_intraday_price_bounds,
    compute_intraday_vwap_analysis,
    build_detail_corp_action_records,
    build_detail_dividend_display_data,
    build_master_corp_action_records,
    build_master_dividend_display_data,
    compute_current_position_metrics,
    compute_position_xirr,
    build_portfolio_summary,
    build_realized_pnl_rows,
    build_reality_pnl_rows,
    fetch_tax_summary_records,
    fetch_global_sell_records,
    fetch_global_buy_transactions,
    fetch_global_dividends,
    fetch_global_investment_stats_buys,
    fetch_global_investment_stats_sells,
    fetch_detail_investment_summary,
    fetch_detail_timeline_rows,
    fetch_holding_bounds,
    fetch_detail_dividend_total,
    fetch_detail_bonus_rows,
    fetch_detail_dividend_source_rows,
    fetch_detail_ledger_rows,
    fetch_position_cashflow_rows,
    fetch_and_filter_online_corp_actions,
    fetch_db_corp_actions_for_matching,
    fetch_realized_detail_rows,
    fetch_report_stock_rows,
    fetch_yearly_realized_amount,
    fetch_detail_split_rows,
    fetch_master_bonus_rows,
    fetch_master_dividend_source_rows,
    fetch_master_ledger_rows,
    fetch_master_split_rows,
    has_corporate_action_history,
    format_dividend_value_with_yield,
    get_financial_years,
    initialize_stock_data_cache,
    resolve_optional_date_filters,
    resolve_reporting_period,
    resolve_intraday_chart_window,
    resolve_action_window,
)
from .trade_utils import (
    compute_dividend_holding_days,
    compute_dividend_annualized_yield,
    compute_dividend_return_percent,
)
from Shared.window_manager import pop_window, push_window


def safe_fmt_date(date_str):
    """Formats date to DD-MM-YYYY and handles database defaults."""
    if not date_str or date_str == "1900-01-01":
        return "-"
    return format_date_for_display(date_str, "%d-%m-%Y")


DIVIDEND_YIELD_NOTE = (
    "Dividend rows show net amount plus two metrics: simple return percent "
    "and annualized return. 'Ret' is gross dividend divided by entitled "
    "investment on the record date. 'Ann' also considers holding days up to "
    "the credit date and annualizes the result. If either metric cannot be "
    "computed reliably, that metric is shown as unavailable."
)

MASTER_DIVIDEND_TABLE_FOOTNOTE = (
    "ES = Entitled Shares | Invested = Invested Amount | "
    "Div Amt = Dividend Amount | Ret % = Return % | "
    "Ann Ret % = Annualized Return %"
)

DETAIL_DIVIDEND_TABLE_FOOTNOTE = (
    MASTER_DIVIDEND_TABLE_FOOTNOTE
    + " | Hold Days = Lot-cost-weighted holding days up to dividend credit"
)


def configure_tree_columns(tree: ttk.Treeview, columns, widths=None):
    """Configure sortable tree headings and base column alignment/width."""
    widths = widths or {}
    for col in columns:
        tree.heading(
            col,
            text=col,
            command=lambda _col=col: universal_tree_sort(tree, _col, False),
        )
        config = widths.get(col, {})
        tree.column(
            col,
            width=config.get("width", 120),
            minwidth=config.get("minwidth", 60),
            anchor=config.get("anchor", "center"),
            stretch=config.get("stretch", True),
        )


def autosize_treeview_columns(
    tree: ttk.Treeview,
    sample_rows=None,
    padding: int = 24,
    max_width: int = 520,
):
    """Size tree columns to the longest visible text, including headings."""
    try:
        if not tree.winfo_exists():
            return
    except tk.TclError:
        return

    sample_rows = sample_rows or []
    try:
        style = ttk.Style(tree)
        default_font_name = style.lookup("Treeview", "font") or "TkDefaultFont"
        heading_font_name = (
            style.lookup("Treeview.Heading", "font") or default_font_name
        )
        columns = tree["columns"]
    except tk.TclError:
        return

    def resolve_font(font_spec, fallback_name="TkDefaultFont"):
        try:
            return tkfont.nametofont(font_spec)
        except tk.TclError:
            try:
                return tkfont.Font(font=font_spec)
            except tk.TclError:
                return tkfont.nametofont(fallback_name)

    body_font = resolve_font(default_font_name)
    heading_font = resolve_font(heading_font_name, default_font_name)

    for col_index, col in enumerate(columns):
        max_text_width = heading_font.measure(str(col))

        try:
            item_ids = tree.get_children("")
        except tk.TclError:
            return

        for item_id in item_ids:
            try:
                value = tree.set(item_id, col)
            except tk.TclError:
                return
            max_text_width = max(max_text_width, body_font.measure(str(value)))

        for row in sample_rows:
            if col_index < len(row):
                max_text_width = max(
                    max_text_width, body_font.measure(str(row[col_index]))
                )

        try:
            tree.column(col, width=min(max_text_width + padding, max_width))
        except tk.TclError:
            return


def configure_summary_row(tree: ttk.Treeview) -> None:
    """Apply the same visual treatment used for grand summary rows."""
    tree.tag_configure(
        "summary", background="#f1c40f", font=("Helvetica", 13, "bold")
    )


def id_stks_with_nonzero_rpnl(parent: Union[tk.Toplevel, tk.Tk]) -> list:
    """
    Fetch id_stk values from `stocks` where rpnl_amt is non-zero.
    This returns a list of integers and logs any DB errors.
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id_stk FROM stocks WHERE rpnl_amt != 0")
            rows = cur.fetchall()
            return [int(r[0]) for r in rows]
    except sqlite3.Error as exc:
        logger.exception("id_stks_with_nonzero_rpnl: DB error %s", exc)
        msg = f"Failed to read rpnl data: {exc}"
        show_colorful_error(parent, "DB Error", msg)
        return []


def latest_trade(
    parent: Union[tk.Toplevel, tk.Tk], calling_button: tk.Widget | None = None
) -> None:
    """
    Show the latest trade report in an informational dialog, with
    navigation to view older and newer trades.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Fetch all transactions ordered ascending so oldest is first, latest is last
        cursor.execute("""
            SELECT id_trd, id_stk, cont_no, trd_dt, company_name,
            trade_type_trd, exchange, qty_trd, wap_unit_trd, brok_unit_trd,
            price_lot_trd, brok_lot_trd, etc_trd, sebi_trd, sell_chrg_trd,
            gst_trd, stamp_trd, stt_trd, igst_trd, net_amt_trd, tax_trd,
            chrg_trd, error, sold_qty, note_trd
            FROM transactions
            ORDER BY id_trd ASC;
        """)
        all_trades = cursor.fetchall()

        if not all_trades:
            show_colorful_error(
                parent,
                "Missing Data",
                "I could not find any data in transactions.",
            )
            return

    # Start at the latest trade
    current_idx = {"i": len(all_trades) - 1}

    # Create UI to show the above details.
    modal_id = disable_parent(parent, calling_button=calling_button)

    def cleanup_and_close(_event=None):
        """Clean up and close the window with proper focus restoration."""
        try:
            pop_window()
        except (RuntimeError, tk.TclError) as _exc:
            logger.debug("pop_window during cleanup failed: %s", _exc)
        try:
            enable_parent(modal_id)
        except (RuntimeError, tk.TclError) as _exc:
            logger.debug("enable_parent during cleanup failed: %s", _exc)
        try:
            lt_win.destroy()
        except (RuntimeError, tk.TclError) as _exc:
            logger.debug("lt_win.destroy failed during cleanup: %s", _exc)

    lt_win = tk.Toplevel(parent)
    lt_win.title("🕶️ Trade Report 🕶️")
    lt_win.geometry(
        "480x410"
    )  # Slightly increased height for navigation buttons
    lt_win.resizable(False, False)
    lt_win.configure(bg="#6f51f7")
    lt_win.transient(parent)
    lt_win.grab_set()
    lt_win.focus_set()

    try:
        push_window(lt_win, parent)
    except (RuntimeError, tk.TclError) as _exc:
        logger.debug("push_window failed: %s", _exc)

    headerlt_frame = tk.Frame(lt_win, bg="#1e3a8a", relief="raised", bd=3)
    headerlt_frame.pack(fill="x", padx=5, pady=5)

    title_label = tk.Label(
        headerlt_frame,
        text="🌄 Latest Trade 🌄",
        font=("Comic Sans MS", 18, "bold"),
        bg="#ceea33",
        fg="#e41ac9",
        pady=8,
        relief="ridge",
        bd=2,
    )
    title_label.pack(fill="x")

    ltfcolor = "#87cefa"
    lt_frame = tk.Frame(
        lt_win, bg=ltfcolor, padx=15, pady=15, relief="groove", bd=2
    )
    lt_frame.pack(fill="both", expand=True, padx=10, pady=5)

    idltbg = "#ff9933"
    idlt_frame = tk.Frame(
        lt_frame, bg=idltbg, relief="ridge", bd=2, padx=10, pady=8
    )
    idlt_frame.grid(
        row=1, column=0, rowspan=2, columnspan=5, sticky="ew", pady=0
    )

    idlt_label_frame = tk.Frame(idlt_frame, bg=idltbg)
    idlt_label_frame.pack(fill="x", pady=(0, 0))

    idlt_entry_frame = tk.Frame(idlt_frame, bg=idltbg)
    idlt_entry_frame.pack(fill="x", pady=(0, 0))

    coltbg = "#ffffff"
    colt_frame = tk.Frame(
        lt_frame, bg=coltbg, relief="groove", bd=2, padx=10, pady=0
    )
    colt_frame.grid(
        row=3, column=0, rowspan=2, columnspan=5, sticky="ew", pady=0
    )

    colt_label_frame = tk.Frame(colt_frame, bg=coltbg)
    colt_label_frame.pack(fill="x", pady=(0, 0))

    colt_entry_frame = tk.Frame(colt_frame, bg=coltbg)
    colt_entry_frame.pack(fill="x", pady=(0, 0))

    prltbg = "#4caf50"
    prlt_frame = tk.Frame(
        lt_frame, bg=prltbg, relief="groove", bd=2, padx=10, pady=0
    )
    prlt_frame.grid(
        row=5, column=0, rowspan=2, columnspan=5, sticky="ew", pady=0
    )

    prlt_label_frame = tk.Frame(prlt_frame, bg=prltbg)
    prlt_label_frame.pack(fill="x", pady=(0, 5))

    prlt_entry_frame = tk.Frame(prlt_frame, bg=prltbg)
    prlt_entry_frame.pack(fill="x", pady=(0, 5))

    # Variable Initializations
    id_trd_var = tk.StringVar()
    cont_no_var = tk.StringVar()
    trd_dt_var = tk.StringVar()
    company_var = tk.StringVar()
    type_var = tk.StringVar()
    qty_var = tk.StringVar()
    wap_var = tk.StringVar()
    lot_pr_var = tk.StringVar()
    net_amt_var = tk.StringVar()

    # --- Trade Id field starts here ---
    tk.Label(
        idlt_label_frame, bg=idltbg, text="Trd Id", font=("Helvetica", 14)
    ).pack(side="left", padx=(10, 0))
    id_trd_entry = tk.Entry(
        idlt_entry_frame,
        textvariable=id_trd_var,
        width=5,
        font=("Helvetica", 14),
    )
    id_trd_entry.pack(side="left", padx=(10, 0))
    id_trd_entry.focus_set()

    # --- Contract No field starts here ---
    tk.Label(
        idlt_label_frame,
        bg=idltbg,
        text="Contract No (ISEC/)",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(10, 0))
    cont_no_entry = tk.Entry(
        idlt_entry_frame,
        textvariable=cont_no_var,
        width=17,
        font=("Helvetica", 14),
    )
    cont_no_entry.pack(side="left", padx=(10, 0))

    # --- Trade Dt field starts here ---
    tk.Label(
        idlt_label_frame, bg=idltbg, text="Trade Dt", font=("Helvetica", 14)
    ).pack(side="left", padx=(25, 0))
    trd_dt_entry = tk.Entry(
        idlt_entry_frame,
        textvariable=trd_dt_var,
        width=10,
        font=("Helvetica", 14),
    )
    trd_dt_entry.pack(side="left", padx=(10, 0))

    # --- Company field starts here ---
    tk.Label(
        colt_label_frame,
        bg=coltbg,
        text="Company                   🛞",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(10, 0))
    company_entry = tk.Entry(
        colt_entry_frame,
        textvariable=company_var,
        width=25,
        font=("Helvetica", 14),
    )
    company_entry.pack(side="left", padx=(10, 0))

    # --- Type field starts here ---
    tk.Label(
        colt_label_frame, bg=coltbg, text="Type", font=("Helvetica", 14)
    ).pack(side="left", padx=(80, 0))
    type_entry = tk.Entry(
        colt_entry_frame,
        textvariable=type_var,
        width=4,
        font=("Helvetica", 14),
    )
    type_entry.pack(side="left", padx=(10, 0))

    # --- Qty field starts here ---
    tk.Label(
        colt_label_frame, bg=coltbg, text="Qty", font=("Helvetica", 14)
    ).pack(side="left", padx=(14, 0))
    qty_entry = tk.Entry(
        colt_entry_frame, textvariable=qty_var, width=3, font=("Helvetica", 14)
    )
    qty_entry.pack(side="left", padx=(10, 0))

    # --- WAP field starts here ---
    tk.Label(
        prlt_label_frame, bg=prltbg, text="WAP", font=("Helvetica", 14)
    ).pack(side="left", padx=(10, 0))
    wap_entry = tk.Entry(
        prlt_entry_frame,
        textvariable=wap_var,
        width=10,
        font=("Helvetica", 14),
        justify="right",
    )
    wap_entry.pack(side="left", padx=(10, 0))

    # --- Lot Price field starts here ---
    tk.Label(
        prlt_label_frame, bg=prltbg, text="Lot Price", font=("Helvetica", 14)
    ).pack(side="left", padx=(75, 0))
    lot_pr_entry = tk.Entry(
        prlt_entry_frame,
        textvariable=lot_pr_var,
        width=10,
        font=("Helvetica", 14),
        justify="right",
    )
    lot_pr_entry.pack(side="left", padx=(10, 0))

    # --- Net Amount field starts here ---
    tk.Label(
        prlt_label_frame, bg=prltbg, text="Net Amount", font=("Helvetica", 14)
    ).pack(side="left", padx=(40, 0))
    net_amt_entry = tk.Entry(
        prlt_entry_frame,
        textvariable=net_amt_var,
        width=10,
        font=("Helvetica", 14),
        justify="right",
    )
    net_amt_entry.pack(side="left", padx=(10, 0))

    # Navigation Controls Frame
    nav_frame = tk.Frame(lt_win, bg="#6f51f7")
    nav_frame.pack(fill="x", pady=5)

    left_btn = ttk.Button(nav_frame, text="◀ Older")
    left_btn.pack(side="left", padx=20)

    ok_button = ttk.Button(nav_frame, text="OK", command=cleanup_and_close)
    ok_button.pack(side="left", expand=True)

    right_btn = ttk.Button(nav_frame, text="Newer ▶")
    right_btn.pack(side="right", padx=20)

    # --- Navigation Logic ---
    def update_view():
        idx = current_idx["i"]
        row = all_trades[idx]

        # Map current row exactly as before
        trade_data = {
            "id_trd": row[0],
            "cont_no": row[2],
            "trd_dt": row[3],
            "company_name": row[4],
            "trade_type_trd": row[5],
            "qty_trd": row[7],
            "wap_unit_trd": row[8],
            "price_lot_trd": row[10],
            "net_amt_trd": row[19],
        }

        id_trd_var.set(trade_data["id_trd"])

        cont_no_val = trade_data.get("cont_no", "")
        display_cont_no = (
            cont_no_val[5:] if cont_no_val.startswith("ISEC/") else cont_no_val
        )
        cont_no_var.set(display_cont_no)

        parsed = datetime.strptime(trade_data["trd_dt"], "%Y-%m-%d")
        trd_dt_var.set(parsed.strftime("%d-%m-%Y"))

        company_var.set(trade_data["company_name"])
        type_var.set(trade_data["trade_type_trd"])
        qty_var.set(trade_data["qty_trd"])

        wap_var.set(f"{float(trade_data.get('wap_unit_trd') or 0.0):.4f}")
        lot_pr_var.set(f"{float(trade_data.get('price_lot_trd') or 0.0):.4f}")
        net_amt_var.set(f"{float(trade_data.get('net_amt_trd') or 0.0):.4f}")

        # Status Update
        if idx == len(all_trades) - 1:
            title_label.config(text="🌄 Latest Trade 🌄")
            right_btn.config(state="disabled")
        else:
            title_label.config(
                text=f"🌄 Trade Record {idx + 1} of {len(all_trades)} 🌄"
            )
            right_btn.config(state="normal")

        if idx == 0:
            left_btn.config(state="disabled")
        else:
            left_btn.config(state="normal")

    def go_prev(_event=None):
        if current_idx["i"] > 0:
            current_idx["i"] -= 1
            update_view()

    def go_next(_event=None):
        if current_idx["i"] < len(all_trades) - 1:
            current_idx["i"] += 1
            update_view()

    # Apply Bindings
    left_btn.config(command=go_prev)
    right_btn.config(command=go_next)

    lt_win.bind("<Left>", lambda e: go_prev())
    lt_win.bind("<Right>", lambda e: go_next())
    lt_win.bind("<Escape>", cleanup_and_close)

    # Configure window close protocol to use cleanup function
    lt_win.protocol("WM_DELETE_WINDOW", cleanup_and_close)

    # Populate Initial View
    update_view()

    parent.wait_window(lt_win)
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        logger.debug("parent.grab_set skipped: parent destroyed.")

    try:
        pop_window()
    except (RuntimeError, tk.TclError) as exc:
        logger.debug("pop_window failed during final cleanup: %s", exc)
    try:
        enable_parent(modal_id)
    except (RuntimeError, tk.TclError) as exc:
        logger.debug("enable_parent failed during final cleanup: %s", exc)


class NotebookTooltip:
    """Provides floating tooltips for ttk.Notebook tabs."""

    def __init__(self, notebook: ttk.Notebook, tooltips: dict):
        self.notebook = notebook
        self.tooltips = tooltips
        self.tw = None
        self.current_tab = None

        self.notebook.bind("<Motion>", self.on_motion)
        self.notebook.bind("<Leave>", self.hide)

    def on_motion(self, event):
        # Identify which tab the mouse is hovering over
        try:
            tab_index = self.notebook.index(f"@{event.x},{event.y}")
        except tk.TclError:
            tab_index = None

        # If the mouse is still over the same tab, do nothing
        if tab_index == self.current_tab:
            return

        self.hide()
        self.current_tab = tab_index

        # If hovering over a valid tab with a defined tooltip, show it
        if tab_index is not None and tab_index in self.tooltips:
            self.show(event, self.tooltips[tab_index])

    def show(self, event, text):
        self.tw = tk.Toplevel(self.notebook)
        self.tw.wm_overrideredirect(True)  # Removes window decorations/borders
        # Position the tooltip slightly offset from the mouse cursor
        self.tw.wm_geometry(f"+{event.x_root + 15}+{event.y_root + 15}")

        label = tk.Label(
            self.tw,
            text=text,
            justify="left",
            background="#ffffe0",
            foreground="#333333",
            relief="solid",
            borderwidth=1,
            font=("Helvetica", 11),
        )
        label.pack(ipadx=6, ipady=3)

    def hide(self, _event=None):
        if self.tw:
            self.tw.destroy()
            self.tw = None
        self.current_tab = None


class TreeHeadingTooltip:
    """Provides floating tooltips for ttk.Treeview column headings."""

    def __init__(self, tree: ttk.Treeview, tooltips: dict[str, str]):
        self.tree = tree
        self.tooltips = tooltips
        self.tw = None
        self.current_column = None

        self.tree.bind("<Motion>", self.on_motion, add="+")
        self.tree.bind("<Leave>", self.hide, add="+")

    def on_motion(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "heading":
            self.hide()
            return

        column_id = self.tree.identify_column(event.x)
        if not column_id or column_id == "#0":
            self.hide()
            return

        column_index = int(column_id[1:]) - 1
        columns = self.tree["columns"]
        if column_index < 0 or column_index >= len(columns):
            self.hide()
            return

        column_name = columns[column_index]
        if column_name == self.current_column:
            return

        self.hide()
        self.current_column = column_name
        tooltip_text = self.tooltips.get(column_name)
        if tooltip_text:
            self.show(event, tooltip_text)

    def show(self, event, text):
        self.tw = tk.Toplevel(self.tree)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{event.x_root + 15}+{event.y_root + 15}")

        label = tk.Label(
            self.tw,
            text=text,
            justify="left",
            background="#ffffe0",
            foreground="#333333",
            relief="solid",
            borderwidth=1,
            font=("Helvetica", 11),
        )
        label.pack(ipadx=6, ipady=3)

    def hide(self, _event=None):
        if self.tw:
            self.tw.destroy()
            self.tw = None
        self.current_column = None


def export_tax_summary(parent_win, selected_fy):
    is_yearly, start_date, end_date = resolve_reporting_period(selected_fy)

    initial_file = (
        f"Tax_Summary_{selected_fy.replace(' ', '_')}.csv"
        if is_yearly
        else "Tax_Summary_All_Years.csv"
    )
    file_path = filedialog.asksaveasfilename(
        parent=parent_win,
        title="Export Tax Summary",
        initialfile=initial_file,
        defaultextension=".csv",
        filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
    )

    if not file_path:
        return

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            rows = fetch_tax_summary_records(
                cursor, is_yearly, start_date, end_date
            )

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Company",
                    "Ticker",
                    "Buy Date",
                    "Sell Date",
                    "Quantity",
                    "Buy Value",
                    "Sell Value",
                    "Gross P&L",
                    "Holding Days",
                    "Capital Gain Type",
                    "Tax Rate (%)",
                    "Est. Tax Amount",
                    "Est. Post-Tax Profit (PAT)",
                ]
            )

            total_pnl = 0.0
            total_tax = 0.0
            total_pat = 0.0

            for row in rows:
                comp, ticker, b_dt, s_dt, qty, b_val, s_val, pnl, days = row
                s_date_obj = datetime.strptime(s_dt, "%Y-%m-%d").date()

                stcg_rate, ltcg_rate = get_capital_gains_tax_rates(s_date_obj)
                is_ltcg = days >= 365
                cg_type = "LTCG" if is_ltcg else "STCG"
                tax_rate = ltcg_rate if is_ltcg else stcg_rate

                tax_amt = (pnl * tax_rate) if pnl > 0 else 0.0
                pat = pnl - tax_amt

                writer.writerow(
                    [
                        comp,
                        ticker,
                        b_dt,
                        s_dt,
                        qty,
                        round(b_val, 2),
                        round(s_val, 2),
                        round(pnl, 2),
                        days,
                        cg_type,
                        round(tax_rate * 100, 2),
                        round(tax_amt, 2),
                        round(pat, 2),
                    ]
                )

                total_pnl += pnl
                total_tax += tax_amt
                total_pat += pat

            writer.writerow([])
            writer.writerow(
                [
                    "TOTALS",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    round(total_pnl, 2),
                    "",
                    "",
                    "",
                    round(total_tax, 2),
                    round(total_pat, 2),
                ]
            )

        show_colorful_info(
            parent_win,
            "Export Successful",
            f"Tax summary exported successfully to:\n{file_path}",
        )

        # Safely try to open the file to view it instantly on Windows
        if os.name == "nt":
            os.startfile(file_path)

    except PermissionError:
        show_colorful_error(
            parent_win,
            "File In Use",
            "The selected file is currently open in another program.\n\nPlease close it and try again.",
        )
    except Exception as e:
        logger.error(f"Failed to export tax summary: {e}", exc_info=True)
        show_colorful_error(
            parent_win,
            "Export Failed",
            f"An error occurred while exporting:\n{e}",
        )


def p_and_l(
    parent: Union[tk.Toplevel, tk.Tk], calling_button: tk.Widget | None = None
) -> None:
    """
    Master-Detail Profit and Loss report supporting Realized and Unrealized computations,
    dynamic sorting, automated price fetching, and historical tax estimations.
    """
    if yf is None:
        show_colorful_error(
            parent,
            "Missing Library",
            "The 'yfinance' library is required for live prices.\nPlease run: pip install yfinance",
        )
        return

    modal_id = disable_parent(parent, calling_button)
    pnl_win = tk.Toplevel(parent)
    pnl_win.title("Portfolio Analytics Dashboard")
    try:
        pnl_win.state("zoomed")
    except tk.TclError:
        pnl_win.geometry("1300x800")
    pnl_win.configure(bg="#2c3e50")

    # Enforce strict modality
    pnl_win.transient(parent)
    pnl_win.grab_set()
    pnl_win.focus_set()

    push_window(pnl_win, parent)

    def cleanup_and_close():
        pop_window()
        enable_parent(modal_id)
        pnl_win.destroy()

    pnl_win.protocol("WM_DELETE_WINDOW", cleanup_and_close)

    # Creates a styling engine object to customize the visual
    # appearance of modern ttk widgets within the pnl_win window.
    style = ttk.Style(pnl_win)
    style.theme_use("clam")
    style.configure(
        "Treeview",
        font=("Helvetica", 12),
        rowheight=30,
        background="#ffffff",
        fieldbackground="#ffffff",
    )
    style.configure(
        "Treeview.Heading",
        font=("Helvetica", 13, "bold"),
        background="#34495e",
        foreground="white",
    )
    style.map("Treeview.Heading", background=[("active", "#2c3e50")])
    style.configure(
        "TNotebook.Tab", font=("Helvetica", 13, "bold"), padding=[10, 5]
    )

    # Top Controls
    controls_frame = tk.Frame(pnl_win, bg="#34495e", padx=10, pady=10)
    controls_frame.pack(fill="x")

    fy_label = tk.Label(
        controls_frame,
        text="Reporting Period:",
        font=("Helvetica", 14, "bold"),
        bg="#34495e",
        fg="white",
    )
    fy_label.pack(side="left", padx=(0, 10))

    fy_var = tk.StringVar()
    fy_combo = ttk.Combobox(
        controls_frame,
        textvariable=fy_var,
        font=("Helvetica", 14),
        state="readonly",
        width=15,
    )
    fy_combo.pack(side="left")

    with get_db_connection() as conn:
        financial_years = get_financial_years(conn)
    fy_combo["values"] = ["All Years"] + financial_years
    fy_combo.set("All Years")

    export_btn = tk.Button(
        controls_frame,
        text="📥 Export Tax Report",
        font=("Helvetica", 12, "bold"),
        bg="#27ae60",
        fg="white",
        activebackground="#219653",
        activeforeground="white",
        cursor="hand2",
        relief="raised",
        bd=2,
        command=lambda: export_tax_summary(pnl_win, fy_var.get()),
    )
    export_btn.pack(side="left", padx=20)

    status_label = tk.Label(
        controls_frame,
        text="Status: Initializing...",
        font=("Helvetica", 12, "italic"),
        bg="#34495e",
        fg="#f1c40f",
    )
    status_label.pack(side="right", padx=10)

    # Main Notebook (Tabs)
    notebook = ttk.Notebook(pnl_win)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)
    tooltip_var = setup_footer_tooltip(
        pnl_win, bg_color="#34495e", fg_color="#ecf0f1"
    )

    def add_widget_tooltip(widget, text):
        bind_tooltip(widget, tooltip_var, text)

    def add_tree_heading_tooltips(tree, tooltips):
        tree._heading_tooltip = TreeHeadingTooltip(tree, tooltips)

    # --- TAB 1: Individual Stocks ---
    tab_stocks = ttk.Frame(notebook)
    notebook.add(tab_stocks, text="📊 Stock-wise Analysis")

    paned = ttk.PanedWindow(tab_stocks, orient=tk.HORIZONTAL)
    paned.pack(fill="both", expand=True, padx=5, pady=5)

    left_frame = ttk.Frame(paned)
    paned.add(left_frame, weight=2)

    columns = (
        "WL",
        "Stock / Symbol",
        "Realized Gain/Loss",
        "Unrealized Gain/Loss",
        "Total Gain/Loss",
        "XIRR (%)",
    )
    tree = ttk.Treeview(
        left_frame, columns=columns, show="headings", selectmode="browse"
    )
    tree_scroll_y = ttk.Scrollbar(
        left_frame, orient="vertical", command=tree.yview
    )
    tree_scroll_x = ttk.Scrollbar(
        left_frame, orient="horizontal", command=tree.xview
    )
    tree.configure(
        yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set
    )

    tree_scroll_x.pack(side="bottom", fill="x")
    tree.pack(side="left", fill="both", expand=True)
    tree_scroll_y.pack(side="right", fill="y")

    for col in columns:
        tree.heading(
            col,
            text=col if col != "WL" else "👁️",
            command=lambda _col=col: universal_tree_sort(tree, _col, False),
        )
        if col == "WL":
            tree.column(col, width=40, anchor="center", stretch=False)
        elif col == "Stock / Symbol":
            tree.column(col, width=160, anchor="w")
        else:
            tree.column(col, width=120, anchor="e")

    add_tree_heading_tooltips(
        tree,
        {
            "WL": "Double-click the ➕ icon to add the stock to your watchlist.",
            "Stock / Symbol": "Stock name or ticker for the selected holding.",
            "Realized Gain/Loss": "Booked profit or loss from completed sales for the stock.",
            "Unrealized Gain/Loss": "Current mark-to-market gain or loss on the remaining holding.",
            "Total Gain/Loss": "Realized and unrealized gain/loss combined.",
            "XIRR (%)": "Annualized internal rate of return for the stock using dated cash flows.",
        },
    )
    add_widget_tooltip(
        tree,
        "Select a stock to update the right-side detail panels and ledgers.",
    )

    right_frame = ttk.Frame(paned)
    paned.add(right_frame, weight=3)

    # --- NESTED NOTEBOOK FOR DETAILS ---
    detail_notebook = ttk.Notebook(right_frame)
    detail_notebook.pack(fill="both", expand=True)

    # Sub-Tab 1: Stock Performance Report
    tab_detail_pnl = ttk.Frame(detail_notebook)
    detail_notebook.add(tab_detail_pnl, text="📄 Stock Performance")

    report_text = tk.Text(
        tab_detail_pnl,
        wrap="none",  # Changed from 'word' to 'none' to prevent table line breaking
        font=("Courier New", 15, "bold"),
        bg="#121212",
        fg="#ffffff",
        insertbackground="yellow",
    )
    # Add a horizontal scrollbar for the report text
    report_scroll_x = ttk.Scrollbar(
        tab_detail_pnl, orient="horizontal", command=report_text.xview
    )
    report_text.config(xscrollcommand=report_scroll_x.set)
    report_scroll_x.pack(side="bottom", fill="x")

    text_scroll = ttk.Scrollbar(tab_detail_pnl, command=report_text.yview)
    report_text.config(yscrollcommand=text_scroll.set)
    report_text.pack(side="left", fill="both", expand=True)
    text_scroll.pack(side="right", fill="y")

    # Sub-Tab 2: Demat Ledger
    tab_detail_ledger = ttk.Frame(detail_notebook)
    detail_notebook.add(tab_detail_ledger, text="📓 Holding Ledger")
    ledger_cols = (
        "Date",
        "Opening Qty",
        "Qty Change",
        "Closing Qty",
        "Cost Basis",
        "Average Cost",
    )
    ledger_tree = ttk.Treeview(
        tab_detail_ledger,
        columns=ledger_cols,
        show="headings",
        selectmode="none",
    )
    ledger_scroll = ttk.Scrollbar(
        tab_detail_ledger, orient="vertical", command=ledger_tree.yview
    )
    ledger_tree.configure(yscrollcommand=ledger_scroll.set)
    ledger_tree.pack(side="left", fill="both", expand=True)
    ledger_scroll.pack(side="right", fill="y")
    configure_tree_columns(
        ledger_tree, ledger_cols, widths={"Date": {"width": 110}}
    )
    add_tree_heading_tooltips(
        ledger_tree,
        {
            "Date": "Transaction or settlement date used in the running holding ledger.",
            "Opening Qty": "Quantity held before this event.",
            "Qty Change": "Shares added or removed by this event.",
            "Closing Qty": "Quantity held after this event.",
            "Cost Basis": "Total invested cost carried after this event.",
            "Average Cost": "Average cost per share after this event.",
        },
    )
    add_widget_tooltip(
        ledger_tree,
        "Chronological holding ledger for the selected stock.",
    )

    # Sub-Tab 3: Corporate Actions
    tab_detail_corp = ttk.Frame(detail_notebook)
    detail_notebook.add(tab_detail_corp, text="🎁 Broker Corporate Actions")
    corp_cols = ("Event Date", "Action Type", "Ratio / Value", "Tax Deducted")
    corp_tree = ttk.Treeview(
        tab_detail_corp, columns=corp_cols, show="headings", selectmode="none"
    )
    corp_scroll = ttk.Scrollbar(
        tab_detail_corp, orient="vertical", command=corp_tree.yview
    )
    corp_tree.configure(yscrollcommand=corp_scroll.set)
    corp_tree.pack(side="left", fill="both", expand=True)
    corp_scroll.pack(side="right", fill="y")
    configure_tree_columns(
        corp_tree,
        corp_cols,
        widths={
            "Action Type": {"width": 180},
            "Ratio / Value": {"width": 220},
        },
    )
    add_tree_heading_tooltips(
        corp_tree,
        {
            "Event Date": "Effective date of the corporate action.",
            "Action Type": "Type of corporate action recorded in the broker-backed history.",
            "Ratio / Value": "Cash value, ratio, or descriptive amount tied to the action.",
            "Tax Deducted": "Any tax deducted at source recorded for the action.",
        },
    )
    add_widget_tooltip(
        corp_tree,
        "Corporate actions imported from your broker or recorded in the local database.",
    )

    # Sub-Tab 4: All Dividend
    tab_detail_dividend = ttk.Frame(detail_notebook)
    detail_notebook.add(tab_detail_dividend, text="💸 Dividend Ledger")
    detail_dividend_cols = (
        "Stock",
        "Eligible Shares",
        "Invested Amount",
        "Dividend Amount",
        "Return (%)",
        "Annualized Return (%)",
        "Holding Days",
    )
    detail_dividend_content = ttk.Frame(tab_detail_dividend)
    detail_dividend_content.pack(fill="both", expand=True)
    dividend_tree = ttk.Treeview(
        detail_dividend_content,
        columns=detail_dividend_cols,
        show="headings",
        selectmode="none",
    )
    dividend_scroll = ttk.Scrollbar(
        detail_dividend_content,
        orient="vertical",
        command=dividend_tree.yview,
    )
    dividend_tree.configure(yscrollcommand=dividend_scroll.set)
    dividend_tree.pack(side="left", fill="both", expand=True)
    dividend_scroll.pack(side="right", fill="y")
    configure_tree_columns(
        dividend_tree,
        detail_dividend_cols,
        widths={
            "Stock": {"width": 180, "anchor": "w", "minwidth": 100},
            "Eligible Shares": {"width": 120, "anchor": "e"},
            "Invested Amount": {"width": 150, "anchor": "e"},
            "Dividend Amount": {"width": 140, "anchor": "e"},
            "Return (%)": {"width": 100, "anchor": "e"},
            "Annualized Return (%)": {"width": 150, "anchor": "e"},
            "Holding Days": {"width": 110, "anchor": "e"},
        },
    )
    configure_summary_row(dividend_tree)
    add_tree_heading_tooltips(
        dividend_tree,
        {
            "Stock": "Stock for which the dividend was credited.",
            "Eligible Shares": "Shares eligible for the dividend on the record date.",
            "Invested Amount": "Invested cost linked to the eligible shares.",
            "Dividend Amount": "Net dividend amount credited.",
            "Return (%)": "Dividend amount as a percentage of the linked invested amount.",
            "Annualized Return (%)": "Dividend return annualized using the weighted holding period.",
            "Holding Days": "Lot-cost-weighted holding days up to the credit date.",
        },
    )
    add_widget_tooltip(
        dividend_tree,
        "Dividend history for the selected stock with return and holding metrics.",
    )
    detail_dividend_footnote = tk.Label(
        tab_detail_dividend,
        text=DETAIL_DIVIDEND_TABLE_FOOTNOTE,
        bg="#0f172a",
        fg="#f8fafc",
        font=("Helvetica", 12, "bold"),
        justify="left",
        anchor="w",
        wraplength=1,
        padx=10,
        pady=8,
    )
    detail_dividend_footnote.pack(fill="x", side="bottom")
    tab_detail_dividend.bind(
        "<Configure>",
        lambda e: detail_dividend_footnote.configure(
            wraplength=max(e.width - 24, 200)
        ),
    )
    add_widget_tooltip(
        detail_dividend_footnote,
        "Legend explaining the dividend ledger abbreviations and return metrics.",
    )

    # Sub-Tab 5: Online CA
    tab_detail_online_corp = ttk.Frame(detail_notebook)
    detail_notebook.add(
        tab_detail_online_corp, text="🌐 Online Corporate Actions"
    )
    online_corp_cols = ("Event Date", "Action Type", "Ratio / Value", "Source", "DB Match")
    online_corp_tree = ttk.Treeview(
        tab_detail_online_corp,
        columns=online_corp_cols,
        show="headings",
        selectmode="none",
    )
    online_corp_tree.tag_configure("missing", foreground="#ef4444", font=("Helvetica", 11, "bold"))
    online_corp_tree.tag_configure("matched", foreground="#27ae60", font=("Helvetica", 11))
    
    online_corp_scroll = ttk.Scrollbar(
        tab_detail_online_corp,
        orient="vertical",
        command=online_corp_tree.yview,
    )
    online_corp_tree.configure(yscrollcommand=online_corp_scroll.set)
    online_corp_tree.pack(side="left", fill="both", expand=True)
    online_corp_scroll.pack(side="right", fill="y")
    configure_tree_columns(
        online_corp_tree,
        online_corp_cols,
        widths={
            "Action Type": {"width": 180},
            "Ratio / Value": {"width": 180},
            "DB Match": {"width": 180},
        },
    )
    add_tree_heading_tooltips(
        online_corp_tree,
        {
            "Event Date": "Effective date published by the online source.",
            "Action Type": "Type of online corporate action detected.",
            "Ratio / Value": "Ratio, cash value, or descriptive amount from the source.",
            "Source": "External source used to detect the action.",
            "DB Match": "Matching status in local database.",
        },
    )
    add_widget_tooltip(
        online_corp_tree,
        "Corporate actions detected from online data providers for the selected stock.",
    )

    # Sub-Tab 6: Intraday Analysis
    tab_detail_analysis = ttk.Frame(detail_notebook)
    detail_notebook.add(tab_detail_analysis, text="📊 Intraday Price Analysis")

    # Split the tab: Top for Chart, Bottom for Text
    chart_frame = tk.Frame(tab_detail_analysis, bg="#2c3e50")
    chart_frame.pack(side="top", fill="both", expand=True)

    # --- NEW: Create the Matplotlib Canvas ONCE to prevent silent crashes ---
    intra_fig = Figure(figsize=(5, 4), dpi=100, facecolor="#2c3e50")
    intra_ax = intra_fig.add_subplot(111)
    intra_ax.set_facecolor("#1e2a38")
    intra_canvas = FigureCanvasTkAgg(intra_fig, master=chart_frame)
    intra_canvas.get_tk_widget().pack(fill="both", expand=True)

    analysis_text = tk.Text(
        tab_detail_analysis,
        wrap="word",
        height=6,
        font=("Courier New", 14, "bold"),
        bg="#121212",
        fg="#00ffff",  # Cyan text
    )
    analysis_text.pack(side="bottom", fill="x")

    # --- IMPLEMENT DETAIL SUB-TAB TOOLTIPS ---
    detail_tooltips = {
        0: "Stock-wise performance summary with realized, unrealized, tax-aware, and opportunity metrics.",
        1: "Running quantity and cost ledger for the selected stock.",
        2: "Broker-backed corporate action history for the selected stock.",
        3: "Dividend ledger with eligible shares, invested amount, and return metrics.",
        4: "Online corporate actions detected during the stock's holding period.",
        5: "Intraday price and VWAP analysis for the selected stock.",
    }
    NotebookTooltip(detail_notebook, detail_tooltips)
    add_widget_tooltip(
        detail_notebook,
        "Hover the detail tabs or review the selected stock's breakdown on the right.",
    )
    add_widget_tooltip(
        report_text,
        "Narrative stock report for the selected holding.",
    )
    add_widget_tooltip(
        analysis_text,
        "Text summary for the intraday price analysis panel.",
    )

    report_text.tag_configure(
        "header",
        font=("Courier New", 18, "bold"),
        foreground="#ffd700",  # Gold
    )
    report_text.tag_configure(
        "subheader",
        font=("Courier New", 16, "bold"),
        foreground="#00ffff",  # Cyan
    )
    report_text.tag_configure(
        "normal",
        font=("Courier New", 15, "bold"),
        foreground="#ffffff",  # White
    )
    report_text.tag_configure(
        "negative",
        font=("Courier New", 15, "bold"),
        foreground="#ff4444",  # Bright Red
    )
    report_text.tag_configure(
        "positive",
        font=("Courier New", 15, "bold"),
        foreground="#00ff00",  # Bright Green
    )
    report_text.tag_configure(
        "italic",
        font=("Courier New", 15, "bold"),
        foreground="#fba414",  # Bright Orange
    )
    report_text.tag_configure(
        "alert",
        font=("Courier New", 16, "bold"),
        background="#ffd700",
        foreground="black",  # Black on Yellow
    )

    # --- TAB 2: Portfolio Summary ---
    tab_summary = ttk.Frame(notebook)
    notebook.add(tab_summary, text="📈 Portfolio Summary")

    summary_panes = ttk.PanedWindow(tab_summary, orient=tk.VERTICAL)
    summary_panes.pack(fill="both", expand=True, padx=10, pady=10)

    summary_upper_frame = ttk.LabelFrame(summary_panes, text="Returns Summary")
    summary_lower_frame = ttk.LabelFrame(
        summary_panes, text="Capital Flow and Balance Statistics"
    )
    summary_panes.add(summary_upper_frame, weight=1)
    summary_panes.add(summary_lower_frame, weight=1)

    summary_upper_body = ttk.Frame(summary_upper_frame)
    summary_upper_body.pack(fill="both", expand=True, padx=6, pady=6)
    summary_upper_body.grid_rowconfigure(0, weight=1)
    summary_upper_body.grid_columnconfigure(0, weight=1)

    sum_cols = (
        "Financial Year",
        "Total Buy Investment",
        "Realized Gain/Loss",
        "Estimated Post-Tax Profit/Loss",
        "Net Dividends",
        "Post-Tax Return + Dividends",
        "Opportunity Profit Missed",
        "Loss Avoided",
    )
    sum_tree = ttk.Treeview(
        summary_upper_body,
        columns=sum_cols,
        show="headings",
        selectmode="none",
    )
    sum_y_scroll = ttk.Scrollbar(
        summary_upper_body, orient="vertical", command=sum_tree.yview
    )
    sum_x_scroll = ttk.Scrollbar(
        summary_upper_body, orient="horizontal", command=sum_tree.xview
    )
    sum_tree.configure(
        yscrollcommand=sum_y_scroll.set, xscrollcommand=sum_x_scroll.set
    )
    sum_tree.grid(row=0, column=0, sticky="nsew")
    sum_y_scroll.grid(row=0, column=1, sticky="ns")
    sum_x_scroll.grid(row=1, column=0, sticky="ew")
    configure_tree_columns(
        sum_tree,
        sum_cols,
        {
            "Financial Year": {"width": 120, "minwidth": 110, "anchor": "w"},
            "Total Buy Investment": {"width": 150, "anchor": "e"},
            "Realized Gain/Loss": {"width": 145, "anchor": "e"},
            "Estimated Post-Tax Profit/Loss": {
                "width": 175,
                "anchor": "e",
            },
            "Net Dividends": {"width": 120, "anchor": "e"},
            "Post-Tax Return + Dividends": {"width": 205, "anchor": "e"},
            "Opportunity Profit Missed": {"width": 185, "anchor": "e"},
            "Loss Avoided": {"width": 130, "anchor": "e"},
        },
    )
    configure_summary_row(sum_tree)

    sum_col_tooltips = {
        "Financial Year": (
            "Financial year summary row, with ALL YEARS as the grand total."
        ),
        "Total Buy Investment": (
            "Total amount invested through BUY trades in that financial year."
        ),
        "Realized Gain/Loss": (
            "Booked profit or loss from sell records in that financial year."
        ),
        "Estimated Post-Tax Profit/Loss": (
            "Estimated post-tax realized profit after applying the "
            "report's capital-gains tax assumptions."
        ),
        "Net Dividends": "Total net dividends credited in that financial year.",
        "Post-Tax Return + Dividends": (
            "Estimated post-tax realized profit/loss plus dividends for "
            "the period."
        ),
        "Opportunity Profit Missed": (
            "Extra profit you would have made if sold quantities were "
            "still held at the current live price."
        ),
        "Loss Avoided": (
            "Loss avoided because sold quantities are below the current "
            "live price."
        ),
    }
    add_tree_heading_tooltips(sum_tree, sum_col_tooltips)
    add_widget_tooltip(
        sum_tree,
        "Portfolio return summary by financial year and for all years combined.",
    )

    summary_lower_body = ttk.Frame(summary_lower_frame)
    summary_lower_body.pack(fill="both", expand=True, padx=6, pady=6)
    summary_lower_body.grid_rowconfigure(0, weight=1)
    summary_lower_body.grid_columnconfigure(0, weight=1)

    stats_cols = (
        "Financial Year",
        "Investment Added",
        "Cost Recovered on Sales",
        "Peak Invested Balance",
        "Lowest Invested Balance",
        "Largest Single Buy",
        "Largest Single Cost Recovery",
    )
    stats_tree = ttk.Treeview(
        summary_lower_body,
        columns=stats_cols,
        show="headings",
        selectmode="none",
    )
    stats_y_scroll = ttk.Scrollbar(
        summary_lower_body, orient="vertical", command=stats_tree.yview
    )
    stats_x_scroll = ttk.Scrollbar(
        summary_lower_body, orient="horizontal", command=stats_tree.xview
    )
    stats_tree.configure(
        yscrollcommand=stats_y_scroll.set,
        xscrollcommand=stats_x_scroll.set,
    )
    stats_tree.grid(row=0, column=0, sticky="nsew")
    stats_y_scroll.grid(row=0, column=1, sticky="ns")
    stats_x_scroll.grid(row=1, column=0, sticky="ew")
    configure_tree_columns(
        stats_tree,
        stats_cols,
        {
            "Financial Year": {"width": 120, "minwidth": 110, "anchor": "w"},
            "Investment Added": {"width": 145, "anchor": "e"},
            "Cost Recovered on Sales": {"width": 185, "anchor": "e"},
            "Peak Invested Balance": {"width": 165, "anchor": "e"},
            "Lowest Invested Balance": {"width": 175, "anchor": "e"},
            "Largest Single Buy": {"width": 155, "anchor": "e"},
            "Largest Single Cost Recovery": {"width": 200, "anchor": "e"},
        },
    )
    configure_summary_row(stats_tree)

    stats_col_tooltips = {
        "Financial Year": (
            "Financial year summary row, with ALL YEARS as the overall "
            "portfolio total."
        ),
        "Investment Added": (
            "Sum of all BUY amounts in the period. Multiple investments are "
            "added together."
        ),
        "Cost Recovered on Sales": (
            "Capital withdrawn in the period, measured on original invested "
            "cost. If you buy for 100 and sell at any price, disinvestment "
            "is 100."
        ),
        "Peak Invested Balance": "Highest running invested balance reached at any point during the period.",
        "Lowest Invested Balance": (
            "Lowest running invested balance reached at any point during the "
            "period, including carried opening balance."
        ),
        "Largest Single Buy": (
            "Biggest single investment event in the period, based on one BUY "
            "trade amount."
        ),
        "Largest Single Cost Recovery": (
            "Biggest single disinvestment event in the period, measured as "
            "total original cost released by one sell trade."
        ),
    }
    add_tree_heading_tooltips(stats_tree, stats_col_tooltips)
    add_widget_tooltip(
        stats_tree,
        "Capital-flow statistics by financial year and for all years combined.",
    )

    # --- TAB 3: Current Holdings ---
    tab_current = ttk.Frame(notebook)
    notebook.add(tab_current, text="💼 Current Holdings")

    # Header for Current Holdings
    curr_header_frame = tk.Frame(
        tab_current, bg="#ecf0f1", bd=2, relief="groove"
    )
    curr_header_frame.pack(fill="x", padx=10, pady=5)

    curr_invested_var = tk.StringVar(value="Current Cost Basis: ₹0.00")
    curr_val_var = tk.StringVar(value="Live Market Value: ₹0.00")
    curr_unrealized_var = tk.StringVar(value="Unrealized Gain/Loss: ₹0.00")
    curr_realized_var = tk.StringVar(value="Realized Gain/Loss: ₹0.00")

    curr_invested_label = tk.Label(
        curr_header_frame,
        textvariable=curr_invested_var,
        font=("Helvetica", 12, "bold"),
        bg="#ecf0f1",
        fg="#2980b9",
    )
    curr_invested_label.pack(side="left", expand=True, pady=5)
    curr_val_label = tk.Label(
        curr_header_frame,
        textvariable=curr_val_var,
        font=("Helvetica", 12, "bold"),
        bg="#ecf0f1",
        fg="#8e44ad",
    )
    curr_val_label.pack(side="left", expand=True, pady=5)
    curr_unrealized_label = tk.Label(
        curr_header_frame,
        textvariable=curr_unrealized_var,
        font=("Helvetica", 12, "bold"),
        bg="#ecf0f1",
    )
    curr_unrealized_label.pack(side="left", expand=True, pady=5)
    curr_realized_label = tk.Label(
        curr_header_frame,
        textvariable=curr_realized_var,
        font=("Helvetica", 12, "bold"),
        bg="#ecf0f1",
        fg="#16a085",
    )
    curr_realized_label.pack(side="left", expand=True, pady=5)

    curr_cols = (
        "Symbol",
        "Current Qty",
        "Average Cost",
        "Cost Basis",
        "Market Price",
        "Unrealized Gain/Loss",
        "Realized Gain/Loss",
    )
    curr_tree = ttk.Treeview(
        tab_current, columns=curr_cols, show="headings", selectmode="browse"
    )
    curr_scroll = ttk.Scrollbar(
        tab_current, orient="vertical", command=curr_tree.yview
    )
    curr_tree.configure(yscrollcommand=curr_scroll.set)
    curr_tree.pack(
        side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10)
    )
    curr_scroll.pack(side="right", fill="y", padx=(0, 10), pady=(0, 10))

    # Tags for color coding the text rows and applying font consistent with the left panel (12pt)
    current_tab_font = ("Helvetica", 12)
    curr_tree.tag_configure(
        "profit", foreground="#27ae60", font=current_tab_font
    )
    curr_tree.tag_configure(
        "loss", foreground="#c0392b", font=current_tab_font
    )
    curr_tree.tag_configure(
        "neutral", foreground="#2c3e50", font=current_tab_font
    )

    # Configure the treeview font globally for the body
    style.configure("Current.Treeview", font=("Helvetica", 12))
    curr_tree.configure(style="Current.Treeview")

    # Tighter custom column widths to prevent sparse empty space
    col_widths = {
        "Symbol": 100,
        "Current Qty": 90,
        "Average Cost": 110,
        "Cost Basis": 120,
        "Market Price": 110,
        "Unrealized Gain/Loss": 180,
        "Realized Gain/Loss": 140,
    }

    for col in curr_cols:
        curr_tree.heading(
            col,
            text=col,
            command=lambda _col=col: universal_tree_sort(
                curr_tree, _col, False
            ),
        )
        curr_tree.column(
            col,
            width=col_widths.get(col, 100),
            anchor="e" if col != "Symbol" else "w",
        )
    add_tree_heading_tooltips(
        curr_tree,
        {
            "Symbol": "Stock symbol or short name for the current holding.",
            "Current Qty": "Shares currently held.",
            "Average Cost": "Average cost per currently held share.",
            "Cost Basis": "Total invested cost still tied to the current holding.",
            "Market Price": "Latest live market price used in the report.",
            "Unrealized Gain/Loss": "Mark-to-market gain or loss on current holdings.",
            "Realized Gain/Loss": "Booked gain or loss already realized for the stock.",
        },
    )
    add_widget_tooltip(
        curr_tree,
        "Current holdings with live prices and realized/unrealized performance.",
    )
    add_widget_tooltip(
        curr_invested_label,
        "Current invested cost basis for all open holdings.",
    )
    add_widget_tooltip(
        curr_val_label, "Latest live market value for all open holdings."
    )
    add_widget_tooltip(
        curr_unrealized_label,
        "Mark-to-market gain or loss across current holdings.",
    )
    add_widget_tooltip(
        curr_realized_label,
        "Booked gain or loss already realized across holdings.",
    )

    # --- TAB 4: Portfolio Allocation ---
    tab_allocation = ttk.Frame(notebook)
    notebook.add(tab_allocation, text="🥧 Portfolio Allocation")

    alloc_paned = ttk.PanedWindow(tab_allocation, orient=tk.HORIZONTAL)
    alloc_paned.pack(fill="both", expand=True, padx=10, pady=10)

    # Sector Allocation
    sector_frame = ttk.LabelFrame(alloc_paned, text="Allocation by Sector")
    alloc_paned.add(sector_frame, weight=1)

    sector_cols = ("Sector", "Market Value", "Weight (%)")
    sector_tree = ttk.Treeview(
        sector_frame, columns=sector_cols, show="headings", selectmode="browse"
    )
    sector_scroll = ttk.Scrollbar(
        sector_frame, orient="vertical", command=sector_tree.yview
    )
    sector_tree.configure(yscrollcommand=sector_scroll.set)
    sector_tree.pack(side="left", fill="both", expand=True)
    sector_scroll.pack(side="right", fill="y")
    configure_tree_columns(
        sector_tree,
        sector_cols,
        widths={
            "Sector": {"width": 200, "anchor": "w"},
            "Market Value": {"width": 150, "anchor": "e"},
            "Weight (%)": {"width": 100, "anchor": "e"},
        },
    )
    add_tree_heading_tooltips(
        sector_tree,
        {
            "Sector": "Industrial or economic sector classification.",
            "Market Value": "Total live market value of all holdings in this sector.",
            "Weight (%)": "Percentage of the total portfolio value.",
        },
    )
    add_widget_tooltip(
        sector_tree,
        "Portfolio allocation grouped by sector.",
    )

    # Stock Allocation
    stock_alloc_frame = ttk.LabelFrame(alloc_paned, text="Allocation by Stock")
    alloc_paned.add(stock_alloc_frame, weight=1)

    stock_alloc_cols = ("Stock", "Market Value", "Weight (%)")
    stock_alloc_tree = ttk.Treeview(
        stock_alloc_frame,
        columns=stock_alloc_cols,
        show="headings",
        selectmode="browse",
    )
    stock_alloc_scroll = ttk.Scrollbar(
        stock_alloc_frame, orient="vertical", command=stock_alloc_tree.yview
    )
    stock_alloc_tree.configure(yscrollcommand=stock_alloc_scroll.set)
    stock_alloc_tree.pack(side="left", fill="both", expand=True)
    stock_alloc_scroll.pack(side="right", fill="y")
    configure_tree_columns(
        stock_alloc_tree,
        stock_alloc_cols,
        widths={
            "Stock": {"width": 200, "anchor": "w"},
            "Market Value": {"width": 150, "anchor": "e"},
            "Weight (%)": {"width": 100, "anchor": "e"},
        },
    )
    add_tree_heading_tooltips(
        stock_alloc_tree,
        {
            "Stock": "Individual holding symbol.",
            "Market Value": "Live market value of the holding.",
            "Weight (%)": "Percentage of the total portfolio value.",
        },
    )
    add_widget_tooltip(
        stock_alloc_tree,
        "Portfolio concentration broken down by individual stock.",
    )

    # --- TAB 5: Master Reconciliation & Ledger ---
    tab_master = ttk.Frame(notebook)
    notebook.add(tab_master, text="📚 Portfolio Ledgers")

    master_notebook = ttk.Notebook(tab_master)
    master_notebook.pack(fill="both", expand=True, padx=10, pady=10)

    # --- IMPLEMENT TOOLTIPS HERE ---
    tab_tooltips = {
        0: "Stock-wise analysis with detailed performance, ledgers, and stock-specific drill-down tabs.",
        1: "Portfolio-level yearly return and capital-flow summaries.",
        2: "Active holdings with current cost basis, live value, and gain/loss tracking.",
        3: "Portfolio concentration and allocation breakdowns by sector and individual stock weightings.",
        4: "Portfolio-wide ledgers covering trades, dividends, and corporate actions.",
    }
    NotebookTooltip(notebook, tab_tooltips)
    add_widget_tooltip(
        notebook,
        "Use the main tabs to switch between stock-wise analysis, portfolio summary, current holdings, and portfolio ledgers.",
    )

    # Master Ledger
    tab_master_ledger = ttk.Frame(master_notebook)
    master_notebook.add(tab_master_ledger, text="📓 All Holding Transactions")
    master_ledger_cols = (
        "Cont No",
        "Company",
        "Trade Date",
        "Trade Type",
        "Debit / Credit",
        "Quantity",
        "WAP",
        "Net Payment",
    )
    master_ledger_tree = ttk.Treeview(
        tab_master_ledger, columns=master_ledger_cols, show="headings"
    )
    ml_scroll = ttk.Scrollbar(
        tab_master_ledger, orient="vertical", command=master_ledger_tree.yview
    )
    master_ledger_tree.configure(yscrollcommand=ml_scroll.set)
    master_ledger_tree.pack(side="left", fill="both", expand=True)
    ml_scroll.pack(side="right", fill="y")
    configure_tree_columns(
        master_ledger_tree,
        master_ledger_cols,
        widths={
            "Cont No": {"width": 150, "anchor": "w", "minwidth": 80},
            "Company": {"width": 250, "anchor": "w", "minwidth": 120},
            "WAP": {"width": 110, "anchor": "e", "minwidth": 60},
            "Net Payment": {"width": 130, "anchor": "e", "minwidth": 70},
        },
    )
    add_tree_heading_tooltips(
        master_ledger_tree,
        {
            "Cont No": "Broker contract note number for this trade.",
            "Company": "Company tied to the transaction.",
            "Trade Date": "Trade or settlement date for the ledger entry.",
            "Trade Type": "BUY, SELL, or another transaction type recorded in the master ledger.",
            "Debit / Credit": "Direction of the quantity movement.",
            "Quantity": "Number of shares moved by the transaction.",
            "WAP": "Weighted average price per unit for this trade.",
            "Net Payment": "Net amount paid or received for this trade.",
        },
    )
    add_widget_tooltip(
        master_ledger_tree,
        "Complete portfolio-wide transaction ledger across all companies.",
    )

    # Master Corp Actions
    tab_master_corp = ttk.Frame(master_notebook)
    master_notebook.add(tab_master_corp, text="🎁 Broker Corporate Actions")
    master_corp_cols = (
        "Company",
        "Event Date",
        "Action Type",
        "Ratio / Value",
        "Tax Deducted",
    )
    master_corp_tree = ttk.Treeview(
        tab_master_corp, columns=master_corp_cols, show="headings"
    )
    mc_scroll = ttk.Scrollbar(
        tab_master_corp, orient="vertical", command=master_corp_tree.yview
    )
    master_corp_tree.configure(yscrollcommand=mc_scroll.set)
    master_corp_tree.pack(side="left", fill="both", expand=True)
    mc_scroll.pack(side="right", fill="y")
    configure_tree_columns(
        master_corp_tree,
        master_corp_cols,
        widths={
            "Company": {"width": 250, "anchor": "w", "minwidth": 120},
            "Action Type": {"width": 180},
            "Ratio / Value": {"width": 220},
        },
    )
    add_tree_heading_tooltips(
        master_corp_tree,
        {
            "Company": "Company tied to the corporate action.",
            "Event Date": "Effective date of the corporate action.",
            "Action Type": "Type of corporate action recorded in the broker-backed history.",
            "Ratio / Value": "Cash value, ratio, or descriptive amount tied to the action.",
            "Tax Deducted": "Any tax deducted at source recorded for the action.",
        },
    )
    add_widget_tooltip(
        master_corp_tree,
        "Portfolio-wide corporate action history sourced from broker-backed records.",
    )

    tab_master_dividend = ttk.Frame(master_notebook)
    master_notebook.add(tab_master_dividend, text="💸 Dividend Ledger")
    master_dividend_cols = (
        "Stock",
        "Date",
        "Eligible Shares",
        "div/share",
        "Invested Amount",
        "Dividend Amount",
        "Return (%)",
        "Annualized Return (%)",
    )
    master_dividend_content = ttk.Frame(tab_master_dividend)
    master_dividend_content.pack(fill="both", expand=True)
    master_dividend_tree = ttk.Treeview(
        master_dividend_content,
        columns=master_dividend_cols,
        show="headings",
    )
    md_scroll = ttk.Scrollbar(
        master_dividend_content,
        orient="vertical",
        command=master_dividend_tree.yview,
    )
    master_dividend_tree.configure(yscrollcommand=md_scroll.set)
    master_dividend_tree.pack(side="left", fill="both", expand=True)
    md_scroll.pack(side="right", fill="y")
    configure_tree_columns(
        master_dividend_tree,
        master_dividend_cols,
        widths={
            "Stock": {"width": 180, "anchor": "w", "minwidth": 100},
            "Date": {"width": 110, "anchor": "center"},
            "Eligible Shares": {"width": 120, "anchor": "e"},
            "div/share": {"width": 110, "anchor": "e"},
            "Invested Amount": {"width": 150, "anchor": "e"},
            "Dividend Amount": {"width": 140, "anchor": "e"},
            "Return (%)": {"width": 100, "anchor": "e"},
            "Annualized Return (%)": {"width": 150, "anchor": "e"},
        },
    )
    configure_summary_row(master_dividend_tree)
    add_tree_heading_tooltips(
        master_dividend_tree,
        {
            "Stock": "Stock for which the dividend was credited.",
            "Date": "Credit Date on which the dividend was paid/credited.",
            "Eligible Shares": "Shares eligible for the dividend on the record date.",
            "div/share": "Dividend amount per share.",
            "Invested Amount": "Invested cost linked to the eligible shares.",
            "Dividend Amount": "Net dividend amount credited.",
            "Return (%)": "Dividend amount as a percentage of the linked invested amount.",
            "Annualized Return (%)": "Dividend return annualized using the weighted holding period.",
        },
    )
    add_widget_tooltip(
        master_dividend_tree,
        "Portfolio-wide dividend ledger with return metrics.",
    )
    master_dividend_footnote = tk.Label(
        tab_master_dividend,
        text=MASTER_DIVIDEND_TABLE_FOOTNOTE,
        bg="#0f172a",
        fg="#f8fafc",
        font=("Helvetica", 12, "bold"),
        justify="left",
        anchor="w",
        wraplength=1,
        padx=10,
        pady=8,
    )
    master_dividend_footnote.pack(fill="x", side="bottom")
    tab_master_dividend.bind(
        "<Configure>",
        lambda e: master_dividend_footnote.configure(
            wraplength=max(e.width - 24, 200)
        ),
    )
    add_widget_tooltip(
        master_dividend_footnote,
        "Legend explaining the dividend ledger abbreviations and return metrics.",
    )

    tab_master_online_corp = ttk.Frame(master_notebook)
    master_notebook.add(
        tab_master_online_corp, text="🌐 Online Corporate Actions"
    )
    master_online_corp_cols = (
        "Company",
        "Event Date",
        "Action Type",
        "Ratio / Value",
        "Source",
        "DB Match",
    )
    master_online_corp_tree = ttk.Treeview(
        tab_master_online_corp,
        columns=master_online_corp_cols,
        show="headings",
    )
    master_online_corp_tree.tag_configure("missing", foreground="#ef4444", font=("Helvetica", 11, "bold"))
    master_online_corp_tree.tag_configure("matched", foreground="#27ae60", font=("Helvetica", 11))
    
    moc_scroll = ttk.Scrollbar(
        tab_master_online_corp,
        orient="vertical",
        command=master_online_corp_tree.yview,
    )
    master_online_corp_tree.configure(yscrollcommand=moc_scroll.set)
    master_online_corp_tree.pack(side="left", fill="both", expand=True)
    moc_scroll.pack(side="right", fill="y")
    configure_tree_columns(
        master_online_corp_tree,
        master_online_corp_cols,
        widths={
            "Company": {"width": 250, "anchor": "w", "minwidth": 120},
            "Action Type": {"width": 180},
            "Ratio / Value": {"width": 180},
            "Source": {"width": 140},
            "DB Match": {"width": 180},
        },
    )
    add_tree_heading_tooltips(
        master_online_corp_tree,
        {
            "Company": "Company tied to the online corporate action.",
            "Event Date": "Effective date published by the online source.",
            "Action Type": "Type of online corporate action detected.",
            "Ratio / Value": "Ratio, cash value, or descriptive amount from the source.",
            "Source": "External source used to detect the action.",
            "DB Match": "Matching status in local database.",
        },
    )
    add_widget_tooltip(
        master_online_corp_tree,
        "Portfolio-wide online corporate actions detected from external sources.",
    )

    master_tooltips = {
        0: "Portfolio-wide ledger of all holding transactions.",
        1: "Portfolio-wide broker-backed corporate action history.",
        2: "Portfolio-wide dividend ledger with return metrics.",
        3: "Portfolio-wide online corporate actions from external sources.",
    }
    NotebookTooltip(master_notebook, master_tooltips)
    add_widget_tooltip(
        master_notebook,
        "Use the ledger tabs to inspect portfolio-wide trades, dividends, and corporate actions.",
    )
    add_widget_tooltip(
        fy_label,
        "Choose All Years or a specific financial year for the stock-wise analysis views.",
    )
    add_widget_tooltip(
        fy_combo,
        "Filters the stock-wise analysis panels to the selected financial year. Portfolio-level summary tables remain multi-year.",
    )
    add_widget_tooltip(
        status_label,
        "Background loading and calculation status for the reporting dashboard.",
    )

    stock_data_cache = {}
    last_focused_items = {}

    def fetch_live_data(ticker):
        if not ticker or yf is None:
            return {"price": 0.0, "high52": 0.0, "low52": 0.0}
        try:
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(period="1d")
            close_price = hist["Close"].iloc[-1] if not hist.empty else 0.0

            try:
                fast_info = ticker_obj.fast_info
            except Exception:
                fast_info = {}

            return build_live_market_snapshot(close_price, fast_info)
        except Exception as e:
            logger.debug(f"Failed to fetch data for {ticker}: {e}")
        return {"price": 0.0, "high52": 0.0, "low52": 0.0}

    def load_data():
        nonlocal stock_data_cache, last_focused_items
        last_focused_items.clear()
        selected_fy = fy_var.get()
        is_yearly, start_date, end_date = resolve_reporting_period(selected_fy)

        filter_start_dt, filter_end_dt = resolve_optional_date_filters(
            start_date,
            end_date,
        )

        pnl_win.after(
            0,
            lambda: status_label.config(text="Status: Fetching DB records..."),
        )
        pnl_win.after(0, lambda: tree.delete(*tree.get_children()))
        pnl_win.after(0, lambda: sum_tree.delete(*sum_tree.get_children()))
        pnl_win.after(0, lambda: stats_tree.delete(*stats_tree.get_children()))
        pnl_win.after(0, lambda: curr_tree.delete(*curr_tree.get_children()))
        pnl_win.after(
            0, lambda: sector_tree.delete(*sector_tree.get_children())
        )
        pnl_win.after(
            0,
            lambda: stock_alloc_tree.delete(*stock_alloc_tree.get_children()),
        )
        pnl_win.after(
            0, lambda: curr_invested_var.set("Current Cost Basis: ₹0.00")
        )
        pnl_win.after(0, lambda: curr_val_var.set("Live Market Value: ₹0.00"))
        pnl_win.after(
            0,
            lambda: curr_unrealized_var.set("Unrealized Gain/Loss: ₹0.00"),
        )
        pnl_win.after(
            0, lambda: curr_realized_var.set("Realized Gain/Loss: ₹0.00")
        )
        pnl_win.after(
            0,
            lambda: master_ledger_tree.delete(
                *master_ledger_tree.get_children()
            ),
        )
        pnl_win.after(
            0,
            lambda: master_corp_tree.delete(*master_corp_tree.get_children()),
        )
        pnl_win.after(
            0,
            lambda: master_dividend_tree.delete(
                *master_dividend_tree.get_children()
            ),
        )
        pnl_win.after(
            0,
            lambda: master_online_corp_tree.delete(
                *master_online_corp_tree.get_children()
            ),
        )
        stock_data_cache.clear()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            if is_yearly:
                cursor.execute(
                    "SELECT DISTINCT id_stk FROM sell_records WHERE sell_dt BETWEEN ? AND ?",
                    (start_date, end_date),
                )
                valid_ids = [row[0] for row in cursor.fetchall()]
                if not valid_ids:
                    pnl_win.after(
                        0,
                        lambda: status_label.config(
                            text=f"Status: No realized trades in {selected_fy}."
                        ),
                    )
                    return
                stocks = fetch_report_stock_rows(cursor, valid_ids)
            else:
                stocks = fetch_report_stock_rows(cursor)

            stock_data_cache, grand_realized = initialize_stock_data_cache(
                cursor, stocks, is_yearly, start_date, end_date
            )

        for id_stk, data in stock_data_cache.items():
            disp_name = (
                data["ticker"] if data["ticker"] else data["short_name"]
            )
            initial_tree_row = build_stock_tree_initial_row(
                display_name=disp_name,
                realized=data["realized"],
                is_yearly=is_yearly,
                current_qty=data["qty"],
            )
            val = ("➕",) + tuple(initial_tree_row)
            pnl_win.after(
                0,
                lambda r=id_stk, values=val: tree.insert(
                    "",
                    "end",
                    iid=str(r),
                    values=values,
                ),
            )

        pnl_win.after(
            0,
            lambda v=build_grand_summary_row(
                grand_realized=grand_realized
            ): tree.insert(
                "",
                0,
                iid="SUMMARY",
                values=("",) + tuple(v),
                tags=("summary",),
            ),
        )
        pnl_win.after(
            0,
            lambda: tree.tag_configure(
                "summary", background="#f1c40f", font=("Helvetica", 13, "bold")
            ),
        )

        # Phase 2: Live Prices
        grand_unrealized = 0.0

        # Track totals for Current tab
        curr_total_invested = 0.0
        curr_total_value = 0.0
        curr_total_unrealized = 0.0
        curr_total_realized = 0.0

        if not is_yearly:
            pnl_win.after(
                0,
                lambda: status_label.config(
                    text="Status: Fetching Live Prices from Web (Parallel)..."
                ),
            )

            # --- NEW: Parallel Network Fetching ---
            market_data_results = {}
            tickers_to_fetch = [
                d["ticker"] for d in stock_data_cache.values() if d["ticker"]
            ]

            def fetch_and_map(tkr):
                return tkr, fetch_live_data(tkr)

            # Dispatch 10 requests at the exact same time
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=10
            ) as executor:
                futures = {
                    executor.submit(fetch_and_map, tkr): tkr
                    for tkr in tickers_to_fetch
                }
                for future in concurrent.futures.as_completed(futures):
                    try:
                        tkr, m_data = future.result()
                        market_data_results[tkr] = m_data
                    except Exception:
                        pass

            for id_stk, data in list(stock_data_cache.items()):
                if data["ticker"]:
                    # Grab the pre-downloaded data from our fast dictionary
                    market_data = market_data_results.get(
                        data["ticker"],
                        {"price": 0.0, "high52": 0.0, "low52": 0.0},
                    )
                    data.update(market_data)

                    # Core Calculations
                    if data["qty"] > 0:
                        cost = data["inv_amt"]
                        avg_price = cost / data["qty"]

                        if data["price"] > 0:
                            current_value = data["qty"] * data["price"]
                            data["unrealized"] = current_value - cost
                            data["total"] = (
                                data["realized"] + data["unrealized"]
                            )
                            grand_unrealized += data["unrealized"]

                            # Update Phase 1 tree item
                            disp_name = (
                                data["ticker"]
                                if data["ticker"]
                                else data["short_name"]
                            )
                            updated_tree_row = build_stock_tree_update_row(
                                display_name=disp_name,
                                realized=data["realized"],
                                total=data["total"],
                                unrealized=data["unrealized"],
                                xirr_rate=None,
                                show_unrealized=True,
                            )
                            val = ("➕",) + tuple(updated_tree_row)
                            pnl_win.after(
                                0,
                                lambda i=id_stk, values=val: (
                                    tree.item(
                                        str(i),
                                        values=values,
                                    )
                                    if tree.winfo_exists()
                                    and tree.exists(str(i))
                                    else None
                                ),
                            )
                        else:
                            current_value = 0.0

                        # Accumulate Header Totals
                        curr_total_invested += cost
                        curr_total_value += current_value
                        curr_total_unrealized += data["unrealized"]
                        curr_total_realized += data["realized"]

                        current_holding_row = build_current_holdings_row(
                            data,
                            avg_price=avg_price,
                            cost=cost,
                            stt_paid=data.get(
                                "stt_paid", 0.0
                            ),  # Pass stock-specific STT
                        )

                        pnl_win.after(
                            0,
                            lambda row=current_holding_row: (
                                curr_tree.insert(
                                    "",
                                    "end",
                                    values=row["values"],
                                    tags=(row["tag"],),
                                )
                                if curr_tree.winfo_exists()
                                else None
                            ),
                        )

            pnl_win.after(
                0,
                lambda v=build_grand_summary_row(
                    grand_realized=grand_realized,
                    grand_unrealized=grand_unrealized,
                ): tree.item(
                    "SUMMARY",
                    values=("",) + tuple(v),
                ),
            )

            allocation_data = build_allocation_tree_rows(
                stock_data_cache, curr_total_value
            )
            for row in allocation_data["sector_rows"]:
                pnl_win.after(
                    0,
                    lambda v=row: (
                        sector_tree.insert("", "end", values=v)
                        if sector_tree.winfo_exists()
                        else None
                    ),
                )
            for row in allocation_data["stock_rows"]:
                pnl_win.after(
                    0,
                    lambda v=row: (
                        stock_alloc_tree.insert("", "end", values=v)
                        if stock_alloc_tree.winfo_exists()
                        else None
                    ),
                )

            # Calculate the aggregate STT for all currently held positions
            total_held_stt = sum(
                d["stt_paid"]
                for d in stock_data_cache.values()
                if d["qty"] > 0
            )

            current_header_values = build_current_holdings_header_values(
                total_invested=curr_total_invested,
                total_value=curr_total_value,
                total_unrealized=curr_total_unrealized,
                total_realized=curr_total_realized,
                total_invested_ex_stt=curr_total_invested - total_held_stt,
            )

            pnl_win.after(
                0,
                lambda text=current_header_values[
                    "invested"
                ]: curr_invested_var.set(text),
            )
            pnl_win.after(
                0,
                lambda text=current_header_values["value"]: curr_val_var.set(
                    text
                ),
            )
            pnl_win.after(
                0,
                lambda text=current_header_values[
                    "unrealized"
                ]: curr_unrealized_var.set(text),
            )
            pnl_win.after(
                0,
                lambda color=current_header_values[
                    "unrealized_color"
                ]: curr_header_frame.winfo_children()[2].config(fg=color),
            )
            pnl_win.after(
                0,
                lambda text=current_header_values[
                    "realized"
                ]: curr_realized_var.set(text),
            )

        # Phase 3: XIRR & Cumulative Summary Data
        pnl_win.after(
            0,
            lambda: status_label.config(
                text="Status: Computing XIRR & Portfolio Summary..."
            ),
        )

        summary_agg = (
            {}
        )  # format: { 'FY 23-24': {'inv': 0, 'pnl': 0, 'pat': 0, 'div': 0, 'miss_profit': 0, 'save_loss': 0} }

        for id_stk, data in list(stock_data_cache.items()):
            with get_db_connection() as conn:
                cursor = conn.cursor()
                purchases, sells = fetch_position_cashflow_rows(
                    cursor,
                    id_stk,
                    start_date if is_yearly else None,
                    end_date if is_yearly else None,
                )

                xirr_rate = compute_position_xirr(
                    purchases,
                    sells,
                    current_qty=data["qty"],
                    current_price=data["price"],
                    include_live_position=not is_yearly,
                )
                data["xirr"] = xirr_rate

                disp_name = (
                    data["ticker"] if data["ticker"] else data["short_name"]
                )
                updated_tree_row = build_stock_tree_update_row(
                    display_name=disp_name,
                    realized=data["realized"],
                    total=data["total"],
                    unrealized=data["unrealized"],
                    xirr_rate=xirr_rate,
                    show_unrealized=not is_yearly and data["qty"] > 0,
                )
                val = ("➕",) + tuple(updated_tree_row)
                pnl_win.after(
                    0,
                    lambda i=id_stk, values=val: (
                        tree.item(
                            str(i),
                            values=values,
                        )
                        if tree.exists(str(i))
                        else None
                    ),
                )

        # Build Global Summary
        with get_db_connection() as conn:
            cursor = conn.cursor()

            all_sells = fetch_global_sell_records(cursor)
            investment_rows = fetch_global_buy_transactions(cursor)
            dividend_rows = fetch_global_dividends(cursor)

            summary_agg = build_portfolio_summary(
                sell_rows=all_sells,
                investment_rows=investment_rows,
                dividend_rows=dividend_rows,
                stock_prices={
                    id_stk: data.get("price", 0.0)
                    for id_stk, data in stock_data_cache.items()
                },
                capital_gains_tax_rates=get_capital_gains_tax_rates,
            )

            investment_rows = fetch_global_investment_stats_buys(cursor)
            disinvestment_rows = fetch_global_investment_stats_sells(cursor)

        capital_stats = calculate_investment_summary_stats(
            investment_rows, disinvestment_rows
        )

        summary_tree_rows = build_summary_tree_rows(summary_agg)
        for row in summary_tree_rows["yearly_rows"]:
            pnl_win.after(
                0,
                lambda v=row: sum_tree.insert("", "end", values=v),
            )
        pnl_win.after(
            0,
            lambda v=summary_tree_rows["summary_row"]: sum_tree.insert(
                "",
                0,
                values=v,
                tags=("summary",),
            ),
        )
        pnl_win.after(
            0,
            lambda: sum_tree.tag_configure(
                "summary", background="#f1c40f", font=("Helvetica", 13, "bold")
            ),
        )

        capital_stats_tree_rows = build_capital_stats_tree_rows(
            capital_stats,
            financial_year_sort_key=financial_year_sort_key,
        )
        pnl_win.after(
            0,
            lambda v=capital_stats_tree_rows["summary_row"]: stats_tree.insert(
                "",
                0,
                values=v,
                tags=("summary",),
            ),
        )
        for row in capital_stats_tree_rows["yearly_rows"]:
            pnl_win.after(
                0,
                lambda v=row: stats_tree.insert("", "end", values=v),
            )

        # --- Phase 4: Populate Master Reconciliation Trees ---
        pnl_win.after(
            0,
            lambda: status_label.config(
                text="Status: Loading Master Ledgers..."
            ),
        )
        with get_db_connection() as conn:
            m_cursor = conn.cursor()
            m_params = (start_date, end_date) if is_yearly else ()

            for row in build_master_ledger_display_rows(
                fetch_master_ledger_rows(
                    m_cursor, *(m_params if is_yearly else ())
                ),
                date_formatter=safe_fmt_date,
            ):
                pnl_win.after(
                    0,
                    lambda v=row: (
                        master_ledger_tree.insert("", "end", values=v)
                        if master_ledger_tree.winfo_exists()
                        else None
                    ),
                )

            master_corp_records = []
            master_dividend_data = build_master_dividend_display_data(
                fetch_master_dividend_source_rows(
                    m_cursor, *(m_params if is_yearly else ())
                ),
                metric_resolver=lambda stock_id, record_dt, credit_dt, entitled_qty, gross_amt: (
                    compute_dividend_return_percent(
                        id_stk=stock_id,
                        record_dt=record_dt,
                        entitled_qty=entitled_qty,
                        gross_dividend_amount=gross_amt,
                        cursor=m_cursor,
                    ),
                    compute_dividend_annualized_yield(
                        id_stk=stock_id,
                        record_dt=record_dt,
                        credit_dt=credit_dt,
                        entitled_qty=entitled_qty,
                        gross_dividend_amount=gross_amt,
                        cursor=m_cursor,
                    ),
                ),
            )
            master_split_rows = []
            master_bonus_rows = []

            try:
                master_split_rows = fetch_master_split_rows(
                    m_cursor, *(m_params if is_yearly else ())
                )
            except sqlite3.OperationalError:
                pass

            try:
                master_bonus_rows = fetch_master_bonus_rows(
                    m_cursor, *(m_params if is_yearly else ())
                )
            except sqlite3.OperationalError:
                pass

            master_corp_records = build_master_corp_action_records(
                master_dividend_data["corp_records"],
                master_split_rows,
                master_bonus_rows,
            )

            for row in build_master_corp_tree_rows(
                master_corp_records,
                date_formatter=safe_fmt_date,
            ):
                pnl_win.after(
                    0,
                    lambda v=row: (
                        master_corp_tree.insert(
                            "",
                            "end",
                            values=v,
                        )
                        if master_corp_tree.winfo_exists()
                        else None
                    ),
                )

            master_dividend_tree_rows = build_master_dividend_tree_rows(
                master_dividend_data
            )
            if master_dividend_tree_rows["summary_row"]:
                pnl_win.after(
                    0,
                    lambda v=master_dividend_tree_rows["summary_row"]: (
                        master_dividend_tree.insert(
                            "",
                            0,
                            values=v,
                            tags=("summary",),
                        )
                        if master_dividend_tree.winfo_exists()
                        else None
                    ),
                )

            for row in master_dividend_tree_rows["detail_rows"]:
                pnl_win.after(
                    0,
                    lambda v=row: (
                        master_dividend_tree.insert("", "end", values=v)
                        if master_dividend_tree.winfo_exists()
                        else None
                    ),
                )

            pnl_win.after(
                0, lambda: autosize_treeview_columns(master_corp_tree)
            )
            pnl_win.after(
                0, lambda: autosize_treeview_columns(master_dividend_tree)
            )

        # --- YFINANCE MASTER RECONCILIATION THREAD ---
        def fetch_all_master_yahoo_actions():
            if not yf:
                pnl_win.after(
                    0,
                    lambda: (
                        status_label.config(
                            text="Status: Fetching online corporate actions in background..."
                        )
                        if status_label.winfo_exists()
                        else None
                    ),
                )
                return

            pnl_win.after(
                0,
                lambda: status_label.config(
                    text="Status: Fetching online corporate actions in background..."
                ),
            )
            import pandas as pd

            try:
                with get_db_connection() as conn_y:
                    cur_y = conn_y.cursor()
                    cur_y.execute(
                        "SELECT id_stk, ticker, short_name, current_qty FROM stocks WHERE ticker != ''"
                    )
                    all_stocks = cur_y.fetchall()

                for s_id, tkr, s_name, curr_qty in all_stocks:
                    try:
                        # 1. Get Holding Period bounds for this stock
                        with get_db_connection() as conn_b:
                            cur_b = conn_b.cursor()
                            bounds = fetch_holding_bounds(cur_b, s_id)

                        if not bounds:
                            continue

                        action_window = resolve_action_window(
                            bounds[0],
                            bounds[1],
                            current_qty=curr_qty,
                            filter_start=filter_start_dt,
                            filter_end=filter_end_dt,
                        )

                        if not action_window:
                            continue
                        actual_start, actual_end = action_window

                        # 2. Fetch Data
                        ticker_obj = yf.Ticker(tkr)
                        actions = ticker_obj.actions

                        if actions is None or actions.empty:
                            continue

                        actions.index = pd.to_datetime(
                            actions.index
                        ).tz_localize(None)
                        mask = (actions.index >= actual_start) & (
                            actions.index <= actual_end
                        )
                        relevant_actions = actions.loc[mask]

                        with get_db_connection() as conn_b:
                            cur_b = conn_b.cursor()
                            db_actions = fetch_db_corp_actions_for_matching(cur_b, s_id)
                        online_rows, _ = build_online_corp_action_rows(
                            build_online_action_entries(
                                relevant_actions.iterrows(),
                                date_formatter=lambda value: format_date_for_display(
                                    value,
                                    "%d-%m-%Y",
                                ),
                            ),
                            db_actions,
                            display_name=(tkr if tkr else s_name),
                        )
                        for values in online_rows:
                            tag = "missing" if "Missing" in values[-1] else "matched"
                            pnl_win.after(
                                0,
                                lambda v=values, t=tag: (
                                    master_online_corp_tree.insert(
                                        "", "end", values=v, tags=(t,)
                                    )
                                    if master_online_corp_tree.winfo_exists()
                                    else None
                                ),
                            )

                    except Exception as e:
                        logger.debug(
                            f"Master Yahoo fetch failed for {tkr}: {e}"
                        )

            except Exception as e:
                logger.error(f"Master Yahoo fetch thread failed: {e}")

            pnl_win.after(
                0,
                lambda: (
                    status_label.config(
                        text="Status: Ready (All Data & Online Actions Loaded)"
                    )
                    if status_label.winfo_exists()
                    else None
                ),
            )
            pnl_win.after(
                0, lambda: autosize_treeview_columns(master_online_corp_tree)
            )

        # Launch the master fetcher in a background thread so it doesn't freeze the UI
        threading.Thread(
            target=fetch_all_master_yahoo_actions, daemon=True
        ).start()

        pnl_win.after(
            0,
            lambda: (
                restore_or_default_focus(notebook),
                restore_or_default_focus(detail_notebook),
                restore_or_default_focus(master_notebook),
            )
        )

    def generate_detail(id_stk):
        data = stock_data_cache.get(int(id_stk))
        if not data:
            return

        for t in (ledger_tree, corp_tree, dividend_tree, online_corp_tree):
            last_focused_items.pop(t, None)

        selected_fy = fy_var.get()
        is_yearly, start_date, end_date = resolve_reporting_period(selected_fy)

        report_text.config(state="normal")
        report_text.delete("1.0", tk.END)
        ledger_tree.delete(*ledger_tree.get_children())
        corp_tree.delete(*corp_tree.get_children())
        dividend_tree.delete(*dividend_tree.get_children())
        online_corp_tree.delete(*online_corp_tree.get_children())

        for text, tag in build_detail_header_fragments(
            data,
            is_yearly=is_yearly,
        ):
            report_text.insert(tk.END, text, tag)

        with get_db_connection() as conn:
            cursor = conn.cursor()

            def insert_fragments(fragments):
                for text, tag in fragments:
                    report_text.insert(tk.END, text, tag)

            # Basic stats logic remains similar...
            total_investment, disinvestment_amt = (
                fetch_detail_investment_summary(
                    cursor,
                    id_stk,
                    start_date if is_yearly else None,
                    end_date if is_yearly else None,
                )
            )

            reality_summary = build_pooled_cost_reality_summary(
                fetch_detail_timeline_rows(cursor, id_stk),
                current_price=data["price"],
            )
            has_corp_action = has_corporate_action_history(cursor, id_stk)

            # --- Live Price & Position Metrics ---
            if data["qty"] > 0:
                position_metrics = compute_current_position_metrics(
                    data["qty"],
                    data["inv_amt"],
                    data["price"],
                    data["realized"],
                )
                data["unrealized"] = position_metrics["unrealized"]
                data["total"] = position_metrics["total"]
            else:
                data["total"] = data["realized"]

            insert_fragments(
                build_report_value_fragments(
                    f"Invested in {selected_fy}:", total_investment
                )
            )
            insert_fragments(
                build_report_value_fragments(
                    f"Disinvested in {selected_fy}:", disinvestment_amt
                )
            )

            report_text.insert(tk.END, "\n")

            if is_yearly:
                insert_fragments(
                    build_report_value_fragments(
                        "Realized Profit/Loss:", data["realized"]
                    )
                )
            else:
                insert_fragments(
                    build_report_value_fragments(
                        "Realized Profit/Loss:",
                        data["realized"],
                        reality_summary["realized_pnl"],
                    )
                )
                insert_fragments(
                    build_report_value_fragments(
                        "Unrealized Profit/Loss:",
                        data["unrealized"],
                        reality_summary["unrealized_pnl"],
                    )
                )
                insert_fragments(
                    build_report_value_fragments(
                        "Total Net Profit/Loss:",
                        data["total"],
                        reality_summary["total_pnl"],
                    )
                )

            # Fetch Dividends for the specific stock
            total_divs = fetch_detail_dividend_total(
                cursor,
                id_stk,
                start_date if is_yearly else None,
                end_date if is_yearly else None,
            )
            if total_divs > 0:
                insert_fragments(
                    build_report_value_fragments(
                        "Net Dividends Received:", total_divs
                    )
                )

            realized_details = build_realized_pnl_rows(
                fetch_realized_detail_rows(
                    cursor,
                    id_stk,
                    start_date if is_yearly else None,
                    end_date if is_yearly else None,
                ),
                current_price=data["price"],
                capital_gains_tax_rates=get_capital_gains_tax_rates,
            )
            reality_rows = None
            if has_corp_action and reality_summary["sells"]:
                reality_rows = build_reality_pnl_rows(
                    reality_summary["sells"],
                    current_price=data["price"],
                )
            insert_fragments(
                build_realized_pnl_report_fragments(
                    realized_details,
                    reality_rows=reality_rows,
                )
            )

        report_text.config(state="disabled")

        # --- LEDGER POPULATION (WITH FRESH DB CONNECTION) ---
        with get_db_connection() as conn:
            cursor = conn.cursor()

            ledger_records = fetch_detail_ledger_rows(
                cursor,
                id_stk,
                start_date if is_yearly else None,
                end_date if is_yearly else None,
            )
            for row in build_detail_ledger_tree_rows(
                build_detail_ledger_display_rows(ledger_records),
                date_formatter=safe_fmt_date,
            ):
                ledger_tree.insert("", "end", values=row)

            # --- CORP ACTIONS (DB FIRST) ---
            detail_dividend_data = build_detail_dividend_display_data(
                fetch_detail_dividend_source_rows(
                    cursor,
                    id_stk,
                    start_date if is_yearly else None,
                    end_date if is_yearly else None,
                ),
                display_name=(
                    data["ticker"] if data["ticker"] else data["short_name"]
                ),
                metric_resolver=lambda record_dt, credit_dt, entitled_qty, gross_amt: (
                    compute_dividend_return_percent(
                        id_stk=id_stk,
                        record_dt=record_dt,
                        entitled_qty=entitled_qty,
                        gross_dividend_amount=gross_amt,
                        cursor=cursor,
                    ),
                    compute_dividend_annualized_yield(
                        id_stk=id_stk,
                        record_dt=record_dt,
                        credit_dt=credit_dt,
                        entitled_qty=entitled_qty,
                        gross_dividend_amount=gross_amt,
                        cursor=cursor,
                    ),
                    compute_dividend_holding_days(
                        id_stk=id_stk,
                        record_dt=record_dt,
                        credit_dt=credit_dt,
                        entitled_qty=entitled_qty,
                        cursor=cursor,
                    ),
                ),
            )
            detail_split_rows = []
            detail_bonus_rows = []

            try:
                detail_split_rows = fetch_detail_split_rows(
                    cursor,
                    id_stk,
                    start_date if is_yearly else None,
                    end_date if is_yearly else None,
                )
            except sqlite3.OperationalError:
                pass

            try:
                detail_bonus_rows = fetch_detail_bonus_rows(
                    cursor,
                    id_stk,
                    start_date if is_yearly else None,
                    end_date if is_yearly else None,
                )
            except sqlite3.OperationalError:
                pass

            db_corp_records = build_detail_corp_action_records(
                detail_dividend_data["corp_records"],
                detail_split_rows,
                detail_bonus_rows,
            )

            for row in build_detail_corp_tree_rows(
                db_corp_records,
                date_formatter=safe_fmt_date,
            ):
                corp_tree.insert("", "end", values=row)

            detail_dividend_tree_rows = build_detail_dividend_tree_rows(
                detail_dividend_data
            )
            if detail_dividend_tree_rows["summary_row"]:
                dividend_tree.insert(
                    "",
                    0,
                    values=detail_dividend_tree_rows["summary_row"],
                    tags=("summary",),
                )

            for row in detail_dividend_tree_rows["detail_rows"]:
                dividend_tree.insert("", "end", values=row)

            autosize_treeview_columns(corp_tree)
            autosize_treeview_columns(dividend_tree)

        # --- YFINANCE CORPORATE ACTIONS (HOLDING PERIOD) ---
        def fetch_yahoo_actions():
            try:
                # 1. Determine Holding Period
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    bounds = fetch_holding_bounds(cur, id_stk)
                    db_actions = fetch_db_corp_actions_for_matching(cur, id_stk)

                if not bounds:
                    return  # No transactions, silently skip

                action_window = resolve_action_window(
                    bounds[0],
                    bounds[1],
                    current_qty=data["qty"],
                )
                if not action_window:
                    return
                start_date, end_date = action_window

                # 2. Fetch and Filter Data
                online_rows = fetch_and_filter_online_corp_actions(
                    data["ticker"],
                    start_date,
                    end_date,
                    db_actions,
                    yf_lib=yf,
                    pd_lib=pd,
                    date_formatter=lambda value: format_date_for_display(
                        value,
                        "%d-%m-%Y",
                    ),
                )

                for values in online_rows:
                    tag = "missing" if "Missing" in values[-1] else "matched"
                    pnl_win.after(
                        0,
                        lambda v=values, t=tag: online_corp_tree.insert(
                            "", "end", values=v, tags=(t,)
                        ),
                    )

            except Exception as e:
                logger.debug(f"Yahoo Corp Act fetch failed: {e}")

            pnl_win.after(
                0, lambda: autosize_treeview_columns(online_corp_tree)
            )

        threading.Thread(target=fetch_yahoo_actions, daemon=True).start()

        # --- INTRADAY ANALYSIS THREAD ---
        def set_intraday_status(message):
            try:
                if not chart_frame.winfo_exists():
                    return

                intra_ax.clear()
                intra_ax.set_facecolor("#1e2a38")
                intra_ax.tick_params(colors="white")
                intra_ax.grid(color="#555555", linestyle=":", alpha=0.6)
                intra_canvas.draw()

                analysis_text.config(state="normal")
                analysis_text.delete("1.0", tk.END)
                analysis_text.insert(tk.END, message)
                analysis_text.config(state="disabled")
            except tk.TclError:
                pass

        def fetch_intraday_analysis():
            if not yf or not data.get("ticker"):
                pnl_win.after(
                    0,
                    lambda: set_intraday_status(
                        "No ticker available for analysis."
                    ),
                )
                return

            try:
                ticker_obj = yf.Ticker(data["ticker"])
                # Fetching 5-minute intervals for today (Runs safely in background)
                hist = ticker_obj.history(period="1d", interval="5m")

                if hist.empty:
                    pnl_win.after(
                        0,
                        lambda: set_intraday_status(
                            "Intraday data not available for this ticker right now.\n"
                            "The market may be closed, or the data provider may not "
                            "have recent 5-minute data."
                        ),
                    )
                    return

                intraday_analysis = compute_intraday_vwap_analysis(
                    zip(
                        hist["High"],
                        hist["Low"],
                        hist["Close"],
                        hist["Volume"],
                    )
                )
                if not intraday_analysis:
                    pnl_win.after(
                        0,
                        lambda: set_intraday_status(
                            "Intraday data not available for this ticker right now."
                        ),
                    )
                    return

                hist["VWAP"] = intraday_analysis["vwap_values"]
                current_price = intraday_analysis["current_price"]
                current_vwap = intraday_analysis["current_vwap"]
                trend = intraday_analysis["trend"]
                delta_pct = intraday_analysis["delta_pct"]

                # 2. Update UI & Draw Chart (MUST run strictly in the Main Thread)
                def update_analysis_ui():
                    try:
                        if not chart_frame.winfo_exists():
                            return

                        # --- NEW: Clear and redraw instead of destroying widgets ---
                        intra_ax.clear()
                        intra_ax.set_facecolor("#1e2a38")

                        # Ensure index is timezone-naive for safe Matplotlib boundary setting
                        import pandas as pd

                        clean_index = pd.to_datetime(hist.index).tz_localize(
                            None
                        )

                        # Plot Price and VWAP
                        intra_ax.plot(
                            clean_index,
                            hist["Close"],
                            color="#00ff00",
                            label="Price",
                        )
                        intra_ax.plot(
                            clean_index,
                            hist["VWAP"],
                            color="#f1c40f",
                            linestyle="--",
                            label="VWAP",
                        )

                        y_lower, y_upper = compute_intraday_price_bounds(
                            hist["Close"],
                            hist["VWAP"],
                            current_price=current_price,
                        )
                        intra_ax.set_ylim(y_lower, y_upper)

                        chart_window = resolve_intraday_chart_window(
                            list(clean_index)
                        )
                        if chart_window:
                            intra_ax.set_xlim(*chart_window)

                        intra_ax.tick_params(colors="white")
                        intra_ax.legend(loc="upper left")
                        intra_ax.grid(
                            color="#555555", linestyle=":", alpha=0.6
                        )

                        # Redraw existing canvas seamlessly
                        intra_canvas.draw()

                        # Update text console with Education and Analysis
                        analysis_text.config(state="normal")
                        analysis_text.delete("1.0", tk.END)
                        for line in build_intraday_analysis_lines(
                            current_price=current_price,
                            current_vwap=current_vwap,
                            trend=trend,
                            delta_pct=delta_pct,
                        ):
                            analysis_text.insert(tk.END, line)
                        analysis_text.config(state="disabled")
                    except tk.TclError:
                        pass

                # Send the entire drawing command to the Main Thread via the bridge
                pnl_win.after(0, update_analysis_ui)

            except Exception as e:
                logger.debug("Intraday analysis failed: %s", e)
                pnl_win.after(
                    0,
                    lambda: set_intraday_status(
                        "Intraday analysis could not be loaded right now."
                    ),
                )

        # Launch the analyzer in the background
        set_intraday_status("Loading intraday analysis...")
        threading.Thread(target=fetch_intraday_analysis, daemon=True).start()

        pnl_win.after(0, lambda: restore_or_default_focus(detail_notebook))

    def on_tree_select(_event):
        sel = tree.selection()
        if not sel:
            return
        item_id = sel[0]
        if item_id == "SUMMARY":
            report_text.config(state="normal")
            report_text.delete("1.0", tk.END)
            for text, tag in build_summary_selection_fragments():
                report_text.insert(tk.END, text, tag)
            report_text.config(state="disabled")
        else:
            generate_detail(item_id)

    def on_tree_double_click(event):
        region = tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col_id = tree.identify_column(event.x)
        if col_id == "#1":  # First column is WL
            sel = tree.selection()
            if not sel:
                return
            item_id = sel[0]
            if item_id == "SUMMARY":
                return
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT 1 FROM watchlist WHERE id_stk = ?", (item_id,)
                    )
                    if cursor.fetchone():
                        show_colorful_info(
                            pnl_win,
                            "Watchlist",
                            "This stock is already in your watchlist.",
                        )
                    else:
                        cursor.execute(
                            "INSERT INTO watchlist (id_stk) VALUES (?)",
                            (item_id,),
                        )
                        conn.commit()
                        show_colorful_info(
                            pnl_win,
                            "Watchlist",
                            "Stock added to watchlist successfully.",
                        )
            except sqlite3.Error as e:
                show_colorful_error(
                    pnl_win,
                    "Database Error",
                    f"Failed to add to watchlist: {e}",
                )

    def find_active_treeviews(widget):
        if isinstance(widget, ttk.Treeview):
            return [widget]
        if isinstance(widget, ttk.Notebook):
            selected = widget.select()
            if selected:
                try:
                    return find_active_treeviews(widget.nametowidget(selected))
                except Exception:
                    pass
            return []
        
        trees = []
        try:
            children = widget.winfo_children()
        except Exception:
            children = []
        for child in children:
            trees.extend(find_active_treeviews(child))
        return trees

    def select_default_item(tree_widget, retries=50):
        if tree_widget in last_focused_items:
            return
        if not tree_widget.winfo_exists():
            return
        children = tree_widget.get_children()
        if children:
            first_item = children[0]
            tree_widget.selection_set(first_item)
            tree_widget.focus(first_item)
            tree_widget.see(first_item)
            last_focused_items[tree_widget] = first_item
        elif retries > 0:
            tree_widget.after(100, lambda: select_default_item(tree_widget, retries - 1))

    def restore_or_default_focus(nb):
        if not nb.winfo_exists():
            return
        selected_tab_id = nb.select()
        if not selected_tab_id:
            return
        try:
            selected_tab = nb.nametowidget(selected_tab_id)
        except Exception:
            return
        
        active_trees = find_active_treeviews(selected_tab)
        for tree_widget in active_trees:
            if tree_widget in last_focused_items:
                saved_item = last_focused_items[tree_widget]
                if tree_widget.winfo_exists() and tree_widget.exists(saved_item):
                    tree_widget.selection_set(saved_item)
                    tree_widget.focus(saved_item)
                    tree_widget.see(saved_item)
            else:
                select_default_item(tree_widget)

    def on_tab_changed(event):
        nb = event.widget
        if nb in (notebook, detail_notebook, master_notebook):
            restore_or_default_focus(nb)

    def on_any_treeview_select(event):
        tree_widget = event.widget
        try:
            if str(tree_widget).startswith(str(pnl_win)):
                sel = tree_widget.selection()
                if sel:
                    last_focused_items[tree_widget] = sel[0]
        except Exception:
            pass

    def bind_treeview_select(widget):
        if isinstance(widget, ttk.Treeview):
            widget.bind("<<TreeviewSelect>>", on_any_treeview_select, add="+")
        try:
            children = widget.winfo_children()
        except Exception:
            children = []
        for child in children:
            bind_treeview_select(child)

    bind_treeview_select(pnl_win)
    notebook.bind("<<NotebookTabChanged>>", on_tab_changed)
    detail_notebook.bind("<<NotebookTabChanged>>", on_tab_changed)
    master_notebook.bind("<<NotebookTabChanged>>", on_tab_changed)

    tree.bind("<<TreeviewSelect>>", on_tree_select)
    tree.bind("<Double-1>", on_tree_double_click)
    fy_combo.bind(
        "<<ComboboxSelected>>",
        lambda e: threading.Thread(target=load_data, daemon=True).start(),
    )

    threading.Thread(target=load_data, daemon=True).start()
    parent.wait_window(pnl_win)
