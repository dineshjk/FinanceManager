# -*- coding: utf-8 -*-
# BankMan/ins_master_add.py

"""
Module for adding new Insurance master records (ins_master table).
"""

from typing import Union
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry

from Shared.gui_utils import (
    apply_entry_theme,
    bind_tooltip,
    setup_footer_tooltip,
    flash_error,
    INS_MASTER_ADD_UI_THEME,
    apply_button_animations,
    bind_date_spin,
)
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno,
)
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from Shared.help_utils import show_standard_help
from .bank_db_utils import (
    get_all_accounts,
    db_add_ins_master as _db_add_ins_master,
)
from Shared.globals import logger
from Shared.gui_progressive import progressive_selection
from .accounts_add import add_account_main as _add_account

# ---------------------------------------------------------------------------
# Theme alias
# ---------------------------------------------------------------------------
_T = INS_MASTER_ADD_UI_THEME

# ---------------------------------------------------------------------------
# Band / label helpers
# ---------------------------------------------------------------------------


def _make_band(container, bg, relief="ridge", padx=10, pady=6):
    band = tk.Frame(
        container, bg=bg, relief=relief, bd=2, padx=padx, pady=pady
    )
    label_row = tk.Frame(band, bg=bg)
    label_row.pack(fill="x", pady=(0, 2))
    entry_row = tk.Frame(band, bg=bg)
    entry_row.pack(fill="x", pady=(0, 2))
    return band, label_row, entry_row


def _band_label(parent, text, bg, font=("Helvetica", 14), padx=0):
    tk.Label(
        parent,
        text=text,
        font=font,
        bg=bg,
        fg=_T.get("label_fg", "gold"),
        anchor="w",
    ).pack(side="left", padx=(padx, 12))


# ---------------------------------------------------------------------------
# Help window (F1)
# ---------------------------------------------------------------------------


def _show_help(win: tk.Toplevel, on_escape) -> None:
    guide_lines = [
        "This form registers a new Insurance Policy.",
        "",
        "Fields:",
        "• Linked Account: The bank account used to pay premiums.",
        "• Company Name: The insurance provider (e.g., LIC, HDFC Ergo).",
        "• Category: Type of insurance (LIFE_TERM, LIFE_SAVINGS, HEALTH, etc.).",
        "• Policy Number: Your unique policy number.",
        "• Plan Name: Name of the policy plan.",
        "• Proposer Name: The person who bought the policy.",
        "• Assured Item: Person whose life is insured, or vehicle number.",
        "• Premium: Amount paid (monthly/yearly).",
        "• Start / Maturity Dates: The duration of the policy.",
        "• Active: Tick to indicate the policy is currently active.",
    ]
    faq_data = [
        (
            "Q: Do I enter the premium payment here?",
            "A: No! Use Data Entry -> Bank to log premium payments.",
        )
    ]
    show_standard_help(win, "Add Insurance Master Help", guide_lines, faq_data)


# ---------------------------------------------------------------------------
# Session viewer (F2)
# ---------------------------------------------------------------------------


