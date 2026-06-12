# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\watchlist_menu.py

"""
Watchlist and Price Alerts UI.
Allows users to track potential investments and set target buy/sell prices.
"""

import tkinter as tk
from tkinter import ttk
import sqlite3
import threading
import concurrent.futures

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
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window, safe_close_modal
from Shared.gui_utils import apply_button_animations, apply_entry_theme
from Shared.gui_progressive import progressive_selection
from .company_add import add_company
from .company_ex_import import export_company
from .helpers import universal_tree_sort


def show_watchlist(parent: tk.Tk | tk.Toplevel) -> None:
    modal_id = disable_parent(parent)

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

    # --- Treeview ---
    tree_frame = tk.Frame(win, bg=UI_THEME["bg_input"])
    tree_frame.pack(fill="both", expand=True, padx=15, pady=10)

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
            "Notes": "Notes"
        }
        if col in text_map:
            tree.heading(
                col,
                text=text_map[col],
                command=lambda _col=col: universal_tree_sort(tree, _col, False),
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
    form_frame.pack(fill="x", padx=15, pady=10)

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
                    "SELECT id_stk, company_name, ticker FROM stocks WHERE is_active = 1 ORDER BY company_name ASC"
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
        except ValueError:
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
                        "UPDATE watchlist SET target_buy_price=?, target_sell_price=?, notes=? WHERE id_watch=?",
                        (t_buy, t_sell, notes, existing[0]),
                    )
                else:
                    cursor.execute(
                        "INSERT INTO watchlist (id_stk, target_buy_price, target_sell_price, notes) VALUES (?, ?, ?, ?)",
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
    bottom_frame = tk.Frame(win, bg=UI_THEME["bg_input"])
    bottom_frame.pack(fill="x", padx=15, pady=(0, 15))

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
    delete_btn.pack(side="right", padx=10)

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
                    text="Status: Scan Complete. No technical signals triggered.",
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

    scan_btn = tk.Button(
        bottom_frame,
        text="📊 Scan Technicals",
        command=run_technical_scan,
        font=("Helvetica", 12, "bold"),
        bg="#8b5cf6",  # Distinct Purple color to separate it from data actions
        fg="white",
        cursor="hand2",
    )
    scan_btn.pack(side="right", padx=10)

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
            "3. Checking scrips in the profit zone (Live Price > Avg Cost Price)...\n"
            "4. Consulting Gemini AI for brokerage sell advice / profit booking research...\n\n"
            "Please wait, this might take a few moments."
        )
        text_area.config(state="disabled")

        def _scan_thread():
            try:
                # 1. Fetch active holdings
                active_holdings = []
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT s.id_stk, s.company_name, s.ticker, s.curr_avg_price,
                               COALESCE((SELECT SUM(CASE WHEN t.trade_type_trd = 'BUY' THEN t.qty_trd WHEN t.trade_type_trd = 'SELL' THEN -t.qty_trd ELSE 0 END)
                                         FROM transactions t WHERE t.id_stk = s.id_stk), 0) AS current_qty
                        FROM stocks s
                        WHERE s.curr_avg_price > 0 AND s.ticker != ''
                    """)
                    for row in cursor.fetchall():
                        id_stk, name, ticker, curr_avg, qty = row
                        if qty > 0:
                            active_holdings.append({
                                "id_stk": id_stk,
                                "name": name,
                                "ticker": ticker,
                                "curr_avg": curr_avg,
                                "qty": qty
                            })

                if not active_holdings:
                    win.after(0, _update_ui, "No active holdings found in your database with an average cost price.")
                    return

                # 2. Fetch live prices concurrently
                def _fetch_price(ticker):
                    if not yf:
                        return 0.0
                    try:
                        t = yf.Ticker(ticker)
                        hist = t.history(period="1d")
                        return float(hist["Close"].iloc[-1]) if not hist.empty else 0.0
                    except Exception:
                        return 0.0

                profitable_scrip_list = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    future_to_stock = {
                        executor.submit(_fetch_price, stock["ticker"]): stock
                        for stock in active_holdings
                    }
                    for future in concurrent.futures.as_completed(future_to_stock):
                        stock = future_to_stock[future]
                        try:
                            live_price = future.result()
                            if live_price > stock["curr_avg"]:
                                gain = ((live_price - stock["curr_avg"]) / stock["curr_avg"]) * 100
                                profitable_scrip_list.append((stock["ticker"], gain))
                        except Exception as e:
                            logger.error(f"Error fetching live price for {stock['ticker']}: {e}")

                if not profitable_scrip_list:
                    win.after(0, _update_ui, "No scrips are currently in the profit zone (Live Price > Avg Cost Price) or live prices could not be fetched.")
                    return

                # 3. Call AI Advisor
                from . import ai_analyzer
                API_KEY = ai_analyzer.get_api_key()

                advice = ai_analyzer.get_portfolio_sell_advice(profitable_scrip_list, API_KEY)
                win.after(0, _update_ui, advice)

            except Exception as e:
                logger.error(f"AI Sell Scan failed: {e}")
                win.after(0, _update_ui, f"[System Error] Sell Scan failed: {e}")

        def _update_ui(content):
            if not ai_win.winfo_exists():
                return
            header.config(text="AI Sell Advice Scan Complete")

            if not content:
                content = "[System Error] No response or empty response received from AI."

            lines = content.strip().split("\n")
            table_lines = [line.strip() for line in lines if line.strip().startswith("|")]

            if len(table_lines) >= 3:
                text_area.pack_forget()

                tree_container = tk.Frame(ai_win, bg=UI_THEME["bg_input"])
                tree_container.pack(fill="both", expand=True, padx=15, pady=(0, 15))

                tree_scroll = ttk.Scrollbar(tree_container)
                tree_scroll.pack(side="right", fill="y")

                advice_cols = ("WL", "Scrip", "Broker House", "Advice", "Date of Report")
                advice_tree = ttk.Treeview(
                    tree_container,
                    columns=advice_cols,
                    show="headings",
                    yscrollcommand=tree_scroll.set,
                    style="Watch.Treeview",
                )
                tree_scroll.config(command=advice_tree.yview)
                advice_tree.pack(side="left", fill="both", expand=True)

                # Configure Columns & Sorting
                for col in advice_cols:
                    advice_tree.heading(
                        col,
                        text=col if col != "WL" else "👁️",
                        command=lambda _col=col: universal_tree_sort(advice_tree, _col, False),
                    )
                    if col == "WL":
                        advice_tree.column(col, width=40, anchor="center", stretch=False)
                    elif col == "Scrip":
                        advice_tree.column(col, width=150, anchor="w")
                    elif col == "Broker House":
                        advice_tree.column(col, width=250, anchor="w")
                    elif col == "Advice":
                        advice_tree.column(col, width=250, anchor="w")
                    elif col == "Date of Report":
                        advice_tree.column(col, width=150, anchor="center")

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
                            cursor.execute("SELECT id_stk FROM stocks WHERE ticker = ? OR company_name = ?", (scrip, scrip))
                            row = cursor.fetchone()
                            if row:
                                id_stk = row[0]
                    except Exception as e:
                        logger.error(f"Failed to lookup stock ID for {scrip}: {e}")

                    row_values = ("➕",) + tuple(parts[:4])
                    if id_stk is not None:
                        advice_tree.insert("", "end", iid=str(id_stk), values=row_values)
                    else:
                        advice_tree.insert("", "end", values=("",) + tuple(parts[:4]))

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
                        try:
                            id_stk = int(item_id)
                        except ValueError:
                            return
                        
                        try:
                            with get_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "SELECT 1 FROM watchlist WHERE id_stk = ?", (id_stk,)
                                )
                                if cursor.fetchone():
                                    show_colorful_info(
                                        ai_win,
                                        "Watchlist",
                                        "This stock is already in your watchlist.",
                                    )
                                else:
                                    cursor.execute(
                                        "INSERT INTO watchlist (id_stk, target_buy_price, target_sell_price, notes) VALUES (?, 0.0, 0.0, '')",
                                        (id_stk,),
                                    )
                                    conn.commit()
                                    show_colorful_info(
                                        ai_win,
                                        "Watchlist",
                                        "Stock added to watchlist successfully.",
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
    ai_sell_btn.pack(side="right", padx=10)

    def run_portfolio_buy_scan():
        # Open Toplevel modal window
        ai_win = tk.Toplevel(win)
        ai_win.title("🟢 AI Buy Advice Scan")
        ai_win.geometry("1000x700")  # slightly wider to accommodate more columns
        ai_win.configure(bg=UI_THEME["bg_input"])
        ai_win.transient(win)
        ai_win.grab_set()
        ai_win.focus_set()

        # Bind Escape key to close
        ai_win.bind("<Escape>", lambda e: ai_win.destroy())

        header = tk.Label(
            ai_win,
            text="Scanning Market for Institutional Buy Advice (Last 7 Days)...",
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
            "3. Querying Gemini AI for recent broker buy calls, targets, and bands (Last 7 Days)...\n\n"
            "Please wait, this might take a few moments."
        )
        text_area.config(state="disabled")

        def _scan_thread():
            try:
                # 1. Fetch active scrip tickers from database
                scrip_list = []
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT DISTINCT ticker FROM stocks WHERE is_active = 1 AND ticker != ''")
                    for row in cursor.fetchall():
                        scrip_list.append(row[0])

                if not scrip_list:
                    win.after(0, _update_ui, "No active stocks with valid tickers found in your database.")
                    return

                # 2. Call AI Advisor in chunks to avoid Gemini search grounding payload overload
                from . import ai_analyzer
                API_KEY = ai_analyzer.get_api_key()

                # Split scrips into chunks of 40
                chunks = [scrip_list[i:i + 40] for i in range(0, len(scrip_list), 40)]
                
                advices = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    future_to_chunk = {
                        executor.submit(ai_analyzer.get_portfolio_buy_advice, chunk, API_KEY): chunk
                        for chunk in chunks
                    }
                    for future in concurrent.futures.as_completed(future_to_chunk):
                        try:
                            result = future.result()
                            if result:
                                advices.append(result)
                        except Exception as e:
                            logger.error(f"AI Buy advice chunk fetch failed: {e}")

                combined_advice = "\n".join(advices)
                win.after(0, _update_ui, combined_advice)

            except Exception as e:
                logger.error(f"AI Buy Scan failed: {e}")
                win.after(0, _update_ui, f"[System Error] Buy Scan failed: {e}")

        def _update_ui(content):
            if not ai_win.winfo_exists():
                return
            header.config(text="AI Buy Advice Scan Complete")

            if not content:
                content = "[System Error] No response or empty response received from AI."

            lines = content.strip().split("\n")
            table_lines = [line.strip() for line in lines if line.strip().startswith("|")]

            # We need at least 3 lines for a markdown table
            if len(table_lines) >= 3:
                text_area.pack_forget()

                tree_container = tk.Frame(ai_win, bg=UI_THEME["bg_input"])
                tree_container.pack(fill="both", expand=True, padx=15, pady=(0, 15))

                tree_scroll = ttk.Scrollbar(tree_container)
                tree_scroll.pack(side="right", fill="y")

                advice_cols = ("WL", "Scrip", "Buy Price Band", "Target Price", "Target Period", "Broker House", "Date of Report")
                advice_tree = ttk.Treeview(
                    tree_container,
                    columns=advice_cols,
                    show="headings",
                    yscrollcommand=tree_scroll.set,
                    style="Watch.Treeview",
                )
                tree_scroll.config(command=advice_tree.yview)
                advice_tree.pack(side="left", fill="both", expand=True)

                # Configure Columns & Sorting
                for col in advice_cols:
                    advice_tree.heading(
                        col,
                        text=col if col != "WL" else "👁️",
                        command=lambda _col=col: universal_tree_sort(advice_tree, _col, False),
                    )
                    if col == "WL":
                        advice_tree.column(col, width=40, anchor="center", stretch=False)
                    elif col == "Scrip":
                        advice_tree.column(col, width=120, anchor="w")
                    elif col == "Buy Price Band":
                        advice_tree.column(col, width=120, anchor="e")
                    elif col == "Target Price":
                        advice_tree.column(col, width=110, anchor="e")
                    elif col == "Target Period":
                        advice_tree.column(col, width=120, anchor="center")
                    elif col == "Broker House":
                        advice_tree.column(col, width=220, anchor="w")
                    elif col == "Date of Report":
                        advice_tree.column(col, width=120, anchor="center")

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
                            cursor.execute("SELECT id_stk FROM stocks WHERE ticker = ? OR company_name = ?", (scrip, scrip))
                            row = cursor.fetchone()
                            if row:
                                id_stk = row[0]
                    except Exception as e:
                        logger.error(f"Failed to lookup stock ID for {scrip}: {e}")

                    row_values = ("➕",) + tuple(parts[:6])
                    if id_stk is not None:
                        advice_tree.insert("", "end", iid=str(id_stk), values=row_values)
                    else:
                        advice_tree.insert("", "end", values=("",) + tuple(parts[:6]))

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
                        try:
                            id_stk = int(item_id)
                        except ValueError:
                            return
                        
                        try:
                            with get_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "SELECT 1 FROM watchlist WHERE id_stk = ?", (id_stk,)
                                )
                                if cursor.fetchone():
                                    show_colorful_info(
                                        ai_win,
                                        "Watchlist",
                                        "This stock is already in your watchlist.",
                                    )
                                else:
                                    cursor.execute(
                                        "INSERT INTO watchlist (id_stk, target_buy_price, target_sell_price, notes) VALUES (?, 0.0, 0.0, '')",
                                        (id_stk,),
                                    )
                                    conn.commit()
                                    show_colorful_info(
                                        ai_win,
                                        "Watchlist",
                                        "Stock added to watchlist successfully.",
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
    ai_buy_btn.pack(side="right", padx=10)

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
            "Querying Gemini AI...\n\nGathering live context and drafting plain-English explanation. Please wait.",
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
                    "[System Error] Could not load ai_analyzer.py module. Ensure it is in the StockMan folder.",
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
                cursor.execute("""
                    SELECT w.id_watch, s.company_name, s.ticker, w.target_buy_price, w.target_sell_price, w.notes, s.id_stk,
                           COALESCE((SELECT SUM(CASE WHEN t.trade_type_trd = 'BUY' THEN t.qty_trd WHEN t.trade_type_trd = 'SELL' THEN -t.qty_trd ELSE 0 END)
                            FROM transactions t WHERE t.id_stk = s.id_stk), 0) AS current_qty,
                           (SELECT ROUND(SUM(t.net_amt_trd) * 1.0 / NULLIF(SUM(t.qty_trd), 0), 2)
                            FROM transactions t
                            WHERE t.id_stk = s.id_stk AND t.trade_type_trd = 'BUY') AS all_time_avg,
                           s.curr_avg_price
                    FROM watchlist w
                    JOIN stocks s ON w.id_stk = s.id_stk
                    ORDER BY s.company_name ASC
                """)
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

    load_watchlist()

    win.bind("<Escape>", _close_manager)
    win.protocol("WM_DELETE_WINDOW", _close_manager)

    apply_button_animations(save_btn, "#22c55e", "#2563eb")
    apply_button_animations(clear_btn, "#f59e0b", "#d97706")
    apply_button_animations(delete_btn, "#ef4444", "#dc2626")
    apply_button_animations(close_btn, "#475569", "#334155")
    apply_button_animations(add_comp_btn, "#10b981", "#059669")
    apply_button_animations(scan_btn, "#8b5cf6", "#7c3aed")
    apply_button_animations(ai_sell_btn, "#d97706", "#b45309")
    apply_button_animations(ai_buy_btn, "#059669", "#047857")

    parent.wait_window(win)
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass
