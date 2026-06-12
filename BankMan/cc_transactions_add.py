# -*- coding: utf-8 -*-
# C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\BankMan\cc_transactions_add.py

"""
Module for adding Credit Card transaction records (cc_transactions table).

Structural pattern from bank_transactions_add.py / ppf_transactions_add.py:
  - Coloured band frames, each with a label_row / entry_row
  - apply_entry_theme / bind_tooltip / setup_footer_tooltip from Shared.gui_utils
  - F1 = Help, F2 = Session viewer, Escape = close without saving
  - Yellow-on-black entry theme via centrally defined apply_entry_theme()
  - Distinct dark-teal window theme (CC_TRANS_ADD_UI_THEME)
"""

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
    CC_TRANS_ADD_UI_THEME,
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
    get_all_budget_heads,
    db_add_cc_transaction as _db_add_cc_transaction,
)
from Shared.globals import logger
from Shared.gui_progressive import progressive_selection
from .budget_head_add import add_account_type_main as _add_budget_head
from .cc_master_add import add_cc_master_main as _add_card

# ---------------------------------------------------------------------------
# Theme alias and constants
# ---------------------------------------------------------------------------
_T = CC_TRANS_ADD_UI_THEME

_TRANS_TYPES = ["EXPENSE", "PAYMENT", "CASHBACK", "REVERSAL"]
_DEFAULT_PARTY = {
    "EXPENSE": "",
    "PAYMENT": "Credit Card Bill Payment",
    "CASHBACK": "Cashback Credit",
    "REVERSAL": "Transaction Reversal",
}

# ---------------------------------------------------------------------------
# Band / label helpers (identical pattern to cc_master_add.py)
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
        fg=_T["label_fg"],
        anchor="w",
    ).pack(side="left", padx=(padx, 12))


# ---------------------------------------------------------------------------
# Help window (F1)
# ---------------------------------------------------------------------------


def _show_help(win: tk.Toplevel, on_escape) -> None:
    """Launch the Help sub-window for Add CC Transaction."""
    win.unbind("<Escape>")

    help_win = tk.Toplevel(win)
    try:
        help_win.transient(win)
    except (tk.TclError, AttributeError) as exc:
        logger.debug("help_win.transient failed: %s", exc)
    help_win.title("Help — Add CC Transaction")
    help_win.configure(bg=_T.get("help_bg", _T["main_bg"]))
    help_win.geometry("720x660")
    help_win.resizable(False, False)
    help_win.grab_set()
    push_window(help_win, win)
    try:
        help_win.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        help_win,
        text="Add CC Transaction  —  Help",
        font=("Helvetica", 16, "bold"),
        bg=_T.get("help_header_bg", _T["header_bg"]),
        fg=_T["header_fg"],
        pady=8,
    ).pack(fill="x")

    body = tk.Frame(help_win, bg=_T.get("help_bg", _T["main_bg"]), padx=12, pady=12)
    body.pack(fill="both", expand=True)

    text = tk.Text(
        body,
        wrap="word",
        bg=_T.get("help_bg", _T["main_bg"]),
        fg=_T.get("help_text_fg", _T.get("header_fg", "black")),
        bd=0,
        padx=6,
        pady=6,
        font=("Helvetica", 11),
        height=30,
        insertbackground=_T.get("help_text_fg", _T.get("header_fg", "black")),
    )
    text.pack(fill="both", expand=True)

    help_lines = [
        "\u2022 This form records a new entry in the cc_transactions table.",
        "",
        "Fields:",
        "  Credit Card      \u2014 Select the credit card from the dropdown.",
        "                     Only active cards are listed.",
        "  Linked Account   \u2014 Auto-filled from the selected card master.",
        "  Trans Date       \u2014 Date the transaction posted to the card " "account.",
        "  Party / Merchant \u2014 Merchant name or description",
        "                     (e.g. 'SWIGGY', 'AMAZON', 'Bill Payment').",
        "  Trans Type       \u2014 EXPENSE  : Purchase/charge on the card.",
        "                     PAYMENT  : Bill payment credited to the card.",
        "                     CASHBACK : Cashback or reward credit.",
        "                     REVERSAL : Merchant reversal / refund.",
        "  Expense (\u20b9)       \u2014 Amount charged (positive for EXPENSE rows).",
        "                     Leave 0 for PAYMENT / CASHBACK / REVERSAL.",
        "  CC Credit (\u20b9)     \u2014 Amount credited (positive for PAYMENT,",
        "                     CASHBACK, REVERSAL). Leave 0 for EXPENSE.",
        "",
        "Validation Rules:",
        "  \u2022 EXPENSE: Expense > 0 and CC Credit = 0.",
        "  \u2022 PAYMENT / CASHBACK / REVERSAL: CC Credit > 0 and Expense = 0.",
        "",
        "Hotkeys:",
        "  F1  : This help screen",
        "  F2  : Session viewer (transactions added this session)",
        "  Esc : Close without saving",
        "  Enter on last field : Submit",
    ]
    text.insert("1.0", "\n".join(help_lines))
    text.config(state="disabled")

    def close_help(_e=None):
        safe_close_modal(help_win, win)
        win.bind("<Escape>", on_escape)
        return "break"

    help_win.bind("<Escape>", close_help)
    help_win.protocol("WM_DELETE_WINDOW", close_help)

    help_close_btn = tk.Button(
        help_win,
        text="Close",
        command=close_help,
        font=("Helvetica", 11, "bold"),
        bg=_T.get("help_btn_bg", _T["button_bg"]),
        fg=_T.get("button_fg", "white"),
        activeforeground=_T.get("button_fg", "white"),
        padx=12,
        pady=6,
        cursor="hand2",
    )
    help_close_btn.pack(side="bottom", pady=10)
    apply_button_animations(
        help_close_btn,
        _T.get("help_btn_bg", _T["button_bg"]),
        _T.get("help_btn_hover_bg", "#115e59"),
    )


