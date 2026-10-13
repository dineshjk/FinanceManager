# -*- coding: utf-8 -*-
# BankMan/ins_master_edit.py

"""
Edit form for the ``ins_master`` table.
Presents a list of Insurance policies in a Treeview and lets the user edit or delete them.
"""

from typing import Union
import sqlite3
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from datetime import datetime

from Shared.gui_utils import (
    apply_button_animations,
    apply_entry_theme,
    INS_MASTER_EDIT_UI_THEME as _T,
    bind_tooltip,
    flash_error,
    setup_footer_tooltip,
    universal_tree_sort,
)
from Shared.dialog_utils import show_colorful_error, show_colorful_info, show_colorful_yesno
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from Shared.help_utils import show_standard_help
from .bank_db_utils import get_all_accounts
from Shared.globals import logger, get_db_connection, BANK_DB_PATH

# ---------------------------------------------------------------------------

def edit_ins_master(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
    preselect_id: int | None = None,
) -> None:
    """Open a modal two-panel window for editing ins_master records.

    Parameters
    ----------
    parent:
        Owning window.
    calling_button:
        The button that opened this modal.
    """
    # ── Lookup data fetched once at open ─────────────────────────────────
    accounts = get_all_accounts()
    # Display: "BankName : [AC_Number]"  →  ac_id
    account_map = {f"{a[1]} : [{a[3]}]": a[0] for a in accounts}

    # ── Modal window ──────────────────────────────────────────────────────
    disable_parent(parent, calling_button=calling_button)

    win = tk.Toplevel(parent)
    win.title("✏️  Edit Insurance Policy Master  ✏️")
    win.geometry("950x760")
    win.resizable(False, False)
    win.configure(bg=_T["main_bg"])
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    try:
        push_window(win, parent)
    except (RuntimeError, tk.TclError) as exc:
        logger.debug("push_window failed: %s", exc)

    # Footer tooltip
    tooltip_var = setup_footer_tooltip(win, bg_color=_T["header_bg"], fg_color=_T.get("header_fg", "white"))

    def cleanup_and_close(_event=None):
        return safe_close_modal(win, parent, calling_button)

    def show_help(win: tk.Toplevel) -> None:
        guide_lines = [
            "This screen allows you to modify the structural details of your registered Insurance Policies.",
            "",
            "• Selection: Click any row in the top grid to load its details into the editable form below.",
            "• Fields: Modify linked account, company, category, policy no, and dates.",
            "• Active: Uncheck for fully matured/closed policies.",
            "",
            "Hotkeys:",
            "• Escape: Cancel and Close",
            "• Ctrl+Enter: Save Changes"
        ]
        faq_data = [
            (
                "Q: Can I delete a policy here?",
                "A: Yes, using 'Delete Selected'. It will be blocked if there are existing INS transactions linked to this policy."
            )
        ]
        show_standard_help(
            parent=win,
            title="Insurance Master Edit Help",
            guide_lines=guide_lines,
            faq_data=faq_data
        )

    # Header
    header_frame = tk.Frame(win, bg=_T["header_bg"], relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=(5, 0))

    tk.Label(
        header_frame,
        text="✏️   Edit Insurance Policy Master   ✏️",
        font=("Helvetica", 18, "bold"),
        bg=_T["header_bg"],
        fg=_T.get("header_fg", "white"),
        relief="ridge",
        bd=2,
    ).pack(fill="x", pady=10)

    # Instruction row
    instr_frame = tk.Frame(win, bg=_T["header_bg"])
    instr_frame.pack(fill="x", padx=5, pady=(0, 2))

    tk.Label(
        instr_frame,
        text="Click a Policy row below to load it into the edit form.",
        font=("Helvetica", 12, "italic"),
        bg=_T["header_bg"],
        fg=_T.get("header_fg", "white"),
    ).pack(anchor="w", padx=10, pady=4)

    # Treeview
    tree_frame = tk.Frame(win, bg=_T["main_bg"], bd=1, relief="ridge")
    tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 4))

    tree_scroll = ttk.Scrollbar(tree_frame)
    tree_scroll.pack(side="right", fill="y")

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "INSEdit.Treeview",
        background=_T.get("readonly_bg", "#FADBD8"),
        foreground=_T.get("entry_fg", "black"),
        fieldbackground=_T.get("readonly_bg", "#FADBD8"),
        rowheight=30,
        font=("Helvetica", 12),
    )
    style.configure(
        "INSEdit.Treeview.Heading",
        background=_T["header_bg"],
        foreground=_T.get("header_fg", "white"),
        font=("Helvetica", 12, "bold"),
    )
    style.map(
        "INSEdit.Treeview",
        background=[("selected", _T.get("button_bg", "#991B1B"))],
        foreground=[("selected", "white")],
    )

    cols = ("ID", "Company", "Category", "Policy No", "Plan Name", "Premium", "Active")
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="INSEdit.Treeview",
        height=5,
    )
    tree_scroll.config(command=tree.yview)

    col_setup = {
        "ID": (0, tk.NO, "center"),
        "Company": (140, tk.YES, "w"),
        "Category": (100, tk.NO, "center"),
        "Policy No": (140, tk.NO, "w"),
        "Plan Name": (160, tk.YES, "w"),
        "Premium": (100, tk.NO, "e"),
        "Active": (80, tk.NO, "center"),
    }
    for col, (width, stretch, anchor) in col_setup.items():
        tree.heading(
            col,
            text=col,
            command=lambda c=col: universal_tree_sort(tree, c, False),
        )
        tree.column(col, width=width, stretch=stretch, anchor=anchor)

    tree.pack(fill="both", expand=True)

    # Data load
    def load_accounts() -> None:
        for item in tree.get_children():
            tree.delete(item)
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT  im.ins_master_id,
                            im.company_name,
                            im.ins_category,
                            im.policy_number,
                            im.plan_name,
                            im.proposer_name,
                            im.assured_item,
                            im.premium_amount,
                            im.start_dt,
                            im.maturity_dt,
                            im.is_active,
                            im.account_id,
                            im.sum_assured,
                            a.ac_number,
                            b.name
                    FROM    ins_master im
                    JOIN    accounts a ON a.ac_id = im.account_id
                    JOIN    banks    b ON b.b_id  = a.b_id
                    ORDER BY im.company_name, im.policy_number
                """)
                for row in cursor.fetchall():
                    is_active_str = "Yes" if row[10] else "No"
                    tree.insert(
                        "",
                        "end",
                        values=(
                            row[0],  # ID
                            row[1],  # Company
                            row[2],  # Category
                            row[3],  # Policy No
                            row[4],  # Plan Name
                            f"{row[7]:.2f}",  # Premium
                            is_active_str,
                            row[11], # account_id
                            row[12], # ac_number
                            row[13], # bank name
                            row[5],  # proposer
                            row[6],  # assured
                            row[8],  # start_dt
                            row[9],  # maturity_dt
                            row[14], # sum_assured
                        ),
                    )
        except sqlite3.Error as exc:
            logger.error("edit_ins_master: failed to load accounts: %s", exc)

    load_accounts()
    


    # Divider and "selected" status label
    divider_frame = tk.Frame(win, height=2, bg=_T["header_bg"])
    divider_frame.pack(fill="x", padx=5, pady=(2, 0))

    sel_label_frame = tk.Frame(win, bg=_T["header_bg"])
    sel_label_frame.pack(fill="x", padx=5, pady=0)

    sel_status_var = tk.StringVar(
        value="No policy selected — click a row in the list above."
    )
    tk.Label(
        sel_label_frame,
        textvariable=sel_status_var,
        font=("Helvetica", 12, "bold"),
        bg=_T["header_bg"],
        fg=_T.get("header_fg", "white"),
    ).pack(anchor="w", padx=10, pady=4)

    # Edit form
    selected_id = {"ins_master_id": None}

    form_frame = tk.Frame(win, bg=_T["main_bg"])
    form_frame.pack(fill="x", padx=10, pady=4)

    # Row 0: Linked Account
    tk.Label(
        form_frame, text="Linked Account:", font=("Helvetica", 12), bg=_T["main_bg"], fg=_T["label_fg"]
    ).grid(row=0, column=0, sticky="w", padx=5, pady=2)
    
    account_combo = ttk.Combobox(form_frame, width=58, font=("Helvetica", 12, "bold"), state="disabled")
    account_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
    account_combo["values"] = list(account_map.keys())
    apply_entry_theme(account_combo)

    # Row 1: Company
    tk.Label(
        form_frame, text="Company Name:", font=("Helvetica", 12), bg=_T["main_bg"], fg=_T["label_fg"]
    ).grid(row=1, column=0, sticky="w", padx=5, pady=2)
    
    company_var = tk.StringVar()
    company_entry = tk.Entry(form_frame, width=60, textvariable=company_var, font=("Helvetica", 12, "bold"))
    company_entry.grid(row=1, column=1, sticky="w", padx=5, pady=2)
    company_entry.config(state="disabled")
    apply_entry_theme(company_entry)

    # Row 2: Category
    tk.Label(
        form_frame, text="Category:", font=("Helvetica", 12), bg=_T["main_bg"], fg=_T["label_fg"]
    ).grid(row=2, column=0, sticky="w", padx=5, pady=2)
    
    category_combo = ttk.Combobox(form_frame, values=['LIFE_TERM', 'LIFE_SAVINGS', 'HEALTH', 'VEHICLE', 'GENERAL'], width=58, font=("Helvetica", 12, "bold"), state="disabled")
    category_combo.grid(row=2, column=1, sticky="w", padx=5, pady=2)
    apply_entry_theme(category_combo)

    # Row 3: Policy No
    tk.Label(
        form_frame, text="Policy Number:", font=("Helvetica", 12), bg=_T["main_bg"], fg=_T["label_fg"]
    ).grid(row=3, column=0, sticky="w", padx=5, pady=2)
    
    policy_var = tk.StringVar()
    policy_entry = tk.Entry(form_frame, width=60, textvariable=policy_var, font=("Helvetica", 12, "bold"))
    policy_entry.grid(row=3, column=1, sticky="w", padx=5, pady=2)
    policy_entry.config(state="disabled")
    apply_entry_theme(policy_entry)

    # Row 4: Plan Name
    tk.Label(
        form_frame, text="Plan Name:", font=("Helvetica", 12), bg=_T["main_bg"], fg=_T["label_fg"]
    ).grid(row=4, column=0, sticky="w", padx=5, pady=2)
    
    plan_var = tk.StringVar()
    plan_entry = tk.Entry(form_frame, width=60, textvariable=plan_var, font=("Helvetica", 12, "bold"))
    plan_entry.grid(row=4, column=1, sticky="w", padx=5, pady=2)
    plan_entry.config(state="disabled")
    apply_entry_theme(plan_entry)

    # Row 5: Proposer Name
    tk.Label(
        form_frame, text="Proposer Name:", font=("Helvetica", 12), bg=_T["main_bg"], fg=_T["label_fg"]
    ).grid(row=5, column=0, sticky="w", padx=5, pady=2)
    
    proposer_var = tk.StringVar()
    proposer_entry = tk.Entry(form_frame, width=60, textvariable=proposer_var, font=("Helvetica", 12, "bold"))
    proposer_entry.grid(row=5, column=1, sticky="w", padx=5, pady=2)
    proposer_entry.config(state="disabled")
    apply_entry_theme(proposer_entry)

    # Row 6: Assured Item
    tk.Label(
        form_frame, text="Life Assured/Vehicle:", font=("Helvetica", 12), bg=_T["main_bg"], fg=_T["label_fg"]
    ).grid(row=6, column=0, sticky="w", padx=5, pady=2)
    
    assured_var = tk.StringVar()
    assured_entry = tk.Entry(form_frame, width=60, textvariable=assured_var, font=("Helvetica", 12, "bold"))
    assured_entry.grid(row=6, column=1, sticky="w", padx=5, pady=2)
    assured_entry.config(state="disabled")
    apply_entry_theme(assured_entry)

    # Row 7: Sum Assured
    tk.Label(
        form_frame, text="Sum Assured:", font=("Helvetica", 12), bg=_T["main_bg"], fg=_T["label_fg"]
    ).grid(row=7, column=0, sticky="w", padx=5, pady=2)
    
    sum_assured_var = tk.StringVar()
    sum_assured_entry = tk.Entry(form_frame, width=60, textvariable=sum_assured_var, font=("Helvetica", 12, "bold"))
    sum_assured_entry.grid(row=7, column=1, sticky="w", padx=5, pady=2)
    sum_assured_entry.config(state="disabled")
    apply_entry_theme(sum_assured_entry)

    # Row 8: Premium
    tk.Label(
        form_frame, text="Premium Amount:", font=("Helvetica", 12), bg=_T["main_bg"], fg=_T["label_fg"]
    ).grid(row=8, column=0, sticky="w", padx=5, pady=2)
    
    premium_var = tk.StringVar()
    premium_entry = tk.Entry(form_frame, width=60, textvariable=premium_var, font=("Helvetica", 12, "bold"))
    premium_entry.grid(row=8, column=1, sticky="w", padx=5, pady=2)
    premium_entry.config(state="disabled")
    apply_entry_theme(premium_entry)

    # Row 9: Start Date
    tk.Label(
        form_frame, text="Start Date:", font=("Helvetica", 12), bg=_T["main_bg"], fg=_T["label_fg"]
    ).grid(row=9, column=0, sticky="w", padx=5, pady=2)
    
    start_dt = DateEntry(form_frame, date_pattern="dd-mm-yyyy", width=20, font=("Helvetica", 12, "bold"), state="disabled")
    start_dt.grid(row=9, column=1, sticky="w", padx=5, pady=2)
    apply_entry_theme(start_dt)

    # Row 10: Maturity Date
    tk.Label(
        form_frame, text="Maturity/Renewal Date:", font=("Helvetica", 12), bg=_T["main_bg"], fg=_T["label_fg"]
    ).grid(row=10, column=0, sticky="w", padx=5, pady=2)
    
    maturity_dt = DateEntry(form_frame, date_pattern="dd-mm-yyyy", width=20, font=("Helvetica", 12, "bold"), state="disabled")
    maturity_dt.grid(row=10, column=1, sticky="w", padx=5, pady=2)
    apply_entry_theme(maturity_dt)

    # Row 11: Active
    is_active_var = tk.BooleanVar(value=True)
    is_active_chk = tk.Checkbutton(
        form_frame,
        variable=is_active_var,
        text="Active",
        font=("Helvetica", 12),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
        selectcolor=_T["main_bg"],
        activebackground=_T["main_bg"],
        activeforeground=_T["label_fg"],
        cursor="hand2",
        state="disabled",
    )
    is_active_chk.grid(row=11, column=1, sticky="w", padx=5, pady=2)

    # Treeview selection
    def on_tree_select(_event=None) -> None:
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0])["values"]
        ins_id = vals[0]
        company = vals[1]
        category = vals[2]
        policy = vals[3]
        plan = vals[4]
        premium = vals[5]
        is_active = True if vals[6] == "Yes" else False
        
        ac_number = vals[8]
        bank_name = vals[9]
        proposer = vals[10]
        assured = vals[11]
        sdt_str = vals[12]
        mdt_str = vals[13]
        sum_assured_val = vals[14]

        selected_id["ins_master_id"] = ins_id
        
        account_label = f"{bank_name} : [{ac_number}]"
        if account_label in account_map:
            account_combo.set(account_label)
        else:
            account_combo.set("")

        company_var.set(company)
        category_combo.set(category)
        policy_var.set(policy)
        plan_var.set(plan)
        proposer_var.set(proposer)
        assured_var.set(assured)
        sum_assured_var.set(str(sum_assured_val) if sum_assured_val is not None else "")
        premium_var.set(str(premium))
        is_active_var.set(is_active)
        
        account_combo.config(state="readonly")
        company_entry.config(state="normal")
        category_combo.config(state="readonly")
        policy_entry.config(state="normal")
        plan_entry.config(state="normal")
        proposer_entry.config(state="normal")
        assured_entry.config(state="normal")
        sum_assured_entry.config(state="normal")
        premium_entry.config(state="normal")
        start_dt.config(state="normal")
        maturity_dt.config(state="normal")
        is_active_chk.config(state="normal")
        
        try:
            start_dt.set_date(datetime.strptime(sdt_str, "%Y-%m-%d").date())
        except Exception:
            pass
        if mdt_str:
            try:
                maturity_dt.set_date(datetime.strptime(mdt_str, "%Y-%m-%d").date())
            except Exception:
                pass

        save_btn.config(state="normal")
        delete_btn.config(state="normal")
        sel_status_var.set(f"Editing:  {company} - {policy}")
        company_entry.focus_set()

    tree.bind("<<TreeviewSelect>>", on_tree_select)
    tree.bind("<Double-1>", on_tree_select)

    # Save
    def on_save(_event=None) -> None:
        ins_id = selected_id["ins_master_id"]
        if ins_id is None:
            show_colorful_error(win, "No Selection", "Please select a policy first.")
            return

        account_label = account_combo.get().strip()
        if not account_label or account_label not in account_map:
            show_colorful_error(win, "Validation Error", "Please select a valid linked bank account.")
            flash_error(account_combo)
            return
        account_id = account_map[account_label]

        company = company_var.get().strip()
        category = category_combo.get().strip()
        policy = policy_var.get().strip()
        plan = plan_var.get().strip()
        proposer = proposer_var.get().strip()
        assured = assured_var.get().strip()
        sum_assured_str = sum_assured_var.get().strip()
        premium_str = premium_var.get().strip()
        
        if not company or not policy or not plan or not proposer or not assured:
            show_colorful_error(win, "Validation", "Missing required fields.")
            return

        sum_assured = None
        if sum_assured_str:
            try:
                sum_assured = float(sum_assured_str)
            except ValueError:
                show_colorful_error(win, "Validation", "Sum Assured must be a valid number.")
                flash_error(sum_assured_entry)
                return

        try:
            premium = float(premium_str) if premium_str else 0.0
        except ValueError:
            show_colorful_error(win, "Validation", "Premium must be a valid number.")
            flash_error(premium_entry)
            return

        try:
            sdt_str = start_dt.get_date().strftime("%Y-%m-%d")
        except Exception:
            show_colorful_error(win, "Validation Error", "Invalid Start Date.")
            return

        try:
            mdt_str = maturity_dt.get_date().strftime("%Y-%m-%d")
        except Exception:
            mdt_str = ""
            
        if mdt_str and mdt_str <= sdt_str:
            show_colorful_error(win, "Validation Error", "Maturity Date must be after Start Date.")
            flash_error(maturity_dt)
            return

        is_active = 1 if is_active_var.get() else 0

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE ins_master
                    SET    account_id = ?,
                           company_name = ?,
                           ins_category = ?,
                           policy_number = ?,
                           plan_name = ?,
                           proposer_name = ?,
                           assured_item = ?,
                           sum_assured = ?,
                           premium_amount = ?,
                           start_dt = ?,
                           maturity_dt = ?,
                           is_active = ?
                    WHERE  ins_master_id = ?
                """, (account_id, company, category, policy, plan, proposer, assured, sum_assured, premium, sdt_str, mdt_str, is_active, ins_id))
                conn.commit()

            show_colorful_info(win, "Success", f"Policy '{policy}' updated.")
            load_accounts()
            _reset_form()
            sel_status_var.set("Saved — select another policy or close.")
        except sqlite3.IntegrityError as exc:
            show_colorful_error(win, "Integrity Error", f"Must be unique.\nDetail: {exc}")
        except Exception as exc:
            show_colorful_error(win, "Error", f"Failed to update:\n{exc}")
            logger.exception("edit_ins_master: UPDATE failed for ins_master_id=%s", ins_id)

    # Delete
    def on_delete(_event=None) -> None:
        ins_id = selected_id["ins_master_id"]
        if ins_id is None:
            return

        policy = policy_var.get().strip()
        tx_count = 0
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM ins_transactions WHERE ins_master_id = ?", (ins_id,))
                row = cur.fetchone()
                if row:
                    tx_count = row[0]
        except sqlite3.Error as e:
            show_colorful_error(win, "Error", f"Could not check linked transactions: {e}")
            return

        if tx_count > 0:
            show_colorful_error(win, "Cannot Delete", f"Policy has {tx_count} transaction(s).")
            return

        confirm = show_colorful_yesno(win, "Confirm Delete", f"Delete policy:\n{policy}\n?")
        if not confirm:
            return

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys = ON;")
                cur.execute("DELETE FROM ins_master WHERE ins_master_id = ?", (ins_id,))
                conn.commit()

            show_colorful_info(win, "Success", f"Deleted '{policy}'.")
            load_accounts()
            _reset_form()
            sel_status_var.set("Deleted — select another policy or close.")
        except sqlite3.Error as e:
            show_colorful_error(win, "Delete Failed", f"Database error: {e}")

    def _reset_form() -> None:
        selected_id["ins_master_id"] = None
        account_combo.set("")
        company_var.set("")
        category_combo.set("")
        policy_var.set("")
        plan_var.set("")
        proposer_var.set("")
        assured_var.set("")
        sum_assured_var.set("")
        premium_var.set("")
        is_active_var.set(True)

        account_combo.config(state="disabled")
        company_entry.config(state="disabled")
        category_combo.config(state="disabled")
        policy_entry.config(state="disabled")
        plan_entry.config(state="disabled")
        proposer_entry.config(state="disabled")
        assured_entry.config(state="disabled")
        sum_assured_entry.config(state="disabled")
        premium_entry.config(state="disabled")
        start_dt.config(state="disabled")
        maturity_dt.config(state="disabled")
        is_active_chk.config(state="disabled")

        save_btn.config(state="disabled")
        delete_btn.config(state="disabled")

    save_btn: tk.Button
    delete_btn: tk.Button

    # Button frame
    btn_frame = tk.Frame(win, bg=_T["main_bg"], relief="ridge", bd=2, pady=6)
    btn_frame.pack(fill="x", padx=10, pady=(4, 6))

    delete_btn = tk.Button(
        btn_frame,
        text="🗑️  DELETE SELECTED  🗑️",
        command=on_delete,
        font=("Helvetica", 14, "bold"),
        bg=_T.get("cancel_bg", "#ef4444"),
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        padx=8,
        pady=4,
        cursor="hand2",
        state="disabled",
    )
    delete_btn.pack(side="left", padx=8)

    save_btn = tk.Button(
        btn_frame,
        text="💾  SAVE CHANGES  💾",
        command=on_save,
        font=("Helvetica", 14, "bold"),
        bg=_T.get("submit_bg", "#22c55e"),
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        padx=8,
        pady=4,
        cursor="hand2",
        state="disabled",
    )
    save_btn.pack(side="right", padx=8)

    cancel_btn = tk.Button(
        btn_frame,
        text="❌  Cancel / Close  ❌",
        command=cleanup_and_close,
        font=("Helvetica", 14, "bold"),
        bg=_T.get("cancel_bg", "#ef4444"),
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        padx=8,
        pady=4,
        cursor="hand2",
    )
    cancel_btn.pack(side="right", padx=4)

    apply_button_animations(delete_btn, _T.get("cancel_bg", "#ef4444"), _T.get("cancel_hover_bg", "#991b1b"))
    apply_button_animations(save_btn, _T.get("submit_bg", "#22c55e"), _T.get("submit_hover_bg", "#16a34a"))
    apply_button_animations(cancel_btn, _T.get("cancel_bg", "#ef4444"), _T.get("cancel_hover_bg", "#991b1b"))

    # Window-level bindings
    win.bind("<Control-Return>", lambda e: save_btn.invoke())
    win.bind("<Escape>", cleanup_and_close)
    win.protocol("WM_DELETE_WINDOW", cleanup_and_close)
    win.bind("<F1>", lambda e: None if (getattr(e, "state", 0) & 0x0004) else (show_help(win)))

    if preselect_id is not None:
        for item in tree.get_children():
            if tree.item(item)["values"][0] == preselect_id:
                tree.selection_set(item)
                on_tree_select()
                break
        
        # Hide the list components to make it a pure edit window
        instr_frame.pack_forget()
        tree_frame.pack_forget()
        sel_label_frame.pack_forget()
        try:
            divider_frame.pack_forget()
        except NameError:
            pass
            
        # Resize window smaller since tree is hidden
        win.geometry("950x550")
        
    parent.wait_window(win)
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except Exception:
        pass
