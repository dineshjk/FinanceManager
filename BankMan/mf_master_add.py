# -*- coding: utf-8 -*-
# BankMan/mf_master_add.py

"""
Module for adding new Mutual Fund master records (mf_master table).
"""

from typing import Union
import tkinter as tk
from tkinter import ttk

from Shared.gui_utils import (
    apply_entry_theme,
    bind_tooltip,
    setup_footer_tooltip,
    flash_error,
    MF_MASTER_ADD_UI_THEME,
    apply_button_animations,
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
    db_add_mf_master as _db_add_mf_master,
    get_distinct_mf_amc_names,
    get_distinct_mf_rta_names,
    get_distinct_mf_folio_numbers,
)

_DEFAULT_RTAS = ["CAMS", "KFintech", "Franklin", "Sundaram", "Others"]


def _get_combined_rta_names() -> list[str]:
    """Combine distinct RTA names from database with standard default RTAs."""
    db_rtas = get_distinct_mf_rta_names()
    seen = set()
    combined = []
    for rta in db_rtas + _DEFAULT_RTAS:
        if rta and rta not in seen:
            seen.add(rta)
            combined.append(rta)
    return combined
from Shared.globals import logger
from Shared.gui_progressive import progressive_selection
from .accounts_add import add_account_main as _add_account

# ---------------------------------------------------------------------------
# Theme alias
# ---------------------------------------------------------------------------
_T = MF_MASTER_ADD_UI_THEME

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
        "This form registers a new Mutual Fund master record.",
        "",
        "Fields:",
        "• Linked Account: The bank account linked for dividends or redemptions.",
        "• AMC Name: Asset Management Company (e.g., SBI Mutual Fund).",
        "• RTA Name: Registrar & Transfer Agent (e.g., CAMS, KFintech).",
        "• Folio Number: Your folio number for this fund.",
        "• Scheme Name: Name of the MF scheme.",
        "• Active: Tick to indicate the folio/scheme is active.",
        "",
        "Hotkeys: F2 (Session Viewer), Esc (Close), Ctrl+Enter (Save)",
    ]
    faq_data = [
        (
            "Q: Should I add different folios of the same AMC separately?",
            "A: Yes, each unique folio + scheme combination needs its own master entry.",
        )
    ]
    show_standard_help(win, "Add MF Master Help", guide_lines, faq_data)


# ---------------------------------------------------------------------------
# Session viewer (F2)
# ---------------------------------------------------------------------------


def _show_session_viewer(
    win: tk.Toplevel,
    session_entries: list,
    on_escape,
    on_save=None,
) -> None:
    """Show MF master records added in this session."""
    if not session_entries:
        try:
            show_colorful_info(
                win,
                "No Entries",
                "No MF master records have been added this session.",
            )
        except tk.TclError:
            pass
        return

    win.unbind("<Escape>")
    idx = {"i": 0}

    viewer = tk.Toplevel(win)
    viewer.title("Session — MF Masters Added")
    viewer.transient(win)
    viewer.grab_set()
    viewer.resizable(False, False)
    viewer.geometry("580x360")
    viewer.configure(bg=_T.get("header_bg", "#1e1b4b"))
    push_window(viewer, win)
    try:
        viewer.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        viewer,
        text="MF Masters Added This Session",
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
    apply_button_animations(
        left_btn,
        _T.get("session_btn_bg", _T.get("button_bg", "#374151")),
        _T.get("session_btn_hover_bg", "#4b5563"),
    )
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
        height=12,
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
            ("Linked Account", rec.get("account_label")),
            ("AMC Name", rec.get("amc_name")),
            ("RTA Name", rec.get("rta_name")),
            ("Folio Number", rec.get("folio_number")),
            ("Scheme Name", rec.get("scheme_name")),
            ("Is Active", "Yes" if rec.get("is_active") else "No"),
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
        win.bind(
            "<Control-Return>",
            (lambda _e: on_save()) if on_save else (lambda _e: None),
        )
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


