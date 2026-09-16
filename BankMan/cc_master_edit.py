# -*- coding: utf-8 -*-
# BankMan/cc_master_edit.py

"""
Edit form for the ``card_master`` master table.
Presents a list of cards in a Treeview and lets the user edit or delete them.
"""

from typing import Union
import sqlite3
import tkinter as tk
from tkinter import ttk

from Shared.gui_utils import (
    apply_button_animations,
    apply_entry_theme,
    CC_MASTER_ADD_UI_THEME as _T,
    bind_tooltip,
    flash_error,
    setup_footer_tooltip,
    universal_tree_sort,
)
from Shared.dialog_utils import show_colorful_error, show_colorful_info, show_colorful_yesno
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from .bank_db_utils import get_all_accounts
from Shared.globals import logger, get_db_connection, BANK_DB_PATH

# ---------------------------------------------------------------------------

def edit_cc_master(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Open a modal two-panel window for editing card_master records.

    Parameters
    ----------
    parent:
        Owning window.
    calling_button:
        The button that opened this modal.
    """
    # ── Lookup data fetched once at open ─────────────────────────────────
    accounts = get_all_accounts("CREDIT_CARD")
    # Display: "BankName : [AC_Number]"  →  ac_id
    account_map = {f"{a[1]} : [{a[3]}]": a[0] for a in accounts}

    # ── Modal window ──────────────────────────────────────────────────────
    disable_parent(parent, calling_button=calling_button)

    win = tk.Toplevel(parent)
    win.title("✏️  Edit Credit Card Master  ✏️")
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

    # Footer tooltip — packed first so it anchors to the absolute bottom.
    tooltip_var = setup_footer_tooltip(win)

    # ------------------------------------------------------------------
    # Close helper
    # ------------------------------------------------------------------
    def cleanup_and_close(_event=None):
        return safe_close_modal(win, parent, calling_button)

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    header_frame = tk.Frame(win, bg=_T["header_bg"], relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=(5, 0))

    tk.Label(
        header_frame,
        text="✏️   Edit Credit Card Master   ✏️",
        font=("Helvetica", 18, "bold"),
        bg=_T["header_bg"],
        fg=_T["header_fg"],
        relief="ridge",
        bd=2,
    ).pack(fill="x", pady=10)

    # ------------------------------------------------------------------
    # Instruction row
    # ------------------------------------------------------------------
    instr_frame = tk.Frame(win, bg=_T["header_bg"])
    instr_frame.pack(fill="x", padx=5, pady=(0, 2))

    tk.Label(
        instr_frame,
        text="Click a credit card row below to load it into the edit form.",
        font=("Helvetica", 11, "italic"),
        bg=_T["header_bg"],
        fg="#FFD1D1",
    ).pack(anchor="w", padx=10, pady=4)

    # ------------------------------------------------------------------
    # Treeview — credit card list
    # ------------------------------------------------------------------
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
        "CCEdit.Treeview",
        background="#FFF5F5",
        foreground="#4A0000",
        fieldbackground="#FFF5F5",
        rowheight=26,
        font=("Helvetica", 11),
    )
    style.configure(
        "CCEdit.Treeview.Heading",
        background=_T["header_bg"],
        foreground=_T["header_fg"],
        font=("Helvetica", 11, "bold"),
    )
    style.map(
        "CCEdit.Treeview",
        background=[("selected", "#7b0000")],
        foreground=[("selected", "white")],
    )

    cols = ("ID", "Card Name", "Card Number", "Bank", "Account", "Credit Limit", "Billing Day", "Active")
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="CCEdit.Treeview",
        height=5,
    )
    tree_scroll.config(command=tree.yview)

    col_setup = {
        "ID": (0, tk.NO, "center"),
        "Card Name": (180, tk.YES, "w"),
        "Card Number": (110, tk.NO, "center"),
        "Bank": (160, tk.YES, "w"),
        "Account": (130, tk.NO, "center"),
        "Credit Limit": (130, tk.NO, "e"),
        "Billing Day": (100, tk.NO, "center"),
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

    # ------------------------------------------------------------------
    # Data load / reload
    # ------------------------------------------------------------------
    def load_cards() -> None:
        """Clear the treeview and repopulate from the database."""
        for item in tree.get_children():
            tree.delete(item)
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT  cm.card_master_id,
                            cm.card_name,
                            COALESCE(cm.card_number, ''),
                            b.name,
                            a.ac_number,
                            COALESCE(cm.credit_limit, 0.0),
                            COALESCE(cm.billing_cycle_day, 1),
                            cm.is_active,
                            cm.account_id
                    FROM    card_master cm
                    JOIN    accounts a ON a.ac_id = cm.account_id
                    JOIN    banks    b ON b.b_id  = a.b_id
                    ORDER BY b.name, cm.card_name
                """)
                for row in cursor.fetchall():
                    is_active_str = "Yes" if row[7] else "No"
                    tree.insert(
                        "",
                        "end",
                        values=(
                            row[0],  # ID
                            row[1],  # Card Name
                            row[2],  # Card Number
                            row[3],  # Bank
                            row[4],  # Account
                            f"₹ {row[5]:,.2f}" if row[5] else "",  # Credit Limit
                            row[6],  # Billing Day
                            is_active_str,
                            row[8],  # account_id (hidden)
                        ),
                    )
        except sqlite3.Error as exc:
            logger.error("edit_cc_master: failed to load cards: %s", exc)

    load_cards()

    # ------------------------------------------------------------------
    # Divider and "selected card" status label
    # ------------------------------------------------------------------
    tk.Frame(win, height=2, bg=_T["header_bg"]).pack(fill="x", padx=5, pady=(2, 0))

    sel_label_frame = tk.Frame(win, bg=_T["header_bg"])
    sel_label_frame.pack(fill="x", padx=5, pady=0)

    sel_status_var = tk.StringVar(
        value="No card selected — click a row in the list above."
    )
    tk.Label(
        sel_label_frame,
        textvariable=sel_status_var,
        font=("Helvetica", 11, "bold"),
        bg=_T["header_bg"],
        fg="#FFD1D1",
    ).pack(anchor="w", padx=10, pady=4)

    # ------------------------------------------------------------------
    # Edit form
    # ------------------------------------------------------------------
    selected_id = {"card_master_id": None}

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
        "Bank account to which this card's bill payments are debited.",
    )

    # Row 1: Card Name
    tk.Label(
        form_frame,
        text="Card Name:",
        font=("Helvetica", 13),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
    ).grid(row=1, column=0, sticky="w", padx=5, pady=4)
    
    card_name_var = tk.StringVar()
    card_name_entry = tk.Entry(form_frame, width=65, textvariable=card_name_var, font=("Helvetica", 13, "bold"))
    card_name_entry.grid(row=1, column=1, sticky="w", padx=5, pady=4)
    card_name_entry.config(state="disabled")
    apply_entry_theme(card_name_entry)
    bind_tooltip(
        card_name_entry,
        tooltip_var,
        "Descriptive product name, e.g. 'HDFC Regalia', 'Axis Magnus'.",
    )

    # Row 2: Card Number
    tk.Label(
        form_frame,
        text="Card Number:",
        font=("Helvetica", 13),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
    ).grid(row=2, column=0, sticky="w", padx=5, pady=4)
    
    card_number_var = tk.StringVar()
    card_number_entry = tk.Entry(form_frame, width=65, textvariable=card_number_var, font=("Helvetica", 13, "bold"))
    card_number_entry.grid(row=2, column=1, sticky="w", padx=5, pady=4)
    card_number_entry.config(state="disabled")
    apply_entry_theme(card_number_entry)
    bind_tooltip(
        card_number_entry,
        tooltip_var,
        "Last 4 digits of the card number (for security).",
    )

    # Row 3: Credit Limit
    tk.Label(
        form_frame,
        text="Credit Limit (₹):",
        font=("Helvetica", 13),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
    ).grid(row=3, column=0, sticky="w", padx=5, pady=4)
    
    credit_limit_var = tk.StringVar()
    credit_limit_entry = tk.Entry(form_frame, width=65, textvariable=credit_limit_var, font=("Helvetica", 13, "bold"))
    credit_limit_entry.grid(row=3, column=1, sticky="w", padx=5, pady=4)
    credit_limit_entry.config(state="disabled")
    apply_entry_theme(credit_limit_entry)
    bind_tooltip(
        credit_limit_entry,
        tooltip_var,
        "Approved credit limit on this card in INR.",
    )

    # Row 4: Billing Cycle Day
    tk.Label(
        form_frame,
        text="Billing Day (1-31):",
        font=("Helvetica", 13),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
    ).grid(row=4, column=0, sticky="w", padx=5, pady=4)
    
    billing_day_spin = ttk.Spinbox(
        form_frame,
        from_=1,
        to=31,
        width=63,
        font=("Helvetica", 13, "bold"),
        state="disabled",
    )
    billing_day_spin.grid(row=4, column=1, sticky="w", padx=5, pady=4)
    apply_entry_theme(billing_day_spin)
    bind_tooltip(
        billing_day_spin,
        tooltip_var,
        "Day of the month on which the billing cycle closes and statement is generated.",
    )

    # Row 5: Active
    is_active_var = tk.BooleanVar(value=True)
    is_active_chk = tk.Checkbutton(
        form_frame,
        variable=is_active_var,
        text="Active",
        font=("Helvetica", 13),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
        selectcolor=_T["header_bg"],
        activebackground=_T["main_bg"],
        activeforeground=_T["label_fg"],
        cursor="hand2",
        state="disabled",
    )
    is_active_chk.grid(row=5, column=1, sticky="w", padx=5, pady=4)
    bind_tooltip(
        is_active_chk,
        tooltip_var,
        "Untick only for cancelled or expired cards.",
    )

    # ------------------------------------------------------------------
    # Treeview selection handler
    # ------------------------------------------------------------------
    def on_tree_select(_event=None) -> None:
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0])["values"]
        card_id = vals[0]
        card_name = vals[1]
        card_number = vals[2]
        bank_name = vals[3]
        ac_number = vals[4]
        credit_limit_str = vals[5].replace("₹", "").replace(",", "").strip() if vals[5] else ""
        billing_day = vals[6]
        is_active = True if vals[7] == "Yes" else False
        account_id = vals[8]

        selected_id["card_master_id"] = card_id
        
        # Populate Combobox
        account_label = f"{bank_name} : [{ac_number}]"
        if account_label in account_map:
            account_combo.set(account_label)
        else:
            account_combo.set("")

        card_name_var.set(card_name)
        card_number_var.set(card_number)
        credit_limit_var.set(credit_limit_str)
        billing_day_spin.set(billing_day)
        is_active_var.set(is_active)

        # Enable fields
        account_combo.config(state="readonly")
        card_name_entry.config(state="normal")
        card_number_entry.config(state="normal")
        credit_limit_entry.config(state="normal")
        billing_day_spin.config(state="normal")
        is_active_chk.config(state="normal")

        save_btn.config(state="normal")
        delete_btn.config(state="normal")
        sel_status_var.set(f"Editing:  {card_name}")
        card_name_entry.focus_set()

    tree.bind("<<TreeviewSelect>>", on_tree_select)
    tree.bind("<Double-1>", on_tree_select)

    # ------------------------------------------------------------------
    # Tab-order within the form
    # ------------------------------------------------------------------
    account_combo.bind("<Return>", lambda _e: card_name_entry.focus_set())
    card_name_entry.bind("<Return>", lambda _e: card_number_entry.focus_set())
    card_number_entry.bind("<Return>", lambda _e: credit_limit_entry.focus_set())
    credit_limit_entry.bind("<Return>", lambda _e: billing_day_spin.focus_set())
    billing_day_spin.bind("<Return>", lambda _e: save_btn.focus_set())

    # ------------------------------------------------------------------
    # Save handler
    # ------------------------------------------------------------------
    def on_save(_event=None) -> None:
        card_id = selected_id["card_master_id"]
        if card_id is None:
            show_colorful_error(
                win,
                "No Selection",
                "Please select a credit card from the list first.",
            )
            return

        account_label = account_combo.get().strip()
        if not account_label or account_label not in account_map:
            show_colorful_error(win, "Validation Error", "Please select a valid linked bank account.")
            flash_error(account_combo)
            account_combo.focus_set()
            return
        account_id = account_map[account_label]

        card_name = card_name_var.get().strip()
        if not card_name:
            show_colorful_error(win, "Validation Error", "Card Name is required.")
            flash_error(card_name_entry)
            card_name_entry.focus_set()
            return

        card_number = card_number_var.get().strip() or None

        credit_limit_raw = credit_limit_var.get().strip()
        credit_limit = None
        if credit_limit_raw:
            try:
                credit_limit = float(credit_limit_raw)
            except ValueError:
                show_colorful_error(win, "Validation Error", "Credit Limit must be a numeric value.")
                flash_error(credit_limit_entry)
                credit_limit_entry.focus_set()
                return

        try:
            billing_day = int(billing_day_spin.get())
            if billing_day < 1 or billing_day > 31:
                raise ValueError()
        except ValueError:
            show_colorful_error(win, "Validation Error", "Billing day must be between 1 and 31.")
            flash_error(billing_day_spin)
            billing_day_spin.focus_set()
            return

        is_active = 1 if is_active_var.get() else 0

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE card_master
                    SET    account_id = ?,
                           card_name = ?,
                           card_number = ?,
                           credit_limit = ?,
                           billing_cycle_day = ?,
                           is_active = ?
                    WHERE  card_master_id = ?
                """, (account_id, card_name, card_number, credit_limit, billing_day, is_active, card_id))
                conn.commit()

            show_colorful_info(
                win,
                "Success",
                f"Credit card '{card_name}' updated successfully.",
            )
            # Reset form & load
            load_cards()
            _reset_form()
            sel_status_var.set("Saved — select another card or close.")
        except sqlite3.IntegrityError as exc:
            show_colorful_error(win, "Integrity Error", f"Card Name must be unique.\nDetail: {exc}")
        except Exception as exc:
            show_colorful_error(win, "Error", f"Failed to update credit card:\n{exc}")
            logger.exception("edit_cc_master: UPDATE failed for card_master_id=%s", card_id)

    # ------------------------------------------------------------------
    # Delete handler
    # ------------------------------------------------------------------
    def on_delete(_event=None) -> None:
        card_id = selected_id["card_master_id"]
        if card_id is None:
            show_colorful_error(
                win,
                "No Selection",
                "Please select a credit card from the list first.",
            )
            return

        card_name = card_name_var.get().strip()

        # Count linked cc_transactions
        tx_count = 0
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT COUNT(*) FROM cc_transactions WHERE card_master_id = ?",
                    (card_id,),
                )
                row = cur.fetchone()
                if row:
                    tx_count = row[0]
        except sqlite3.Error as e:
            show_colorful_error(
                win, "Error", f"Could not check linked transactions: {e}"
            )
            return

        if tx_count > 0:
            show_colorful_error(
                win,
                "Cannot Delete",
                f"Card '{card_name}' has {tx_count} linked transaction(s).\n\n"
                f"Delete or reassign all cc_transactions for this card "
                f"before removing the card record.",
            )
            return

        confirm = show_colorful_yesno(
            win,
            "Confirm Delete",
            f"Are you sure you want to permanently delete the credit card record:\n\n"
            f"  {card_name}\n\n"
            f"This action cannot be undone.",
        )
        if not confirm:
            return

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys = ON;")
                cur.execute(
                    "DELETE FROM card_master WHERE card_master_id = ?",
                    (card_id,),
                )
                conn.commit()

            show_colorful_info(
                win,
                "Success",
                f"Credit Card '{card_name}' deleted successfully.",
            )
            load_cards()
            _reset_form()
            sel_status_var.set("Deleted — select another card or close.")
        except sqlite3.IntegrityError as e:
            show_colorful_error(
                win,
                "Delete Blocked",
                f"Could not delete '{card_name}' — it is still referenced in the database.\n\n"
                f"Detail: {e}",
            )
        except sqlite3.Error as e:
            show_colorful_error(win, "Delete Failed", f"Database error: {e}")

    # ── Reset form ────────────────────────────────────────────────────────
    def _reset_form() -> None:
        selected_id["card_master_id"] = None
        account_combo.set("")
        card_name_var.set("")
        card_number_var.set("")
        credit_limit_var.set("")
        billing_day_spin.set(1)
        is_active_var.set(True)

        account_combo.config(state="disabled")
        card_name_entry.config(state="disabled")
        card_number_entry.config(state="disabled")
        credit_limit_entry.config(state="disabled")
        billing_day_spin.config(state="disabled")
        is_active_chk.config(state="disabled")

        save_btn.config(state="disabled")
        delete_btn.config(state="disabled")

    save_btn: tk.Button  # forward declaration for on_tree_select closure
    delete_btn: tk.Button  # forward declaration for on_tree_select closure

    # ------------------------------------------------------------------
    # Button frame
    # ------------------------------------------------------------------
    btn_frame = tk.Frame(win, bg=_T["main_bg"], relief="ridge", bd=2, pady=6)
    btn_frame.pack(fill="x", padx=10, pady=(4, 6))

    delete_btn = tk.Button(
        btn_frame,
        text="🗑️  DELETE SELECTED  🗑️",
        command=on_delete,
        font=("Comic Sans MS", 12, "bold"),
        bg=_T["cancel_bg"],
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
        bg=_T["submit_bg"],
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
        bg=_T["cancel_bg"],
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        padx=8,
        pady=4,
        cursor="hand2",
    )
    cancel_btn.pack(side="right", padx=4)

    apply_button_animations(delete_btn, _T["cancel_bg"], _T["cancel_hover_bg"])
    apply_button_animations(save_btn, _T["submit_bg"], _T["submit_hover_bg"])
    apply_button_animations(cancel_btn, _T["cancel_bg"], _T["cancel_hover_bg"])

    # ------------------------------------------------------------------
    # Window-level bindings
    # ------------------------------------------------------------------
    win.bind("<Escape>", cleanup_and_close)
    win.protocol("WM_DELETE_WINDOW", cleanup_and_close)

    parent.wait_window(win)

    # Restore grab to caller so it doesn't fall out of focus.
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass
