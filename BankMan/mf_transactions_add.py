# -*- coding: utf-8 -*-
# BankMan/mf_transactions_add.py

"""
Module for adding Mutual Fund transaction records (mf_transactions table).
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
    MF_TRANS_ADD_UI_THEME,
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
    get_all_mf_masters_for_display,
    db_add_mf_transaction as _db_add_mf_transaction,
)
from Shared.globals import logger
from Shared.gui_progressive import progressive_selection
from .mf_master_add import add_mf_master_main as _add_mf

# ---------------------------------------------------------------------------
# Theme alias
# ---------------------------------------------------------------------------
_T = MF_TRANS_ADD_UI_THEME

# ---------------------------------------------------------------------------
# Band / label helpers
# ---------------------------------------------------------------------------


def _make_band(container, bg, relief="ridge", padx=10, pady=6):
    """Create a coloured section band with stacked label_row / entry_row."""
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


def _band_label(parent, text, bg, font=("Helvetica", 14), padx=0):
    """Pack a gold field label into a band label_row."""
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
        "This form records events that happen within a Mutual Fund scheme.",
        "",
        "Fields:",
        "• MF Master: Select the mutual fund scheme/folio.",
        "• Date: Transaction date.",
        "• Description: Note/Description of the transaction.",
        "• Purchase (\u20b9): Amount invested.",
        "• Redemption (\u20b9): Amount withdrawn.",
        "• Units: Number of units allotted or redeemed.",
        "• NAV: Net Asset Value per unit at the time of transaction.",
        "",
        "Hotkeys: F2 (Session Viewer), Esc (Close), Ctrl+Enter (Save)",
    ]
    faq_data = [
        (
            "Q: Does this update my bank account balance?",
            "A: No, use Data Entry -> Bank if you need to log money leaving or entering your bank account.",
        )
    ]
    show_standard_help(win, "Add MF Transaction Help", guide_lines, faq_data)


# ---------------------------------------------------------------------------
# Session viewer (F2)
# ---------------------------------------------------------------------------


def _show_session_viewer(
    win: tk.Toplevel,
    session_entries: list,
    on_escape,
) -> None:
    """Show MF transactions added in this session."""
    if not session_entries:
        try:
            show_colorful_info(
                win,
                "No Entries",
                "No MF transactions have been added this session.",
            )
        except tk.TclError:
            pass
        return

    win.unbind("<Escape>")
    idx = {"i": 0}

    viewer = tk.Toplevel(win)
    viewer.title("Session — MF Transactions Added")
    viewer.transient(win)
    viewer.grab_set()
    viewer.resizable(False, False)
    viewer.geometry("600x380")
    viewer.configure(bg=_T.get("header_bg", "#1e1b4b"))
    push_window(viewer, win)
    try:
        viewer.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        viewer,
        text="MF Transactions Added This Session",
        font=("Helvetica", 14, "bold"),
        bg=_T.get("header_bg", "#1e1b4b"),
        fg=_T.get("header_fg", "#fbbf24"),
        pady=6,
    ).pack(fill="x")

    content = tk.Frame(viewer, bg=_T.get("header_bg", "#1e1b4b"))
    content.pack(fill="both", expand=True, padx=10, pady=6)

    left_btn = tk.Button(
        content,
        text="\u25c4",
        width=3,
        bg=_T.get("session_btn_bg", _T.get("button_bg", "#374151")),
        fg=_T.get("button_fg", "white"),
        activeforeground=_T.get("button_fg", "white"),
        cursor="hand2",
    )
    left_btn.pack(side="left", padx=(6, 4), pady=6)
    right_btn = tk.Button(
        content,
        text="\u25ba",
        width=3,
        bg=_T.get("session_btn_bg", _T.get("button_bg", "#374151")),
        fg=_T.get("button_fg", "white"),
        activeforeground=_T.get("button_fg", "white"),
        cursor="hand2",
    )
    right_btn.pack(side="right", padx=(4, 6), pady=6)
    apply_button_animations(
        right_btn,
        _T.get("session_btn_bg", _T.get("button_bg", "#374151")),
        _T.get("session_btn_hover_bg", "#4b5563"),
    )

    info_text = tk.Text(
        content,
        wrap="word",
        height=14,
        bg=_T.get("session_bg", _T.get("main_bg", "#312e81")),
        fg=_T.get("session_value_fg", _T.get("header_fg", "#fbbf24")),
        bd=0,
        relief="flat",
        font=("Helvetica", 11),
        insertbackground=_T.get(
            "session_value_fg", _T.get("header_fg", "#fbbf24")
        ),
    )
    info_text.pack(fill="both", expand=True, padx=6, pady=4)
    info_text.tag_configure(
        "label",
        font=("Helvetica", 11, "bold"),
        foreground=_T.get("session_label_fg", _T.get("header_fg", "#fbbf24")),
    )
    info_text.tag_configure(
        "value",
        font=("Helvetica", 11),
        foreground=_T.get("session_value_fg", "#93c5fd"),
    )
    info_text.config(state="disabled")

    status_label = tk.Label(
        content,
        text="",
        font=("Helvetica", 10, "bold"),
        bg=_T.get("session_bg", _T.get("header_bg", "#1e1b4b")),
        fg=_T.get("session_ok_fg", _T.get("header_fg", "#fbbf24")),
    )
    status_label.pack(side="bottom", pady=(0, 4))

    def _update_view():
        i = idx["i"]
        rec = session_entries[i]
        total = len(session_entries)
        info_text.config(state="normal")
        info_text.delete("1.0", "end")
        fields = [
            ("MF Master", rec.get("mf_label")),
            ("Trans Date", rec.get("mf_trans_dt")),
            ("Description", rec.get("mf_description")),
            ("Purchase (\u20b9)", f"{rec.get('mf_purchase', 0.0):,.2f}"),
            ("Redemption (\u20b9)", f"{rec.get('mf_redemption', 0.0):,.2f}"),
            ("Units", f"{rec.get('units', 0.0):,.4f}"),
            ("NAV (\u20b9)", f"{rec.get('nav', 0.0):,.4f}"),
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
        win.bind("<Control-Return>", lambda e: None)
        win.bind("<Escape>", on_escape)
        return "break"

    viewer.bind("<Control-Return>", lambda e: None)
    viewer.bind("<Escape>", _close_viewer)
    viewer.protocol("WM_DELETE_WINDOW", _close_viewer)
    viewer.bind("<Return>", _close_viewer)

    ok_btn = tk.Button(
        content,
        text="OK",
        width=10,
        command=_close_viewer,
        bg=_T.get("session_btn_bg", _T.get("button_bg", "#374151")),
        fg=_T.get("button_fg", "white"),
        activeforeground=_T.get("button_fg", "white"),
        font=("Helvetica", 11, "bold"),
        cursor="hand2",
    )
    ok_btn.pack(side="bottom", pady=(0, 6))
    apply_button_animations(
        ok_btn,
        _T.get("session_btn_bg", _T.get("button_bg", "#374151")),
        _T.get("session_btn_hover_bg", "#4b5563"),
    )
    try:
        ok_btn.focus_set()
    except tk.TclError:
        pass
    _update_view()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def add_mf_transaction_main(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Launch the Add MF Transaction dialog."""

    # ── Lookup data ───────────────────────────────────────────────────────
    # Store master info as: mf_map["Display Text"] = dict(mf_master_id=..., account_id=...)
    mf_map = {}

    def _refresh_mf_combo():
        mf_map.clear()
        masters = get_all_mf_masters_for_display()
        for m in masters:
            # m has mf_master_id, folio_number, scheme_name, ac_name, ac_number, display_label
            mf_map[m["display_label"]] = m
        if "mf_combo" in locals():
            mf_combo["values"] = list(mf_map.keys())
            progressive_selection(mf_combo, list(mf_map.keys()))

    _refresh_mf_combo()

    # ── Window setup ──────────────────────────────────────────────────────
    disable_parent(parent, calling_button=calling_button)
    session_records: list = []

    win = tk.Toplevel(parent)
    win.title("\U0001f4b8 Add MF Transaction \U0001f4b8")
    win.geometry("960x600")
    win.resizable(False, False)
    win.configure(bg=_T.get("main_bg", "#312e81"))
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    try:
        push_window(win, parent)
    except (RuntimeError, tk.TclError) as exc:
        logger.debug("push_window failed: %s", exc)

    # ── Footer tooltip ────────────────────────────────────────────────────
    tooltip_var = setup_footer_tooltip(
        win,
        bg_color=_T.get("header_bg", "#1e1b4b"),
        fg_color=_T.get("header_fg", "#fbbf24"),
    )

    # ── Closure helpers ───────────────────────────────────────────────────
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
        "<F2>",
        lambda e: _show_session_viewer(win, session_records, on_escape),
    )
    win.bind("<Control-Return>", lambda e: None)
    win.bind("<Escape>", on_escape)
    win.protocol("WM_DELETE_WINDOW", on_escape)

    # ── Header ────────────────────────────────────────────────────────────
    header_frame = tk.Frame(
        win, bg=_T.get("header_bg", "#1e1b4b"), relief="raised", bd=3
    )
    header_frame.pack(fill="x", padx=5, pady=0)
    tk.Label(
        header_frame,
        text="\U0001f4b8  Add MF Transaction  \U0001f4b8",
        font=("Helvetica", 18, "bold"),
        bg=_T.get("header_bg", "#1e1b4b"),
        fg=_T.get("header_fg", "#fbbf24"),
        relief="ridge",
        bd=2,
        pady=8,
    ).pack(fill="x")

    hint_frame = tk.Frame(win, bg=_T.get("main_bg", "#312e81"))
    hint_frame.pack(fill="x", padx=10, pady=(2, 0))
    for hint in ("F1: Help", "F2: Session Viewer", "Esc: Close"):
        tk.Label(
            hint_frame,
            text=hint,
            font=("Helvetica", 10, "italic"),
            bg=_T.get("main_bg", "#312e81"),
            fg="#93c5fd",
        ).pack(side="left", padx=12)

    # ── Form body ─────────────────────────────────────────────────────────
    _F = ("Helvetica", 14)
    _FB = ("Helvetica", 14, "bold")

    _C_MF = _T.get("band_1_bg", "#3730a3")
    _C_DATE = _T.get("band_2_bg", "#4338ca")
    _C_AMT = _T.get("band_3_bg", "#4f46e5")
    _C_UNITS = _T.get("band_4_bg", "#5a67d8")

    form_body = tk.Frame(win, bg=_T.get("main_bg", "#312e81"))
    form_body.pack(fill="x", padx=12, pady=6)

    # ── Band 1: MF Master ───────────────────────────────
    mf_band, mf_lrow, mf_erow = _make_band(form_body, _C_MF)
    mf_band.pack(fill="x", pady=(0, 5))

    _band_label(mf_lrow, "Mutual Fund Master", _C_MF, _F)

    mf_combo = ttk.Combobox(
        mf_erow,
        width=55,
        values=list(mf_map.keys()),
        font=_F,
    )
    mf_combo.pack(side="left", padx=(0, 8))
    apply_entry_theme(mf_combo)
    progressive_selection(mf_combo, list(mf_map.keys()))
    bind_tooltip(
        mf_combo,
        tooltip_var,
        "Select the folio/scheme for this transaction.",
    )

    def on_mf_focus_out(_event=None):
        try:
            if not win.winfo_exists():
                return
        except (tk.TclError, NameError):
            return
        typed = mf_combo.get().strip()
        if not typed:
            return
        if typed not in mf_map:
            response = show_colorful_yesno(
                win,
                "MF Master Not Found",
                f"'{typed}' was not found. Add a new MF master now?",
            )
            if response:
                _add_mf(win)
                _refresh_mf_combo()
                mf_combo.focus_set()
            else:
                show_colorful_error(
                    win,
                    "Invalid Selection",
                    "Please select a valid MF Master from the list.",
                )
                flash_error(mf_combo)
                mf_combo.focus_set()

    mf_combo.bind("<FocusOut>", on_mf_focus_out, add="+")

    if mf_map:
        mf_combo.set(next(iter(mf_map)))

    # ── Band 2: Date + Description ─────────────────────
    dt_band, dt_lrow, dt_erow = _make_band(form_body, _C_DATE)
    dt_band.pack(fill="x", pady=(0, 5))

    _band_label(dt_lrow, "Date", _C_DATE, _F)
    _band_label(dt_lrow, "Description", _C_DATE, _F, padx=120)

    trans_dt = DateEntry(dt_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    trans_dt.pack(side="left", padx=(0, 8))
    apply_entry_theme(trans_dt)
    bind_tooltip(trans_dt, tooltip_var, "Date of the transaction.")
    bind_date_spin(trans_dt)

    desc_entry = tk.Entry(dt_erow, width=32, font=_FB)
    desc_entry.pack(side="left", padx=(30, 0))
    apply_entry_theme(desc_entry)
    bind_tooltip(desc_entry, tooltip_var, "Short description or remark.")

    # ── Band 3: Purchase + Redemption ────────────────────────────────
    amt_band, amt_lrow, amt_erow = _make_band(form_body, _C_AMT)
    amt_band.pack(fill="x", pady=(0, 5))

    _band_label(amt_lrow, "Purchase Amount (\u20b9)", _C_AMT, _F)
    _band_label(amt_lrow, "Redemption Amount (\u20b9)", _C_AMT, _F, padx=60)

    pur_entry = tk.Entry(amt_erow, width=18, font=_FB)
    pur_entry.pack(side="left", padx=(0, 8))
    apply_entry_theme(pur_entry)
    pur_entry.insert(0, "0.0")
    bind_tooltip(pur_entry, tooltip_var, "Amount invested in \u20b9.")

    red_entry = tk.Entry(amt_erow, width=18, font=_FB)
    red_entry.pack(side="left", padx=(78, 0))
    apply_entry_theme(red_entry)
    red_entry.insert(0, "0.0")
    bind_tooltip(red_entry, tooltip_var, "Amount redeemed in \u20b9.")

    # ── Band 4: Units + NAV ────────────────────────────────
    units_band, units_lrow, units_erow = _make_band(form_body, _C_UNITS)
    units_band.pack(fill="x", pady=(0, 5))

    _band_label(units_lrow, "Units", _C_UNITS, _F)
    _band_label(units_lrow, "NAV (\u20b9)", _C_UNITS, _F, padx=160)

    units_entry = tk.Entry(units_erow, width=16, font=_FB)
    units_entry.pack(side="left", padx=(0, 8))
    apply_entry_theme(units_entry)
    units_entry.insert(0, "0.0")
    bind_tooltip(
        units_entry,
        tooltip_var,
        "Number of units allotted (positive) or redeemed (negative/positive).",
    )

    nav_entry = tk.Entry(units_erow, width=16, font=_FB)
    nav_entry.pack(side="left", padx=(80, 0))
    apply_entry_theme(nav_entry)
    nav_entry.insert(0, "0.0")
    bind_tooltip(nav_entry, tooltip_var, "Net Asset Value per unit.")

    # ── Session count label ───────────────────────────────────────────────
    session_count_var = tk.StringVar(value="Session: 0 saved")
    tk.Label(
        win,
        textvariable=session_count_var,
        font=("Helvetica", 11, "italic"),
        bg=_T.get("main_bg", "#312e81"),
        fg="#93c5fd",
    ).pack(anchor="e", padx=16)

    # ── Buttons row ───────────────────────────────────────────────────────
    btn_frame = tk.Frame(win, bg=_T.get("main_bg", "#312e81"))
    btn_frame.pack(pady=8)

    def _reset_form():
        import datetime

        trans_dt.set_date(datetime.date.today())
        desc_entry.delete(0, "end")
        pur_entry.delete(0, "end")
        pur_entry.insert(0, "0.0")
        red_entry.delete(0, "end")
        red_entry.insert(0, "0.0")
        units_entry.delete(0, "end")
        units_entry.insert(0, "0.0")
        nav_entry.delete(0, "end")
        nav_entry.insert(0, "0.0")
        mf_combo.focus_set()

    def _validate_and_save():
        # MF Master
        mf_label = mf_combo.get()
        if not mf_label or mf_label not in mf_map:
            flash_error(mf_combo)
            show_colorful_error(
                win, "Validation Error", "Please select a valid MF Master."
            )
            return

        master_info = mf_map[mf_label]

        # Dates
        try:
            t_date = trans_dt.get_date()
        except Exception:  # noqa: BLE001
            show_colorful_error(
                win,
                "Validation Error",
                "Please enter a valid transaction date.",
            )
            return

        desc = desc_entry.get().strip()

        try:
            purchase = float(pur_entry.get().strip().replace(",", "") or 0)
        except ValueError:
            flash_error(pur_entry)
            show_colorful_error(
                win, "Validation Error", "Purchase must be a valid number."
            )
            return

        try:
            redemption = float(red_entry.get().strip().replace(",", "") or 0)
        except ValueError:
            flash_error(red_entry)
            show_colorful_error(
                win, "Validation Error", "Redemption must be a valid number."
            )
            return

        try:
            units = float(units_entry.get().strip().replace(",", "") or 0)
        except ValueError:
            flash_error(units_entry)
            show_colorful_error(
                win, "Validation Error", "Units must be a valid number."
            )
            return

        try:
            nav = float(nav_entry.get().strip().replace(",", "") or 0)
        except ValueError:
            flash_error(nav_entry)
            show_colorful_error(
                win, "Validation Error", "NAV must be a valid number."
            )
            return

        data = {
            "mf_master_id": master_info["mf_master_id"],
            "account_id": master_info["account_id"],
            "mf_trans_dt": t_date.strftime("%Y-%m-%d"),
            "mf_description": desc,
            "mf_purchase": purchase,
            "mf_redemption": redemption,
            "units": units,
            "nav": nav,
        }

        try:
            mf_trans_id = _db_add_mf_transaction(data)
        except Exception as exc:  # noqa: BLE001
            logger.error("add_mf_transaction failed: %s", exc)
            msg = f"Failed to save MF transaction:\n{exc}"
            show_colorful_error(win, "Database Error", msg)
            return

        session_records.append(
            {
                **data,
                "mf_trans_id": mf_trans_id,
                "mf_label": mf_label,
            }
        )
        session_count_var.set(f"Session: {len(session_records)} saved")

        _yes = show_colorful_yesno(
            win,
            "Success",
            f"MF Transaction saved (ID {mf_trans_id})."
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
        bg=_T.get("submit_bg", _T.get("button_bg", "#10b981")),
        fg=_T.get("button_fg", "white"),
        activeforeground=_T.get("button_fg", "white"),
        padx=18,
        pady=6,
        cursor="hand2",
        relief="raised",
        bd=3,
    )
    save_btn.pack(side="left", padx=12)
    apply_button_animations(
        save_btn,
        _T.get("submit_bg", _T.get("button_bg", "#10b981")),
        _T.get("submit_hover_bg", "#059669"),
    )

    clear_btn = tk.Button(
        btn_frame,
        text="Clear",
        command=_reset_form,
        font=("Helvetica", 13, "bold"),
        bg=_T.get("cancel_bg", _T.get("button_bg", "#ef4444")),
        fg=_T.get("button_fg", "white"),
        activeforeground=_T.get("button_fg", "white"),
        padx=18,
        pady=6,
        cursor="hand2",
        relief="raised",
        bd=3,
    )
    clear_btn.pack(side="left", padx=12)
    apply_button_animations(
        clear_btn,
        _T.get("cancel_bg", _T.get("button_bg", "#ef4444")),
        _T.get("cancel_hover_bg", "#dc2626"),
    )

    cancel_btn = tk.Button(
        btn_frame,
        text="Cancel",
        command=cleanup_and_close,
        font=("Helvetica", 13, "bold"),
        bg=_T.get("cancel_bg", _T.get("button_bg", "#ef4444")),
        fg=_T.get("button_fg", "white"),
        activeforeground=_T.get("button_fg", "white"),
        padx=18,
        pady=6,
        cursor="hand2",
        relief="raised",
        bd=3,
    )
    cancel_btn.pack(side="left", padx=12)
    apply_button_animations(
        cancel_btn,
        _T.get("cancel_bg", _T.get("button_bg", "#ef4444")),
        _T.get("cancel_hover_bg", "#dc2626"),
    )

    # ── Return-key navigation ─────────────────────────────────────────────
    def _focus_next(w):
        def _h(_e=None):
            w.focus_set()
            return "break"

        return _h

    mf_combo.bind("<Return>", _focus_next(trans_dt))
    trans_dt.bind("<Return>", _focus_next(desc_entry))
    desc_entry.bind("<Return>", _focus_next(pur_entry))
    pur_entry.bind("<Return>", _focus_next(red_entry))
    red_entry.bind("<Return>", _focus_next(units_entry))
    units_entry.bind("<Return>", _focus_next(nav_entry))
    nav_entry.bind("<Return>", lambda _e: _validate_and_save())

    # ── Modal wait ────────────────────────────────────────────────────────
    mf_combo.focus_set()
    parent.wait_window(win)