def add_mf_master_main(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Launch the Add MF Master dialog."""

    # ── Lookup data ───────────────────────────────────────────────────────
    accounts = get_all_accounts()
    # Display: "BankName : [AC_Number]"  →  ac_id
    account_map = {f"{a[1]} : [{a[3]}]": a[0] for a in accounts}

    # ── Window setup ──────────────────────────────────────────────────────
    disable_parent(parent, calling_button=calling_button)
    session_records: list = []

    win = tk.Toplevel(parent)
    win.title("\U0001f4c8 Add MF Master \U0001f4c8")
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
        lambda e: _show_session_viewer(
            win, session_records, on_escape, on_save=_validate_and_save
        ),
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
        text="\U0001f4c8  Add MF Master  \U0001f4c8",
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

    _C_ACCT = _T.get("band_1_bg", "#3730a3")
    _C_AMC = _T.get("band_2_bg", "#4338ca")
    _C_FOLIO = _T.get("band_3_bg", "#4f46e5")

    form_body = tk.Frame(win, bg=_T.get("main_bg", "#312e81"))
    form_body.pack(fill="x", padx=12, pady=6)

    # ── Band 1: Linked Account ───────────────────────────────
    acct_band, acct_lrow, acct_erow = _make_band(form_body, _C_ACCT)
    acct_band.pack(fill="x", pady=(0, 5))

    _band_label(acct_lrow, "Linked Bank Account", _C_ACCT, _F)

    account_combo = ttk.Combobox(
        acct_erow,
        width=40,
        values=list(account_map.keys()),
        font=_F,
    )
    account_combo.pack(side="left", padx=(0, 8))
    apply_entry_theme(account_combo)
    progressive_selection(account_combo, list(account_map.keys()))
    bind_tooltip(
        account_combo,
        tooltip_var,
        "The bank account used for redemptions and dividend credits.",
    )

    def _refresh_account_combo():
        new_accounts = get_all_accounts()
        account_map.clear()
        account_map.update({f"{a[1]} : [{a[3]}]": a[0] for a in new_accounts})
        account_combo["values"] = list(account_map.keys())
        progressive_selection(account_combo, list(account_map.keys()))

    def on_account_focus_out(_event=None):
        try:
            if not win.winfo_exists():
                return
        except (tk.TclError, NameError):
            return
        typed = account_combo.get().strip()
        if not typed:
            return
        if typed not in account_map:
            response = show_colorful_yesno(
                win,
                "Account Not Found",
                f"'{typed}' was not found. Add a new bank account now?",
            )
            if response:
                _add_account(win)
                _refresh_account_combo()
                account_combo.focus_set()
            else:
                show_colorful_error(
                    win,
                    "Invalid Selection",
                    "Please select a valid account from the list.",
                )
                flash_error(account_combo)
                account_combo.focus_set()

    account_combo.bind("<FocusOut>", on_account_focus_out, add="+")

    if account_map:
        account_combo.set(next(iter(account_map)))

    # ── Lookup distinct values from DB ──────────────────────────────────
    amc_values = get_distinct_mf_amc_names()
    rta_values = _get_combined_rta_names()
    folio_values = get_distinct_mf_folio_numbers()

    # ── Band 2: AMC + RTA ─────────────────────
    amc_band, amc_lrow, amc_erow = _make_band(form_body, _C_AMC)
    amc_band.pack(fill="x", pady=(0, 5))

    _band_label(amc_lrow, "AMC Name", _C_AMC, _F)
    _band_label(amc_lrow, "RTA Name", _C_AMC, _F, padx=160)

    amc_combo = ttk.Combobox(
        amc_erow,
        width=28,
        values=amc_values,
        font=_FB,
    )
    amc_combo.pack(side="left", padx=(0, 8))
    apply_entry_theme(amc_combo)
    progressive_selection(amc_combo, amc_values)
    bind_tooltip(
        amc_combo,
        tooltip_var,
        "Asset Management Company (e.g., SBI Mutual Fund, HDFC Mutual Fund)",
    )

    rta_combo = ttk.Combobox(
        amc_erow,
        width=20,
        values=rta_values,
        font=_FB,
    )
    rta_combo.pack(side="left", padx=(18, 8))
    apply_entry_theme(rta_combo)
    progressive_selection(rta_combo, rta_values)
    bind_tooltip(rta_combo, tooltip_var, "Registrar & Transfer Agent")
    rta_combo.set("CAMS" if "CAMS" in rta_values else (rta_values[0] if rta_values else ""))

    # ── Band 3: Folio + Scheme + Active ────────────────────────────────
    folio_band, folio_lrow, folio_erow = _make_band(form_body, _C_FOLIO)
    folio_band.pack(fill="x", pady=(0, 5))

    _band_label(folio_lrow, "Folio Number", _C_FOLIO, _F)
    _band_label(folio_lrow, "Scheme Name", _C_FOLIO, _F, padx=60)
    _band_label(folio_lrow, "Is Active", _C_FOLIO, _F, padx=220)

    folio_combo = ttk.Combobox(
        folio_erow,
        width=18,
        values=folio_values,
        font=_FB,
    )
    folio_combo.pack(side="left", padx=(0, 8))
    apply_entry_theme(folio_combo)
    progressive_selection(folio_combo, folio_values)
    bind_tooltip(
        folio_combo, tooltip_var, "Your folio number for this scheme."
    )

    scheme_entry = tk.Entry(folio_erow, width=35, font=_FB)
    scheme_entry.pack(side="left", padx=(18, 0))
    apply_entry_theme(scheme_entry)
    bind_tooltip(scheme_entry, tooltip_var, "Name of the Mutual Fund scheme.")

    is_active_var = tk.BooleanVar(value=True)
    is_active_cb = tk.Checkbutton(
        folio_erow,
        variable=is_active_var,
        text="Active",
        font=_F,
        bg=_C_FOLIO,
        fg=_T.get("label_fg", "gold"),
        selectcolor="#001a50",
        activebackground=_C_FOLIO,
        activeforeground=_T.get("label_fg", "gold"),
    )
    is_active_cb.pack(side="left", padx=(25, 0))
    bind_tooltip(
        is_active_cb,
        tooltip_var,
        "Tick = Scheme is currently active.",
    )

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

    def _refresh_combos():
        cur_amc_vals = get_distinct_mf_amc_names()
        cur_rta_vals = _get_combined_rta_names()
        cur_folio_vals = get_distinct_mf_folio_numbers()

        amc_combo["values"] = cur_amc_vals
        progressive_selection(amc_combo, cur_amc_vals)

        rta_combo["values"] = cur_rta_vals
        progressive_selection(rta_combo, cur_rta_vals)

        folio_combo["values"] = cur_folio_vals
        progressive_selection(folio_combo, cur_folio_vals)

    def _reset_form():
        _refresh_combos()
        amc_combo.set("")
        rta_combo.set("CAMS" if "CAMS" in rta_combo["values"] else (rta_combo["values"][0] if rta_combo["values"] else ""))
        folio_combo.set("")
        scheme_entry.delete(0, "end")
        is_active_var.set(True)
        amc_combo.focus_set()

    def _validate_and_save():
        # Account
        acct_label = account_combo.get()
        if not acct_label or acct_label not in account_map:
            flash_error(account_combo)
            show_colorful_error(
                win, "Validation Error", "Please select a linked bank account."
            )
            return

        # AMC
        amc = amc_combo.get().strip()
        if not amc:
            flash_error(amc_combo)
            show_colorful_error(
                win, "Validation Error", "AMC Name cannot be blank."
            )
            return

        rta = rta_combo.get().strip()
        if not rta:
            flash_error(rta_combo)
            show_colorful_error(
                win, "Validation Error", "RTA Name cannot be blank."
            )
            return

        folio = folio_combo.get().strip()
        if not folio:
            flash_error(folio_combo)
            show_colorful_error(
                win, "Validation Error", "Folio Number cannot be blank."
            )
            return

        scheme = scheme_entry.get().strip()
        if not scheme:
            flash_error(scheme_entry)
            show_colorful_error(
                win, "Validation Error", "Scheme Name cannot be blank."
            )
            return

        data = {
            "account_id": account_map[acct_label],
            "amc_name": amc,
            "rta_name": rta,
            "folio_number": folio,
            "scheme_name": scheme,
            "is_active": 1 if is_active_var.get() else 0,
        }

        try:
            mf_master_id = _db_add_mf_master(data)
        except Exception as exc:  # noqa: BLE001
            logger.error("add_mf_master failed: %s", exc)
            msg = f"Failed to save MF master:\n{exc}"
            show_colorful_error(win, "Database Error", msg)
            return

        session_records.append(
            {
                **data,
                "mf_master_id": mf_master_id,
                "account_label": acct_label,
            }
        )
        session_count_var.set(f"Session: {len(session_records)} saved")

        # Save to parent for callback
        setattr(parent, "last_added_mf_id", mf_master_id)

        yes = show_colorful_yesno(
            win,
            "Saved",
            f"MF Master saved (ID {mf_master_id}).\n\nDo you want to add another record?",
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

    account_combo.bind("<Return>", _focus_next(amc_combo))
    amc_combo.bind("<Return>", _focus_next(rta_combo))
    rta_combo.bind("<Return>", _focus_next(folio_combo))
    folio_combo.bind("<Return>", _focus_next(scheme_entry))
    scheme_entry.bind("<Return>", lambda _e: _validate_and_save())
    win.bind("<Control-Return>", lambda _e: _validate_and_save())

    # ── Modal wait ────────────────────────────────────────────────────────
    account_combo.focus_set()
    parent.wait_window(win)
