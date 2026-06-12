# -*- coding: utf-8 -*-
# C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\BankMan\rewards_points_add.py

"""
Module for adding Credit Card Rewards Points (rewards_points table).

Structural pattern:
  - F1 = Help, F2 = Session viewer, Escape = close without saving
  - Yellow-on-black entry theme via centrally defined apply_entry_theme()
  - Distinct deep-indigo / gold window theme (REWARDS_ADD_UI_THEME)
"""

from datetime import timedelta as _timedelta
from typing import Union
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from tkcalendar import DateEntry

from Shared.gui_utils import (
    apply_entry_theme,
    bind_tooltip,
    setup_footer_tooltip,
    flash_error,
    REWARDS_ADD_UI_THEME,
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
from .bank_db_utils import (
    get_all_card_masters,
    db_add_rewards_points,
)

# ── Help / Session Viewers ─────────────────────────────────────────────


def show_master_help(parent_win, escape_callback):
    """Displays the F1 Help window for Rewards Points Entry."""
    help_win = tk.Toplevel(parent_win)
    help_win.title("Rewards Points Entry - Help (F1)")
    help_win.geometry("650x400")
    help_win.configure(bg="#2e1065")
    push_window(help_win, parent_win)

    def _close(_e=None):
        safe_close_modal(help_win, parent_win)

    help_win.bind("<Escape>", _close)
    help_win.bind("<F1>", _close)
    help_win.protocol("WM_DELETE_WINDOW", _close)

    text_w = tk.Text(
        help_win,
        wrap="word",
        bg="#1e1b4b",
        fg="#e0e7ff",
        font=("Helvetica", 11),
        padx=15,
        pady=15,
        relief="flat",
    )
    text_w.pack(fill="both", expand=True, padx=10, pady=10)

    lines = [
        "Rewards Points Entry Guide\n",
        "This module tracks credit card loyalty points at the STATEMENT "
        "level. Do not enter points per-transaction.\n",
        "Fields:",
        "  Card           — Select the specific physical credit card.",
        "  Statement Date — The date printed on the generated bill.",
        "  Points Earned  — Total points earned in this billing cycle.",
        "  Points Redeemed— Points used for statement credit or rewards.\n",
        "Note: You do not need to calculate the running balance. The "
        "background automation script will calculate the current balance for "
        "you, even if statements are entered out of chronological order.\n",
        "Hotkeys:",
        "  <F1>     : Show/Hide this help.",
        "  <F2>     : Show current session entries.",
        "  <Up/Down>: Change the Statement Date by one day.",
        "  <Enter>  : Move to next field or Save.",
        "  <Escape> : Close the main window.",
    ]
    text_w.insert("1.0", "\n".join(lines))
    text_w.config(state="disabled")


def show_session_transactions(parent_win, records, escape_callback):
    """Displays the F2 Session Viewer."""
    if not records:
        show_colorful_info(
            parent_win, "Session Empty", "No points entered yet in this session."
        )
        return

    view_win = tk.Toplevel(parent_win)
    view_win.title("Current Session Rewards (F2)")
    view_win.geometry("650x300")
    view_win.configure(bg="#2e1065")
    push_window(view_win, parent_win)

    def _close(_e=None):
        safe_close_modal(view_win, parent_win)

    view_win.bind("<Escape>", _close)
    view_win.bind("<F2>", _close)
    view_win.protocol("WM_DELETE_WINDOW", _close)

    tree_frame = tk.Frame(view_win, bg="#1e1b4b", bd=2, relief="groove")
    tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

    cols = ("card", "date", "earned", "redeemed")
    tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8)
    tree.heading("card", text="Card Master")
    tree.heading("date", text="Statement Dt")
    tree.heading("earned", text="Earned")
    tree.heading("redeemed", text="Redeemed")

    tree.column("card", width=200, anchor="w")
    tree.column("date", width=100, anchor="center")
    tree.column("earned", width=100, anchor="e")
    tree.column("redeemed", width=100, anchor="e")

    for idx, rec in enumerate(records):
        tag = "even" if idx % 2 == 0 else "odd"
        tree.insert(
            "",
            "end",
            values=(
                rec.get("card_name", ""),
                rec.get("statement_dt", ""),
                rec.get("points_earned", 0),
                rec.get("points_redeemed", 0),
            ),
            tags=(tag,),
        )

    tree.tag_configure("even", background="#1e1b4b", foreground="#fde047")
    tree.tag_configure("odd", background="#312e81", foreground="#fde047")
    tree.pack(side="left", fill="both", expand=True)


