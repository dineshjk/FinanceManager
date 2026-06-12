# -*- coding: utf-8 -*-
# BankMan/loan_master_edit.py

"""
Edit form for the ``loan_master`` table.

Layout follows the same two-panel pattern as ``accounts_edit.py``:

* **Top panel** — sortable treeview of every loan master row (active and
  closed).  Click a row to load it into the edit form below.

* **Bottom panel** — coloured band form matching the structure of
  ``loan_master_add.py`` (Band 1: account / type, Band 2: numeric loan
  details, Band 3: dates and active flag).  Save validates and persists
  via ``db_update_loan_master``.

Theme
-----
``LOAN_MASTER_EDIT_UI_THEME`` — vivid teal / cyan — is the visual
complement of ``LOAN_MASTER_ADD_UI_THEME`` (near-black olive / gold),
so edit and add windows are immediately distinguishable at a glance.
"""

from datetime import datetime
from typing import Union
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry

from Shared.gui_utils import (
    LOAN_MASTER_EDIT_UI_THEME as _T,
    apply_button_animations,
    apply_entry_theme,
    bind_tooltip,
    flash_error,
    setup_footer_tooltip,
    bind_date_spin,
    universal_tree_sort,
)
from Shared.dialog_utils import show_colorful_error, show_colorful_info
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from Shared.globals import logger
from Shared.gui_progressive import progressive_selection
from .bank_db_utils import (
    db_get_all_loan_masters_for_edit,
    db_update_loan_master,
    get_all_accounts,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOAN_TYPES = [
    "HOME LOAN",
    "PERSONAL LOAN",
    "AUTO LOAN",
    "CAR LOAN",
    "EDUCATION LOAN",
    "BUSINESS LOAN",
    "GOLD LOAN",
    "PROPERTY LOAN",
    "OTHER",
]

_F = ("Helvetica", 14)
_FB = ("Helvetica", 14, "bold")
_FH = ("Helvetica", 17, "bold")
_FL = ("Helvetica", 12)

# ---------------------------------------------------------------------------
# Band helper — mirrors loan_master_add._make_band, but with light palette
# ---------------------------------------------------------------------------


def _make_band(container, bg, relief="ridge", padx=10, pady=6):
    band = tk.Frame(
        container,
        bg=bg,
        relief=relief,
        bd=2,
        padx=padx,
        pady=pady,
    )
    label_row = tk.Frame(band, bg=bg)
    label_row.pack(fill="x", pady=(0, 2))
    entry_row = tk.Frame(band, bg=bg)
    entry_row.pack(fill="x", pady=(0, 2))
    return band, label_row, entry_row


def _band_label(parent, text, bg, font=_F, padx=0):
    tk.Label(parent, text=text, font=font, bg=bg, fg=_T["label_fg"], anchor="w").pack(
        side="left", padx=(padx, 12)
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def edit_loan_master(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Open a modal two-panel window for editing loan master records.

    Parameters
    ----------
    parent:
        Owning window.
    calling_button:
        The button that opened this modal (disabled while open).
    """
    # ── Lookup data ───────────────────────────────────────────────────────
    accounts = get_all_accounts()
    # label: "BankName  [AccType]  ac_number"  → ac_id
    account_map: dict[str, int] = {
        f"{r[1]}  [{r[2]}]  {r[3]}": int(r[0]) for r in accounts
    }
    # reverse: ac_id → label (for pre-populating the combo)
    ac_id_to_label: dict[int, str] = {v: k for k, v in account_map.items()}

    # ── Modal window ──────────────────────────────────────────────────────
    disable_parent(parent, calling_button=calling_button)

    win = tk.Toplevel(parent)
    win.title("✏️  Edit Loan Master  ✏️")
    win.geometry("1060x700")
    win.resizable(False, False)
    win.configure(bg=_T["main_bg"])
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    try:
        push_window(win, parent)
    except (RuntimeError, tk.TclError) as exc:
        logger.debug("push_window failed: %s", exc)

    # Footer tooltip — packed first so it anchors to the absolute bottom
    tooltip_var = setup_footer_tooltip(
        win, bg_color=_T["header_bg"], fg_color=_T["header_fg"]
    )

    def cleanup_and_close(_event=None):
        return safe_close_modal(win, parent, calling_button)

    # ── Header ────────────────────────────────────────────────────────────
    hdr = tk.Frame(win, bg=_T["header_bg"], relief="raised", bd=3)
    hdr.pack(fill="x", padx=5, pady=(5, 0))

    tk.Label(
        hdr,
        text="✏️   Edit Loan Master   ✏️",
        font=_FH,
        bg=_T["header_bg"],
        fg=_T["header_fg"],
        relief="ridge",
        bd=2,
        pady=8,
    ).pack(fill="x")

    # ── Treeview (top panel) ──────────────────────────────────────────────
    tv_outer = tk.Frame(win, bg=_T["main_bg"], relief="ridge", bd=2)
    tv_outer.pack(fill="both", expand=True, padx=8, pady=(6, 2))

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "LoanEdit.Treeview",
        background="#EAFAFA",
        foreground="#012525",
        fieldbackground="#EAFAFA",
        rowheight=24,
        font=("Helvetica", 11),
    )
    style.configure(
        "LoanEdit.Treeview.Heading",
        background=_T["header_bg"],
        foreground="white",
        font=("Helvetica", 11, "bold"),
    )
    style.map(
        "LoanEdit.Treeview",
        background=[("selected", "#1FA8A8")],
        foreground=[("selected", "white")],
    )

    tv_scroll = ttk.Scrollbar(tv_outer)
    tv_scroll.pack(side="right", fill="y")

    _TV_COLS = (
        "id",
        "Bank",
        "Account No",
        "Loan Type",
        "Loan Acc No",
        "Principal",
        "Rate %",
        "EMI",
        "Start",
        "End",
        "Active",
    )
    tree = ttk.Treeview(
        tv_outer,
        columns=_TV_COLS,
        show="headings",
        height=7,
        yscrollcommand=tv_scroll.set,
        style="LoanEdit.Treeview",
        selectmode="browse",
    )
    tv_scroll.config(command=tree.yview)

    tree.column("id", width=0, stretch=tk.NO, minwidth=0)
    tree.column("Bank", width=160, anchor="w")
    tree.column("Account No", width=110, anchor="w")
    tree.column("Loan Type", width=120, anchor="w")
    tree.column("Loan Acc No", width=130, anchor="w")
    tree.column("Principal", width=110, anchor="e")
    tree.column("Rate %", width=65, anchor="center")
    tree.column("EMI", width=100, anchor="e")
    tree.column("Start", width=85, anchor="center")
    tree.column("End", width=85, anchor="center")
    tree.column("Active", width=55, anchor="center")

    for col in _TV_COLS:
        tree.heading(
            col,
            text=col if col != "id" else "",
            command=lambda c=col: universal_tree_sort(tree, c, False),
        )

    tree.pack(fill="both", expand=True)



    # ── Load treeview ─────────────────────────────────────────────────────
    def load_tree() -> None:
        for item in tree.get_children():
            tree.delete(item)
        rows = db_get_all_loan_masters_for_edit()
        for r in rows:
            # r: (loan_master_id[0], account_id[1], bank_name[2],
            #     ac_number[3], loan_type[4], loan_account_number[5],
            #     principal_amount[6], interest_rate[7], emi_amount[8],
            #     start_dt[9], end_dt[10], is_active[11])
            tree.insert(
                "",
                "end",
                values=(
                    r[0],  # id (hidden)
                    r[2],  # bank_name
                    r[3],  # ac_number
                    r[4],  # loan_type
                    r[5],  # loan_account_number
                    f"₹ {(r[6] or 0.0):,.0f}",  # principal
                    f"{(r[7] or 0.0):.2f} %",  # interest rate
                    f"₹ {(r[8] or 0.0):,.0f}",  # emi
                    r[9] or "",  # start_dt
                    r[10] or "",  # end_dt
                    "Yes" if r[11] else "No",  # is_active
                ),
            )

    load_tree()

    # ── Divider + instruction label ───────────────────────────────────────
    tk.Frame(win, height=2, bg=_T["header_bg"]).pack(fill="x", padx=8, pady=(4, 0))
    tk.Label(
        win,
        text="  Select a row above, then edit the fields below:",
        font=("Helvetica", 11, "bold"),
        bg=_T["header_bg"],
        fg="white",
        padx=6,
        pady=2,
    ).pack(fill="x", padx=8, pady=(0, 4))

    # ── Edit form — band layout matching loan_master_add ──────────────────
    form_body = tk.Frame(win, bg=_T["main_bg"])
    form_body.pack(fill="x", padx=12, pady=4)

    _loaded: dict = {}  # mirrors the currently-loaded loan_master row

    _C_ACC = _T["band_account"]
    _C_LOAN = _T["band_loan"]
    _C_DATES = _T["band_dates"]

    # ── Band 1: Account + Loan Type ───────────────────────────────────────
    acc_band, acc_lrow, acc_erow = _make_band(form_body, _C_ACC)
    acc_band.pack(fill="x", pady=(0, 4))

    _band_label(acc_lrow, "Linked Bank Account", _C_ACC, _F)
    _band_label(acc_lrow, "Loan Type", _C_ACC, _F, padx=110)

    account_combo = ttk.Combobox(
        acc_erow, width=42, values=list(account_map.keys()), font=_F
    )
    account_combo.pack(side="left", padx=(0, 8))
    apply_entry_theme(account_combo)
    progressive_selection(account_combo, list(account_map.keys()))
    bind_tooltip(
        account_combo, tooltip_var, "Bank account through which EMIs are debited."
    )

    loan_type_combo = ttk.Combobox(acc_erow, width=22, values=_LOAN_TYPES, font=_F)
    loan_type_combo.pack(side="left", padx=(18, 0))
    apply_entry_theme(loan_type_combo)
    progressive_selection(loan_type_combo, _LOAN_TYPES)
    bind_tooltip(loan_type_combo, tooltip_var, "Loan product category.")

    # ── Band 2: Loan Details ──────────────────────────────────────────────
    loan_band, loan_lrow, loan_erow = _make_band(form_body, _C_LOAN)
    loan_band.pack(fill="x", pady=(0, 4))

    _band_label(loan_lrow, "Loan Account Number", _C_LOAN, _F)
    _band_label(loan_lrow, "Principal Amount (₹)", _C_LOAN, _F, padx=28)
    _band_label(loan_lrow, "Interest Rate (%)", _C_LOAN, _F, padx=28)
    _band_label(loan_lrow, "EMI Amount (₹)", _C_LOAN, _F, padx=28)

    loan_acc_no_var = tk.StringVar()
    loan_acc_no_entry = tk.Entry(
        loan_erow, textvariable=loan_acc_no_var, width=20, font=_FB
    )
    loan_acc_no_entry.pack(side="left", padx=(0, 8))
    apply_entry_theme(loan_acc_no_entry)
    bind_tooltip(
        loan_acc_no_entry,
        tooltip_var,
        "Bank-assigned loan account / reference number.",
    )

    principal_var = tk.StringVar()
    principal_entry = tk.Entry(
        loan_erow, textvariable=principal_var, width=14, font=_FB
    )
    principal_entry.pack(side="left", padx=(18, 8))
    apply_entry_theme(principal_entry)
    bind_tooltip(principal_entry, tooltip_var, "Original sanctioned loan amount (₹).")

    interest_var = tk.StringVar()
    interest_entry = tk.Entry(loan_erow, textvariable=interest_var, width=10, font=_FB)
    interest_entry.pack(side="left", padx=(18, 8))
    apply_entry_theme(interest_entry)
    bind_tooltip(
        interest_entry,
        tooltip_var,
        "Annual interest rate at origination (%, e.g. 8.5).",
    )

    emi_var = tk.StringVar()
    emi_entry = tk.Entry(loan_erow, textvariable=emi_var, width=14, font=_FB)
    emi_entry.pack(side="left", padx=(18, 0))
    apply_entry_theme(emi_entry)
    bind_tooltip(emi_entry, tooltip_var, "Fixed monthly instalment amount (₹).")

    # ── Band 3: Dates + Is Active ─────────────────────────────────────────
    date_band, date_lrow, date_erow = _make_band(form_body, _C_DATES)
    date_band.pack(fill="x", pady=(0, 4))

    _band_label(date_lrow, "Start Date", _C_DATES, _F)
    _band_label(date_lrow, "End Date", _C_DATES, _F, padx=60)
    _band_label(date_lrow, "Is Active", _C_DATES, _F, padx=60)

    start_dt = DateEntry(date_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    start_dt.pack(side="left", padx=(0, 8))
    apply_entry_theme(start_dt)
    bind_tooltip(start_dt, tooltip_var, "Loan disbursement / first EMI date.")

    end_dt = DateEntry(date_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    end_dt.pack(side="left", padx=(18, 8))
    apply_entry_theme(end_dt)
    bind_tooltip(end_dt, tooltip_var, "Scheduled final EMI / loan closure date.")

    bind_date_spin(start_dt)
    bind_date_spin(end_dt)

    is_active_var = tk.IntVar(value=1)
    tk.Checkbutton(
        date_erow,
        text="Active",
        variable=is_active_var,
        font=_F,
        bg=_C_DATES,
        fg=_T["label_fg"],
        selectcolor=_T["band_loan"],
        activebackground=_C_DATES,
        activeforeground=_T["label_fg"],
    ).pack(side="left", padx=(18, 0))

    # ── Disable all form widgets until a row is selected ─────────────────
    _FORM_WIDGETS = [
        account_combo,
        loan_type_combo,
        loan_acc_no_entry,
        principal_entry,
        interest_entry,
        emi_entry,
        start_dt,
        end_dt,
    ]

    def _set_form_state(state: str) -> None:
        for w in _FORM_WIDGETS:
            try:
                w.configure(state=state)
            except tk.TclError:
                pass

    _set_form_state("disabled")

    # ── Populate form from a treeview selection ───────────────────────────
    def _populate_form(loan_master_id: int) -> None:
        rows = db_get_all_loan_masters_for_edit()
        row = next((r for r in rows if r[0] == loan_master_id), None)
        if row is None:
            return

        # r: (loan_master_id[0], account_id[1], bank_name[2],
        #     ac_number[3], loan_type[4], loan_account_number[5],
        #     principal_amount[6], interest_rate[7], emi_amount[8],
        #     start_dt[9], end_dt[10], is_active[11])
        _loaded.clear()
        _loaded.update(
            {
                "loan_master_id": row[0],
                "account_id": row[1],
                "loan_type": row[4],
                "loan_account_number": row[5],
                "principal_amount": row[6] or 0.0,
                "interest_rate": row[7] or 0.0,
                "emi_amount": row[8] or 0.0,
                "start_dt": row[9],
                "end_dt": row[10],
                "is_active": row[11],
            }
        )

        _set_form_state("normal")

        # Bank account
        label = ac_id_to_label.get(row[1], "")
        account_combo.set(label)

        # Loan type
        loan_type_combo.set(row[4])

        # Loan account number
        loan_acc_no_var.set(row[5] or "")

        # Numeric fields
        principal_var.set(f"{(row[6] or 0.0):.2f}")
        interest_var.set(f"{(row[7] or 0.0):.2f}")
        emi_var.set(f"{(row[8] or 0.0):.2f}")

        # Dates
        def _parse_date(s):
            try:
                return datetime.strptime(s, "%Y-%m-%d")
            except (ValueError, TypeError):
                return datetime.today()

        start_dt.set_date(_parse_date(row[9]))
        end_dt.set_date(_parse_date(row[10]))

        is_active_var.set(1 if row[11] else 0)

        account_combo.focus_set()

    # ── Treeview selection binding ────────────────────────────────────────
    def _on_tree_select(_event=None) -> None:
        selected = tree.selection()
        if not selected:
            return
        values = tree.item(selected[0])["values"]
        _populate_form(values[0])

    tree.bind("<<TreeviewSelect>>", _on_tree_select)
    tree.bind("<Double-1>", _on_tree_select)

    # ── Button bar ────────────────────────────────────────────────────────
    btn_frame = tk.Frame(win, bg=_T["main_bg"], relief="ridge", bd=2, pady=6)
    btn_frame.pack(fill="x", padx=12, pady=(4, 4))

    # ── Save handler ──────────────────────────────────────────────────────
    def on_save(_event=None) -> None:
        if not _loaded:
            show_colorful_error(
                win, "No Selection", "Please select a loan from the list first."
            )
            return

        # — Account —
        ac_label = account_combo.get().strip()
        if not ac_label or ac_label not in account_map:
            show_colorful_error(
                win, "Validation", "Please select a valid bank account."
            )
            flash_error(account_combo)
            return
        account_id = account_map[ac_label]

        # — Loan Type —
        loan_type = loan_type_combo.get().strip()
        if loan_type not in _LOAN_TYPES:
            show_colorful_error(win, "Validation", "Please select a valid loan type.")
            flash_error(loan_type_combo)
            return

        # — Loan Account Number —
        loan_acc_no = loan_acc_no_var.get().strip()
        if not loan_acc_no:
            show_colorful_error(win, "Validation", "Loan Account Number is required.")
            flash_error(loan_acc_no_entry)
            return

        # — Numeric fields —
        def _parse(var, widget, name, positive=True):
            try:
                v = float(var.get().strip().replace(",", "") or "0")
            except ValueError:
                show_colorful_error(win, "Validation", f"{name} must be a number.")
                flash_error(widget)
                return None
            if positive and v <= 0:
                show_colorful_error(
                    win, "Validation", f"{name} must be greater than 0."
                )
                flash_error(widget)
                return None
            return v

        principal = _parse(principal_var, principal_entry, "Principal Amount")
        if principal is None:
            return
        rate = _parse(interest_var, interest_entry, "Interest Rate")
        if rate is None:
            return
        emi = _parse(emi_var, emi_entry, "EMI Amount")
        if emi is None:
            return

        # — Dates —
        try:
            s_dt = start_dt.get_date().strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            show_colorful_error(win, "Validation", "Start Date is invalid.")
            flash_error(start_dt)
            return
        try:
            e_dt = end_dt.get_date().strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            show_colorful_error(win, "Validation", "End Date is invalid.")
            flash_error(end_dt)
            return
        if e_dt <= s_dt:
            show_colorful_error(win, "Validation", "End Date must be after Start Date.")
            flash_error(end_dt)
            return

        loan_master_id = _loaded["loan_master_id"]

        try:
            db_update_loan_master(
                loan_master_id=loan_master_id,
                account_id=account_id,
                loan_type=loan_type,
                loan_account_number=loan_acc_no,
                principal_amount=principal,
                interest_rate=rate,
                emi_amount=emi,
                start_dt=s_dt,
                end_dt=e_dt,
                is_active=is_active_var.get(),
            )
        except Exception as exc:  # noqa: BLE001
            show_colorful_error(win, "Database Error", f"Failed to save:\n{exc}")
            logger.exception(
                "loan_master_edit: UPDATE failed for loan_master_id=%s",
                loan_master_id,
            )
            return

        show_colorful_info(
            win,
            "Saved",
            f"Loan Master '{loan_acc_no}' updated successfully.",
        )
        _loaded.clear()
        _set_form_state("disabled")
        load_tree()

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

    apply_button_animations(save_btn, _T["submit_bg"], _T["submit_hover_bg"])
    apply_button_animations(cancel_btn, _T["cancel_bg"], _T["cancel_hover_bg"])

    # ── Keyboard bindings ─────────────────────────────────────────────────
    win.bind("<Escape>", cleanup_and_close)
    win.protocol("WM_DELETE_WINDOW", cleanup_and_close)

    def _focus(w):
        def _h(_e=None):
            w.focus_set()
            return "break"

        return _h

    account_combo.bind("<Return>", _focus(loan_type_combo))
    loan_type_combo.bind("<Return>", _focus(loan_acc_no_entry))
    loan_acc_no_entry.bind("<Return>", _focus(principal_entry))
    principal_entry.bind("<Return>", _focus(interest_entry))
    interest_entry.bind("<Return>", _focus(emi_entry))
    emi_entry.bind("<Return>", _focus(start_dt))
    start_dt.bind("<Return>", _focus(end_dt))
    end_dt.bind("<Return>", _focus(save_btn))

    # ── Initial focus — treeview ──────────────────────────────────────────
    tree.focus_set()

    parent.wait_window(win)

    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass
