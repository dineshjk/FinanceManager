# -*- coding: utf-8 -*-
# BankMan/accounts_edit.py

"""
Edit form for the ``accounts`` master table.

Opened from the BankMan data-entry menu when the user clicks
"Edit Account".  Presents a two-panel layout:

* **Top panel** — sortable treeview of every account (bank, type,
  number, opening date, balance, status).  Click a row to load it
  into the edit form; double-click also triggers load.

* **Bottom panel** — form with all editable fields pre-populated
  from the selected row.  Save validates the input and persists the
  change via ``db_update_account``.

Fields exposed
--------------
Bank (combobox), Account Type (combobox), Account Number (Entry),
Opening Date (DateEntry), Current Balance (Entry),
Balance Date (DateEntry), Joint Account (checkbox), Active (checkbox).

Theme
-----
``ACCOUNTS_EDIT_UI_THEME`` — warm coral / terracotta — is the visual
complement of ``ACCOUNTS_ADD_UI_THEME`` (deep navy blue), so edit and
add windows are immediately distinguishable at a glance.
"""

from datetime import datetime
from typing import Union
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry

from Shared.gui_utils import (
    ACCOUNTS_EDIT_UI_THEME as _THEME,
    apply_button_animations,
    apply_entry_theme,
    bind_tooltip,
    flash_error,
    setup_footer_tooltip,
    bind_date_spin,
)
from Shared.dialog_utils import show_colorful_error, show_colorful_info
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from Shared.globals import logger
from Shared.gui_progressive import progressive_selection
from .bank_db_utils import (
    db_get_all_accounts_for_edit,
    db_update_account,
    get_all_banks,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ACCOUNT_TYPES = ["SAVINGS", "CURRENT", "OVERDRAFT"]
_F = ("Helvetica", 13)
_FB = ("Helvetica", 13, "bold")
_FH = ("Helvetica", 17, "bold")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def edit_account(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Open a modal two-panel window for editing account master records.

    Parameters
    ----------
    parent:
        Owning window (the BankMan data-entry menu or any Toplevel).
    calling_button:
        The button that opened this modal (disabled while open).
    """
    # ── Lookup data fetched once at open ─────────────────────────────────
    banks = get_all_banks()  # [(b_id, name, branch, IFSC, MICR)]
    bank_name_to_id = {b[1]: b[0] for b in banks}
    bank_names = [b[1] for b in banks]

    # ── Modal window ──────────────────────────────────────────────────────
    disable_parent(parent, calling_button=calling_button)

    win = tk.Toplevel(parent)
    win.title("✏️  Edit Account  ✏️")
    win.geometry("900x680")
    win.resizable(False, False)
    win.configure(bg=_THEME["main_bg"])
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    try:
        push_window(win, parent)
    except (RuntimeError, tk.TclError) as exc:
        logger.debug("push_window failed: %s", exc)

    # Footer tooltip — packed FIRST so it anchors to absolute bottom
    tooltip_var = setup_footer_tooltip(win)

    def cleanup_and_close(_event=None):
        return safe_close_modal(win, parent, calling_button)

    # ── Header ────────────────────────────────────────────────────────────
    hdr = tk.Frame(win, bg=_THEME["header_bg"], relief="raised", bd=3)
    hdr.pack(fill="x", padx=5, pady=(5, 0))

    tk.Label(
        hdr,
        text="✏️   Edit Account   ✏️",
        font=_FH,
        bg=_THEME["header_bg"],
        fg=_THEME["header_fg"],
        relief="ridge",
        bd=2,
    ).pack(fill="x", pady=8)

    # ── Treeview (top panel) ──────────────────────────────────────────────
    tv_outer = tk.Frame(win, bg=_THEME["main_bg"], relief="ridge", bd=2)
    tv_outer.pack(fill="both", expand=True, padx=8, pady=(6, 2))

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(
        "AccEdit.Treeview",
        background="#FFF7F3",  # Very light coral
        foreground="#2C1A14",
        fieldbackground="#FFF7F3",
        rowheight=24,
        font=("Helvetica", 11),
    )
    style.configure(
        "AccEdit.Treeview.Heading",
        background=_THEME["header_bg"],
        foreground="white",
        font=("Helvetica", 11, "bold"),
    )
    style.map(
        "AccEdit.Treeview",
        background=[("selected", "#D4634A")],
        foreground=[("selected", "white")],
    )

    tv_scroll = ttk.Scrollbar(tv_outer)
    tv_scroll.pack(side="right", fill="y")

    _TV_COLS = (
        "ac_id",
        "Bank",
        "Type",
        "Account No",
        "Open Date",
        "Balance",
        "Bal. Date",
        "Joint",
        "Active",
    )
    tree = ttk.Treeview(
        tv_outer,
        columns=_TV_COLS,
        show="headings",
        height=7,
        yscrollcommand=tv_scroll.set,
        style="AccEdit.Treeview",
        selectmode="browse",
    )
    tv_scroll.config(command=tree.yview)

    # Column definitions — ac_id is hidden (zero-width)
    tree.column("ac_id", width=0, stretch=tk.NO, minwidth=0)
    tree.column("Bank", width=200, anchor="w")
    tree.column("Type", width=90, anchor="center")
    tree.column("Account No", width=160, anchor="w")
    tree.column("Open Date", width=90, anchor="center")
    tree.column("Balance", width=110, anchor="e")
    tree.column("Bal. Date", width=90, anchor="center")
    tree.column("Joint", width=50, anchor="center")
    tree.column("Active", width=55, anchor="center")

    for col in _TV_COLS:
        tree.heading(
            col,
            text=col if col != "ac_id" else "",
            command=lambda c=col: _sort_tree(tree, c, False),
        )

    tree.pack(fill="both", expand=True)

    # Column-sort helper
    def _sort_tree(tv: ttk.Treeview, col: str, desc: bool) -> None:
        data = [(tv.set(child, col), child) for child in tv.get_children("")]

        def _k(v):
            try:
                return float(v[0].replace("₹", "").replace(",", "").strip())
            except ValueError:
                return v[0].lower()

        data.sort(key=_k, reverse=desc)
        for i, (_, iid) in enumerate(data):
            tv.move(iid, "", i)
        tv.heading(col, command=lambda c=col: _sort_tree(tv, c, not desc))

    # ── Load treeview from DB ─────────────────────────────────────────────
    def load_tree() -> None:
        for item in tree.get_children():
            tree.delete(item)
        rows = db_get_all_accounts_for_edit()
        for r in rows:
            # r: (ac_id, b_id, bank_name, type, ac_number,
            #     open_dt, curr_balance, curr_balance_dt, is_joint, is_active)
            bal = r[6] or 0.0
            tree.insert(
                "",
                "end",
                values=(
                    r[0],  # ac_id (hidden)
                    r[2],  # bank_name
                    r[3],  # type
                    r[4],  # ac_number
                    r[5] or "",  # open_dt
                    f"₹ {bal:,.2f}",  # curr_balance
                    r[7] or "",  # curr_balance_dt
                    "Yes" if r[8] else "No",  # is_joint
                    "Yes" if r[9] else "No",  # is_active
                ),
            )

    load_tree()

    # ── Divider ───────────────────────────────────────────────────────────
    tk.Frame(win, height=2, bg=_THEME["header_bg"]).pack(fill="x", padx=8, pady=(4, 0))
    tk.Label(
        win,
        text="  Select a row above, then edit the fields below:",
        font=("Helvetica", 11, "bold"),
        bg=_THEME["header_bg"],
        fg="white",
        padx=6,
        pady=2,
    ).pack(fill="x", padx=8, pady=(0, 4))

    # ── Edit form (bottom panel) ──────────────────────────────────────────
    form = tk.Frame(win, bg=_THEME["main_bg"])
    form.pack(fill="x", padx=12, pady=4)

    # Internal state — which row is loaded
    _loaded: dict = {}  # mirrors the DB row currently in the form

    # ── Form widgets ──────────────────────────────────────────────────────
    # Row 0: labels
    ttk.Label(form, text="Bank:", font=_F, background=_THEME["label_bg"]).grid(
        row=0, column=0, sticky="w", padx=(4, 2), pady=2
    )
    ttk.Label(form, text="Account Type:", font=_F, background=_THEME["label_bg"]).grid(
        row=0, column=1, sticky="w", padx=(12, 2), pady=2
    )
    ttk.Label(
        form, text="Account Number:", font=_F, background=_THEME["label_bg"]
    ).grid(row=0, column=2, sticky="w", padx=(12, 2), pady=2)
    ttk.Label(form, text="Opening Date:", font=_F, background=_THEME["label_bg"]).grid(
        row=0, column=3, sticky="w", padx=(12, 2), pady=2
    )

    # Row 1: widgets
    bank_combo = ttk.Combobox(form, width=22, values=bank_names, font=_F)
    bank_combo.grid(row=1, column=0, sticky="w", padx=(4, 2), pady=3)
    apply_entry_theme(bank_combo)
    progressive_selection(bank_combo, bank_names)
    bind_tooltip(bank_combo, tooltip_var, "Holding bank for this account.")

    type_combo = ttk.Combobox(form, width=14, values=_ACCOUNT_TYPES, font=_F)
    type_combo.grid(row=1, column=1, sticky="w", padx=(12, 2), pady=3)
    apply_entry_theme(type_combo)
    progressive_selection(type_combo, _ACCOUNT_TYPES)
    bind_tooltip(type_combo, tooltip_var, "Account product type.")

    ac_number_var = tk.StringVar()
    ac_number_entry = tk.Entry(form, textvariable=ac_number_var, width=22, font=_F)
    ac_number_entry.grid(row=1, column=2, sticky="w", padx=(12, 2), pady=3)
    apply_entry_theme(ac_number_entry)
    bind_tooltip(ac_number_entry, tooltip_var, "Account number (unique within bank).")

    open_dt_entry = DateEntry(form, date_pattern="dd-mm-yyyy", width=13, font=_F)
    open_dt_entry.grid(row=1, column=3, sticky="w", padx=(12, 2), pady=3)
    apply_entry_theme(open_dt_entry)
    bind_tooltip(open_dt_entry, tooltip_var, "Date the account was opened.")

    # Row 2: labels
    ttk.Label(
        form, text="Current Balance:", font=_F, background=_THEME["label_bg"]
    ).grid(row=2, column=0, sticky="w", padx=(4, 2), pady=(8, 2))
    ttk.Label(form, text="Balance Date:", font=_F, background=_THEME["label_bg"]).grid(
        row=2, column=1, sticky="w", padx=(12, 2), pady=(8, 2)
    )
    ttk.Label(form, text="Joint Account:", font=_F, background=_THEME["label_bg"]).grid(
        row=2, column=2, sticky="w", padx=(12, 2), pady=(8, 2)
    )
    ttk.Label(form, text="Active:", font=_F, background=_THEME["label_bg"]).grid(
        row=2, column=3, sticky="w", padx=(12, 2), pady=(8, 2)
    )

    # Row 3: widgets
    balance_var = tk.StringVar()
    balance_entry = tk.Entry(form, textvariable=balance_var, width=22, font=_FB)
    balance_entry.grid(row=3, column=0, sticky="w", padx=(4, 2), pady=3)
    apply_entry_theme(balance_entry)
    bind_tooltip(balance_entry, tooltip_var, "Current balance snapshot (INR).")

    balance_dt_entry = DateEntry(form, date_pattern="dd-mm-yyyy", width=13, font=_F)
    balance_dt_entry.grid(row=3, column=1, sticky="w", padx=(12, 2), pady=3)
    apply_entry_theme(balance_dt_entry)
    bind_tooltip(balance_dt_entry, tooltip_var, "Date of the balance snapshot.")

    bind_date_spin(open_dt_entry)
    bind_date_spin(balance_dt_entry)

    is_joint_var = tk.BooleanVar()
    joint_check = ttk.Checkbutton(form, text="Yes", variable=is_joint_var)
    joint_check.grid(row=3, column=2, sticky="w", padx=(12, 2), pady=3)
    bind_tooltip(joint_check, tooltip_var, "Tick if this is a joint account.")

    is_active_var = tk.BooleanVar()
    active_check = ttk.Checkbutton(form, text="Yes", variable=is_active_var)
    active_check.grid(row=3, column=3, sticky="w", padx=(12, 2), pady=3)
    bind_tooltip(active_check, tooltip_var, "Uncheck for closed / inactive accounts.")

    # ── Disable all form widgets until a row is selected ─────────────────
    _FORM_WIDGETS = [
        bank_combo,
        type_combo,
        ac_number_entry,
        open_dt_entry,
        balance_entry,
        balance_dt_entry,
        joint_check,
        active_check,
    ]

    def _set_form_state(state: str) -> None:
        for w in _FORM_WIDGETS:
            try:
                w.configure(state=state)
            except tk.TclError:
                pass

    _set_form_state("disabled")

    # ── Populate form from a treeview row ─────────────────────────────────
    def _populate_form(ac_id: int) -> None:
        """Load the account with *ac_id* into the edit form."""
        rows = db_get_all_accounts_for_edit()
        row = next((r for r in rows if r[0] == ac_id), None)
        if row is None:
            return
        # r: (ac_id, b_id, bank_name, type, ac_number,
        #     open_dt, curr_balance, curr_balance_dt, is_joint, is_active)
        _loaded.clear()
        _loaded.update(
            {
                "ac_id": row[0],
                "b_id": row[1],
                "bank_name": row[2],
                "type": row[3],
                "ac_number": row[4],
                "open_dt": row[5],
                "curr_balance": row[6] or 0.0,
                "curr_bal_dt": row[7],
                "is_joint": bool(row[8]),
                "is_active": bool(row[9]),
            }
        )

        _set_form_state("normal")

        bank_combo.set(row[2])
        type_combo.set(row[3])
        ac_number_var.set(row[4])

        # Opening date
        try:
            open_dt_entry.set_date(datetime.strptime(row[5], "%Y-%m-%d"))
        except (ValueError, TypeError):
            open_dt_entry.set_date(datetime.today())

        # Balance
        balance_var.set(f"{(row[6] or 0.0):.2f}")

        # Balance date
        try:
            balance_dt_entry.set_date(datetime.strptime(row[7], "%Y-%m-%d"))
        except (ValueError, TypeError):
            balance_dt_entry.set_date(datetime.today())

        is_joint_var.set(bool(row[8]))
        is_active_var.set(bool(row[9]))

        bank_combo.focus_set()

    # ── Treeview selection binding ─────────────────────────────────────────
    def _on_tree_select(_event=None) -> None:
        selected = tree.selection()
        if not selected:
            return
        values = tree.item(selected[0])["values"]
        ac_id = values[0]
        _populate_form(ac_id)

    tree.bind("<<TreeviewSelect>>", _on_tree_select)
    tree.bind("<Double-1>", _on_tree_select)

    # ── Button bar ────────────────────────────────────────────────────────
    btn_frame = tk.Frame(win, bg=_THEME["main_bg"], relief="ridge", bd=2, pady=6)
    btn_frame.pack(fill="x", padx=12, pady=(6, 4))

    # ── Save handler ──────────────────────────────────────────────────────
    def on_save(_event=None) -> None:
        if not _loaded:
            show_colorful_error(win, "No Selection", "Please select an account first.")
            return

        # — Bank —
        bank_name = bank_combo.get().strip()
        if not bank_name or bank_name not in bank_name_to_id:
            show_colorful_error(
                win, "Validation", "Please select a valid bank from the list."
            )
            flash_error(bank_combo)
            return
        b_id = bank_name_to_id[bank_name]

        # — Account Type —
        ac_type = type_combo.get().strip()
        if ac_type not in _ACCOUNT_TYPES:
            show_colorful_error(
                win,
                "Validation",
                "Account type must be SAVINGS, CURRENT, or OVERDRAFT.",
            )
            flash_error(type_combo)
            return

        # — Account Number —
        ac_number = ac_number_var.get().strip()
        if not ac_number:
            show_colorful_error(win, "Validation", "Account Number is required.")
            flash_error(ac_number_entry)
            return

        # — Opening Date —
        try:
            open_dt = open_dt_entry.get_date().strftime("%Y-%m-%d")
        except Exception:
            show_colorful_error(win, "Validation", "Opening Date is invalid.")
            flash_error(open_dt_entry)
            return

        # — Current Balance —
        try:
            balance_str = balance_var.get().strip().replace(",", "")
            curr_balance = float(balance_str or "0")
        except ValueError:
            show_colorful_error(win, "Validation", "Balance must be a number.")
            flash_error(balance_entry)
            return

        # — Balance Date —
        try:
            curr_balance_dt = balance_dt_entry.get_date().strftime("%Y-%m-%d")
        except Exception:
            show_colorful_error(win, "Validation", "Balance Date is invalid.")
            flash_error(balance_dt_entry)
            return

        is_joint = 1 if is_joint_var.get() else 0
        is_active = 1 if is_active_var.get() else 0
        ac_id = _loaded["ac_id"]

        try:
            db_update_account(
                ac_id=ac_id,
                b_id=b_id,
                open_dt=open_dt,
                ac_number=ac_number,
                type_=ac_type,
                curr_balance=curr_balance,
                curr_balance_dt=curr_balance_dt,
                is_joint=is_joint,
                is_active=is_active,
            )
        except Exception as exc:
            show_colorful_error(win, "Database Error", f"Failed to save:\n{exc}")
            logger.exception("accounts_edit: UPDATE failed for ac_id=%s", ac_id)
            return

        show_colorful_info(
            win,
            "Saved",
            f"Account '{ac_number}' ({bank_name}) updated successfully.",
        )
        _loaded.clear()
        _set_form_state("disabled")
        load_tree()

    save_btn = tk.Button(
        btn_frame,
        text="💾  SAVE CHANGES  💾",
        command=on_save,
        font=("Comic Sans MS", 12, "bold"),
        bg=_THEME["submit_bg"],
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        padx=8,
        pady=4,
        cursor="hand2",
    )
    save_btn.pack(side="right", padx=8)

    cancel_btn = tk.Button(
        btn_frame,
        text="❌  Cancel / Close  ❌",
        command=cleanup_and_close,
        font=("Comic Sans MS", 12, "bold"),
        bg=_THEME["cancel_bg"],
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        padx=8,
        pady=4,
        cursor="hand2",
    )
    cancel_btn.pack(side="right", padx=4)

    apply_button_animations(save_btn, _THEME["submit_bg"], _THEME["submit_hover_bg"])
    apply_button_animations(cancel_btn, _THEME["cancel_bg"], _THEME["cancel_hover_bg"])

    # ── Keyboard bindings ─────────────────────────────────────────────────
    win.bind("<Escape>", cleanup_and_close)
    win.protocol("WM_DELETE_WINDOW", cleanup_and_close)

    # Tab order within the edit form
    bank_combo.bind("<Return>", lambda _e: type_combo.focus_set())
    type_combo.bind("<Return>", lambda _e: ac_number_entry.focus_set())
    ac_number_entry.bind("<Return>", lambda _e: open_dt_entry.focus_set())
    open_dt_entry.bind("<Return>", lambda _e: balance_entry.focus_set())
    balance_entry.bind("<Return>", lambda _e: balance_dt_entry.focus_set())
    balance_dt_entry.bind("<Return>", lambda _e: joint_check.focus_set())
    joint_check.bind("<Return>", lambda _e: active_check.focus_set())
    active_check.bind("<Return>", lambda _e: save_btn.focus_set())

    # Give focus to the treeview first
    tree.focus_set()

    parent.wait_window(win)

    # Restore grab so the caller stays in focus
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass
