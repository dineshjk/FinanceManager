# -*- coding: utf-8 -*-
# BankMan/manage_mf.py

import tkinter as tk
from tkinter import ttk

from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from Shared.gui_utils import universal_tree_sort, apply_button_animations
from .bank_database_setup import setup_bankman_database
from .bank_db_utils import get_mf_summary_for_display
from Shared.help_utils import show_standard_help

def _get_mf_help_data():
    guide_lines = [
        "This screen acts as a read-only summary dashboard for all your Mutual Fund investments.",
        "",
        "• Grid Data: It aggregates total SIPs/lump-sums (Total Invested) and total withdrawals (Total Redeemed) grouped by AMC, RTA, Folio Number, and Scheme Name.",
        "• Navigation: Click any column header to sort your portfolio alphabetically or numerically.",
        "",
        "Hotkeys:",
        "• Escape: Close window"
    ]
    faq_data = [
        (
            "Q: How do I add or edit a Mutual Fund transaction?",
            "A: This screen provides a consolidated summary. To log new SIPs, lump-sum purchases, or redemptions, use the main passbook form ('Data Entry' -> 'Bank'). Select 'MF' from the Module Type dropdown to link the transaction to a specific folio. To edit existing transactions, use 'Manage Transactions'."
        )
    ]
    return guide_lines, faq_data

def show_mf_main_menu(parent: tk.Toplevel | tk.Tk) -> None:
    """Show the Mutual Funds Portfolio management window."""
    setup_bankman_database()
    disable_parent(parent)

    win = tk.Toplevel(parent)
    win.title("📈 Mutual Funds Portfolio (MFMan) 📈")
    win.geometry("1050x550")
    win.configure(bg="#1e293b")
    win.resizable(True, True)
    
    # Try transient if needed, but push_window usually handles focus
    try:
        win.transient(parent)
    except tk.TclError:
        pass
        
    def _show_help(_e=None):
        guide, faq = _get_mf_help_data()
        show_standard_help(
            parent=win,
            title="Mutual Funds Portfolio Help",
            guide_lines=guide,
            faq_data=faq
        )
    win.bind("<F1>", lambda e: None if getattr(e, "state", 0) & 0x0004 else _show_help(e))

    push_window(win, parent)

    # Clean up function
    def _close(_e=None):
        safe_close_modal(win, parent)
        return "break"

    win.bind("<Escape>", _close)
    win.protocol("WM_DELETE_WINDOW", _close)

    # Title label
    tk.Label(
        win,
        text="📈 Mutual Funds Portfolio (MFMan) 📈",
        font=("Helvetica", 16, "bold"),
        bg="#0f172a",
        fg="white",
        pady=10,
    ).pack(fill="x")

    # Frame for Treeview
    tree_frame = tk.Frame(win, bg="#1e293b")
    tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Scrollbars
    vsb = ttk.Scrollbar(tree_frame, orient="vertical")
    hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
    
    cols = (
        "ID",
        "AMC",
        "RTA",
        "Folio No",
        "Scheme Name",
        "Linked Account",
        "Total Invested (₹)",
        "Total Redeemed (₹)",
        "Status"
    )
    
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=vsb.set,
        xscrollcommand=hsb.set,
        selectmode="browse",
    )
    vsb.config(command=tree.yview)
    hsb.config(command=tree.xview)
    
    vsb.pack(side="right", fill="y")
    hsb.pack(side="bottom", fill="x")
    tree.pack(side="left", fill="both", expand=True)
    
    # Configure headings and sort
    for col in cols:
        tree.heading(
            col,
            text=col,
            command=lambda c=col: universal_tree_sort(tree, c, False),
        )
        if col == "ID":
            tree.column(col, width=40, anchor="center")
        elif col in ("Total Invested (₹)", "Total Redeemed (₹)"):
            tree.column(col, width=120, anchor="e")
        elif col == "Status":
            tree.column(col, width=80, anchor="center")
        else:
            tree.column(col, width=150, anchor="w")

    def refresh_data():
        for item in tree.get_children():
            tree.delete(item)
            
        rows = get_mf_summary_for_display()
        for r in rows:
            # (mf_master_id, amc_name, rta_name, folio_number, scheme_name, bank_acct, invested, redeemed, is_active)
            status = "Active" if r[8] else "Closed"
            values = (
                r[0],
                r[1],
                r[2],
                r[3],
                r[4],
                r[5],
                f"{r[6]:,.2f}",
                f"{r[7]:,.2f}",
                status,
            )
            tree.insert("", "end", values=values)
            
    refresh_data()

    # Bottom Buttons
    btn_frame = tk.Frame(win, bg="#1e293b", pady=10)
    btn_frame.pack(fill="x")
    
    btn_bg = "#3b82f6"
    btn_fg = "white"

    refresh_btn = tk.Button(
        btn_frame,
        text="🔄 Refresh",
        command=refresh_data,
        font=("Helvetica", 11, "bold"),
        bg=btn_bg,
        fg=btn_fg,
        cursor="hand2",
        padx=12,
        pady=6,
    )
    refresh_btn.pack(side="left", padx=10)
    apply_button_animations(refresh_btn, btn_bg, "#2563eb")

    close_btn = tk.Button(
        btn_frame,
        text="❌ Close",
        command=_close,
        font=("Helvetica", 11, "bold"),
        bg="#ef4444",
        fg="white",
        cursor="hand2",
        padx=12,
        pady=6,
    )
    close_btn.pack(side="right", padx=10)
    apply_button_animations(close_btn, "#ef4444", "#b91c1c")

