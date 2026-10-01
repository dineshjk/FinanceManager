# -*- coding: utf-8 -*-
# BankMan/ppf_master_edit.py

"""
Edit form for the ``ppf_master`` table.
Presents a list of PPF accounts in a Treeview and lets the user edit or delete them.
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
    PPF_MASTER_ADD_UI_THEME as _T,
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

def edit_ppf_master(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Open a modal two-panel window for editing ppf_master records.

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
    win.title("✏️  Edit PPF Master  ✏️")
    win.geometry("950x660")
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
            "This screen allows you to modify the structural details of your registered PPF accounts.",
            "",
            "• Selection: Click any row in the top grid to load its details into the editable form below.",
            "• Fields: You can modify the Linked Account, PPF Account No, Holder Name, and Dates.",
            "• Active: Uncheck for fully closed accounts.",
            "",
            "Hotkeys:",
            "• Escape: Cancel and Close",
            "• Ctrl+Enter: Save Changes"
        ]
        faq_data = [
            (
                "Q: Can I delete an account here?",
                "A: Yes, using 'Delete Selected'. It will be blocked if there are existing PPF transactions linked to this account."
            )
        ]
        show_standard_help(
            parent=win,
            title="PPF Master Edit Help",
            guide_lines=guide_lines,
            faq_data=faq_data
        )

    # Header
    header_frame = tk.Frame(win, bg=_T["header_bg"], relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=(5, 0))

    tk.Label(
        header_frame,
        text="✏️   Edit PPF Master Account   ✏️",
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
        text="Click a PPF account row below to load it into the edit form.",
        font=("Helvetica", 11, "italic"),
        bg=_T["header_bg"],
        fg="#FFD1D1",
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
        "PPFEdit.Treeview",
        background="#013220",
        foreground="white",
        fieldbackground="#013220",
        rowheight=26,
        font=("Helvetica", 11),
    )
    style.configure(
        "PPFEdit.Treeview.Heading",
        background=_T["header_bg"],
        foreground=_T.get("header_fg", "white"),
        font=("Helvetica", 11, "bold"),
    )
    style.map(
        "PPFEdit.Treeview",
        background=[("selected", "#00704A")],
        foreground=[("selected", "white")],
    )

    cols = ("ID", "PPF Account No", "Holder Name", "Bank", "Open Date", "Maturity Date", "Active")
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="PPFEdit.Treeview",
        height=5,
    )
    tree_scroll.config(command=tree.yview)

    col_setup = {
        "ID": (0, tk.NO, "center"),
        "PPF Account No": (150, tk.NO, "w"),
        "Holder Name": (180, tk.YES, "w"),
        "Bank": (160, tk.YES, "w"),
        "Open Date": (100, tk.NO, "center"),
        "Maturity Date": (100, tk.NO, "center"),
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
                    SELECT  pm.ppf_master_id,
                            pm.ppf_account_number,
                            pm.holder_name,
                            b.name,
                            pm.open_dt,
                            pm.maturity_dt,
                            pm.is_active,
                            pm.account_id,
                            a.ac_number
                    FROM    ppf_master pm
                    JOIN    accounts a ON a.ac_id = pm.account_id
                    JOIN    banks    b ON b.b_id  = a.b_id
                    ORDER BY pm.holder_name, pm.ppf_account_number
                """)
                for row in cursor.fetchall():
                    is_active_str = "Yes" if row[6] else "No"
                    tree.insert(
                        "",
                        "end",
                        values=(
                            row[0],  # ID
                            row[1],  # PPF Account No
                            row[2],  # Holder Name
                            row[3],  # Bank Name
                            row[4],  # Open Date
                            row[5],  # Maturity Date
                            is_active_str,
                            row[7],  # account_id
                            row[8],  # ac_number
                        ),
                    )
        except sqlite3.Error as exc:
            logger.error("edit_ppf_master: failed to load accounts: %s", exc)

    load_accounts()

    # Divider and "selected" status label
    tk.Frame(win, height=2, bg=_T["header_bg"]).pack(fill="x", padx=5, pady=(2, 0))

    sel_label_frame = tk.Frame(win, bg=_T["header_bg"])
    sel_label_frame.pack(fill="x", padx=5, pady=0)

    sel_status_var = tk.StringVar(
        value="No account selected — click a row in the list above."
    )
    tk.Label(
        sel_label_frame,
        textvariable=sel_status_var,
        font=("Helvetica", 11, "bold"),
        bg=_T["header_bg"],
        fg="#FFD1D1",
    ).pack(anchor="w", padx=10, pady=4)

    # Edit form
    selected_id = {"ppf_master_id": None}

    form_frame = tk.Frame(win, bg=_T["main_bg"])
    form_frame.pack(fill="x", padx=10, pady=4)

    # Row 0: Linked Account
    tk.Label(
        form_frame,
        text="Linked Account:",
        font=("Helvetica", 13),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
    ).grid(row=0, column=0, sticky="w", padx=5, pady=4)
    
    account_combo = ttk.Combobox(
        form_frame,
        width=62,
        font=("Helvetica", 13, "bold"),
        state="disabled",
    )
    account_combo.grid(row=0, column=1, sticky="w", padx=5, pady=4)
    account_combo["values"] = list(account_map.keys())
    apply_entry_theme(account_combo)
    bind_tooltip(
        account_combo,
        tooltip_var,
        "Bank account to which this PPF account is linked.",
    )

    # Row 1: PPF Account Number
    tk.Label(
        form_frame,
        text="PPF Account No:",
        font=("Helvetica", 13),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
    ).grid(row=1, column=0, sticky="w", padx=5, pady=4)
    
    ppf_no_var = tk.StringVar()
    ppf_no_entry = tk.Entry(form_frame, width=65, textvariable=ppf_no_var, font=("Helvetica", 13, "bold"))
    ppf_no_entry.grid(row=1, column=1, sticky="w", padx=5, pady=4)
    ppf_no_entry.config(state="disabled")
    apply_entry_theme(ppf_no_entry)
    bind_tooltip(
        ppf_no_entry,
        tooltip_var,
        "PPF Account Number.",
    )

    # Row 2: Holder Name
    tk.Label(
        form_frame,
        text="Holder Name:",
        font=("Helvetica", 13),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
    ).grid(row=2, column=0, sticky="w", padx=5, pady=4)
    
    holder_var = tk.StringVar()
    holder_entry = tk.Entry(form_frame, width=65, textvariable=holder_var, font=("Helvetica", 13, "bold"))
    holder_entry.grid(row=2, column=1, sticky="w", padx=5, pady=4)
    holder_entry.config(state="disabled")
    apply_entry_theme(holder_entry)
    bind_tooltip(
        holder_entry,
        tooltip_var,
        "Name of the PPF account holder.",
    )

    # Row 3: Open Date
    tk.Label(
        form_frame,
        text="Open Date:",
        font=("Helvetica", 13),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
    ).grid(row=3, column=0, sticky="w", padx=5, pady=4)
    
    open_dt = DateEntry(form_frame, date_pattern="dd-mm-yyyy", width=20, font=("Helvetica", 13, "bold"), state="disabled")
    open_dt.grid(row=3, column=1, sticky="w", padx=5, pady=4)
    apply_entry_theme(open_dt)

    # Row 4: Maturity Date
    tk.Label(
        form_frame,
        text="Maturity Date:",
        font=("Helvetica", 13),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
    ).grid(row=4, column=0, sticky="w", padx=5, pady=4)
    
    maturity_dt = DateEntry(form_frame, date_pattern="dd-mm-yyyy", width=20, font=("Helvetica", 13, "bold"), state="disabled")
    maturity_dt.grid(row=4, column=1, sticky="w", padx=5, pady=4)
    apply_entry_theme(maturity_dt)

    # Row 5: Active
    is_active_var = tk.BooleanVar(value=True)
    is_active_chk = tk.Checkbutton(
        form_frame,
        variable=is_active_var,
        text="Active",
        font=("Helvetica", 13),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
        selectcolor="#013220",
        activebackground=_T["main_bg"],
        activeforeground=_T["label_fg"],
        cursor="hand2",
        state="disabled",
    )
    is_active_chk.grid(row=5, column=1, sticky="w", padx=5, pady=4)

    # Treeview selection
    def on_tree_select(_event=None) -> None:
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0])["values"]
        ppf_id = vals[0]
        ppf_acct_no = vals[1]
        holder = vals[2]
        bank_name = vals[3]
        od_str = vals[4]
        md_str = vals[5]
        is_active = True if vals[6] == "Yes" else False
        vals[7]
        ac_number = vals[8]

        selected_id["ppf_master_id"] = ppf_id
        
        account_label = f"{bank_name} : [{ac_number}]"
        if account_label in account_map:
            account_combo.set(account_label)
        else:
            account_combo.set("")

        ppf_no_var.set(ppf_acct_no)
        holder_var.set(holder)
        is_active_var.set(is_active)
        
        # Set dates
        account_combo.config(state="readonly")
        ppf_no_entry.config(state="normal")
        holder_entry.config(state="normal")
        open_dt.config(state="normal")
        maturity_dt.config(state="normal")
        is_active_chk.config(state="normal")
        
        try:
            open_dt.set_date(datetime.strptime(od_str, "%Y-%m-%d").date())
        except Exception:
            pass
        try:
            maturity_dt.set_date(datetime.strptime(md_str, "%Y-%m-%d").date())
        except Exception:
            pass

        save_btn.config(state="normal")
        delete_btn.config(state="normal")
        sel_status_var.set(f"Editing:  {holder} - {ppf_acct_no}")
        ppf_no_entry.focus_set()

    tree.bind("<<TreeviewSelect>>", on_tree_select)
    tree.bind("<Double-1>", on_tree_select)

    # Tab-order
    account_combo.bind("<Return>", lambda _e: ppf_no_entry.focus_set())
    ppf_no_entry.bind("<Return>", lambda _e: holder_entry.focus_set())
    holder_entry.bind("<Return>", lambda _e: open_dt.focus_set())
    open_dt.bind("<Return>", lambda _e: maturity_dt.focus_set())
    maturity_dt.bind("<Return>", lambda _e: save_btn.focus_set())

    # Save
    def on_save(_event=None) -> None:
        ppf_id = selected_id["ppf_master_id"]
        if ppf_id is None:
            show_colorful_error(win, "No Selection", "Please select a PPF account first.")
            return

        account_label = account_combo.get().strip()
        if not account_label or account_label not in account_map:
            show_colorful_error(win, "Validation Error", "Please select a valid linked bank account.")
            flash_error(account_combo)
            return
        account_id = account_map[account_label]

        ppf_no = ppf_no_var.get().strip()
        if not ppf_no:
            show_colorful_error(win, "Validation Error", "PPF Account Number is required.")
            flash_error(ppf_no_entry)
            return

        holder = holder_var.get().strip()
        if not holder:
            show_colorful_error(win, "Validation Error", "Holder Name is required.")
            flash_error(holder_entry)
            return

        try:
            od_str = open_dt.get_date().strftime("%Y-%m-%d")
        except Exception:
            show_colorful_error(win, "Validation Error", "Invalid Open Date.")
            return

        try:
            md_str = maturity_dt.get_date().strftime("%Y-%m-%d")
        except Exception:
            show_colorful_error(win, "Validation Error", "Invalid Maturity Date.")
            return
            
        if md_str <= od_str:
            show_colorful_error(win, "Validation Error", "Maturity Date must be after Open Date.")
            flash_error(maturity_dt)
            return

        is_active = 1 if is_active_var.get() else 0

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE ppf_master
                    SET    account_id = ?,
                           ppf_account_number = ?,
                           holder_name = ?,
                           open_dt = ?,
                           maturity_dt = ?,
                           is_active = ?
                    WHERE  ppf_master_id = ?
                """, (account_id, ppf_no, holder, od_str, md_str, is_active, ppf_id))
                conn.commit()

            show_colorful_info(win, "Success", f"PPF account '{ppf_no}' updated.")
            load_accounts()
            _reset_form()
            sel_status_var.set("Saved — select another account or close.")
        except sqlite3.IntegrityError as exc:
            show_colorful_error(win, "Integrity Error", f"Must be unique.\nDetail: {exc}")
        except Exception as exc:
            show_colorful_error(win, "Error", f"Failed to update:\n{exc}")
            logger.exception("edit_ppf_master: UPDATE failed for ppf_master_id=%s", ppf_id)

    # Delete
    def on_delete(_event=None) -> None:
        ppf_id = selected_id["ppf_master_id"]
        if ppf_id is None:
            return

        ppf_no = ppf_no_var.get().strip()
        tx_count = 0
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM ppf_transactions WHERE ppf_master_id = ?", (ppf_id,))
                row = cur.fetchone()
                if row:
                    tx_count = row[0]
        except sqlite3.Error as e:
            show_colorful_error(win, "Error", f"Could not check linked transactions: {e}")
            return

        if tx_count > 0:
            show_colorful_error(win, "Cannot Delete", f"Account has {tx_count} transaction(s).")
            return

        confirm = show_colorful_yesno(win, "Confirm Delete", f"Delete PPF account:\n{ppf_no}\n?")
        if not confirm:
            return

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys = ON;")
                cur.execute("DELETE FROM ppf_master WHERE ppf_master_id = ?", (ppf_id,))
                conn.commit()

            show_colorful_info(win, "Success", f"Deleted '{ppf_no}'.")
            load_accounts()
            _reset_form()
            sel_status_var.set("Deleted — select another account or close.")
        except sqlite3.Error as e:
            show_colorful_error(win, "Delete Failed", f"Database error: {e}")

    def _reset_form() -> None:
        selected_id["ppf_master_id"] = None
        account_combo.set("")
        ppf_no_var.set("")
        holder_var.set("")
        is_active_var.set(True)

        account_combo.config(state="disabled")
        ppf_no_entry.config(state="disabled")
        holder_entry.config(state="disabled")
        open_dt.config(state="disabled")
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
        font=("Comic Sans MS", 12, "bold"),
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
        font=("Comic Sans MS", 12, "bold"),
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
        font=("Comic Sans MS", 12, "bold"),
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

    parent.wait_window(win)
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except Exception:
        pass
