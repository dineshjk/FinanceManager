# -*- coding: utf-8 -*-
# BankMan/manage_ins.py

import tkinter as tk
from tkinter import ttk

from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from Shared.gui_utils import universal_tree_sort, apply_button_animations
from .bank_database_setup import setup_bankman_database
from .bank_db_utils import get_ins_summary_for_display
from Shared.help_utils import show_standard_help

def _get_ins_help_data():
    guide_lines = [
        "This screen acts as a read-only summary dashboard for all your Insurance Policies.",
        "",
        "• Coverage: Tracks Term Life, Savings/Endowment, Health, Vehicle, and General insurance.",
        "• Grid Data: Aggregates total premiums paid and total payouts/claims received, grouped by Company, Category, Policy No, and Life Assured/Vehicle.",
        "• Navigation: Click any column header to sort your portfolio alphabetically or numerically.",
        "",
        "Hotkeys:",
        "• Escape: Close window"
    ]
    faq_data = [
        (
            "Q: How do I log a premium payment?",
            "A: This screen provides a consolidated summary. To log a new premium payment, use the main passbook form ('Data Entry' -> 'Bank'). Select 'INS' from the Module Type dropdown to link the withdrawal to a specific policy."
        ),
        (
            "Q: How do I handle maturity payouts or claims?",
            "A: Log a deposit in the passbook form and link it to the 'INS' module. It will automatically reflect under 'Total Payout (₹)' here."
        )
    ]
    return guide_lines, faq_data