# ── Main UI ─────────────────────────────────────────────────────────────


def add_rewards_points_main(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Launch the Rewards Points Entry dialog."""

    card_masters = get_all_card_masters()  # noqa: F841
    # Build dropdown mapping: "CardName : [CardNumber]" -> (card_master_id, account_id)
    card_map = {f"{row[2]} : [{row[3]}]": (row[0], row[1]) for row in card_masters}

    _T = REWARDS_ADD_UI_THEME
    _F = ("Helvetica", 12)
    _FB = ("Helvetica", 12, "bold")

    session_records = []
    _state = {"card_master_id": None, "account_id": None}

    # ── Window Setup ──
    modal_id = disable_parent(parent)
    win = tk.Toplevel(parent)
    win.title("Rewards Points Entry")
    win.geometry("750x450")
    win.configure(bg=_T["main_bg"])
    win.resizable(False, False)
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    push_window(win, parent)

    # Center window
    win.update_idletasks()
    x = (win.winfo_screenwidth() // 2) - (750 // 2)
    y = (win.winfo_screenheight() // 2) - (450 // 2)
    win.geometry(f"+{x}+{y}")

    def cleanup_and_close(_event=None):
        safe_close_modal(win, parent)
        if calling_button:
            calling_button.focus_set()

    win.protocol("WM_DELETE_WINDOW", cleanup_and_close)
    win.bind("<Escape>", cleanup_and_close)

    # ── Header ──
    hdr = tk.Label(
        win,
        text="Rewards Points Entry (Statement Level)",
        font=("Helvetica", 16, "bold"),
        bg=_T["header_bg"],
        fg=_T["header_fg"],
        pady=12,
    )
    hdr.pack(fill="x")

    main_frame = tk.Frame(win, bg=_T["main_bg"])
    main_frame.pack(fill="both", expand=True, padx=20, pady=15)

    def _make_band(parent_frame, bg_color):
        band = tk.Frame(parent_frame, bg=bg_color, bd=1, relief="ridge")
        band.pack(fill="x", pady=6)
        l_row = tk.Frame(band, bg=bg_color)
        l_row.pack(fill="x", padx=10, pady=(8, 2))
        e_row = tk.Frame(band, bg=bg_color)
        e_row.pack(fill="x", padx=10, pady=(0, 10))
        return l_row, e_row

    def _band_label(parent_frame, text, bg_color, font, width=None, padx=0):
        lbl = tk.Label(
            parent_frame,
            text=text,
            bg=bg_color,
            fg=_T["text_fg"],
            font=font,
            anchor="w",
            width=width,
        )
        lbl.pack(side="left", padx=(padx, 0))
        return lbl

    # ── Band 1: Card Selection ──────────────────────────────────────────
    _C_MASTER = _T["band1_bg"]
    mst_lrow, mst_erow = _make_band(main_frame, _C_MASTER)

    _band_label(mst_lrow, "Credit Card*", _C_MASTER, _FB)

    card_var = tk.StringVar()
    card_combo = ttk.Combobox(
        mst_erow,
        textvariable=card_var,
        values=list(card_map.keys()),
        state="readonly",
        font=_F,
        width=35,
    )
    card_combo.pack(side="left")
    apply_entry_theme(card_combo)

    linked_acct_var = tk.StringVar(value="—")
    linked_acct_lbl = tk.Label(
        mst_erow,
        textvariable=linked_acct_var,
        font=_F,
        bg=_C_MASTER,
        fg="#a5b4fc",
        width=30,
        anchor="w",
    )
    linked_acct_lbl.pack(side="left", padx=(18, 0))

    def _on_card_change(_event=None):
        card_label = card_var.get()
        if card_label in card_map:
            cm_id, ac_id = card_map[card_label]
            _state["card_master_id"] = cm_id
            _state["account_id"] = ac_id
            linked_acct_var.set(f"Liability Acct ID: {ac_id}")

    card_combo.bind("<<ComboboxSelected>>", _on_card_change)

    if card_map:
        card_combo.set(list(card_map.keys())[0])
        _on_card_change()

    # ── Band 2: Statement Date & Points ─────────────────────────────────
    _C_PTS = _T["band2_bg"]
    pts_lrow, pts_erow = _make_band(main_frame, _C_PTS)

    _band_label(pts_lrow, "Statement Date*", _C_PTS, _FB)
    _band_label(pts_lrow, "Points Earned", _C_PTS, _F, padx=42)
    _band_label(pts_lrow, "Points Redeemed", _C_PTS, _F, padx=38)

    statement_dt = DateEntry(
        pts_erow,
        width=12,
        font=_F,
        background="darkblue",
        foreground="white",
        borderwidth=2,
        date_pattern="yyyy-mm-dd",
    )
    statement_dt.pack(side="left")
    apply_entry_theme(statement_dt)

    # Arrow Key Spinbox Feature for DateEntry
    bind_date_spin(statement_dt)

    pts_earned_spin = tk.Spinbox(pts_erow, from_=0, to=999999, width=12, font=_FB)
    pts_earned_spin.pack(side="left", padx=(42, 0))
    pts_earned_spin.delete(0, tk.END)
    pts_earned_spin.insert(0, "0")
    apply_entry_theme(pts_earned_spin)

    pts_redeemed_spin = tk.Spinbox(pts_erow, from_=0, to=999999, width=12, font=_FB)
    pts_redeemed_spin.pack(side="left", padx=(42, 0))
    pts_redeemed_spin.delete(0, tk.END)
    pts_redeemed_spin.insert(0, "0")
    apply_entry_theme(pts_redeemed_spin)

    # ── Tooltips & Footer ──
    tooltip_var = setup_footer_tooltip(
        win, bg_color=_T["footer_bg"], fg_color=_T["header_fg"]
    )

    bind_tooltip(
        statement_dt,
        tooltip_var,
        "The closing date printed on the credit card statement.",
    )
    bind_tooltip(
        pts_earned_spin,
        tooltip_var,
        "Total reward points earned in this billing cycle.",
    )
    bind_tooltip(
        pts_redeemed_spin,
        tooltip_var,
        "Points redeemed for statement credit or vouchers.",
    )

    # ── Actions ─────────────────────────────────────────────────────────

    def _reset_form():
        if card_map:
            card_combo.set(list(card_map.keys())[0])
            _on_card_change()
        statement_dt.set_date(
            statement_dt.get_date()
        )  # Keep current date for rapid entry
        pts_earned_spin.delete(0, tk.END)
        pts_earned_spin.insert(0, "0")
        pts_redeemed_spin.delete(0, tk.END)
        pts_redeemed_spin.insert(0, "0")
        card_combo.focus_set()

    def _validate_and_save():
        card_label = card_combo.get()
        if card_label not in card_map:
            show_colorful_error(
                win, "Validation Error", "Please select a valid Credit Card."
            )
            return

        dt = statement_dt.get()
        if not dt:
            show_colorful_error(win, "Validation Error", "Statement Date is required.")
            return

        try:
            earned_str = pts_earned_spin.get() or "0"
            earned = int(float(earned_str))
            redeemed_str = pts_redeemed_spin.get() or "0"
            redeemed = int(float(redeemed_str))
        except ValueError:
            show_colorful_error(
                win, "Validation Error", "Points must be whole numbers."
            )
            return

        cm_id, ac_id = card_map[card_label]

        data = {
            "account_id": ac_id,
            "card_master_id": cm_id,
            "statement_dt": dt,
            "points_earned": earned,
            "points_redeemed": redeemed,
        }

        try:
            reward_id = db_add_rewards_points(data)
            show_colorful_info(
                win, "Success", f"Rewards saved successfully (ID: {reward_id})."
            )

            # Log for session viewer
            session_records.append(
                {
                    "card_name": card_label,
                    "statement_dt": dt,
                    "points_earned": earned,
                    "points_redeemed": redeemed,
                }
            )
            _reset_form()

        except Exception as exc:
            flash_error(pts_earned_spin)
            msg = f"Failed to save rewards:\n{exc}"
            show_colorful_error(win, "Database Error", msg)

    # ── Hint bar ──
    hint_frame = tk.Frame(win, bg=_T["main_bg"], relief="ridge", bd=2)
    hint_frame.pack(fill="x", padx=10, pady=(0, 2))
    msg = "Press F1 for help, F2 for session rewards, Esc to close."
    tk.Label(
        hint_frame, text=msg, font=("Helvetica", 12), bg=_T["main_bg"], fg=_T["text_fg"]
    ).pack(side="left", padx=8)

    # ── Buttons ──
    btn_frame = tk.Frame(win, bg=_T["main_bg"])
    btn_frame.pack(fill="x", padx=20, pady=5)

    def _make_button(parent, text, command, bg_color, hover_bg):
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Helvetica", 13, "bold"),
            bg=bg_color,
            fg=_T["button_fg"],
            activeforeground=_T["button_fg"],
            padx=18,
            pady=6,
            cursor="hand2",
            relief="raised",
            bd=3,
        )
        btn.pack(side="right", padx=(12, 0))
        apply_button_animations(btn, bg_color, hover_bg)
        return btn

    save_btn = _make_button(
        btn_frame,
        "Save  [Enter]",
        _validate_and_save,
        _T["submit_bg"],
        _T["submit_hover_bg"],
    )
    _make_button(
        btn_frame, "Reset", _reset_form, "#831843", "#4c0519"
    )  # Dark indigo-red
    close_btn = tk.Button(
        btn_frame,
        text="Close  [Esc]",
        command=cleanup_and_close,
        font=("Helvetica", 13, "bold"),
        bg=_T["cancel_bg"],
        fg=_T["button_fg"],
        activeforeground=_T["button_fg"],
        padx=18,
        pady=6,
        cursor="hand2",
        relief="raised",
        bd=3,
    )
    close_btn.pack(side="left", padx=12)
    apply_button_animations(close_btn, _T["cancel_bg"], _T["cancel_hover_bg"])

    # ── Keyboard Navigation & Hotkeys ──
    def _focus_next(next_widget):
        def _handler(_event=None):
            next_widget.focus_set()
            return "break"

        return _handler

    card_combo.bind("<Return>", _focus_next(statement_dt))
    statement_dt.bind("<Return>", _focus_next(pts_earned_spin))
    pts_earned_spin.bind("<Return>", _focus_next(pts_redeemed_spin))
    pts_redeemed_spin.bind("<Return>", lambda _e: _validate_and_save())

    win.bind(
        "<Return>",
        lambda e: (
            _validate_and_save()
            if win.focus_get() in (pts_redeemed_spin, save_btn)
            else None
        ),
    )

    win.bind("<F1>", lambda e: show_master_help(win, cleanup_and_close))
    win.bind(
        "<F2>",
        lambda e: show_session_transactions(win, session_records, cleanup_and_close),
    )

    # Start focus on the Credit Card dropdown.
    if card_map:
        card_combo.focus_set()
