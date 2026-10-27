# -*- coding: utf-8 -*-
# StockMan/watchlist_menu.py

"""
Watchlist and Price Alerts UI.
Allows users to track potential investments and set target buy/sell prices.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import threading
import concurrent.futures
import re
import textwrap
import tkinter.font as tkfont
from Shared.help_utils import show_standard_help

try:
    import yfinance as yf
except ImportError:
    yf = None

from Shared.globals import get_db_connection, logger, UI_THEME
from Shared.dialog_utils import (
    show_colorful_error,
    show_colorful_info,
    show_colorful_yesno,
)
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from Shared.gui_utils import apply_button_animations, apply_entry_theme
from Shared.gui_progressive import progressive_selection
from .company_add import add_company
from .company_ex_import import export_company
from .helpers import universal_tree_sort


def auto_adjust_and_wrap_columns(
    tree,
    style_name=None,
    wrap_cols=None,
    max_col_widths=None,
    col_separation=28,
    font_family=None,
    font_size=None,
    hidden_cols=None,
):
    """Auto-adjusts treeview column widths and wraps large text into multiple lines.

    For small text columns, computes maximum width among all cells and heading
    plus generous blank separation. For large text columns, wraps text across
    multiple lines within target width and adjusts rowheight dynamically.
    """
    if wrap_cols is None:
        wrap_cols = set()
    if max_col_widths is None:
        max_col_widths = {}
    if hidden_cols is None:
        hidden_cols = {"ID", "id_stk", "ticker"}

    f_fam = font_family or UI_THEME.get("font_main", ("Helvetica", 12))[0]
    f_sz = font_size or UI_THEME.get("font_main", ("Helvetica", 12))[1]
    font_obj = tkfont.Font(family=f_fam, size=f_sz)
    bold_font_obj = tkfont.Font(family=f_fam, size=f_sz, weight="bold")

    cols = tree["columns"]
    col_widths = {}
    max_lines = 1

    sample_str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    avg_char_w = max(1, font_obj.measure(sample_str) // len(sample_str))

    # Initialize column widths with measured bold heading texts
    for col in cols:
        if col in hidden_cols:
            col_widths[col] = 0
            continue
        heading_dict = tree.heading(col)
        h_text = heading_dict.get("text", col) if heading_dict else col
        col_widths[col] = bold_font_obj.measure(str(h_text)) + col_separation

    # Inspect all rows, wrap designated/large columns, and compute widths
    for item in tree.get_children():
        row_vals = list(tree.item(item, "values"))
        item_lines = 1

        for idx, col in enumerate(cols):
            if idx >= len(row_vals) or col in hidden_cols:
                continue
            val_str = str(row_vals[idx])
            if not val_str or val_str == "-":
                continue

            target_max_w = max_col_widths.get(col, 340)
            measured_w = font_obj.measure(val_str)

            # Wrap if in wrap_cols or if measured width exceeds target width
            if col in wrap_cols or (measured_w > target_max_w and len(val_str) > 30):
                wrap_chars = max(20, target_max_w // avg_char_w)
                paragraphs = val_str.split("\n")
                wrapped_paragraphs = [
                    textwrap.fill(p, width=wrap_chars)
                    for p in paragraphs
                    if p
                ]
                wrapped_text = "\n".join(wrapped_paragraphs)
                row_vals[idx] = wrapped_text

                lines = wrapped_text.split("\n")
                item_lines = max(item_lines, len(lines))
                for line in lines:
                    line_w = font_obj.measure(line) + col_separation
                    col_widths[col] = max(col_widths[col], line_w)
            else:
                col_widths[col] = max(col_widths[col], measured_w + col_separation)

        tree.item(item, values=row_vals)
        max_lines = max(max_lines, item_lines)

    # Apply final column widths
    for col in cols:
        if col in hidden_cols:
            tree.column(col, width=0, stretch=False)
        else:
            tree.column(col, width=col_widths[col])

    # Dynamically scale rowheight based on maximum lines in any cell
    line_h = font_obj.metrics("linespace")
    row_h = max(35, max_lines * line_h + 14)
    if style_name:
        try:
            ttk.Style().configure(style_name, rowheight=row_h)
        except Exception:
            pass
    return col_widths, row_h


def prompt_available_cash_dialog(parent, default_val=100000.0):
    res = {"cash": None}

    dialog = tk.Toplevel(parent)
    dialog.title("💰 Available Cash for Investment Allocation")
    dialog.geometry("560x280")
    dialog.configure(bg="#1e293b")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)

    title_lbl = tk.Label(
        dialog,
        text="💰 Available Cash for Investment Allocation",
        font=("Helvetica", 16, "bold"),
        bg="#1e293b",
        fg="#38bdf8",
    )
    title_lbl.pack(pady=(20, 8))

    desc_lbl = tk.Label(
        dialog,
        text=(
            "Please enter available cash (INR) for new capital deployment:\n"
            "(This will be factored into Pick of the Day sizing, tranches, "
            "and portfolio fit)"
        ),
        font=("Helvetica", 13),
        bg="#1e293b",
        fg="#cbd5e1",
        justify="center",
    )
    desc_lbl.pack(pady=(0, 14))

    entry_frame = tk.Frame(dialog, bg="#1e293b")
    entry_frame.pack(pady=5)

    curr_lbl = tk.Label(
        entry_frame,
        text="₹",
        font=("Helvetica", 18, "bold"),
        bg="#1e293b",
        fg="#fbbf24",
    )
    curr_lbl.pack(side="left", padx=(0, 8))

    cash_var = tk.StringVar(
        value=f"{default_val:,.2f}" if default_val > 0 else "0.00"
    )
    cash_entry = tk.Entry(
        entry_frame,
        textvariable=cash_var,
        font=("Helvetica", 15, "bold"),
        width=20,
        bg="#0f172a",
        fg="#ffffff",
        insertbackground="white",
        justify="right",
    )
    cash_entry.pack(side="left")
    cash_entry.focus_set()
    cash_entry.select_range(0, tk.END)

    btn_frame = tk.Frame(dialog, bg="#1e293b")
    btn_frame.pack(pady=(22, 0))

    def on_confirm():
        raw_val = (
            cash_var.get()
            .replace(",", "")
            .replace("₹", "")
            .replace("INR", "")
            .replace("Rs", "")
            .strip()
        )
        try:
            val = float(raw_val) if raw_val else 0.0
            res["cash"] = max(0.0, val)
            dialog.destroy()
        except ValueError:
            cash_entry.config(bg="#7f1d1d")

    def on_cancel():
        res["cash"] = None
        dialog.destroy()

    dialog.bind("<Return>", lambda e: on_confirm())
    dialog.bind("<Escape>", lambda e: on_cancel())

    confirm_btn = tk.Button(
        btn_frame,
        text="Continue to Analysis",
        command=on_confirm,
        font=("Helvetica", 13, "bold"),
        bg="#10b981",
        fg="white",
        cursor="hand2",
        padx=16,
        pady=6,
    )
    confirm_btn.pack(side="left", padx=10)

    cancel_btn = tk.Button(
        btn_frame,
        text="Cancel",
        command=on_cancel,
        font=("Helvetica", 13),
        bg="#64748b",
        fg="white",
        cursor="hand2",
        padx=16,
        pady=6,
    )
    cancel_btn.pack(side="left", padx=10)

    dialog.wait_window()
    return res["cash"]


def show_watchlist(parent: tk.Tk | tk.Toplevel) -> None:
    disable_parent(parent)

    win = tk.Toplevel(parent)
    win.title("👁️ Watchlist & Price Alerts")
    win.geometry("1400x950")
    win.configure(bg=UI_THEME["bg_input"])
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    push_window(win, parent)

    # --- Header ---
    header_frame = tk.Frame(win, bg=UI_THEME.get("bg_header", "#1e293b"))
    header_frame.pack(fill="x")
    tk.Label(
        header_frame,
        text="👁️ WATCHLIST & PRICE ALERTS",
        font=UI_THEME.get("font_bold", ("Helvetica", 16, "bold")),
        bg=UI_THEME.get("bg_header", "#1e293b"),
        fg=UI_THEME.get("gold", "#FFD700"),
        pady=12,
    ).pack()

    # --- Styling ---
    style = ttk.Style(win)
    if "clam" not in style.theme_names():
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

    style.configure(
        "Watch.Treeview",
        background=UI_THEME.get("charcoal", "#334155"),
        foreground="white",
        fieldbackground=UI_THEME.get("charcoal", "#334155"),
        bordercolor=UI_THEME.get("slate_light", "#475569"),
        rowheight=35,
        font=UI_THEME.get("font_main", ("Helvetica", 12)),
    )
    style.map(
        "Watch.Treeview",
        background=[("selected", UI_THEME.get("bg_focus", "red"))],
    )
    style.configure(
        "Watch.Treeview.Heading",
        background=UI_THEME.get("dark_slate", "#1e293b"),
        foreground=UI_THEME.get("gold", "#FFD700"),
        font=UI_THEME.get("font_bold", ("Helvetica", 12, "bold")),
    )

    # --- Bottom Actions Frame (pinned to bottom so buttons are always visible) ---
    bottom_frame = tk.Frame(win, bg=UI_THEME["bg_input"])
    bottom_frame.pack(side="bottom", fill="x", padx=15, pady=(0, 15))

    # --- Form Frame ---
    form_frame = tk.LabelFrame(
        win,
        text=" Add / Edit Watchlist Entry ",
        bg=UI_THEME["bg_input"],
        fg="white",
        font=UI_THEME.get("font_bold", ("Helvetica", 12, "bold")),
        bd=2,
        padx=10,
        pady=10,
    )
    form_frame.pack(side="bottom", fill="x", padx=15, pady=10)

    # --- Treeview ---
    tree_frame = tk.Frame(win, bg=UI_THEME["bg_input"])
    tree_frame.pack(side="top", fill="both", expand=True, padx=15, pady=10)

    tree_scroll = ttk.Scrollbar(tree_frame)
    tree_scroll.pack(side="right", fill="y")

    cols = (
        "ID",
        "Company",
        "Target Buy",
        "Target Sell",
        "Current",
        "Full Avg",
        "Curr Avg",
        "Live Price",
        "Status",
        "Notes",
        "id_stk",
        "ticker",
    )
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="Watch.Treeview",
    )
    tree_scroll.config(command=tree.yview)

    # Configure Columns and Sorting
    for col in cols:
        if col in ("ID", "id_stk", "ticker"):
            continue
        text_map = {
            "Company": "Company",
            "Target Buy": "Target Buy",
            "Target Sell": "Target Sell",
            "Current": "Cur. Qty",
            "Full Avg": "Full Avg",
            "Curr Avg": "Curr Avg",
            "Live Price": "Live Price",
            "Status": "Status",
            "Notes": "Notes",
        }
        if col in text_map:
            tree.heading(
                col,
                text=text_map[col],
                command=lambda _col=col: universal_tree_sort(
                    tree, _col, False
                ),
            )

    tree.column("ID", width=0, stretch=tk.NO)
    tree.column("id_stk", width=0, stretch=tk.NO)
    tree.column("ticker", width=0, stretch=tk.NO)

    tree.column("Company", width=220, anchor="w")
    tree.column("Target Buy", width=95, anchor="e")
    tree.column("Target Sell", width=95, anchor="e")
    tree.column("Current", width=95, anchor="e")
    tree.column("Full Avg", width=110, anchor="e")
    tree.column("Curr Avg", width=110, anchor="e")
    tree.column("Live Price", width=110, anchor="e")
    tree.column("Status", width=140, anchor="center")
    tree.column("Notes", width=200, anchor="w")

    # Tags for coloring alerts
    tree.tag_configure(
        "buy_alert",
        foreground="#4ade80",
        font=UI_THEME.get("font_bold", ("Helvetica", 12, "bold")),
    )
    tree.tag_configure(
        "sell_alert",
        foreground="#f87171",
        font=UI_THEME.get("font_bold", ("Helvetica", 12, "bold")),
    )
    tree.tag_configure("monitoring", foreground="white")

    tree.pack(fill="both", expand=True)

    # --- Form Variables ---

    # Form Variables
    company_var = tk.StringVar()
    target_buy_var = tk.DoubleVar(value=0.0)
    target_sell_var = tk.DoubleVar(value=0.0)
    notes_var = tk.StringVar()

    companies = []
    company_map = {}

    # Form Layout
    tk.Label(
        form_frame,
        text="Company:",
        bg=UI_THEME["bg_input"],
        fg="white",
        font=("Helvetica", 12),
    ).grid(row=0, column=0, sticky="w", padx=5)

    comp_inner_frame = tk.Frame(form_frame, bg=UI_THEME["bg_input"])
    comp_inner_frame.grid(row=0, column=1, padx=5, pady=5, sticky="w")

    company_combo = ttk.Combobox(
        comp_inner_frame,
        textvariable=company_var,
        values=companies,
        width=28,
        font=("Helvetica", 12),
    )
    company_combo.pack(side="left")

    def _invoke_add_company():
        add_company(win)
        export_company(win)
        _refresh_company_data()
        company_combo.focus_set()

    add_comp_btn = tk.Button(
        comp_inner_frame,
        text="➕ New",
        font=("Helvetica", 10, "bold"),
        bg="#10b981",
        fg="white",
        cursor="hand2",
        command=_invoke_add_company,
    )
    add_comp_btn.pack(side="left", padx=(5, 0))

    def _refresh_company_data():
        companies.clear()
        company_map.clear()
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    (
                        "SELECT id_stk, company_name, ticker FROM stocks "
                        "WHERE is_active = 1 ORDER BY company_name ASC"
                    )
                )
                for row in cursor.fetchall():
                    display = row[
                        1
                    ]  # Strictly use company name to match trade_add.py
                    companies.append(display)
                    company_map[display] = {
                        "id_stk": row[0],
                        "ticker": row[2],
                        "name": row[1],
                    }
        except sqlite3.Error as e:
            logger.error(f"Failed to fetch companies for watchlist: {e}")

        company_combo["values"] = companies
        progressive_selection(company_combo, companies)

    _refresh_company_data()
    apply_entry_theme(company_combo)

    def on_company_focus_out(_event=None):
        comp = company_var.get().strip()
        if not comp:
            return
        if comp not in company_map:
            show_colorful_error(win, "Error", "Please select a valid company.")
            company_combo.focus_set()
            company_combo.select_range(0, "end")

    company_combo.bind("<FocusOut>", on_company_focus_out, add="+")

    tk.Label(
        form_frame,
        text="Target Buy (₹):",
        bg=UI_THEME["bg_input"],
        fg="white",
        font=("Helvetica", 12),
    ).grid(row=0, column=2, sticky="w", padx=(20, 5))
    target_buy_entry = tk.Entry(
        form_frame,
        textvariable=target_buy_var,
        width=12,
        font=("Helvetica", 12),
    )
    target_buy_entry.grid(row=0, column=3, padx=5, pady=5)
    apply_entry_theme(target_buy_entry)

    tk.Label(
        form_frame,
        text="Target Sell (₹):",
        bg=UI_THEME["bg_input"],
        fg="white",
        font=("Helvetica", 12),
    ).grid(row=0, column=4, sticky="w", padx=(20, 5))
    target_sell_entry = tk.Entry(
        form_frame,
        textvariable=target_sell_var,
        width=12,
        font=("Helvetica", 12),
    )
    target_sell_entry.grid(row=0, column=5, padx=5, pady=5)
    apply_entry_theme(target_sell_entry)

    tk.Label(
        form_frame,
        text="Notes:",
        bg=UI_THEME["bg_input"],
        fg="white",
        font=("Helvetica", 12),
    ).grid(row=1, column=0, sticky="w", padx=5, pady=10)
    notes_entry = tk.Entry(
        form_frame, textvariable=notes_var, width=50, font=("Helvetica", 12)
    )
    notes_entry.grid(
        row=1, column=1, columnspan=3, sticky="w", padx=5, pady=10
    )
    apply_entry_theme(notes_entry)

    # Action Buttons inside Form
    btn_inner_frame = tk.Frame(form_frame, bg=UI_THEME["bg_input"])
    btn_inner_frame.grid(row=1, column=4, columnspan=2, sticky="e", pady=10)

    def clear_form():
        company_var.set("")
        target_buy_var.set(0.0)
        target_sell_var.set(0.0)
        notes_var.set("")
        company_combo.config(state="normal")

        # Reset progressive selection state fully
        setattr(company_combo, "_user_typing", False)
        setattr(company_combo, "_ignore_next_event", False)
        company_combo["values"] = companies

    def save_entry():
        comp = company_var.get().strip()
        if comp not in company_map:
            show_colorful_error(win, "Error", "Please select a valid company.")
            return

        id_stk = company_map[comp]["id_stk"]
        try:
            t_buy = float(target_buy_var.get() or 0.0)
            t_sell = float(target_sell_var.get() or 0.0)
        except (ValueError, tk.TclError):
            show_colorful_error(
                win, "Error", "Target prices must be valid numbers."
            )
            return

        notes = notes_var.get().strip()

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id_watch FROM watchlist WHERE id_stk = ?",
                    (id_stk,),
                )
                existing = cursor.fetchone()
                if existing:
                    cursor.execute(
                        (
                            "UPDATE watchlist SET target_buy_price=?, "
                            "target_sell_price=?, notes=? WHERE id_watch=?"
                        ),
                        (t_buy, t_sell, notes, existing[0]),
                    )
                else:
                    cursor.execute(
                        (
                            "INSERT INTO watchlist (id_stk, target_buy_price, "
                            "target_sell_price=?, notes) VALUES (?, ?, ?, ?)"
                        ),
                        (id_stk, t_buy, t_sell, notes),
                    )
                conn.commit()
            load_watchlist()
            clear_form()
            show_colorful_info(
                win, "Success", "Watchlist updated successfully."
            )
        except sqlite3.Error as e:
            show_colorful_error(
                win, "Database Error", f"Failed to save to watchlist: {e}"
            )

    save_btn = tk.Button(
        btn_inner_frame,
        text="💾 Save / Update",
        command=save_entry,
        font=("Helvetica", 11, "bold"),
        bg="#22c55e",
        activebackground="#16a34a",
        activeforeground="white",
        fg="white",
        cursor="hand2",
    )
    save_btn.pack(side="left", padx=5)
    clear_btn = tk.Button(
        btn_inner_frame,
        text="🔄 Clear",
        command=clear_form,
        font=("Helvetica", 11),
        bg="#f59e0b",
        fg="white",
        cursor="hand2",
    )
    clear_btn.pack(side="left", padx=5)

    # --- Bottom Actions ---

    status_label = tk.Label(
        bottom_frame,
        text="Status: Ready",
        font=("Helvetica", 11, "italic"),
        bg=UI_THEME["bg_input"],
        fg="#94a3b8",
    )
    status_label.pack(side="left")

    def _close_manager(_event=None):
        safe_close_modal(win, parent)

    def delete_selected():
        selected = tree.selection()
        if not selected:
            return
        item = tree.item(selected[0])
        id_watch = item["values"][0]
        comp_name = item["values"][1]

        if show_colorful_yesno(
            win, "Confirm Delete", f"Remove '{comp_name}' from Watchlist?"
        ):
            try:
                with get_db_connection() as conn:
                    conn.cursor().execute(
                        "DELETE FROM watchlist WHERE id_watch=?", (id_watch,)
                    )
                    conn.commit()
                load_watchlist()
                clear_form()
            except sqlite3.Error as e:
                show_colorful_error(
                    win, "Database Error", f"Failed to delete: {e}"
                )

    close_btn = tk.Button(
        bottom_frame,
        text="Close",
        command=_close_manager,
        font=("Helvetica", 12, "bold"),
        bg="#475569",
        fg="white",
        width=12,
        cursor="hand2",
    )
    close_btn.pack(side="right", padx=5)

    delete_btn = tk.Button(
        bottom_frame,
        text="🗑️ Remove Selected",
        command=delete_selected,
        font=("Helvetica", 12, "bold"),
        bg="#ef4444",
        fg="white",
        cursor="hand2",
    )
    delete_btn.pack(side="right", padx=6)

    def run_technical_scan():
        win.after(
            0,
            lambda: status_label.config(
                text="Status: Running Technical Scan...", fg="#f1c40f"
            ),
        )

        def _scan_thread():
            try:
                # Import scanner module we just created
                from . import scanner

                ticker_to_item = {}
                watchlist_tickers = []

                # Extract tickers directly from the UI tree
                for item in tree.get_children():
                    vals = tree.item(item, "values")
                    ticker = vals[11]  # Shifted to 11 due to Curr Avg
                    if ticker and ticker != "None":
                        # Ensure standard format for the scanner
                        clean_ticker = (
                            ticker
                            if ticker.endswith(".NS") or ticker.endswith(".BO")
                            else f"{ticker}.NS"
                        )
                        ticker_to_item[clean_ticker] = item
                        if clean_ticker not in watchlist_tickers:
                            watchlist_tickers.append(clean_ticker)

                if not watchlist_tickers:
                    win.after(
                        0,
                        lambda: status_label.config(
                            text="Status: No valid tickers to scan.",
                            fg="#f87171",
                        ),
                    )
                    return

                # Pass the portfolio to the scanner
                alerts = scanner.scan_watchlist_for_signals(watchlist_tickers)
                win.after(0, _apply_alerts, alerts, ticker_to_item)

            except ImportError as e:
                logger.error(f"Scanner import failed: {e}")
                win.after(
                    0,
                    lambda err=e: status_label.config(
                        text=f"Status: Import Error - {err}", fg="#f87171"
                    ),
                )
            except Exception as e:
                logger.error(f"Scan failed: {e}")
                win.after(
                    0,
                    lambda err=e: status_label.config(
                        text=f"Status: Scan failed - {err}", fg="#f87171"
                    ),
                )

        def _apply_alerts(alerts, ticker_to_item):
            if not alerts:
                status_label.config(
                    text="Status: Scan Complete. No signals triggered.",
                    fg="#4ade80",
                )
                return

            for alert in alerts:
                scrip = alert["scrip"]
                if scrip in ticker_to_item:
                    item = ticker_to_item[scrip]
                    if tree.exists(item):
                        vals = list(tree.item(item, "values"))
                        current_status = vals[
                            8
                        ]  # Shifted to 8 due to Curr Avg
                        new_signal = f"⚡ {alert['signal']}"

                        # Prevent duplicate text if clicked multiple times
                        if new_signal not in current_status:
                            if current_status in ["Monitoring", "Fetching..."]:
                                vals[8] = new_signal
                            else:
                                vals[8] = f"{current_status} | {new_signal}"

                        # Apply the green alert tag to make it pop visually
                        tree.item(item, values=vals, tags=("buy_alert",))
                        tree.item(item, values=vals, tags=("buy_alert",))

            status_label.config(
                text=f"Status: Scan Complete. {len(alerts)} alerts generated!",
                fg="#10b981",
            )

        # Run scanner in background to prevent UI freezing while downloading
        threading.Thread(target=_scan_thread, daemon=True).start()

    def open_ipo_advice_window():
        ipo_win = tk.Toplevel(win)
        ipo_win.title("IPO Advice — Ongoing & Next 30 Days (AI Grounded)")
        ipo_win.geometry("1400x950")
        ipo_win.configure(bg=UI_THEME["bg_input"])
        ipo_win.bind("<Escape>", lambda e: ipo_win.destroy())
        ipo_win.transient(win)
        ipo_win.grab_set()

        # --- Header ---
        header_frame = tk.Frame(
            ipo_win, bg=UI_THEME.get("bg_header", "#1e293b")
        )
        header_frame.pack(fill="x")
        tk.Label(
            header_frame,
            text="📈 ONGOING & UPCOMING IPOs (NEXT 30 DAYS)",
            font=UI_THEME.get("font_bold", ("Helvetica", 16, "bold")),
            bg=UI_THEME.get("bg_header", "#1e293b"),
            fg=UI_THEME.get("gold", "#FFD700"),
            pady=12,
        ).pack()

        ipo_status_lbl = tk.Label(
            ipo_win,
            text=(
                "Contacting Gemini with Google Search to fetch live "
                "IPO schedules, GMP, and brokerage ratings..."
            ),
            font=UI_THEME.get("font_main", ("Helvetica", 12)),
            bg=UI_THEME["bg_input"],
            fg="#38bdf8",
            pady=4,
        )
        ipo_status_lbl.pack(fill="x")

        # Table Frame with Vertical & Horizontal Scrollbars
        table_frame = tk.Frame(ipo_win, bg=UI_THEME["bg_input"])
        table_frame.pack(fill="both", expand=True, padx=15, pady=10)

        columns = (
            "ipo_name",
            "issue_price",
            "issue_size",
            "min_lot",
            "open_date",
            "close_date",
            "allotment_date",
            "listing_date",
            "gmp",
            "bullish_brokerages",
            "avoid_brokerages",
        )

        col_headers = {
            "ipo_name": "IPO Name",
            "issue_price": "Issue Price",
            "issue_size": "Issue Size",
            "min_lot": "Min Lot",
            "open_date": "Open Date",
            "close_date": "Close Date",
            "allotment_date": "Allotment",
            "listing_date": "Listing Date",
            "gmp": "GMP",
            "bullish_brokerages": "Bullish Brokerages (Apply)",
            "avoid_brokerages": "Brokerages Suggesting Avoid",
        }

        ipo_style = ttk.Style()
        ipo_style.configure(
            "IPO.Treeview",
            background=UI_THEME.get("charcoal", "#334155"),
            foreground="white",
            fieldbackground=UI_THEME.get("charcoal", "#334155"),
            bordercolor=UI_THEME.get("slate_light", "#475569"),
            rowheight=35,
            font=UI_THEME.get("font_main", ("Helvetica", 12)),
        )
        ipo_style.map(
            "IPO.Treeview",
            background=[("selected", UI_THEME.get("bg_focus", "red"))],
        )
        ipo_style.configure(
            "IPO.Treeview.Heading",
            background=UI_THEME.get("dark_slate", "#1e293b"),
            foreground=UI_THEME.get("gold", "#FFD700"),
            font=UI_THEME.get("font_bold", ("Helvetica", 12, "bold")),
        )

        ipo_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=15,
            style="IPO.Treeview",
        )

        vsb = ttk.Scrollbar(
            table_frame, orient="vertical", command=ipo_tree.yview
        )
        hsb = ttk.Scrollbar(
            table_frame, orient="horizontal", command=ipo_tree.xview
        )
        ipo_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        ipo_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Detail bar at bottom to read full brokerage lists when clicked
        detail_var = tk.StringVar(
            value=(
                "Tip: Click any IPO row to view Bullish "
                "and Avoid brokerage houses."
            )
        )
        detail_lbl = tk.Label(
            ipo_win,
            textvariable=detail_var,
            font=UI_THEME.get("font_main", ("Helvetica", 12)),
            bg=UI_THEME.get("bg_header", "#1e293b"),
            fg=UI_THEME.get("gold", "#FFD700"),
            anchor="w",
            justify="left",
            wraplength=1340,
            padx=12,
            pady=8,
        )
        detail_lbl.pack(fill="x", padx=15, pady=(0, 15))

        def on_ipo_row_select(event):
            selected = ipo_tree.selection()
            if not selected:
                return
            vals = ipo_tree.item(selected[0], "values")
            if vals:
                b_bullish = str(vals[9]).replace("\n", ", ")
                b_avoid = str(vals[10]).replace("\n", ", ")
                detail_var.set(
                    f"IPO: {vals[0]}  |  GMP: {vals[8]}  |  "
                    f"✅ Bullish (Apply): {b_bullish}  |  "
                    f"❌ Avoid (Do Not Apply): {b_avoid}"
                )

        ipo_tree.bind("<<TreeviewSelect>>", on_ipo_row_select)

        def _populate_ipo_tree(result):
            if not ipo_win.winfo_exists():
                return
            if "error" in result:
                ipo_status_lbl.config(text=result["error"], fg="#f87171")
                return

            ipo_list = result.get("data", [])
            if not ipo_list:
                ipo_status_lbl.config(
                    text="No ongoing/upcoming IPOs found for next 30 days.",
                    fg="#fbbf24",
                )
                return

            for item in ipo_tree.get_children():
                ipo_tree.delete(item)

            for ipo in ipo_list:
                vals = []
                for col in columns:
                    val_str = str(
                        ipo.get(
                            col,
                            (
                                "N/A"
                                if col in ["ipo_name", "gmp"]
                                else ("None" if "brokerages" in col else "TBA")
                            ),
                        )
                    )
                    vals.append(val_str)

                ipo_tree.insert("", "end", values=tuple(vals))

            # Apply headers & initial alignments
            for col in columns:
                anchor = (
                    "w"
                    if col
                    in ("ipo_name", "bullish_brokerages", "avoid_brokerages")
                    else "center"
                )
                ipo_tree.heading(col, text=col_headers[col])
                ipo_tree.column(col, anchor=anchor, stretch=False)

            # Auto-adjust small columns with separation and wrap large text
            auto_adjust_and_wrap_columns(
                ipo_tree,
                style_name="IPO.Treeview",
                wrap_cols={"ipo_name", "bullish_brokerages", "avoid_brokerages"},
                max_col_widths={
                    "ipo_name": 260,
                    "bullish_brokerages": 320,
                    "avoid_brokerages": 260,
                },
                col_separation=28,
            )

            ipo_status_lbl.config(
                text=(
                    f"Loaded {len(ipo_list)} ongoing/upcoming IPO(s). "
                    "Click any row to expand."
                ),
                fg="#4ade80",
            )

        def _fetch_ipo_thread():
            try:
                from . import ai_analyzer
            except ImportError:
                import ai_analyzer

            API_KEY = ai_analyzer.get_api_key()
            result = ai_analyzer.get_ipo_advice(API_KEY)
            if ipo_win.winfo_exists():
                ipo_win.after(0, _populate_ipo_tree, result)

        threading.Thread(target=_fetch_ipo_thread, daemon=True).start()

    scan_btn = tk.Button(
        bottom_frame,
        text="📊 Scan Technicals",
        command=run_technical_scan,
        font=("Helvetica", 12, "bold"),
        bg="#8b5cf6",  # Distinct Purple color to separate it from data actions
        fg="white",
        cursor="hand2",
    )
    scan_btn.pack(side="right", padx=6)

    ipo_btn = tk.Button(
        bottom_frame,
        text="🏛️ IPO Advice",
        command=open_ipo_advice_window,
        font=("Helvetica", 12, "bold"),
        bg="#0ea5e9",
        fg="white",
        cursor="hand2",
    )
    ipo_btn.pack(side="right", padx=6)

    def run_portfolio_sell_scan():
        # Open Toplevel modal window
        ai_win = tk.Toplevel(win)
        ai_win.title("📋 AI Sell Advice Scan")
        ai_win.geometry("900x700")
        ai_win.configure(bg=UI_THEME["bg_input"])
        ai_win.transient(win)
        ai_win.grab_set()
        ai_win.focus_set()

        # Bind Escape key to close
        ai_win.bind("<Escape>", lambda e: ai_win.destroy())

        header = tk.Label(
            ai_win,
            text="Scanning Portfolio for Profit-Booking Sell Advice...",
            font=("Helvetica", 16, "bold"),
            bg=UI_THEME["bg_input"],
            fg=UI_THEME.get("gold", "#FFD700"),
        )
        header.pack(pady=15)

        text_area = tk.Text(
            ai_win,
            wrap="word",
            font=("Helvetica", 14),
            bg="#1e293b",
            fg="white",
            padx=20,
            pady=20,
        )
        text_area.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        text_area.insert(
            tk.END,
            "1. Fetching active holdings from database...\n"
            "2. Downloading live prices from Yahoo! Finance...\n"
            "3. Checking scrips in profit zone (Price > Avg Cost)...\n"
            "4. Consulting Gemini AI for brokerage sell advice...\n\n"
            "Please wait, this might take a few moments.",
        )
        text_area.config(state="disabled")

        def _scan_thread():
            try:
                # 1. Fetch active holdings
                active_holdings = []
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT s.id_stk, s.company_name, s.ticker,
                               s.curr_avg_price,
                               COALESCE((
                                   SELECT SUM(
                                       CASE
                                           WHEN t.trade_type_trd = 'BUY'
                                           THEN t.qty_trd
                                           WHEN t.trade_type_trd = 'SELL'
                                           THEN -t.qty_trd
                                           ELSE 0
                                       END
                                   )
                                   FROM transactions t
                                   WHERE t.id_stk = s.id_stk
                               ), 0) AS current_qty
                        FROM stocks s
                        WHERE s.curr_avg_price > 0 AND s.ticker != ''
                    """
                    )
                    for row in cursor.fetchall():
                        id_stk, name, ticker, curr_avg, qty = row
                        if qty > 0:
                            active_holdings.append(
                                {
                                    "id_stk": id_stk,
                                    "name": name,
                                    "ticker": ticker,
                                    "curr_avg": curr_avg,
                                    "qty": qty,
                                }
                            )

                if not active_holdings:
                    win.after(
                        0,
                        _update_ui,
                        "No active holdings in DB with an average cost price.",
                    )
                    return

                # 2. Fetch live prices concurrently
                def _fetch_price(ticker):
                    if not yf:
                        return 0.0
                    try:
                        t = yf.Ticker(ticker)
                        hist = t.history(period="1d")
                        return (
                            float(hist["Close"].iloc[-1])
                            if not hist.empty
                            else 0.0
                        )
                    except Exception:
                        return 0.0

                profitable_scrip_list = []
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=10
                ) as executor:
                    future_to_stock = {
                        executor.submit(_fetch_price, stock["ticker"]): stock
                        for stock in active_holdings
                    }
                    for future in concurrent.futures.as_completed(
                        future_to_stock
                    ):
                        stock = future_to_stock[future]
                        try:
                            live_price = future.result()
                            if live_price > stock["curr_avg"]:
                                gain = (
                                    (live_price - stock["curr_avg"])
                                    / stock["curr_avg"]
                                ) * 100
                                profitable_scrip_list.append(
                                    (stock["ticker"], gain)
                                )
                        except Exception as e:
                            logger.error(
                                "Error fetching live price for %s: %s",
                                stock["ticker"],
                                e,
                            )

                if not profitable_scrip_list:
                    win.after(
                        0,
                        _update_ui,
                        "No scrips in profit zone or live prices unavailable.",
                    )
                    return

                # 3. Call AI Advisor
                from . import ai_analyzer

                API_KEY = ai_analyzer.get_api_key()

                advice = ai_analyzer.get_portfolio_sell_advice(
                    profitable_scrip_list, API_KEY
                )
                win.after(0, _update_ui, advice)

            except Exception as e:
                logger.error(f"AI Sell Scan failed: {e}")
                win.after(
                    0, _update_ui, f"[System Error] Sell Scan failed: {e}"
                )

        def _update_ui(content):
            if not ai_win.winfo_exists():
                return
            header.config(text="AI Sell Advice Scan Complete")

            if not content:
                content = (
                    "[System Error] No response or empty response from AI."
                )

            lines = content.strip().split("\n")
            table_lines = [
                line.strip() for line in lines if line.strip().startswith("|")
            ]

            if len(table_lines) >= 3:
                text_area.pack_forget()

                tree_container = tk.Frame(ai_win, bg=UI_THEME["bg_input"])
                tree_container.pack(
                    fill="both", expand=True, padx=15, pady=(0, 15)
                )

                tree_scroll = ttk.Scrollbar(tree_container, orient="vertical")
                tree_scroll.pack(side="right", fill="y")

                h_scroll = ttk.Scrollbar(tree_container, orient="horizontal")
                h_scroll.pack(side="bottom", fill="x")

                advice_cols = (
                    "WL",
                    "Scrip",
                    "Broker House",
                    "Advice",
                    "Date of Report",
                )
                sell_style = ttk.Style()
                sell_style.configure(
                    "SellAdvice.Treeview",
                    background=UI_THEME.get("charcoal", "#334155"),
                    foreground="white",
                    fieldbackground=UI_THEME.get("charcoal", "#334155"),
                    bordercolor=UI_THEME.get("slate_light", "#475569"),
                    rowheight=35,
                    font=UI_THEME.get("font_main", ("Helvetica", 12)),
                )
                sell_style.map(
                    "SellAdvice.Treeview",
                    background=[("selected", UI_THEME.get("bg_focus", "red"))],
                )
                sell_style.configure(
                    "SellAdvice.Treeview.Heading",
                    background=UI_THEME.get("dark_slate", "#1e293b"),
                    foreground=UI_THEME.get("gold", "#FFD700"),
                    font=UI_THEME.get("font_bold", ("Helvetica", 12, "bold")),
                )

                advice_tree = ttk.Treeview(
                    tree_container,
                    columns=advice_cols,
                    show="headings",
                    yscrollcommand=tree_scroll.set,
                    xscrollcommand=h_scroll.set,
                    style="SellAdvice.Treeview",
                )
                tree_scroll.config(command=advice_tree.yview)
                h_scroll.config(command=advice_tree.xview)
                advice_tree.pack(side="left", fill="both", expand=True)

                # Configure Columns & Sorting
                for col in advice_cols:
                    advice_tree.heading(
                        col,
                        text=col if col != "WL" else "👁️",
                        command=lambda _col=col: universal_tree_sort(
                            advice_tree, _col, False
                        ),
                    )
                    if col == "WL":
                        advice_tree.column(
                            col, width=40, anchor="center", stretch=False
                        )
                    elif col == "Scrip":
                        advice_tree.column(col, anchor="w", stretch=False)
                    elif col == "Broker House":
                        advice_tree.column(col, anchor="w", stretch=False)
                    elif col == "Advice":
                        advice_tree.column(col, anchor="w", stretch=False)
                    elif col == "Date of Report":
                        advice_tree.column(col, anchor="center", stretch=False)

                header_seen = False
                for line in table_lines:
                    parts = [p.strip() for p in line.split("|")[1:-1]]
                    if not parts:
                        continue
                    if all(p.startswith("-") or p == "" for p in parts):
                        continue
                    if not header_seen:
                        header_seen = True
                        continue

                    while len(parts) < 4:
                        parts.append("")

                    scrip = parts[0]
                    id_stk = None
                    try:
                        with get_db_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                (
                                    "SELECT id_stk FROM stocks "
                                    "WHERE ticker = ? OR company_name = ?"
                                ),
                                (scrip, scrip),
                            )
                            row = cursor.fetchone()
                            if row:
                                id_stk = row[0]
                    except Exception as e:
                        logger.error(
                            f"Failed to lookup stock ID for {scrip}: {e}"
                        )

                    if id_stk is not None:
                        row_values = ("➕",) + tuple(parts[:4])
                        advice_tree.insert(
                            "", "end", values=row_values, tags=(str(id_stk),)
                        )
                    else:
                        row_values = ("",) + tuple(parts[:4])
                        advice_tree.insert("", "end", values=row_values)

                # Auto-adjust small columns with separation and wrap large Advice text
                auto_adjust_and_wrap_columns(
                    advice_tree,
                    style_name="SellAdvice.Treeview",
                    wrap_cols={"Advice", "Broker House"},
                    max_col_widths={"Advice": 380, "Broker House": 220},
                    col_separation=26,
                )

                def on_advice_double_click(event):
                    region = advice_tree.identify("region", event.x, event.y)
                    if region != "cell":
                        return
                    col_id = advice_tree.identify_column(event.x)
                    if col_id == "#1":  # First column is WL
                        sel = advice_tree.selection()
                        if not sel:
                            return
                        item_id = sel[0]
                        tags = advice_tree.item(item_id, "tags")
                        id_stk = None
                        if tags:
                            try:
                                id_stk = int(tags[0])
                            except (ValueError, TypeError, IndexError):
                                pass

                        if id_stk is None:
                            values = advice_tree.item(item_id, "values")
                            if len(values) > 1:
                                scrip = values[1]
                                try:
                                    with get_db_connection() as conn:
                                        cursor = conn.cursor()
                                        cursor.execute(
                                            (
                                                "SELECT id_stk FROM stocks "
                                                "WHERE ticker = ? "
                                                "OR company_name = ?"
                                            ),
                                            (scrip, scrip),
                                        )
                                        row = cursor.fetchone()
                                        if row:
                                            id_stk = row[0]
                                except Exception as e:
                                    logger.error(
                                        "Lookup failed for %s: %s", scrip, e
                                    )

                        if id_stk is None:
                            return

                        try:
                            with get_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "SELECT 1 FROM watchlist WHERE id_stk = ?",
                                    (id_stk,),
                                )
                                if cursor.fetchone():
                                    show_colorful_info(
                                        ai_win,
                                        "Watchlist",
                                        "Stock already in watchlist.",
                                    )
                                else:
                                    cursor.execute(
                                        "INSERT INTO watchlist (id_stk, "
                                        "target_buy_price, target_sell_price, "
                                        "notes) VALUES (?, 0.0, 0.0, '')",
                                        (id_stk,),
                                    )
                                    conn.commit()
                                    show_colorful_info(
                                        ai_win,
                                        "Watchlist",
                                        "Stock added to watchlist.",
                                    )
                                    load_watchlist()
                        except sqlite3.Error as e:
                            show_colorful_error(
                                ai_win,
                                "Database Error",
                                f"Failed to add to watchlist: {e}",
                            )

                advice_tree.bind("<Double-1>", on_advice_double_click)
            else:
                text_area.config(state="normal")
                text_area.delete("1.0", tk.END)
                text_area.insert(tk.END, content)
                text_area.config(state="disabled")

        threading.Thread(target=_scan_thread, daemon=True).start()

    ai_sell_btn = tk.Button(
        bottom_frame,
        text="📋 AI Sell Advice",
        command=run_portfolio_sell_scan,
        font=("Helvetica", 12, "bold"),
        bg="#d97706",  # Gold/Amber theme
        fg="white",
        cursor="hand2",
    )
    ai_sell_btn.pack(side="right", padx=6)

    def run_portfolio_buy_scan():
        # Open Toplevel modal window
        ai_win = tk.Toplevel(win)
        ai_win.title("🟢 AI Buy Advice Scan")
        ai_win.geometry(
            "1000x700"
        )  # slightly wider to accommodate more columns
        ai_win.configure(bg=UI_THEME["bg_input"])
        ai_win.transient(win)
        ai_win.grab_set()
        ai_win.focus_set()

        # Bind Escape key to close
        ai_win.bind("<Escape>", lambda e: ai_win.destroy())

        header = tk.Label(
            ai_win,
            text="Scanning Market for Recent Buy Advice...",
            font=("Helvetica", 16, "bold"),
            bg=UI_THEME["bg_input"],
            fg=UI_THEME.get("gold", "#FFD700"),
        )
        header.pack(pady=15)

        text_area = tk.Text(
            ai_win,
            wrap="word",
            font=("Helvetica", 14),
            bg="#1e293b",
            fg="white",
            padx=20,
            pady=20,
        )
        text_area.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        text_area.insert(
            tk.END,
            "1. Fetching active tracked tickers from database...\n"
            "2. Filtering and preparing scrip list...\n"
            "3. Querying Gemini AI for recent institutional buy calls...\n\n"
            "Please wait, this might take a few moments.",
        )
        text_area.config(state="disabled")

        def _scan_thread():
            try:
                # 1. Fetch active scrip tickers from database
                scrip_list = []
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        (
                            "SELECT DISTINCT ticker FROM stocks "
                            "WHERE is_active = 1 AND ticker != ''"
                        )
                    )
                    for row in cursor.fetchall():
                        scrip_list.append(row[0])

                if not scrip_list:
                    win.after(
                        0,
                        _update_ui,
                        "No active stocks with valid tickers found in DB.",
                    )
                    return

                # 2. Call AI Advisor in chunks to avoid payload overload
                from . import ai_analyzer

                API_KEY = ai_analyzer.get_api_key()

                # Split scrips into chunks of 40
                chunks = [
                    scrip_list[i:i + 40]
                    for i in range(0, len(scrip_list), 40)
                ]

                advices = []
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=3
                ) as executor:
                    future_to_chunk = {
                        executor.submit(
                            ai_analyzer.get_portfolio_buy_advice,
                            chunk,
                            API_KEY,
                        ): chunk
                        for chunk in chunks
                    }
                    for future in concurrent.futures.as_completed(
                        future_to_chunk
                    ):
                        try:
                            result = future.result()
                            if result:
                                advices.append(result)
                        except Exception as e:
                            logger.error(
                                f"AI Buy advice chunk fetch failed: {e}"
                            )

                combined_advice = "\n".join(advices)
                win.after(0, _update_ui, combined_advice)

            except Exception as e:
                logger.error(f"AI Buy Scan failed: {e}")
                win.after(
                    0, _update_ui, f"[System Error] Buy Scan failed: {e}"
                )

        def _update_ui(content):
            if not ai_win.winfo_exists():
                return
            header.config(text="AI Buy Advice Scan Complete")

            if not content:
                content = (
                    "[System Error] No response or empty response from AI."
                )

            lines = content.strip().split("\n")
            table_lines = [
                line.strip() for line in lines if line.strip().startswith("|")
            ]

            # We need at least 3 lines for a markdown table
            if len(table_lines) >= 3:
                text_area.pack_forget()

                tree_container = tk.Frame(ai_win, bg=UI_THEME["bg_input"])
                tree_container.pack(
                    fill="both", expand=True, padx=15, pady=(0, 15)
                )

                tree_scroll = ttk.Scrollbar(tree_container, orient="vertical")
                tree_scroll.pack(side="right", fill="y")

                h_scroll = ttk.Scrollbar(tree_container, orient="horizontal")
                h_scroll.pack(side="bottom", fill="x")

                advice_cols = (
                    "WL",
                    "Scrip",
                    "Buy Price Band",
                    "Target Price",
                    "Target Period",
                    "Broker House",
                    "Date of Report",
                )
                buy_style = ttk.Style()
                buy_style.configure(
                    "BuyAdvice.Treeview",
                    background=UI_THEME.get("charcoal", "#334155"),
                    foreground="white",
                    fieldbackground=UI_THEME.get("charcoal", "#334155"),
                    bordercolor=UI_THEME.get("slate_light", "#475569"),
                    rowheight=35,
                    font=UI_THEME.get("font_main", ("Helvetica", 12)),
                )
                buy_style.map(
                    "BuyAdvice.Treeview",
                    background=[("selected", UI_THEME.get("bg_focus", "red"))],
                )
                buy_style.configure(
                    "BuyAdvice.Treeview.Heading",
                    background=UI_THEME.get("dark_slate", "#1e293b"),
                    foreground=UI_THEME.get("gold", "#FFD700"),
                    font=UI_THEME.get("font_bold", ("Helvetica", 12, "bold")),
                )

                advice_tree = ttk.Treeview(
                    tree_container,
                    columns=advice_cols,
                    show="headings",
                    yscrollcommand=tree_scroll.set,
                    xscrollcommand=h_scroll.set,
                    style="BuyAdvice.Treeview",
                )
                tree_scroll.config(command=advice_tree.yview)
                h_scroll.config(command=advice_tree.xview)
                advice_tree.pack(side="left", fill="both", expand=True)

                # Configure Columns & Sorting
                for col in advice_cols:
                    advice_tree.heading(
                        col,
                        text=col if col != "WL" else "👁️",
                        command=lambda _col=col: universal_tree_sort(
                            advice_tree, _col, False
                        ),
                    )
                    if col == "WL":
                        advice_tree.column(
                            col, width=40, anchor="center", stretch=False
                        )
                    elif col == "Scrip":
                        advice_tree.column(col, anchor="w", stretch=False)
                    elif col == "Buy Price Band":
                        advice_tree.column(col, anchor="e", stretch=False)
                    elif col == "Target Price":
                        advice_tree.column(col, anchor="e", stretch=False)
                    elif col == "Target Period":
                        advice_tree.column(col, anchor="center", stretch=False)
                    elif col == "Broker House":
                        advice_tree.column(col, anchor="w", stretch=False)
                    elif col == "Date of Report":
                        advice_tree.column(col, anchor="center", stretch=False)

                for line in table_lines:
                    parts = [p.strip() for p in line.split("|")[1:-1]]
                    if not parts:
                        continue
                    if all(p.startswith("-") or p == "" for p in parts):
                        continue
                    # Skip duplicate header rows from merged tables
                    if parts[0].lower() == "scrip":
                        continue

                    while len(parts) < 6:
                        parts.append("")

                    scrip = parts[0]
                    id_stk = None
                    try:
                        with get_db_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                (
                                    "SELECT id_stk FROM stocks "
                                    "WHERE ticker = ? OR company_name = ?"
                                ),
                                (scrip, scrip),
                            )
                            row = cursor.fetchone()
                            if row:
                                id_stk = row[0]
                    except Exception as e:
                        logger.error(
                            f"Failed to lookup stock ID for {scrip}: {e}"
                        )

                    if id_stk is not None:
                        row_values = ("➕",) + tuple(parts[:6])
                        advice_tree.insert(
                            "", "end", values=row_values, tags=(str(id_stk),)
                        )
                    else:
                        row_values = ("",) + tuple(parts[:6])
                        advice_tree.insert("", "end", values=row_values)

                # Auto-adjust small columns with separation and wrap large text
                auto_adjust_and_wrap_columns(
                    advice_tree,
                    style_name="BuyAdvice.Treeview",
                    wrap_cols={"Broker House", "Target Period"},
                    max_col_widths={"Broker House": 220, "Target Period": 180},
                    col_separation=26,
                )

                def on_advice_double_click(event):
                    region = advice_tree.identify("region", event.x, event.y)
                    if region != "cell":
                        return
                    col_id = advice_tree.identify_column(event.x)
                    if col_id == "#1":  # First column is WL
                        sel = advice_tree.selection()
                        if not sel:
                            return
                        item_id = sel[0]
                        tags = advice_tree.item(item_id, "tags")
                        id_stk = None
                        if tags:
                            try:
                                id_stk = int(tags[0])
                            except (ValueError, TypeError, IndexError):
                                pass

                        if id_stk is None:
                            values = advice_tree.item(item_id, "values")
                            if len(values) > 1:
                                scrip = values[1]
                                try:
                                    with get_db_connection() as conn:
                                        cursor = conn.cursor()
                                        cursor.execute(
                                            (
                                                "SELECT id_stk FROM stocks "
                                                "WHERE ticker = ? "
                                                "OR company_name = ?"
                                            ),
                                            (scrip, scrip),
                                        )
                                        row = cursor.fetchone()
                                        if row:
                                            id_stk = row[0]
                                except Exception as e:
                                    logger.error(
                                        "Lookup failed for %s: %s", scrip, e
                                    )

                        if id_stk is None:
                            return

                        try:
                            with get_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "SELECT 1 FROM watchlist WHERE id_stk = ?",
                                    (id_stk,),
                                )
                                if cursor.fetchone():
                                    show_colorful_info(
                                        ai_win,
                                        "Watchlist",
                                        "Stock already in watchlist.",
                                    )
                                else:
                                    cursor.execute(
                                        "INSERT INTO watchlist (id_stk, "
                                        "target_buy_price, target_sell_price, "
                                        "notes) VALUES (?, 0.0, 0.0, '')",
                                        (id_stk,),
                                    )
                                    conn.commit()
                                    show_colorful_info(
                                        ai_win,
                                        "Watchlist",
                                        "Stock added to watchlist.",
                                    )
                                    load_watchlist()
                        except sqlite3.Error as e:
                            show_colorful_error(
                                ai_win,
                                "Database Error",
                                f"Failed to add to watchlist: {e}",
                            )

                advice_tree.bind("<Double-1>", on_advice_double_click)
            else:
                text_area.config(state="normal")
                text_area.delete("1.0", tk.END)
                text_area.insert(tk.END, content)
                text_area.config(state="disabled")

        threading.Thread(target=_scan_thread, daemon=True).start()

    ai_buy_btn = tk.Button(
        bottom_frame,
        text="🟢 AI Buy Advice",
        command=run_portfolio_buy_scan,
        font=("Helvetica", 12, "bold"),
        bg="#059669",  # Green theme
        fg="white",
        cursor="hand2",
    )
    ai_buy_btn.pack(side="right", padx=6)

    def run_pick_of_the_day_scan():
        # Open Toplevel modal window with spacious dimensions
        pod_win = tk.Toplevel(win)
        pod_win.title("🏆 Daily Pick of the Day — Intelligence Report")
        pod_win.geometry("1260x860")
        pod_win.configure(bg=UI_THEME["bg_input"])
        pod_win.transient(win)
        pod_win.grab_set()
        pod_win.focus_set()

        # Bind Escape key to close
        pod_win.bind("<Escape>", lambda e: pod_win.destroy())

        top_header_frame = tk.Frame(pod_win, bg=UI_THEME["bg_input"])
        top_header_frame.pack(fill="x", padx=15, pady=(12, 6))

        header = tk.Label(
            top_header_frame,
            text="🏆 Daily Pick of the Day — Latest Intelligence Report",
            font=("Helvetica", 19, "bold"),
            bg=UI_THEME["bg_input"],
            fg=UI_THEME.get("gold", "#FFD700"),
        )
        header.pack()

        report_info_lbl = tk.Label(
            top_header_frame,
            text="Loading locally synced report...",
            font=("Helvetica", 12),
            bg=UI_THEME["bg_input"],
            fg="#38bdf8",
        )
        report_info_lbl.pack(pady=(4, 0))

        text_frame = tk.Frame(pod_win, bg=UI_THEME["bg_input"])
        text_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        text_scroll = ttk.Scrollbar(text_frame, orient="vertical")
        text_scroll.pack(side="right", fill="y")

        h_scroll = ttk.Scrollbar(text_frame, orient="horizontal")
        h_scroll.pack(side="bottom", fill="x")

        text_area = tk.Text(
            text_frame,
            wrap="word",
            font=("Helvetica", 15),
            bg="#0f172a",
            fg="#cbd5e1",
            padx=18,
            pady=18,
            yscrollcommand=text_scroll.set,
            xscrollcommand=h_scroll.set,
        )
        text_scroll.config(command=text_area.yview)
        h_scroll.config(command=text_area.xview)
        text_area.pack(side="left", fill="both", expand=True)

        current_state = {
            "content": "",
            "base_size": 15,
            "file_name": "",
            "mtime": "",
        }

        def render_markdown(text_widget, md_text, base_size=15):
            text_widget.config(state="normal", wrap="word")
            text_widget.delete("1.0", tk.END)

            if not md_text:
                text_widget.config(state="disabled")
                text_widget.yview_moveto(0.0)
                text_widget.see("1.0")
                return

            wrap_width = max(60, min(100, int(1250 / (base_size * 0.95))))

            # Enhanced Readability & Senior-Friendly Typography (15pt baseline)
            text_widget.tag_configure(
                "title",
                font=("Helvetica", base_size + 6, "bold"),
                foreground="#38bdf8",
                spacing1=16,
                spacing3=10,
                wrap="word",
            )
            text_widget.tag_configure(
                "h2",
                font=("Helvetica", base_size + 4, "bold"),
                foreground="#fbbf24",
                spacing1=16,
                spacing3=10,
                wrap="word",
            )
            text_widget.tag_configure(
                "h3",
                font=("Helvetica", base_size + 2, "bold"),
                foreground="#34d399",
                spacing1=12,
                spacing3=8,
                wrap="word",
            )
            text_widget.tag_configure(
                "bold",
                font=("Helvetica", base_size, "bold"),
                foreground="#ffffff",
                wrap="word",
            )
            text_widget.tag_configure(
                "normal",
                font=("Helvetica", base_size),
                foreground="#cbd5e1",
                spacing1=3,
                spacing3=4,
                wrap="word",
            )
            text_widget.tag_configure(
                "bullet",
                font=("Helvetica", base_size),
                foreground="#cbd5e1",
                spacing1=3,
                spacing3=4,
                lmargin1=28,
                lmargin2=50,
                wrap="word",
            )
            text_widget.tag_configure(
                "bullet_sym",
                font=("Helvetica", base_size, "bold"),
                foreground="#38bdf8",
            )
            text_widget.tag_configure(
                "blockquote",
                font=("Helvetica", base_size, "italic"),
                foreground="#93c5fd",
                spacing1=4,
                spacing3=4,
                lmargin1=24,
                lmargin2=24,
                wrap="word",
            )
            text_widget.tag_configure(
                "divider",
                font=("Consolas", max(9, base_size - 4)),
                foreground="#475569",
                spacing1=8,
                spacing3=8,
                wrap="none",
            )
            text_widget.tag_configure(
                "code_block",
                font=("Consolas", max(11, base_size - 1)),
                background="#1e293b",
                foreground="#94a3b8",
                spacing1=3,
                spacing3=3,
                wrap="none",
            )

            # Table styling with clear monospace fonts (14pt at 15pt baseline)
            tab_size = max(11, base_size - 1)
            text_widget.tag_configure(
                "table_header",
                font=("Consolas", tab_size, "bold"),
                background="#1e3a5f",
                foreground="#93c5fd",
                wrap="none",
            )
            text_widget.tag_configure(
                "table_row_even",
                font=("Consolas", tab_size),
                background="#1e293b",
                foreground="#f8fafc",
                wrap="none",
            )
            text_widget.tag_configure(
                "table_row_odd",
                font=("Consolas", tab_size),
                background="#0f172a",
                foreground="#cbd5e1",
                wrap="none",
            )
            text_widget.tag_configure(
                "action_buy",
                font=("Consolas", tab_size, "bold"),
                foreground="#4ade80",
                wrap="none",
            )
            text_widget.tag_configure(
                "action_hold",
                font=("Consolas", tab_size, "bold"),
                foreground="#38bdf8",
                wrap="none",
            )
            text_widget.tag_configure(
                "action_wait",
                font=("Consolas", tab_size, "bold"),
                foreground="#facc15",
                wrap="none",
            )
            text_widget.tag_configure(
                "action_exit",
                font=("Consolas", tab_size, "bold"),
                foreground="#f87171",
                wrap="none",
            )

            # Educational Note Callout styling
            text_widget.tag_configure(
                "edu_callout",
                font=("Helvetica", base_size, "italic"),
                background="#1e2238",
                foreground="#e0e7ff",
                spacing1=6,
                spacing2=4,
                spacing3=6,
                lmargin1=28,
                lmargin2=28,
                rmargin=24,
                wrap="word",
            )
            text_widget.tag_configure(
                "edu_callout_bold",
                font=("Helvetica", base_size, "bold italic"),
                background="#1e2238",
                foreground="#38bdf8",
                wrap="word",
            )
            text_widget.tag_configure(
                "edu_callout_badge",
                font=("Helvetica", max(11, base_size - 1), "bold"),
                background="#1e2238",
                foreground="#fbbf24",
                lmargin1=28,
                lmargin2=28,
                rmargin=24,
                wrap="word",
            )

            text_widget.tag_raise("action_buy")
            text_widget.tag_raise("action_hold")
            text_widget.tag_raise("action_wait")
            text_widget.tag_raise("action_exit")
            text_widget.tag_raise("edu_callout_bold")
            text_widget.tag_raise("edu_callout_badge")
            text_widget.tag_raise("bold")

            # Pre-compiled high performance patterns
            re_cite = re.compile(r"\[cite:[^\]]*\]")
            re_divider_cell = re.compile(r"^:?-+:?$")
            re_span = re.compile(r"(\*\*[^*]+?\*\*|\*[^*]+?\*)")
            re_action_word = re.compile(
                r"\b(BUY|ADD|ACCUMULATE|HOLD|WAIT|WATCH|REDUCE|EXIT|AVOID|OVER-INVESTED|UNDER-INVESTED|NEUTRAL)\b",
                re.IGNORECASE,
            )
            action_tag_map = {
                "BUY": "action_buy",
                "ADD": "action_buy",
                "ACCUMULATE": "action_buy",
                "UNDER-INVESTED": "action_buy",
                "HOLD": "action_hold",
                "NEUTRAL": "action_hold",
                "WAIT": "action_wait",
                "WATCH": "action_wait",
                "REDUCE": "action_exit",
                "EXIT": "action_exit",
                "AVOID": "action_exit",
                "OVER-INVESTED": "action_exit",
            }
            re_edu_start = re.compile(
                r"^(?:>\s*)?"
                r"(?:[-*•]\s+)?"
                r"(?:\*{1,2}|_{1,2})?"
                r"(?:[\U0001F000-\U0001FAFF]\s*)?"
                r"(?:"
                r"educational(?:\s+note|\s+segment|\s+primer|\s+tip|\s+guide|\s+corner|:|\b)"
                r"|education(?:\b|:)"
                r"|note\s+on\s+(?:technical\s+indicators?|indicators?|technical\s+analysis)"
                r"|technical\s+(?:analysis\s+)?(?:note|primer|concept|tip|insight|guide|segment)"
                r"|indicator\s+(?:primer|spotlight|guide|explained|breakdown|note)"
                r"|concept(?:\s+in\s+focus)?(?:\b|:)"
                r"|metric\s+(?:explained|definition|guide|in\s+focus)"
                r"|learning\s+(?:point|corner|note)"
                r"|did\s+you\s+know\b"
                r"|(?:understanding|what\s+is)\s+(?:rsi|moving\s+average|dma|ema|macd|bollinger|indicators?|slb)"
                r"|(?:(?:rsi|relative\s+strength\s+index|\d+\s*[- ]?(?:dma|ema|sma)|moving\s+averages?|dma|ema|sma|macd|bollinger\s+bands?|supertrend|vwap|stochastics?|atr|adx|slb|securities\s+lending)"
                r"(?:[,\s/&+-]+(?:rsi|relative\s+strength\s+index|\d+\s*[- ]?(?:dma|ema|sma)|moving\s+averages?|dma|ema|sma|macd|bollinger\s+bands?|supertrend|vwap|stochastics?|atr|adx|slb|securities\s+lending))*"
                r"(?:\s*\([^)]*\))?"
                r"(?:\s*:|\s+is\b|\s+measures\b|\s+indicates\b|\s*[\-\—]))"
                r")",
                re.IGNORECASE,
            )

            cleaned_md = re_cite.sub("", md_text)
            lines = cleaned_md.split("\n")
            idx_line = 0

            def _insert_spans(text_w, text_span, base_tag, bold_tag="bold"):
                parts = re_span.split(text_span)
                args = []
                for p in parts:
                    if not p:
                        continue
                    if p.startswith("**") and p.endswith("**") and len(p) >= 4:
                        args.extend([p[2:-2], (bold_tag, base_tag)])
                    elif p.startswith("*") and p.endswith("*") and len(p) >= 2:
                        args.extend([p[1:-1], (bold_tag, base_tag)])
                    else:
                        args.extend([p, base_tag])
                if args:
                    text_w.insert(tk.END, *args)

            def _render_table(text_w, t_lines, tab_font_size):
                if len(t_lines) < 2:
                    for tl in t_lines:
                        text_w.insert(tk.END, tl + "\n", "code_block")
                    return

                # Split multiple consecutive tables if separated by another divider line
                sub_tables = []
                curr_table = []
                for tl in t_lines:
                    st = tl.strip()
                    c_test = [c.strip() for c in (st[1:-1] if st.startswith("|") and st.endswith("|") else st.strip("|")).split("|")]
                    is_div = bool(c_test and all(re_divider_cell.match(c) for c in c_test if c) and any("-" in c for c in c_test))
                    if is_div and len(curr_table) > 1:
                        prev_header = curr_table.pop()
                        if curr_table:
                            sub_tables.append(curr_table)
                        curr_table = [prev_header, tl]
                    else:
                        curr_table.append(tl)
                if curr_table:
                    sub_tables.append(curr_table)

                for table_lines in sub_tables:
                    rows = []
                    for tl in table_lines:
                        st = tl.strip()
                        if st.startswith("|"):
                            st = st[1:]
                        if st.endswith("|"):
                            st = st[:-1]
                        cells = [c.replace("**", "").replace("*", "").strip() for c in st.split("|")]
                        if any(c for c in cells):
                            rows.append(cells)

                    if not rows:
                        continue

                    # Filter out pure markdown divider rows
                    data_rows = []
                    for r in rows:
                        if all(re_divider_cell.match(c) for c in r if c) and any("-" in c for c in r):
                            continue
                        data_rows.append(r)

                    if not data_rows:
                        continue

                    num_cols = max(len(r) for r in data_rows)
                    if num_cols == 0:
                        continue

                    normalized_rows = []
                    for r in data_rows:
                        if len(r) < num_cols:
                            r = r + [""] * (num_cols - len(r))
                        elif len(r) > num_cols:
                            r = r[:num_cols]
                        normalized_rows.append(r)

                    col_widths = [0] * num_cols
                    for r in normalized_rows:
                        for c_i in range(num_cols):
                            col_widths[c_i] = max(col_widths[c_i], len(r[c_i]))

                    pad_widths = [max(w + 3, 10) for w in col_widths]

                    table_args = []
                    header_row = normalized_rows[0]
                    header_str = " | ".join(header_row[c_i].ljust(pad_widths[c_i]) for c_i in range(num_cols))
                    table_args.extend([f"| {header_str} |\n", "table_header"])

                    div_str = "-+-".join("-" * pad_widths[c_i] for c_i in range(num_cols))
                    table_args.extend([f"+-{div_str}-+\n", "divider"])

                    for row_idx, r in enumerate(normalized_rows[1:], start=1):
                        row_tag = "table_row_even" if row_idx % 2 == 0 else "table_row_odd"
                        row_str = " | ".join(r[c_i].ljust(pad_widths[c_i]) for c_i in range(num_cols))
                        line_str = f"| {row_str} |\n"

                        last_pos = 0
                        for m in re_action_word.finditer(line_str):
                            start, end = m.span()
                            if start > last_pos:
                                table_args.extend([line_str[last_pos:start], row_tag])
                            word = m.group(0).upper()
                            act_tag = action_tag_map.get(word, row_tag)
                            table_args.extend([line_str[start:end], (row_tag, act_tag)])
                            last_pos = end
                        if last_pos < len(line_str):
                            table_args.extend([line_str[last_pos:], row_tag])

                    table_args.extend(["\n", "normal"])
                    text_w.insert(tk.END, *table_args)

            while idx_line < len(lines):
                line = lines[idx_line]
                s_line = line.strip()

                # Code Blocks (```)
                if s_line.startswith("```"):
                    code_lines = []
                    idx_line += 1
                    while idx_line < len(lines) and not lines[idx_line].strip().startswith("```"):
                        code_lines.append(lines[idx_line])
                        idx_line += 1
                    if idx_line < len(lines):
                        idx_line += 1
                    if code_lines:
                        text_widget.insert(tk.END, "\n".join(code_lines) + "\n", "code_block")
                    continue

                # Markdown Tables (supports multiple distinct tables across sections)
                if s_line.startswith("|") or (
                    "|" in s_line
                    and idx_line + 1 < len(lines)
                    and re.match(r"^\s*\|?\s*[-:]+[-| :]*$", lines[idx_line + 1].strip())
                ):
                    table_block = []
                    while idx_line < len(lines):
                        t_cur = lines[idx_line].strip()
                        if not t_cur:
                            break
                        if t_cur.startswith("|") or (
                            "|" in t_cur and not t_cur.startswith(("#", "```", ">", "* ", "- ", "• "))
                        ):
                            table_block.append(t_cur)
                            idx_line += 1
                        else:
                            break
                    _render_table(text_widget, table_block, tab_size)
                    continue

                # Top-level Title (# )
                if s_line.startswith("# ") and not s_line.startswith("## "):
                    text_widget.insert(tk.END, "\n" + s_line[2:] + "\n", "title")
                    text_widget.insert(tk.END, "━" * wrap_width + "\n", "divider")
                    idx_line += 1
                    continue

                # Major Section Headers (## )
                if s_line.startswith("## "):
                    text_widget.insert(tk.END, "\n" + s_line[3:] + "\n", "h2")
                    text_widget.insert(tk.END, "─" * wrap_width + "\n", "divider")
                    idx_line += 1
                    continue

                # Sub-Section Headers (### )
                if s_line.startswith("### "):
                    text_widget.insert(tk.END, "\n" + s_line[4:] + "\n", "h3")
                    idx_line += 1
                    continue

                # Section Divider
                if s_line in ("---", "***", "___"):
                    text_widget.insert(tk.END, "─" * wrap_width + "\n", "divider")
                    idx_line += 1
                    continue

                # Educational Note / Callout Block (Indicators, RSI, Moving Averages, SLB)
                if re_edu_start.match(s_line):
                    callout_lines = []
                    while idx_line < len(lines):
                        cur_l = lines[idx_line].strip()
                        if not cur_l:
                            # Allow one empty line if subsequent line continues the callout block (> or bullet or edu keyword)
                            if idx_line + 1 < len(lines):
                                next_l = lines[idx_line + 1].strip()
                                if next_l.startswith(">") or re_edu_start.match(next_l):
                                    idx_line += 1
                                    continue
                            break
                        if cur_l.startswith(("#", "```", "---", "***", "___")) or cur_l.startswith("|"):
                            break
                        if cur_l.startswith(">"):
                            cur_l = cur_l[1:].strip()
                        callout_lines.append(cur_l)
                        idx_line += 1

                    if callout_lines:
                        # Group callout lines into distinct parameter items
                        items = []
                        curr_item = []
                        for cl in callout_lines:
                            is_new_param = bool(
                                curr_item
                                and (
                                    re.match(r"^[-*•]\s+", cl)
                                    or re.match(r"^\d+[\.)]\s+", cl)
                                    or (cl.startswith("**") and ":" in cl[:50])
                                )
                            )
                            if is_new_param:
                                items.append(" ".join(curr_item))
                                curr_item = [cl]
                            else:
                                curr_item.append(cl)
                        if curr_item:
                            items.append(" ".join(curr_item))

                        first_clean = re.sub(
                            r"^[-*•_#>\s]+|[:*_\s]+$", "", items[0]
                        ).strip()
                        is_title_only = bool(
                            len(items) > 1
                            and len(items[0]) < 60
                            and re.search(
                                r"^(?:note|educational|indicator|technical)",
                                first_clean,
                                re.IGNORECASE,
                            )
                        )

                        text_widget.insert(tk.END, "\n")
                        badge_text = "💡 EDUCATIONAL NOTE:"
                        if is_title_only:
                            badge_text = f"💡 {first_clean.upper()}:"
                            items = items[1:]

                        text_widget.insert(
                            tk.END, f"{badge_text}\n\n", "edu_callout_badge"
                        )

                        for idx_item, item_text in enumerate(items):
                            clean_item = re.sub(
                                r"^[-*•]\s+", "", item_text
                            ).strip()
                            if not clean_item:
                                continue
                            _insert_spans(
                                text_widget,
                                clean_item + "\n",
                                "edu_callout",
                                bold_tag="edu_callout_bold",
                            )
                            # One blank line before explaining the next parameter
                            if idx_item < len(items) - 1:
                                text_widget.insert(tk.END, "\n", "edu_callout")

                        text_widget.insert(tk.END, "\n")
                    continue

                # Blockquotes (> )
                if s_line.startswith(">"):
                    bq_body = s_line[1:].strip()
                    _insert_spans(text_widget, bq_body + "\n", "blockquote")
                    idx_line += 1
                    continue

                # Bullet points
                if s_line.startswith(("* ", "- ", "• ")):
                    bullet_body = s_line[2:]
                    text_widget.insert(tk.END, "  • ", "bullet_sym")
                    _insert_spans(text_widget, bullet_body + "\n", "bullet")
                    idx_line += 1
                    continue

                # Standard paragraph line
                if s_line:
                    _insert_spans(text_widget, s_line + "\n", "normal")
                else:
                    text_widget.insert(tk.END, "\n")

                idx_line += 1

            text_widget.config(state="disabled")
            text_widget.yview_moveto(0.0)
            text_widget.xview_moveto(0.0)
            text_widget.see("1.0")

        def _load_report():
            from .drive_sync import get_local_pick_of_the_day

            report_tuple = get_local_pick_of_the_day()
            if report_tuple:
                content, fname, mtime_str = report_tuple
                current_state["content"] = content
                current_state["file_name"] = fname
                current_state["mtime"] = mtime_str
                header.config(
                    text="🏆 Daily Pick of the Day — Latest Intelligence Report"
                )
                report_info_lbl.config(
                    text=(
                        f"📄 Local Source: {fname}  •  "
                        f"Last Modified: {mtime_str}"
                    ),
                    fg="#38bdf8",
                )
                render_markdown(
                    text_area, content, base_size=current_state["base_size"]
                )
            else:
                placeholder = (
                    "# 🏆 Daily Pick of the Day — No Local Report Found\n\n"
                    "No local report starting with `Pick_of_the_day_` "
                    "was found in `data/`.\n\n"
                    "### Next Steps:\n"
                    "1. **Automated LLM Workflow**: Verify that your "
                    "workflow generated a file starting with "
                    "`Pick_of_the_day_` in the **Finance** folder.\n"
                    "2. **Google Drive Credentials**: Place your "
                    "`credentials.json` (OAuth 2.0 Desktop Client) into the "
                    "project folder to enable automatic Drive downloads.\n"
                    "3. **Sync Now**: Click the **🔄 Sync from Drive** button "
                    "below to download the latest report now.\n"
                )
                current_state["content"] = placeholder
                header.config(
                    text="⚠️ Daily Pick of the Day — Report Not Found"
                )
                report_info_lbl.config(
                    text="No local report found in data/ folder.",
                    fg="#f59e0b",
                )
                render_markdown(
                    text_area,
                    placeholder,
                    base_size=current_state["base_size"],
                )

        # Modal Footer Action Buttons with Font Zoom & Drive Sync
        btn_bar = tk.Frame(pod_win, bg=UI_THEME["bg_input"])
        btn_bar.pack(fill="x", padx=15, pady=(0, 15))

        def _sync_from_drive():
            report_info_lbl.config(
                text="⏳ Connecting to Drive and downloading latest report...",
                fg="#38bdf8",
            )

            def _worker():
                try:
                    from .drive_sync import (
                        get_drive_service,
                        download_latest_pick_of_the_day,
                    )

                    service = get_drive_service()
                    res = download_latest_pick_of_the_day(service)
                    if res:
                        pod_win.after(0, _load_report)
                        pod_win.after(
                            0,
                            lambda: messagebox.showinfo(
                                "Sync Complete",
                                f"Downloaded report from Drive:\n{res[1]}",
                                parent=pod_win,
                            ),
                        )
                    else:
                        pod_win.after(
                            0,
                            lambda: report_info_lbl.config(
                                text=(
                                    "⚠️ No file starting with "
                                    "'Pick_of_the_day_' "
                                    "found in Drive 'Finance' folder."
                                ),
                                fg="#f59e0b",
                            ),
                        )
                        pod_win.after(
                            0,
                            lambda: messagebox.showwarning(
                                "Report Not Found",
                                (
                                    "No 'Pick_of_the_day_' report found "
                                    "in Google Drive 'Finance' folder."
                                ),
                                parent=pod_win,
                            ),
                        )
                except Exception as ex:
                    err_msg = str(ex)
                    pod_win.after(
                        0,
                        lambda: report_info_lbl.config(
                            text=f"⚠️ Drive Sync Error: {err_msg[:60]}",
                            fg="#f87171",
                        ),
                    )
                    pod_win.after(
                        0,
                        lambda: messagebox.showerror(
                            "Drive Sync Error",
                            f"Failed to sync with Google Drive:\n{err_msg}",
                            parent=pod_win,
                        ),
                    )

            threading.Thread(target=_worker, daemon=True).start()

        def copy_to_clipboard():
            text = current_state["content"] or text_area.get("1.0", tk.END)
            pod_win.clipboard_clear()
            pod_win.clipboard_append(text)
            messagebox.showinfo(
                "Copied",
                "Pick of the Day report copied to clipboard!",
                parent=pod_win,
            )

        def export_markdown():
            text = current_state["content"] or text_area.get("1.0", tk.END)
            save_path = filedialog.asksaveasfilename(
                parent=pod_win,
                title="Save Pick of the Day Report",
                defaultextension=".md",
                initialfile="Pick_of_the_Day_Report.md",
                filetypes=[
                    ("Markdown files", "*.md"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*"),
                ],
            )
            if save_path:
                try:
                    with open(save_path, "w", encoding="utf-8") as f_out:
                        f_out.write(text)
                    messagebox.showinfo(
                        "Export Successful",
                        f"Report saved successfully to:\n{save_path}",
                        parent=pod_win,
                    )
                except Exception as ex:
                    messagebox.showerror(
                        "Export Failed",
                        f"Failed to save report: {ex}",
                        parent=pod_win,
                    )

        def zoom_in_font():
            if current_state["base_size"] < 26:
                current_state["base_size"] += 1
                if current_state["content"]:
                    render_markdown(
                        text_area,
                        current_state["content"],
                        base_size=current_state["base_size"],
                    )

        def zoom_out_font():
            if current_state["base_size"] > 11:
                current_state["base_size"] -= 1
                if current_state["content"]:
                    render_markdown(
                        text_area,
                        current_state["content"],
                        base_size=current_state["base_size"],
                    )

        # 1. Sync from Google Drive Button
        sync_btn = tk.Button(
            btn_bar,
            text="🔄 Sync from Drive",
            command=_sync_from_drive,
            font=("Helvetica", 12, "bold"),
            bg="#0284c7",  # Sky blue
            fg="white",
            cursor="hand2",
            padx=10,
            pady=4,
        )
        sync_btn.pack(side="left", padx=(0, 8))

        # 2. Copy Button
        copy_btn = tk.Button(
            btn_bar,
            text="📋 Copy",
            command=copy_to_clipboard,
            font=("Helvetica", 12, "bold"),
            bg="#3b82f6",
            fg="white",
            cursor="hand2",
            padx=10,
            pady=4,
        )
        copy_btn.pack(side="left", padx=(0, 8))

        # 3. Export Button
        export_btn = tk.Button(
            btn_bar,
            text="💾 Export (.md)",
            command=export_markdown,
            font=("Helvetica", 12, "bold"),
            bg="#10b981",  # Emerald green
            fg="white",
            cursor="hand2",
            padx=10,
            pady=4,
        )
        export_btn.pack(side="left", padx=(0, 8))

        # 4. Font Zoom Buttons for Accessibility (Senior user friendly)
        zoom_frame = tk.Frame(btn_bar, bg=UI_THEME["bg_input"])
        zoom_frame.pack(side="left", padx=10)

        zoom_in_btn = tk.Button(
            zoom_frame,
            text="🔍 A+",
            command=zoom_in_font,
            font=("Helvetica", 12, "bold"),
            bg="#7c3aed",
            fg="white",
            cursor="hand2",
            padx=8,
            pady=4,
        )
        zoom_in_btn.pack(side="left", padx=2)

        zoom_out_btn = tk.Button(
            zoom_frame,
            text="🔍 A-",
            command=zoom_out_font,
            font=("Helvetica", 12, "bold"),
            bg="#6d28d9",
            fg="white",
            cursor="hand2",
            padx=8,
            pady=4,
        )
        zoom_out_btn.pack(side="left", padx=2)

        # 5. Close Button
        close_btn = tk.Button(
            btn_bar,
            text="❌ Close",
            command=pod_win.destroy,
            font=("Helvetica", 12, "bold"),
            bg="#64748b",
            fg="white",
            cursor="hand2",
            padx=14,
            pady=4,
        )
        close_btn.pack(side="right")

        # Load latest local report on window open
        _load_report()

    pick_of_the_day_btn = tk.Button(
        bottom_frame,
        text="⭐ Pick of the Day",
        command=run_pick_of_the_day_scan,
        font=("Helvetica", 12, "bold"),
        bg="#e11d48",  # Rose/Ruby theme
        fg="white",
        cursor="hand2",
    )
    pick_of_the_day_btn.pack(side="right", padx=6)

    def on_tree_select(_event):
        selected = tree.selection()
        if not selected:
            return
        item = tree.item(selected[0])
        vals = item["values"]

        # Pre-fill form
        company_var.set(vals[1])
        t_buy_val = str(vals[2]).replace("₹", "").replace(",", "")
        t_sell_val = str(vals[3]).replace("₹", "").replace(",", "")

        target_buy_var.set(float(t_buy_val) if t_buy_val != "-" else 0.0)
        target_sell_var.set(float(t_sell_val) if t_sell_val != "-" else 0.0)
        notes_var.set(
            vals[9] if vals[9] != "-" else ""
        )  # Shifted to 9 due to Curr Avg
        company_combo.config(state="disabled")  # Lock company when editing

    tree.bind("<<TreeviewSelect>>", on_tree_select)

    def on_tree_double_click(_event):
        selected = tree.selection()
        if not selected:
            return

        item = tree.item(selected[0])
        vals = item["values"]
        status = str(vals[8])  # Shifted to 8 due to Curr Avg

        # Only trigger the AI if there is an active technical alert
        if "⚡" not in status:
            return

        company = vals[1]
        ticker = vals[11]  # Shifted to 11 due to Curr Avg

        # Extract just the signal name from the status string
        signal_text = status.split("⚡")[-1].strip()

        # Build the pop-up window
        ai_win = tk.Toplevel(win)
        ai_win.title(f"🧠 AI Insight: {company}")
        ai_win.geometry("850x650")  # Increased window size
        ai_win.configure(bg=UI_THEME["bg_input"])
        ai_win.transient(win)
        ai_win.grab_set()
        ai_win.focus_set()

        # Bind the Escape key to close the window instantly
        ai_win.bind("<Escape>", lambda e: ai_win.destroy())

        header = tk.Label(
            ai_win,
            text=f"Analyzing {signal_text} for {ticker}...",
            font=("Helvetica", 18, "bold"),  # Increased header font size
            bg=UI_THEME["bg_input"],
            fg=UI_THEME.get("gold", "#FFD700"),
        )
        header.pack(pady=15)

        text_area = tk.Text(
            ai_win,
            wrap="word",
            font=("Helvetica", 15),  # Increased body font size
            bg="#1e293b",
            fg="white",
            padx=20,
            pady=20,
        )
        text_area.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        text_area.insert(
            tk.END,
            (
                "Querying Gemini AI...\n\n"
                "Gathering live context and drafting explanation."
            ),
        )
        text_area.config(state="disabled")

        def fetch_insight():
            try:
                from . import ai_analyzer

                # Replace with your actual Gemini API key from Google AI Studio
                API_KEY = ai_analyzer.get_api_key()

                insight = ai_analyzer.get_market_insight(
                    ticker, signal_text, API_KEY
                )
                win.after(0, update_text, insight)

            except ImportError:
                win.after(
                    0,
                    update_text,
                    "[System Error] Could not load ai_analyzer.py module.",
                )
            except Exception as e:
                win.after(
                    0,
                    update_text,
                    f"[Error] An unexpected error occurred: {e}",
                )

        def update_text(content):
            if ai_win.winfo_exists():
                header.config(text=f"Insight for {company} ({signal_text})")
                text_area.config(state="normal")
                text_area.delete("1.0", tk.END)
                text_area.insert(tk.END, content)
                text_area.config(state="disabled")

        # Launch API call in background thread
        threading.Thread(target=fetch_insight, daemon=True).start()

    tree.bind("<Double-1>", on_tree_double_click)

    # --- Data Loading and Threading ---
    def load_watchlist():
        for item in tree.get_children():
            tree.delete(item)

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT w.id_watch, s.company_name, s.ticker,
                           w.target_buy_price, w.target_sell_price,
                           w.notes, s.id_stk,
                           COALESCE((
                               SELECT SUM(CASE WHEN t.trade_type_trd = 'BUY'
                                               THEN t.qty_trd
                                               WHEN t.trade_type_trd = 'SELL'
                                               THEN -t.qty_trd ELSE 0 END)
                               FROM transactions t
                               WHERE t.id_stk = s.id_stk
                           ), 0) AS current_qty,
                           (SELECT ROUND(SUM(t.net_amt_trd) * 1.0 /
                                         NULLIF(SUM(t.qty_trd), 0), 2)
                            FROM transactions t
                            WHERE t.id_stk = s.id_stk AND
                                  t.trade_type_trd = 'BUY') AS all_time_avg,
                           s.curr_avg_price
                    FROM watchlist w
                    JOIN stocks s ON w.id_stk = s.id_stk
                    ORDER BY s.company_name ASC
                """
                )
                for row in cursor.fetchall():
                    (
                        id_watch,
                        comp,
                        ticker,
                        t_buy,
                        t_sell,
                        notes,
                        id_stk,
                        current_qty,
                        all_time_avg,
                        curr_avg,
                    ) = row
                    display_comp = comp  # Keep it consistent with the dropdown

                    buy_str = f"₹{t_buy:,.2f}" if t_buy > 0 else "-"
                    sell_str = f"₹{t_sell:,.2f}" if t_sell > 0 else "-"
                    full_avg_str = (
                        f"₹{all_time_avg:,.2f}"
                        if all_time_avg is not None
                        else "-"
                    )
                    curr_avg_str = (
                        f"₹{curr_avg:,.2f}"
                        if curr_avg is not None and curr_avg > 0
                        else "-"
                    )
                    qty_str = int(current_qty) if current_qty else 0

                    tree.insert(
                        "",
                        "end",
                        iid=str(id_watch),
                        values=(
                            id_watch,
                            display_comp,
                            buy_str,
                            sell_str,
                            qty_str,
                            full_avg_str,
                            curr_avg_str,
                            "Fetching...",
                            "Monitoring",
                            notes or "-",
                            id_stk,
                            ticker,
                        ),
                        tags=("monitoring",),
                    )

            # Trigger background price fetch
            threading.Thread(target=fetch_live_prices, daemon=True).start()

        except sqlite3.Error as e:
            logger.error(f"Failed to load watchlist: {e}")

    def fetch_live_prices():
        if not yf:
            win.after(
                0,
                lambda: status_label.config(
                    text="Status: yfinance not installed. Prices unavailable.",
                    fg="#f87171",
                ),
            )
            return

        win.after(
            0,
            lambda: status_label.config(
                text="Status: Fetching live market prices...", fg="#f1c40f"
            ),
        )

        def fetch_ticker(ticker):
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="1d")
                return float(hist["Close"].iloc[-1]) if not hist.empty else 0.0
            except Exception:
                return 0.0

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_item = {}
            for item in tree.get_children():
                vals = tree.item(item, "values")
                ticker = vals[11]  # Shifted to 11 due to Curr Avg
                if ticker:
                    future_to_item[executor.submit(fetch_ticker, ticker)] = (
                        item
                    )
                else:
                    win.after(0, update_row_price, item, 0.0)

            for future in concurrent.futures.as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    price = future.result()
                    win.after(0, update_row_price, item, price)
                except Exception:
                    pass

        win.after(
            0,
            lambda: status_label.winfo_exists()
            and status_label.config(
                text="Status: Live prices updated.", fg="#4ade80"
            ),
        )

    def update_row_price(item, price):
        if not tree.winfo_exists():
            return

        vals = list(tree.item(item, "values"))
        vals[7] = (
            f"₹{price:,.2f}" if price > 0 else "N/A"
        )  # Shifted to 7 due to Curr Avg

        t_buy_val = str(vals[2]).replace("₹", "").replace(",", "")
        t_sell_val = str(vals[3]).replace("₹", "").replace(",", "")

        t_buy = float(t_buy_val) if t_buy_val != "-" else 0.0
        t_sell = float(t_sell_val) if t_sell_val != "-" else 0.0

        status = "Monitoring"
        tag = "monitoring"

        if price > 0:
            if t_buy > 0 and price <= t_buy:
                status = "BUY ALERT 🟢"
                tag = "buy_alert"
            elif t_sell > 0 and price >= t_sell:
                status = "SELL ALERT 🔴"
                tag = "sell_alert"

        vals[8] = status  # Shifted to 8 due to Curr Avg
        tree.item(item, values=vals, tags=(tag,))

    def _show_help(e=None):
        guide = [
            "Welcome to the Watchlist & Alerts module.",
            "",
            (
                "• Use this view to track target prices for buying "
                "or selling stocks."
            ),
            (
                "• The system will alert you when current prices meet "
                "your target prices."
            ),
            "• You can add, edit, or delete items from your watchlist.",
        ]
        faq = [
            (
                "Q: How are prices updated?",
                (
                    "A: You can update current prices manually "
                    "or run the price updater."
                ),
            ),
        ]
        show_standard_help(win, "Watchlist & Alerts Help", guide, faq)

    win.bind(
        "<F1>",
        lambda e: None if getattr(e, "state", 0) & 0x0004 else _show_help(e),
    )

    load_watchlist()

    win.bind("<Escape>", _close_manager)
    win.protocol("WM_DELETE_WINDOW", _close_manager)

    apply_button_animations(save_btn, "#22c55e", "#2563eb")
    apply_button_animations(clear_btn, "#f59e0b", "#d97706")
    apply_button_animations(delete_btn, "#ef4444", "#dc2626")
    apply_button_animations(close_btn, "#475569", "#334155")
    apply_button_animations(add_comp_btn, "#10b981", "#059669")
    apply_button_animations(scan_btn, "#8b5cf6", "#7c3aed")
    apply_button_animations(ipo_btn, "#0ea5e9", "#0284c7")
    apply_button_animations(ai_sell_btn, "#d97706", "#b45309")
    apply_button_animations(ai_buy_btn, "#059669", "#047857")
    apply_button_animations(pick_of_the_day_btn, "#e11d48", "#be123c")

    parent.wait_window(win)
    try:
        if parent.winfo_exists():
            try:
                parent.grab_set()
            except Exception:
                pass
    except tk.TclError:
        pass