def show_ins_main_menu(parent: tk.Toplevel | tk.Tk) -> None:
    """Show the Insurance Policies management window."""
    setup_bankman_database()
    disable_parent(parent)

    win = tk.Toplevel(parent)
    win.title("🛡️ Insurance Policies (Life, Health, Vehicle, General) 🛡️")
    win.geometry("1180x550")
    win.configure(bg="#1e293b")
    win.resizable(True, True)
    
    try:
        win.transient(parent)
    except tk.TclError:
        pass
        
    def _show_help(_e=None):
        guide, faq = _get_ins_help_data()
        show_standard_help(
            parent=win,
            title="Insurance Policies Help",
            guide_lines=guide,
            faq_data=faq
        )
    win.bind("<F1>", lambda e: None if getattr(e, "state", 0) & 0x0004 else _show_help(e))

    push_window(win, parent)

    def _close(_e=None):
        safe_close_modal(win, parent)
        return "break"

    win.bind("<Escape>", _close)
    win.protocol("WM_DELETE_WINDOW", _close)

    tk.Label(
        win,
        text="🛡️ Insurance Policies (Life, Health, Vehicle, General) 🛡️",
        font=("Helvetica", 18, "bold"),
        bg="#0f172a",
        fg="white",
        pady=10,
    ).pack(fill="x")

    tree_frame = tk.Frame(win, bg="#1e293b")
    tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

    vsb = ttk.Scrollbar(tree_frame, orient="vertical")
    hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
    
    cols = (
        "ID",
        "Category",
        "Company",
        "Policy No",
        "Plan Name",
        "Proposer",
        "Assured / Vehicle",
        "Premium (₹)",
        "Total Paid (₹)",
        "Total Payout (₹)",
        "Status"
    )
    
    style = ttk.Style()
    if "clam" not in style.theme_names():
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

    from Shared.globals import UI_THEME
    
    style.configure(
        "Dark.Treeview",
        background=UI_THEME.get("charcoal", "#334155"),
        foreground="white",
        fieldbackground=UI_THEME.get("charcoal", "#334155"),
        bordercolor=UI_THEME.get("slate_light", "#475569"),
        rowheight=30,
        font=UI_THEME.get("font_main", ("Helvetica", 12)),
    )
    style.configure(
        "Dark.Treeview.Heading",
        background=UI_THEME.get("dark_slate", "#1e293b"),
        foreground=UI_THEME.get("gold", "#FFD700"),
        font=UI_THEME.get("font_bold", ("Helvetica", 12, "bold")),
    )
    
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=vsb.set,
        xscrollcommand=hsb.set,
        selectmode="browse",
        style="Dark.Treeview",
    )
    vsb.config(command=tree.yview)
    hsb.config(command=tree.xview)
    
    vsb.pack(side="right", fill="y")
    hsb.pack(side="bottom", fill="x")
    tree.pack(side="left", fill="both", expand=True)
    
    for col in cols:
        tree.heading(
            col,
            text=col,
            command=lambda c=col: universal_tree_sort(tree, c, False),
        )
        if col == "ID":
            tree.column(col, width=40, anchor="center")
        elif col in ("Premium (₹)", "Total Paid (₹)", "Total Payout (₹)"):
            tree.column(col, width=110, anchor="e")
        elif col == "Status":
            tree.column(col, width=80, anchor="center")
        else:
            tree.column(col, width=120, anchor="w")

    def refresh_data():
        for item in tree.get_children():
            tree.delete(item)
            
        rows = get_ins_summary_for_display()
        for r in rows:
            # (id, company, category, policy, plan, proposer, assured, premium, start, maturity, paid, payout, active)
            status = "Active" if r[12] else "Closed"
            values = (
                r[0],
                r[2],
                r[1],
                r[3],
                r[4],
                r[5],
                r[6],
                f"{r[7]:,.2f}",
                f"{r[10]:,.2f}",
                f"{r[11]:,.2f}",
                status,
            )
            tree.insert("", "end", values=values)
            
    refresh_data()

    def _get_selected():
        sel = tree.selection()
        if not sel:
            return None, None
        item = tree.item(sel[0])["values"]
        return item[0], item[3]  # ID, Policy No

    def _on_edit():
        ins_id, policy = _get_selected()
        if ins_id is None:
            return
        from BankMan.ins_master_edit import edit_ins_master
        edit_ins_master(win, preselect_id=ins_id)
        refresh_data()

    def _on_delete():
        ins_id, policy = _get_selected()
        if ins_id is None:
            return
            
        from Shared.dialog_utils import show_colorful_error, show_colorful_yesno, show_colorful_info
        from Shared.globals import get_db_connection, BANK_DB_PATH
        import sqlite3
        
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM ins_transactions WHERE ins_master_id = ?", (ins_id,))
                row = cur.fetchone()
                tx_count = row[0] if row else 0
        except sqlite3.Error as e:
            show_colorful_error(win, "Error", f"Could not check transactions: {e}")
            return
            
        if tx_count > 0:
            show_colorful_error(win, "Cannot Delete", f"Policy '{policy}' has {tx_count} linked transaction(s).")
            return
            
        if show_colorful_yesno(win, "Confirm", f"Are you sure you want to delete policy '{policy}'?"):
            try:
                with get_db_connection(BANK_DB_PATH) as conn:
                    cur = conn.cursor()
                    cur.execute("PRAGMA foreign_keys = ON;")
                    cur.execute("DELETE FROM ins_master WHERE ins_master_id = ?", (ins_id,))
                    conn.commit()
                show_colorful_info(win, "Success", "Policy deleted successfully.")
                refresh_data()
            except sqlite3.Error as e:
                show_colorful_error(win, "Delete Failed", f"Database error: {e}")

    btn_frame = tk.Frame(win, bg="#1e293b", pady=10)
    btn_frame.pack(fill="x")
    
    edit_btn = tk.Button(
        btn_frame,
        text="✏️ Edit Selected",
        command=_on_edit,
        font=("Helvetica", 14, "bold"),
        bg="#1e293b",
        fg="#60a5fa",
        cursor="hand2",
        padx=12,
        pady=6,
        relief="flat",
    )
    edit_btn.pack(side="left", padx=10)
    apply_button_animations(edit_btn, "#1e293b", "#334155")

    del_btn = tk.Button(
        btn_frame,
        text="🗑️ Delete Selected",
        command=_on_delete,
        font=("Helvetica", 14, "bold"),
        bg="#1e293b",
        fg="#ef4444",
        cursor="hand2",
        padx=12,
        pady=6,
        relief="flat",
    )
    del_btn.pack(side="left", padx=10)
    apply_button_animations(del_btn, "#1e293b", "#334155")

    close_btn = tk.Button(
        btn_frame,
        text="❌ Close",
        command=_close,
        font=("Helvetica", 14, "bold"),
        bg="#ef4444",
        fg="white",
        cursor="hand2",
        padx=12,
        pady=6,
    )
    close_btn.pack(side="right", padx=10)
    apply_button_animations(close_btn, "#ef4444", "#b91c1c")

    refresh_btn = tk.Button(
        btn_frame,
        text="🔄 Refresh",
        command=refresh_data,
        font=("Helvetica", 14, "bold"),
        bg="#3b82f6",
        fg="white",
        cursor="hand2",
        padx=12,
        pady=6,
    )
    refresh_btn.pack(side="right", padx=10)
    apply_button_animations(refresh_btn, "#3b82f6", "#2563eb")