# ---------------------------------------------------------------------------
# Session viewer (F2)
# ---------------------------------------------------------------------------


def _show_session_viewer(
    win: tk.Toplevel,
    session_entries: list,
    on_escape,
) -> None:
    """Show CC transactions added in this session."""
    if not session_entries:
        try:
            show_colorful_info(
                win,
                "No Entries",
                "No CC transactions have been added this session.",
            )
        except tk.TclError:
            pass
        return

    win.unbind("<Escape>")
    idx = {"i": 0}

    viewer = tk.Toplevel(win)
    viewer.title("Session — CC Transactions Added")
    viewer.transient(win)
    viewer.grab_set()
    viewer.resizable(False, False)
    viewer.geometry("600x380")
    viewer.configure(bg=_T["header_bg"])
    push_window(viewer, win)
    try:
        viewer.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        viewer,
        text="CC Transactions Added This Session",
        font=("Helvetica", 14, "bold"),
        bg=_T["header_bg"],
        fg=_T["header_fg"],
        pady=6,
    ).pack(fill="x")

    content = tk.Frame(viewer, bg=_T["header_bg"])
    content.pack(fill="both", expand=True, padx=10, pady=6)

    left_btn = tk.Button(
        content,
        text="\u25c4",
        width=3,
        bg=_T["button_bg"],
        fg=_T["button_fg"],
    )
    left_btn.pack(side="left", padx=(6, 4), pady=6)
    right_btn = tk.Button(
        content,
        text="\u25ba",
        width=3,
        bg=_T["button_bg"],
        fg=_T["button_fg"],
    )
    right_btn.pack(side="right", padx=(4, 6), pady=6)

    info_text = tk.Text(
        content,
        wrap="word",
        height=14,
        bg=_T.get("session_bg", _T["main_bg"]),
        fg=_T.get("session_value_fg", _T["header_fg"]),
        bd=0,
        relief="flat",
        font=("Helvetica", 11),
        insertbackground=_T.get("session_value_fg", _T["header_fg"]),
    )
    info_text.pack(fill="both", expand=True, padx=6, pady=4)
    info_text.tag_configure(
        "label",
        font=("Helvetica", 11, "bold"),
        foreground=_T.get("session_label_fg", _T["header_fg"]),
    )
    info_text.tag_configure(
        "value",
        font=("Helvetica", 11),
        foreground=_T.get("session_value_fg", "#5eead4"),
    )
    info_text.config(state="disabled")

    status_label = tk.Label(
        content,
        text="",
        font=("Helvetica", 10, "bold"),
        bg=_T.get("session_bg", _T["header_bg"]),
        fg=_T.get("session_ok_fg", _T["header_fg"]),
    )
    status_label.pack(side="bottom", pady=(0, 4))

    def _update_view():
        i = idx["i"]
        rec = session_entries[i]
        total = len(session_entries)
        info_text.config(state="normal")
        info_text.delete("1.0", "end")
        fields = [
            ("Card", rec.get("card_label")),
            ("Trans Date", rec.get("cc_trans_dt")),
            ("Party / Merchant", rec.get("party")),
            ("Trans Type", rec.get("trans_type")),
            ("Expense (\u20b9)", f"{rec.get('expense', 0.0):,.2f}"),
            ("CC Credit (\u20b9)", f"{rec.get('cc_credit', 0.0):,.2f}"),
        ]
        for label, val in fields:
            info_text.insert("end", f"{label}: ", "label")
            info_text.insert("end", f"{val or chr(8212)}\n", "value")
        info_text.config(state="disabled")
        left_btn.config(state="disabled" if i == 0 else "normal")
        if i >= total - 1:
            right_btn.config(state="disabled")
            status_label.config(
                text="Last Entry", fg=_T.get("session_alert_fg", "#ef4444")
            )
        else:
            right_btn.config(state="normal")
            status_label.config(
                text=f"Entry {i + 1} of {total}",
                fg=_T.get("session_ok_fg", _T["header_fg"]),
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
        bg=_T.get("session_btn_bg", _T["button_bg"]),
        fg=_T.get("button_fg", "white"),
        activeforeground=_T.get("button_fg", "white"),
        font=("Helvetica", 11, "bold"),
        cursor="hand2",
    )
    ok_btn.pack(side="bottom", pady=(0, 6))
    apply_button_animations(
        ok_btn,
        _T.get("session_btn_bg", _T["button_bg"]),
        _T.get("session_btn_hover_bg", "#115e59"),
    )
    try:
        ok_btn.focus_set()
    except tk.TclError:
        pass
    _update_view()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def add_cc_transaction_main(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Launch the Add CC Transaction dialog."""

    # ── Lookup data ───────────────────────────────────────────────────────
    cards = get_all_card_masters()
    # Display: "CardName  [****XXXX]  [BankName]"  →  (card_master_id, account_id)
    card_map: dict[str, tuple[int, int]] = {}
    for row in cards:
        label = f"{row[1]}  [****{row[2][-4:]}]  [{row[4]}]"
        card_map[label] = (int(row[0]), int(row[3]))

    bh_rows = sorted(get_all_budget_heads(), key=lambda r: r[1])
    budget_map: dict[str, int] = {r[1]: r[0] for r in bh_rows}
    bh_type_map: dict[str, str] = {r[1]: r[2] for r in bh_rows}
    bh_values: list[str] = ["(none)"] + [r[1] for r in bh_rows]

    # Running state: selected card
    _state: dict = {"card_master_id": None, "account_id": None}

    # ── Window setup ──────────────────────────────────────────────────────
    disable_parent(parent, calling_button=calling_button)
    session_records: list = []

    win = tk.Toplevel(parent)
    win.title("\U0001f4b3 Add CC Transaction \U0001f4b3")
    win.geometry("1060x660")
    win.resizable(False, False)
    win.configure(bg=_T["main_bg"])
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    try:
        push_window(win, parent)
    except (RuntimeError, tk.TclError) as exc:
        logger.debug("push_window failed: %s", exc)

    # ── Footer tooltip ────────────────────────────────────────────────────
    tooltip_var = setup_footer_tooltip(
        win, bg_color=_T["header_bg"], fg_color=_T["header_fg"]
    )

    # ── Closure helpers ───────────────────────────────────────────────────
    def cleanup_and_close(_event=None):
        return safe_close_modal(win, parent, calling_button)

    def on_escape(_event=None):
        return cleanup_and_close()

    win.bind("<F1>", lambda e: _show_help(win, on_escape))
    win.bind(
        "<F2>",
        lambda e: _show_session_viewer(win, session_records, on_escape),
    )
    win.bind("<Escape>", on_escape)
    win.protocol("WM_DELETE_WINDOW", on_escape)

    # ── Header ────────────────────────────────────────────────────────────
    header_frame = tk.Frame(win, bg=_T["header_bg"], relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=0)
    tk.Label(
        header_frame,
        text="\U0001f4b3  Add CC Transaction  \U0001f4b3",
        font=("Helvetica", 18, "bold"),
        bg=_T["header_bg"],
        fg=_T["header_fg"],
        relief="ridge",
        bd=2,
        pady=8,
    ).pack(fill="x")

    hint_frame = tk.Frame(win, bg=_T["main_bg"])
    hint_frame.pack(fill="x", padx=10, pady=(2, 0))
    for hint in ("F1: Help", "F2: Session Viewer", "Esc: Close"):
        tk.Label(
            hint_frame,
            text=hint,
            font=("Helvetica", 10, "italic"),
            bg=_T["main_bg"],
            fg="#5eead4",  # soft teal hint text
        ).pack(side="left", padx=12)

    # ── Form body ─────────────────────────────────────────────────────────
    _F = ("Helvetica", 14)
    _FB = ("Helvetica", 14, "bold")

    _C_MASTER = _T["band_master"]
    _C_DETAIL = _T["band_details"]
    _C_AMT = _T["band_amounts"]

    form_body = tk.Frame(win, bg=_T["main_bg"])
    form_body.pack(fill="x", padx=12, pady=6)

    # ── Band 1: Card selector + Linked Account ───────────────────────────
    mst_band, mst_lrow, mst_erow = _make_band(form_body, _C_MASTER)
    mst_band.pack(fill="x", pady=(0, 5))

    _band_label(mst_lrow, "Credit Card", _C_MASTER, _F)
    _band_label(mst_lrow, "Linked Bank Account (auto)", _C_MASTER, _F, padx=130)

    card_combo = ttk.Combobox(
        mst_erow,
        width=40,
        values=list(card_map.keys()),
        font=_F,
    )
    card_combo.pack(side="left", padx=(0, 8))
    apply_entry_theme(card_combo)
    progressive_selection(card_combo, list(card_map.keys()))
    bind_tooltip(
        card_combo,
        tooltip_var,
        "Select the credit card for this transaction.",
    )

    def _refresh_card_combo():
        new_cards = get_all_card_masters()
        card_map.clear()
        for row in new_cards:
            label = f"{row[1]}  [****{row[2][-4:]}]  [{row[4]}]"
            card_map[label] = (int(row[0]), int(row[3]))
        card_combo["values"] = list(card_map.keys())
        progressive_selection(card_combo, list(card_map.keys()))

    def on_card_focus_out(_event=None):
        try:
            if not win.winfo_exists():
                return
        except (tk.TclError, NameError):
            return
        typed = card_combo.get().strip()
        if not typed:
            return
        if typed not in card_map:
            response = show_colorful_yesno(
                win,
                "Card Not Found",
                f"'{typed}' was not found. Add a new credit card " "now?",
            )
            if response:
                _add_card(win)
                _refresh_card_combo()
                card_combo.focus_set()
            else:
                show_colorful_error(
                    win,
                    "Invalid Selection",
                    "Please select a valid credit card from the list.",
                )
                flash_error(card_combo)
                card_combo.focus_set()

    card_combo.bind("<FocusOut>", on_card_focus_out, add="+")

    if card_map:
        card_combo.set(next(iter(card_map)))

    linked_acct_var = tk.StringVar(value="—")
    linked_acct_lbl = tk.Label(
        mst_erow,
        textvariable=linked_acct_var,
        font=_F,
        bg=_C_MASTER,
        fg="#5eead4",
        width=30,
        anchor="w",
    )
    linked_acct_lbl.pack(side="left", padx=(18, 0))

    # ── Band 2: Date + Party + Trans Type ────────────────────────────────
    det_band, det_lrow, det_erow = _make_band(form_body, _C_DETAIL)
    det_band.pack(fill="x", pady=(0, 5))

    _band_label(det_lrow, "Trans Date", _C_DETAIL, _F)
    _band_label(det_lrow, "Party / Merchant", _C_DETAIL, _F, padx=40)
    _band_label(det_lrow, "Trans Type", _C_DETAIL, _F, padx=90)

    trans_dt = DateEntry(det_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    trans_dt.pack(side="left", padx=(0, 8))
    apply_entry_theme(trans_dt)
    bind_tooltip(trans_dt, tooltip_var, "Date the transaction posted on the card.")
    bind_date_spin(trans_dt)

    party_entry = tk.Entry(det_erow, width=28, font=_FB)
    party_entry.pack(side="left", padx=(18, 8))
    apply_entry_theme(party_entry)
    bind_tooltip(
        party_entry,
        tooltip_var,
        "Merchant name or description (e.g. SWIGGY, Bill Payment).",
    )

    trans_type_var = tk.StringVar(value="EXPENSE")

    type_frame = tk.Frame(det_erow, bg=_C_DETAIL)
    type_frame.pack(side="left", padx=(18, 0))
    for ttype in _TRANS_TYPES:
        rb = tk.Radiobutton(
            type_frame,
            text=ttype,
            variable=trans_type_var,
            value=ttype,
            font=("Helvetica", 12),
            bg=_C_DETAIL,
            fg=_T["label_fg"],
            selectcolor="#003333",
            activebackground=_C_DETAIL,
            activeforeground=_T["label_fg"],
        )
        rb.pack(side="left", padx=4)

    # ── Band 3: Amounts + Points ──────────────────────────────────────────
    amt_band, amt_lrow, amt_erow = _make_band(form_body, _C_AMT)
    amt_band.pack(fill="x", pady=(0, 5))

    _band_label(amt_lrow, "Expense (\u20b9)", _C_AMT, _F)
    _band_label(amt_lrow, "CC Credit (\u20b9)", _C_AMT, _F, padx=36)

    expense_entry = tk.Entry(amt_erow, width=14, font=_FB)
    expense_entry.pack(side="left", padx=(0, 8))
    expense_entry.insert(0, "0.00")
    apply_entry_theme(expense_entry)
    bind_tooltip(
        expense_entry,
        tooltip_var,
        "Amount charged on the card (EXPENSE rows). Enter 0 otherwise.",
    )

    cc_credit_entry = tk.Entry(amt_erow, width=14, font=_FB)
    cc_credit_entry.pack(side="left", padx=(18, 8))
    cc_credit_entry.insert(0, "0.00")
    apply_entry_theme(cc_credit_entry)
    bind_tooltip(
        cc_credit_entry,
        tooltip_var,
        "Amount credited to the card (PAYMENT/CASHBACK/REVERSAL). Enter 0 for "
        "EXPENSE.",
    )

    # ── Band 4: Budget Head ───────────────────────────────────────────────
    _C_BH = "#003333"
    bh_band, bh_lrow, bh_erow = _make_band(form_body, _C_BH)
    bh_band.pack(fill="x", pady=(0, 5))

    _band_label(bh_lrow, "Budget Head (optional)", _C_BH, _F)

    budget_head_combo = ttk.Combobox(bh_erow, width=40, values=bh_values, font=_F)
    budget_head_combo.set("(none)")
    budget_head_combo.pack(side="left")
    apply_entry_theme(budget_head_combo)
    progressive_selection(budget_head_combo, bh_values)
    bind_tooltip(
        budget_head_combo,
        tooltip_var,
        "Budget category for CC transaction analysis reports.",
    )

    def _refresh_budget_head_combo():
        new_bh = sorted(get_all_budget_heads(), key=lambda r: r[1])
        budget_map.clear()
        budget_map.update({r[1]: r[0] for r in new_bh})
        bh_type_map.clear()
        bh_type_map.update({r[1]: r[2] for r in new_bh})
        bh_values.clear()
        bh_values.extend(["(none)"] + [r[1] for r in new_bh])
        budget_head_combo["values"] = list(bh_values)
        progressive_selection(budget_head_combo, list(bh_values))

    def on_budget_head_focus_out(_event=None):
        try:
            if not win.winfo_exists():
                return
        except (tk.TclError, NameError):
            return
        typed = budget_head_combo.get().strip()
        if not typed or typed == "(none)":
            return
        if typed not in bh_values:
            response = show_colorful_yesno(
                win,
                "Budget Category Not Found",
                f"'{typed}' was not found. Add a new budget category " "now?",
            )
            if response:
                _add_budget_head(win)
                _refresh_budget_head_combo()
                budget_head_combo.focus_set()
            else:
                show_colorful_error(
                    win,
                    "Invalid Selection",
                    "Please select a valid budget category from the list.",
                )
                flash_error(budget_head_combo)
                budget_head_combo.focus_set()

    budget_head_combo.bind("<FocusOut>", on_budget_head_focus_out, add="+")

    def _widen_bh_popup(pd_name, min_width):
        try:
            geo = str(budget_head_combo.tk.call("wm", "geometry", pd_name))
            wh, _, rest = geo.partition("+")
            rest = "+" + rest
            pw, _, ph = wh.partition("x")
            new_w = max(int(pw), min_width)
            budget_head_combo.tk.call("wm", "geometry", pd_name, f"{new_w}x{ph}{rest}")
        except (tk.TclError, ValueError):
            pass

    def _set_bh_dropdown_font():
        try:
            lb = f"[ttk::combobox::PopdownWindow {budget_head_combo._w}].f.l"
            budget_head_combo.tk.eval(f"{lb} configure -font {{Helvetica 14}}")
            if bh_values:
                f14 = tkfont.Font(family="Helvetica", size=14)
                min_px = max(f14.measure(v) for v in bh_values) + 30
                pd_name = str(
                    budget_head_combo.tk.call(
                        "ttk::combobox::PopdownWindow", budget_head_combo._w
                    )
                )
                budget_head_combo.after(
                    1, lambda pw=pd_name, w=min_px: _widen_bh_popup(pw, w)
                )
        except tk.TclError:
            pass

    budget_head_combo.configure(postcommand=_set_bh_dropdown_font)

    # ── Auto-logic: card selection changes ────────────────────────────────
    def _on_card_selected(_event=None):
        label = card_combo.get()
        if label not in card_map:
            return
        cm_id, ac_id = card_map[label]
        _state["card_master_id"] = cm_id
        _state["account_id"] = ac_id
        linked_acct_var.set(f"Account ID = {ac_id}")

    card_combo.bind("<<ComboboxSelected>>", _on_card_selected)

    # ── Auto-logic: trans type fills default party + enables fields ───────
    def _on_type_change(*_args):
        ttype = trans_type_var.get()
        default = _DEFAULT_PARTY.get(ttype, "")
        if party_entry.get().strip() in ("", *_DEFAULT_PARTY.values()):
            party_entry.delete(0, "end")
            party_entry.insert(0, default)

    trans_type_var.trace_add("write", _on_type_change)

    # Initialise from first card (must be after _compute_points_balance is defined)
    if card_map:
        _on_card_selected()

    # ── Session count label ───────────────────────────────────────────────
    session_count_var = tk.StringVar(value="Session: 0 saved")
    tk.Label(
        win,
        textvariable=session_count_var,
        font=("Helvetica", 11, "italic"),
        bg=_T["main_bg"],
        fg="#5eead4",
    ).pack(anchor="e", padx=16)

    # ── Buttons row ───────────────────────────────────────────────────────
    btn_frame = tk.Frame(win, bg=_T["main_bg"])
    btn_frame.pack(pady=8)

    def _reset_form():
        trans_dt.set_date(__import__("datetime").date.today())
        party_entry.delete(0, "end")
        trans_type_var.set("EXPENSE")
        expense_entry.delete(0, "end")
        expense_entry.insert(0, "0.00")
        cc_credit_entry.delete(0, "end")
        cc_credit_entry.insert(0, "0.00")
        budget_head_combo.set("(none)")
        party_entry.focus_set()

    def _validate_and_save():
        # Card selected?
        card_label = card_combo.get()
        if not card_label or card_label not in card_map:
            flash_error(card_combo)
            show_colorful_error(win, "Validation Error", "Please select a credit card.")
            return

        # Date
        try:
            cc_trans_dt = trans_dt.get_date().strftime("%Y-%m-%d")
        except Exception:  # noqa: BLE001
            flash_error(trans_dt)
            show_colorful_error(
                win,
                "Validation Error",
                "Please enter a valid transaction date.",
            )
            return

        # Party
        party = party_entry.get().strip()
        if not party:
            flash_error(party_entry)
            show_colorful_error(
                win, "Validation Error", "Party / Merchant cannot be blank."
            )
            return

        # Amounts
        try:
            expense_str = expense_entry.get().replace(",", "")
            expense = float(expense_str or "0")
        except ValueError:
            flash_error(expense_entry)
            show_colorful_error(win, "Validation Error", "Expense must be a number.")
            return
        try:
            credit_str = cc_credit_entry.get().replace(",", "")
            cc_credit = float(credit_str or "0")
        except ValueError:
            flash_error(cc_credit_entry)
            show_colorful_error(win, "Validation Error", "CC Credit must be a number.")
            return

        ttype = trans_type_var.get()
        if ttype == "EXPENSE":
            if expense <= 0:
                flash_error(expense_entry)
                show_colorful_error(
                    win,
                    "Validation Error",
                    "Expense must be > 0 for EXPENSE transactions.",
                )
                return
            if cc_credit != 0:
                flash_error(cc_credit_entry)
                show_colorful_error(
                    win,
                    "Validation Error",
                    "CC Credit must be 0 for EXPENSE transactions.",
                )
                return
        else:
            if cc_credit <= 0:
                flash_error(cc_credit_entry)
                show_colorful_error(
                    win,
                    "Validation Error",
                    f"CC Credit must be > 0 for {ttype} " "transactions.",
                )
                return
            if expense != 0:
                flash_error(expense_entry)
                show_colorful_error(
                    win,
                    "Validation Error",
                    f"Expense must be 0 for {ttype} " "transactions.",
                )
                return

        cm_id, ac_id = card_map[card_label]

        bh_desc = budget_head_combo.get().strip()
        bh_id: int | None = budget_map.get(bh_desc)

        data = {
            "card_master_id": cm_id,
            "account_id": ac_id,
            "cc_trans_dt": cc_trans_dt,
            "party": party,
            "expense": expense,
            "cc_credit": cc_credit,
            "bh_id": bh_id,
        }

        try:
            cc_trans_id = _db_add_cc_transaction(data)
        except Exception as exc:  # noqa: BLE001
            logger.error("add_cc_transaction failed: %s", exc)
            msg = f"Failed to save transaction:\n{exc}"
            show_colorful_error(win, "Database Error", msg)
            return

        # Track session
        session_records.append(
            {
                **data,
                "cc_trans_id": cc_trans_id,
                "card_label": card_label,
                "trans_type": ttype,
            }
        )
        session_count_var.set(f"Session: {len(session_records)} saved")

        show_colorful_info(
            win,
            "Saved",
            f"CC Transaction saved (ID {cc_trans_id}).",
        )
        _reset_form()

    save_btn = tk.Button(
        btn_frame,
        text="Save  [Enter]",
        command=_validate_and_save,
        font=("Helvetica", 13, "bold"),
        bg=_T.get("submit_bg", _T["button_bg"]),
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
        _T.get("submit_bg", _T["button_bg"]),
        _T.get("submit_hover_bg", "#2563eb"),
    )

    close_btn = tk.Button(
        btn_frame,
        text="Close  [Esc]",
        command=cleanup_and_close,
        font=("Helvetica", 13, "bold"),
        bg=_T.get("cancel_bg", _T["button_bg"]),
        fg=_T.get("button_fg", "white"),
        activeforeground=_T.get("button_fg", "white"),
        padx=18,
        pady=6,
        cursor="hand2",
        relief="raised",
        bd=3,
    )
    close_btn.pack(side="left", padx=12)
    apply_button_animations(
        close_btn,
        _T.get("cancel_bg", _T["button_bg"]),
        _T.get("cancel_hover_bg", "#991b1b"),
    )

    # ── Return-key navigation ─────────────────────────────────────────────
    def _focus_next(next_widget):
        def _handler(_event=None):
            next_widget.focus_set()
            return "break"

        return _handler

    trans_dt.bind("<Return>", _focus_next(party_entry))
    party_entry.bind("<Return>", _focus_next(expense_entry))
    expense_entry.bind("<Return>", _focus_next(cc_credit_entry))
    cc_credit_entry.bind("<Return>", _focus_next(budget_head_combo))
    budget_head_combo.bind("<Return>", lambda _e: _validate_and_save())

    win.bind(
        "<Return>",
        lambda e: (
            _validate_and_save()
            if win.focus_get() in (budget_head_combo, save_btn)
            else None
        ),
    )

    # ── Modal wait ────────────────────────────────────────────────────────
    if card_map:
        party_entry.focus_set()
    else:
        card_combo.focus_set()

    parent.wait_window(win)
