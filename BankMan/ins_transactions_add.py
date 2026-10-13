# -*- coding: utf-8 -*-
# BankMan/ins_transactions_add.py

"""
Module for adding Insurance transaction records (ins_transactions table).
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
    INS_TRANS_ADD_UI_THEME,
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
    get_all_ins_masters_for_display,
    db_add_ins_transaction as _db_add_ins_transaction,
)
from Shared.globals import logger
from Shared.gui_progressive import progressive_selection
from .ins_master_add import add_ins_master_main as _add_ins

# ---------------------------------------------------------------------------
# Theme alias
# ---------------------------------------------------------------------------
_T = INS_TRANS_ADD_UI_THEME

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
        "This form records internal events for an Insurance Policy.",
        "",
        "Fields:",
        "• INS Master: Select the policy.",
        "• Date: Transaction date.",
        "• Description: Note/Description of the transaction.",
        "• Premium Paid (\u20b9): Premium amount.",
        "• Payout Received (\u20b9): Claim or maturity amount received.",
        "",
        "Hotkeys: F2 (Session Viewer), Esc (Close), Ctrl+Enter (Save)",
    ]
    faq_data = [
        (
            "Q: Does this update my bank account balance?",
            "A: No! Use Data Entry -> Bank if you need to log money leaving or entering your bank account.",
        )
    ]
    show_standard_help(
        win, "Add Insurance Transaction Help", guide_lines, faq_data
    )


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
                "No INS transactions have been added this session.",
            )
        except tk.TclError:
            pass
        return

    win.unbind("<Escape>")
    idx = {"i": 0}

    viewer = tk.Toplevel(win)
    viewer.title("Session — INS Transactions Added")
    viewer.transient(win)
    viewer.grab_set()
    viewer.resizable(False, False)
    viewer.geometry("600x380")
    viewer.configure(bg=_T.get("header_bg", "#3f271d"))
    push_window(viewer, win)

    tk.Label(
        viewer,
        text="INS Transactions Added This Session",
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
        height=14,
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
            ("Policy", rec.get("ins_label")),
            ("Date", rec.get("ins_trans_dt")),
            ("Desc", rec.get("ins_description")),
            ("Premium Paid", f"{rec.get('premium_paid', 0.0):,.2f}"),
            ("Payout Received", f"{rec.get('payout_received', 0.0):,.2f}"),
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


def add_ins_transaction_main(
    parent: Union[tk.Toplevel, tk.Tk], calling_button: tk.Widget | None = None
) -> None:
    ins_map = {}

    def _refresh_ins_combo():
        ins_map.clear()
        masters = get_all_ins_masters_for_display()
        for m in masters:
            ins_map[m["display_label"]] = m
        if "ins_combo" in locals():
            ins_combo["values"] = list(ins_map.keys())
            progressive_selection(ins_combo, list(ins_map.keys()))

    _refresh_ins_combo()

    disable_parent(parent, calling_button=calling_button)
    session_records: list = []

    win = tk.Toplevel(parent)
    win.title("\U0001f4b8 Add INS Transaction \U0001f4b8")
    win.geometry("960x600")
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
        text="\U0001f4b8  Add INS Transaction  \U0001f4b8",
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

    _C_INS = _T.get("band_1_bg", "#78350f")
    _C_DATE = _T.get("band_2_bg", "#92400e")
    _C_AMT = _T.get("band_3_bg", "#b45309")

    form_body = tk.Frame(win, bg=_T.get("main_bg", "#593122"))
    form_body.pack(fill="x", padx=12, pady=6)

    # Band 1: INS Master
    ins_band, ins_lrow, ins_erow = _make_band(form_body, _C_INS)
    ins_band.pack(fill="x", pady=(0, 5))
    _band_label(ins_lrow, "Insurance Policy Master", _C_INS, _F)

    ins_combo = ttk.Combobox(
        ins_erow, width=55, values=list(ins_map.keys()), font=_F
    )
    ins_combo.pack(side="left", padx=(0, 8))
    apply_entry_theme(ins_combo)
    progressive_selection(ins_combo, list(ins_map.keys()))

    def on_ins_focus_out(_event=None):
        try:
            if not win.winfo_exists():
                return
        except (tk.TclError, NameError):
            return
        typed = ins_combo.get().strip()
        if not typed:
            return
        if typed not in ins_map:
            if show_colorful_yesno(
                win, "Not Found", f"'{typed}' not found. Add new?"
            ):
                _add_ins(win)
                _refresh_ins_combo()
                ins_combo.focus_set()
            else:
                flash_error(ins_combo)
                ins_combo.focus_set()

    ins_combo.bind("<FocusOut>", on_ins_focus_out, add="+")
    if ins_map:
        ins_combo.set(next(iter(ins_map)))

    # Band 2: Date + Description
    dt_band, dt_lrow, dt_erow = _make_band(form_body, _C_DATE)
    dt_band.pack(fill="x", pady=(0, 5))
    _band_label(dt_lrow, "Date", _C_DATE, _F)
    _band_label(dt_lrow, "Description", _C_DATE, _F, padx=120)

    trans_dt = DateEntry(dt_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    trans_dt.pack(side="left", padx=(0, 8))
    apply_entry_theme(trans_dt)
    bind_date_spin(trans_dt)

    desc_entry = tk.Entry(dt_erow, width=32, font=_FB)
    desc_entry.pack(side="left", padx=(30, 0))
    apply_entry_theme(desc_entry)

    # Band 3: Premium + Payout
    amt_band, amt_lrow, amt_erow = _make_band(form_body, _C_AMT)
    amt_band.pack(fill="x", pady=(0, 5))
    _band_label(amt_lrow, "Premium Paid (\u20b9)", _C_AMT, _F)
    _band_label(amt_lrow, "Payout Received (\u20b9)", _C_AMT, _F, padx=60)

    prem_entry = tk.Entry(amt_erow, width=18, font=_FB)
    prem_entry.pack(side="left", padx=(0, 8))
    apply_entry_theme(prem_entry)
    prem_entry.insert(0, "0.0")

    payout_entry = tk.Entry(amt_erow, width=18, font=_FB)
    payout_entry.pack(side="left", padx=(78, 0))
    apply_entry_theme(payout_entry)
    payout_entry.insert(0, "0.0")

    session_count_var = tk.StringVar(value="Session: 0 saved")
    tk.Label(
        win,
        textvariable=session_count_var,
        font=("Helvetica", 11, "italic"),
        bg=_T.get("main_bg", "#593122"),
        fg="#fed7aa",
    ).pack(anchor="e", padx=16)

    btn_frame = tk.Frame(win, bg=_T.get("main_bg", "#593122"))
    btn_frame.pack(pady=8)

    def _reset_form():
        import datetime

        trans_dt.set_date(datetime.date.today())
        desc_entry.delete(0, "end")
        prem_entry.delete(0, "end")
        prem_entry.insert(0, "0.0")
        payout_entry.delete(0, "end")
        payout_entry.insert(0, "0.0")
        ins_combo.focus_set()

    def _validate_and_save():
        lbl = ins_combo.get()
        if not lbl or lbl not in ins_map:
            flash_error(ins_combo)
            show_colorful_error(
                win, "Error", "Select a valid Insurance Policy."
            )
            return

        master_info = ins_map[lbl]

        try:
            t_date = trans_dt.get_date()
        except Exception:
            show_colorful_error(win, "Error", "Invalid date.")
            return

        desc = desc_entry.get().strip()

        try:
            prem = float(prem_entry.get().strip().replace(",", "") or 0)
            pay = float(payout_entry.get().strip().replace(",", "") or 0)
        except ValueError:
            show_colorful_error(win, "Error", "Amounts must be valid numbers.")
            return

        data = {
            "ins_master_id": master_info["ins_master_id"],
            "account_id": master_info["account_id"],
            "ins_trans_dt": t_date.strftime("%Y-%m-%d"),
            "ins_description": desc,
            "premium_paid": prem,
            "payout_received": pay,
        }

        try:
            tid = _db_add_ins_transaction(data)
        except Exception as exc:
            show_colorful_error(win, "Database Error", str(exc))
            return

        session_records.append({**data, "ins_trans_id": tid, "ins_label": lbl})
        session_count_var.set(f"Session: {len(session_records)} saved")
        _yes = show_colorful_yesno(
            win,
            "Success",
            f"Transaction saved (ID {tid})."
            + "\n\nDo you want to add another record?",
        )
        if not _yes:

            cleanup_and_close()

            return
        _reset_form()

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

    ins_combo.bind("<Return>", _focus_next(trans_dt))
    trans_dt.bind("<Return>", _focus_next(desc_entry))
    desc_entry.bind("<Return>", _focus_next(prem_entry))
    prem_entry.bind("<Return>", _focus_next(payout_entry))
    payout_entry.bind("<Return>", lambda _e: _validate_and_save())

    ins_combo.focus_set()
    parent.wait_window(win)