def _show_session_viewer(
    win: tk.Toplevel, session_entries: list, on_escape
) -> None:
    if not session_entries:
        try:
            show_colorful_info(
                win,
                "No Entries",
                "No Insurance master records have been added this session.",
            )
        except tk.TclError:
            pass
        return

    win.unbind("<Escape>")
    idx = {"i": 0}

    viewer = tk.Toplevel(win)
    viewer.title("Session — Insurance Masters Added")
    viewer.transient(win)
    viewer.grab_set()
    viewer.resizable(False, False)
    viewer.geometry("580x380")
    viewer.configure(bg=_T.get("header_bg", "#3f271d"))
    push_window(viewer, win)

    tk.Label(
        viewer,
        text="Insurance Masters Added This Session",
        font=("Helvetica", 14, "bold"),
        bg=_T.get("header_bg", "#3f271d"),
        fg=_T.get("header_fg", "#fbbf24"),
        pady=6,
    ).pack(fill="x")

    content = tk.Frame(viewer, bg=_T.get("header_bg", "#3f271d"))
    content.pack(fill="both", expand=True, padx=10, pady=6)

    left_btn = tk.Button(
        content,
        text="\u25c4",
        width=3,
        bg=_T.get("button_bg", "#78350f"),
        fg="white",
        cursor="hand2",
    )
    left_btn.pack(side="left", padx=(6, 4), pady=6)
    right_btn = tk.Button(
        content,
        text="\u25ba",
        width=3,
        bg=_T.get("button_bg", "#78350f"),
        fg="white",
        cursor="hand2",
    )
    right_btn.pack(side="right", padx=(4, 6), pady=6)

    info_text = tk.Text(
        content,
        wrap="word",
        height=13,
        bg=_T.get("main_bg", "#593122"),
        fg=_T.get("header_fg", "#fbbf24"),
        bd=0,
        relief="flat",
        font=("Helvetica", 11),
    )
    info_text.pack(fill="both", expand=True, padx=6, pady=4)
    info_text.tag_configure(
        "label",
        font=("Helvetica", 11, "bold"),
        foreground=_T.get("header_fg", "#fbbf24"),
    )
    info_text.tag_configure(
        "value", font=("Helvetica", 11), foreground="#fed7aa"
    )
    info_text.config(state="disabled")

    status_label = tk.Label(
        content,
        text="",
        font=("Helvetica", 10, "bold"),
        bg=_T.get("header_bg", "#3f271d"),
        fg=_T.get("header_fg", "#fbbf24"),
    )
    status_label.pack(side="bottom", pady=(0, 4))

    def _update_view():
        i = idx["i"]
        rec = session_entries[i]
        total = len(session_entries)
        info_text.config(state="normal")
        info_text.delete("1.0", "end")
        fields = [
            ("Company", rec.get("company_name")),
            ("Category", rec.get("ins_category")),
            ("Policy No", rec.get("policy_number")),
            ("Plan", rec.get("plan_name")),
            ("Proposer", rec.get("proposer_name")),
            ("Assured", rec.get("assured_item")),
            ("Premium (\u20b9)", f"{rec.get('premium_amount', 0.0):,.2f}"),
        ]
        for label, val in fields:
            info_text.insert("end", f"{label}: ", "label")
            info_text.insert("end", f"{val or chr(8212)}\n", "value")
        info_text.config(state="disabled")
        left_btn.config(state="disabled" if i == 0 else "normal")
        if i >= total - 1:
            right_btn.config(state="disabled")
            status_label.config(text="Last Entry", fg="#ef4444")
        else:
            right_btn.config(state="normal")
            status_label.config(
                text=f"Entry {i + 1} of {total}",
                fg=_T.get("header_fg", "#fbbf24"),
            )

    def _go_prev(_e=None):
        if idx["i"] > 0:
            idx["i"] -= 1
            _update_view()

    def _go_next(_e=None):
        if idx["i"] < len(session_entries) - 1:
            idx["i"] += 1
            _update_view()

    left_btn.config(command=_go_prev)
    right_btn.config(command=_go_next)
    viewer.bind("<Left>", lambda e: _go_prev())
    viewer.bind("<Right>", lambda e: _go_next())

    def _close_viewer(_e=None):
        safe_close_modal(viewer, win)
        win.bind("<Escape>", on_escape)
        return "break"

    viewer.bind("<Escape>", _close_viewer)
    viewer.protocol("WM_DELETE_WINDOW", _close_viewer)
    viewer.bind("<Return>", _close_viewer)

    ok_btn = tk.Button(
        content,
        text="OK",
        width=10,
        command=_close_viewer,
        bg=_T.get("button_bg", "#78350f"),
        fg="white",
        font=("Helvetica", 11, "bold"),
        cursor="hand2",
    )
    ok_btn.pack(side="bottom", pady=(0, 6))
    _update_view()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def add_ins_master_main(
    parent: Union[tk.Toplevel, tk.Tk], calling_button: tk.Widget | None = None
) -> None:
    accounts = get_all_accounts()
    account_map = {f"{a[1]} : [{a[3]}]": a[0] for a in accounts}

    disable_parent(parent, calling_button=calling_button)
    session_records: list = []

    win = tk.Toplevel(parent)
    win.title("\U0001f6e1 Add Insurance Master \U0001f6e1")
    win.geometry("960x730")
    win.resizable(False, False)
    win.configure(bg=_T.get("main_bg", "#593122"))
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    try:
        push_window(win, parent)
    except Exception:
        pass

    tooltip_var = setup_footer_tooltip(
        win,
        bg_color=_T.get("header_bg", "#3f271d"),
        fg_color=_T.get("header_fg", "#fbbf24"),
    )

    def cleanup_and_close(_event=None):
        return safe_close_modal(win, parent, calling_button)

    def on_escape(_event=None):
        return cleanup_and_close()

    win.bind(
        "<F1>",
        lambda e: None
        if (getattr(e, "state", 0) & 0x0004)
        else (_show_help(win, on_escape)),
    )
    win.bind(
        "<F2>", lambda e: _show_session_viewer(win, session_records, on_escape)
    )
    win.bind("<Escape>", on_escape)
    win.protocol("WM_DELETE_WINDOW", on_escape)

    # Header
    header_frame = tk.Frame(
        win, bg=_T.get("header_bg", "#3f271d"), relief="raised", bd=3
    )
    header_frame.pack(fill="x", padx=5, pady=0)
    tk.Label(
        header_frame,
        text="\U0001f6e1  Add Insurance Master  \U0001f6e1",
        font=("Helvetica", 18, "bold"),
        bg=_T.get("header_bg", "#3f271d"),
        fg=_T.get("header_fg", "#fbbf24"),
        relief="ridge",
        bd=2,
        pady=8,
    ).pack(fill="x")

    hint_frame = tk.Frame(win, bg=_T.get("main_bg", "#593122"))
    hint_frame.pack(fill="x", padx=10, pady=(2, 0))
    for hint in ("F1: Help", "F2: Session Viewer", "Esc: Close"):
        tk.Label(
            hint_frame,
            text=hint,
            font=("Helvetica", 10, "italic"),
            bg=_T.get("main_bg", "#593122"),
            fg="#fed7aa",
        ).pack(side="left", padx=12)

    _F = ("Helvetica", 14)
    _FB = ("Helvetica", 14, "bold")

    _C_ACCT = _T.get("band_1_bg", "#78350f")
    _C_COMP = _T.get("band_2_bg", "#92400e")
    _C_POL = _T.get("band_3_bg", "#b45309")
    _C_PROP = _T.get("band_4_bg", "#d97706")
    _C_DATES = _T.get("band_5_bg", "#78350f")

    form_body = tk.Frame(win, bg=_T.get("main_bg", "#593122"))
    form_body.pack(fill="x", padx=12, pady=6)

    # Band 1: Account
    acct_band, acct_lrow, acct_erow = _make_band(form_body, _C_ACCT)
    acct_band.pack(fill="x", pady=(0, 5))
    _band_label(acct_lrow, "Linked Bank Account", _C_ACCT, _F)
    account_combo = ttk.Combobox(
        acct_erow, width=40, values=list(account_map.keys()), font=_F
    )
    account_combo.pack(side="left", padx=(0, 8))
    apply_entry_theme(account_combo)
    progressive_selection(account_combo, list(account_map.keys()))
    if account_map:
        account_combo.set(next(iter(account_map)))

    # Band 2: Company + Category
    comp_band, comp_lrow, comp_erow = _make_band(form_body, _C_COMP)
    comp_band.pack(fill="x", pady=(0, 5))
    _band_label(comp_lrow, "Company Name", _C_COMP, _F)
    _band_label(comp_lrow, "Category", _C_COMP, _F, padx=120)

    comp_entry = tk.Entry(comp_erow, width=24, font=_FB)
    comp_entry.pack(side="left", padx=(0, 8))
    apply_entry_theme(comp_entry)

    cat_combo = ttk.Combobox(
        comp_erow,
        width=20,
        values=["LIFE_TERM", "LIFE_SAVINGS", "HEALTH", "VEHICLE", "GENERAL"],
        font=_FB,
    )
    cat_combo.pack(side="left", padx=(25, 0))
    apply_entry_theme(cat_combo)
    progressive_selection(
        cat_combo,
        ["LIFE_TERM", "LIFE_SAVINGS", "HEALTH", "VEHICLE", "GENERAL"],
    )
    cat_combo.set("LIFE_TERM")

    # Band 3: Policy No + Plan
    pol_band, pol_lrow, pol_erow = _make_band(form_body, _C_POL)
    pol_band.pack(fill="x", pady=(0, 5))
    _band_label(pol_lrow, "Policy Number", _C_POL, _F)
    _band_label(pol_lrow, "Plan Name", _C_POL, _F, padx=100)

    pol_entry = tk.Entry(pol_erow, width=20, font=_FB)
    pol_entry.pack(side="left", padx=(0, 8))
    apply_entry_theme(pol_entry)

    plan_entry = tk.Entry(pol_erow, width=30, font=_FB)
    plan_entry.pack(side="left", padx=(15, 0))
    apply_entry_theme(plan_entry)

    # Band 4: Proposer + Assured Item
    prop_band, prop_lrow, prop_erow = _make_band(form_body, _C_PROP)
    prop_band.pack(fill="x", pady=(0, 5))
    _band_label(prop_lrow, "Proposer Name", _C_PROP, _F)
    _band_label(prop_lrow, "Assured Item (Life/Car)", _C_PROP, _F, padx=30)

    prop_entry = tk.Entry(prop_erow, width=20, font=_FB)
    prop_entry.pack(side="left", padx=(0, 8))
    apply_entry_theme(prop_entry)

    assure_entry = tk.Entry(prop_erow, width=20, font=_FB)
    assure_entry.pack(side="left", padx=(20, 8))
    apply_entry_theme(assure_entry)

    # Band 4b: Amounts
    _C_AMTS = _T.get("band_5_bg", "#92400e")
    amt_band, amt_lrow, amt_erow = _make_band(form_body, _C_AMTS)
    amt_band.pack(fill="x", pady=(0, 5))
    _band_label(amt_lrow, "Sum Assured (\u20b9)", _C_AMTS, _F)
    _band_label(amt_lrow, "Premium (\u20b9)", _C_AMTS, _F, padx=60)

    sum_assured_entry = tk.Entry(amt_erow, width=15, font=_FB)
    sum_assured_entry.pack(side="left", padx=(0, 8))
    apply_entry_theme(sum_assured_entry)

    prem_entry = tk.Entry(amt_erow, width=15, font=_FB)
    prem_entry.pack(side="left", padx=(35, 0))
    apply_entry_theme(prem_entry)
    prem_entry.insert(0, "0.0")

    # Band 5: Dates + Active
    dates_band, dates_lrow, dates_erow = _make_band(form_body, _C_DATES)
    dates_band.pack(fill="x", pady=(0, 5))
    _band_label(dates_lrow, "Start Date", _C_DATES, _F)
    _band_label(dates_lrow, "Maturity Date (Optional)", _C_DATES, _F, padx=60)
    _band_label(dates_lrow, "Is Active", _C_DATES, _F, padx=20)

    start_dt = DateEntry(
        dates_erow, date_pattern="dd-mm-yyyy", width=14, font=_F
    )
    start_dt.pack(side="left", padx=(0, 8))
    apply_entry_theme(start_dt)
    bind_date_spin(start_dt)

    mat_dt = DateEntry(
        dates_erow, date_pattern="dd-mm-yyyy", width=14, font=_F
    )
    mat_dt.pack(side="left", padx=(40, 8))
    apply_entry_theme(mat_dt)
    bind_date_spin(mat_dt)

    is_active_var = tk.BooleanVar(value=True)
    is_active_cb = tk.Checkbutton(
        dates_erow,
        variable=is_active_var,
        text="Active",
        font=_F,
        bg=_C_DATES,
        fg=_T.get("label_fg", "gold"),
        selectcolor="#001a50",
        activebackground=_C_DATES,
        activeforeground=_T.get("label_fg", "gold"),
    )
    is_active_cb.pack(side="left", padx=(50, 0))

    session_count_var = tk.StringVar(value="Session: 0 saved")
    tk.Label(
        win,
        textvariable=session_count_var,
        font=("Helvetica", 11, "italic"),
        bg=_T.get("main_bg"),
        fg="#fed7aa",
    ).pack(anchor="e", padx=16)

    btn_frame = tk.Frame(win, bg=_T.get("main_bg"))
    btn_frame.pack(pady=8)

    def _reset_form():
        comp_entry.delete(0, "end")
        pol_entry.delete(0, "end")
        plan_entry.delete(0, "end")
        prop_entry.delete(0, "end")
        assure_entry.delete(0, "end")
        sum_assured_entry.delete(0, "end")
        prem_entry.delete(0, "end")
        prem_entry.insert(0, "0.0")
        is_active_var.set(True)
        comp_entry.focus_set()

    def _validate_and_save():
        acct = account_combo.get()
        if not acct or acct not in account_map:
            flash_error(account_combo)
            show_colorful_error(win, "Error", "Invalid account.")
            return

        comp = comp_entry.get().strip()
        cat = cat_combo.get().strip()
        pol = pol_entry.get().strip()
        plan = plan_entry.get().strip()
        prop = prop_entry.get().strip()
        assure = assure_entry.get().strip()

        if not all([comp, cat, pol, plan, prop, assure]):
            show_colorful_error(
                win, "Error", "Please fill in all required text fields."
            )
            return

        try:
            prem = float(prem_entry.get().strip().replace(",", "") or 0)
        except ValueError:
            flash_error(prem_entry)
            show_colorful_error(win, "Error", "Invalid premium amount.")
            return

        sum_ass_str = sum_assured_entry.get().strip().replace(",", "")
        sum_assured_val = None
        if sum_ass_str:
            try:
                sum_assured_val = float(sum_ass_str)
            except ValueError:
                show_colorful_error(win, "Error", "Invalid sum assured amount.")
                flash_error(sum_assured_entry)
                return

        try:
            sd = start_dt.get_date()
            md = mat_dt.get_date()
        except Exception:
            show_colorful_error(win, "Error", "Invalid dates.")
            return

        data = {
            "account_id": account_map[acct],
            "company_name": comp,
            "ins_category": cat,
            "policy_number": pol,
            "plan_name": plan,
            "proposer_name": prop,
            "assured_item": assure,
            "sum_assured": sum_assured_val,
            "premium_amount": prem,
            "start_dt": sd.strftime("%Y-%m-%d"),
            "maturity_dt": md.strftime("%Y-%m-%d"),
            "is_active": 1 if is_active_var.get() else 0,
        }

        try:
            mid = _db_add_ins_master(data)
        except Exception as exc:
            show_colorful_error(win, "Database Error", str(exc))
            return

        session_records.append({**data, "ins_master_id": mid})
        session_count_var.set(f"Session: {len(session_records)} saved")

        # Save to parent for callback
        setattr(parent, "last_added_ins_id", mid)

        yes = show_colorful_yesno(
            win,
            "Saved",
            f"Insurance Master saved (ID {mid}).\n\nDo you want to add another record?",
        )
        if yes:
            _reset_form()
        else:
            cleanup_and_close()

    save_btn = tk.Button(
        btn_frame,
        text="Save",
        command=_validate_and_save,
        font=("Helvetica", 13, "bold"),
        bg=_T.get("submit_bg", "#10b981"),
        fg="white",
        padx=18,
        pady=6,
        cursor="hand2",
    )
    save_btn.pack(side="left", padx=12)
    clear_btn = tk.Button(
        btn_frame,
        text="Clear",
        command=_reset_form,
        font=("Helvetica", 13, "bold"),
        bg=_T.get("cancel_bg", "#ef4444"),
        fg="white",
        padx=18,
        pady=6,
        cursor="hand2",
    )
    clear_btn.pack(side="left", padx=12)
    cancel_btn = tk.Button(
        btn_frame,
        text="Cancel",
        command=cleanup_and_close,
        font=("Helvetica", 13, "bold"),
        bg=_T.get("cancel_bg", "#ef4444"),
        fg="white",
        padx=18,
        pady=6,
        cursor="hand2",
    )
    cancel_btn.pack(side="left", padx=12)

    def _focus_next(w):
        def _h(_e=None):
            w.focus_set()
            return "break"

        return _h

    account_combo.bind("<Return>", _focus_next(comp_entry))
    comp_entry.bind("<Return>", _focus_next(cat_combo))
    cat_combo.bind("<Return>", _focus_next(pol_entry))
    pol_entry.bind("<Return>", _focus_next(plan_entry))
    plan_entry.bind("<Return>", _focus_next(prop_entry))
    prop_entry.bind("<Return>", _focus_next(assure_entry))
    assure_entry.bind("<Return>", _focus_next(prem_entry))
    prem_entry.bind("<Return>", _focus_next(start_dt))
    start_dt.bind("<Return>", _focus_next(mat_dt))
    mat_dt.bind("<Return>", lambda _e: _validate_and_save())

    account_combo.focus_set()
    parent.wait_window(win)
