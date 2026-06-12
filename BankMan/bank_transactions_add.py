# -*- coding: utf-8 -*-
# BankMan/bank_transactions_add.py

"""
Module for adding new bank transactions to the database.
"""

from datetime import date as _date, timedelta as _timedelta
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
    BANK_TRANSACTION_ADD_UI_THEME,
    apply_button_animations,  # <-- Added missing import
    bind_date_spin,
    universal_tree_sort,
)
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno,
)
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from .bank_db_utils import (
    add_bank_transaction_v2 as _db_add_transaction,
    get_all_accounts,
    get_all_budget_heads,
    get_active_fd_masters,
    db_add_fd_master as _db_add_fd_master,
    get_fd_principal as _db_get_fd_principal,
    get_transactions_for_pairing,
    get_last_trans_date,
    get_last_serial_no,
    get_last_balance,
    get_account_curr_balance,
    get_last_used_account_id,
    get_single_ppf_master_id as _db_get_ppf_master_id,
    get_last_ppf_balance as _db_get_last_ppf_balance,
    get_budget_heads_with_parents as _db_get_bh_with_parents,
    get_all_card_masters as _db_get_all_card_masters,
    get_all_user_descriptions,
)
from Shared.globals import logger
from Shared.gui_progressive import progressive_selection
from .accounts_add import add_account_main as _add_account
from .budget_head_add import add_account_type_main as _add_budget_head

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_THEME = BANK_TRANSACTION_ADD_UI_THEME
_last_used_account: str | None = None


# ---------------------------------------------------------------------------
# Working-day helper
# ---------------------------------------------------------------------------


def _next_working_day(from_date: _date) -> _date:
    """Return the next Monday–Friday date strictly after from_date."""
    d = from_date + _timedelta(days=1)
    while d.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        d += _timedelta(days=1)
    return d


# ---------------------------------------------------------------------------
# Module-level helpers (no closure variables; receive all context as params)
# ---------------------------------------------------------------------------


def _make_band(container, bg, relief="ridge", padx=10, pady=6):
    """Create a coloured section band with a stacked label_row / entry_row.

    Returns (band_frame, label_row, entry_row).
    The caller is responsible for packing / gridding the returned band_frame.
    """
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
    """Pack a field label into a band label_row."""
    tk.Label(parent, text=text, font=font, bg=bg, fg="#1e293b", anchor="w").pack(
        side="left", padx=(padx, 12)
    )


def show_master_help(win: tk.Toplevel, on_escape) -> None:
    """Launch a tabbed help window.

    Contains General Help, Budget Heads, and FAQ tabs.
    """
    win.unbind("<Escape>")

    help_win = tk.Toplevel(win)
    try:
        help_win.transient(win)
    except (tk.TclError, AttributeError) as _exc:
        logger.debug("help_win.transient failed: %s", _exc)
    help_win.title("Master Help — Bank Transactions")
    help_win.configure(bg=_THEME["help_bg"])
    help_win.geometry("800x700")
    help_win.resizable(True, True)
    help_win.grab_set()
    push_window(help_win, win)
    try:
        help_win.focus_set()
    except tk.TclError:
        pass

    # ── Title bar ─────────────────────────────────────────────────────────
    tk.Label(
        help_win,
        text="Bank Transaction Help Center",
        font=("Helvetica", 16, "bold"),
        bg=_THEME["help_header_bg"],
        fg="white",
        pady=8,
    ).pack(fill="x")

    # ── Notebook Setup ────────────────────────────────────────────────────
    style = ttk.Style(help_win)
    original_theme = style.theme_use()
    style.theme_use("default")
    style.configure("TNotebook", background=_THEME["help_bg"], borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        font=("Helvetica", 12, "bold"),
        padding=[10, 5],
        background="#e0e0e0",
        foreground="#333",
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", BANK_TRANSACTION_ADD_UI_THEME["help_tab_bg"])],
        foreground=[("selected", "white")],
    )

    notebook = ttk.Notebook(help_win)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    # ======================================================================
    # TAB 1: GENERAL HELP
    # ======================================================================
    tab_general = tk.Frame(notebook, bg=_THEME["help_bg"], padx=12, pady=12)
    notebook.add(tab_general, text="General Help")

    gen_text = tk.Text(
        tab_general,
        wrap="word",
        bg=_THEME["help_bg"],
        bd=0,
        padx=6,
        pady=6,
        font=("Helvetica", 11),
    )
    gen_text.pack(fill="both", expand=True)

    help_lines = [
        "\u2022 This form records a new bank statement transaction.",
        "",
        "Fields:",
        "  Account      \u2014 Select the bank account.  Defaults to last-used.",
        "  Serial No    \u2014 Optional bank serial / reference number.",
        "  Value Dt     \u2014 Date the bank applied this transaction for "
        "interest purposes.  Defaults to the next working day.",
        "  Trans Dt     \u2014 Calendar date the event was initiated.  "
        "Auto-syncs to Value Dt when Value Dt changes.",
        "  Cheque No    \u2014 Cheque reference for cheque-based transactions.",
        "  Bank Remark  \u2014 Narration as printed on the bank statement.",
        "  Withdrawal   \u2014 Amount leaving the account (debit).  Enter 0 if N/A.",
        "  Deposit      \u2014 Amount entering the account (credit). Enter 0 if N/A.",
        "  Balance      \u2014 Running balance after this transaction.",
        "  Pair ID      \u2014 Links this row to an opposite transfer row. "
        "Click \u2018Select\u2019 to browse recent unpaired entries.",
        "  Budget Head  \u2014 Budget category for analysis reports.",
        "  Module Type  \u2014 NONE for plain transactions; choose FD, CC, "
        "LOAN, PPF, STOCK_COMP, STOCK_ACTU, or MF to link to a sub-ledger "
        "product.",
        "  Module Ref   \u2014 For FD: pick from the active-FD dropdown and "
        "use \u2018New\u2019 to create a new FD on the fly. For all other "
        "types: enter the integer product ID.",
        "",
        "FD Logic:",
        "  Withdrawal > 0  \u2192  Deposit into FD (fd_saving entry).",
        "  Deposit > 0     \u2192  Maturity / partial withdrawal from FD.",
        "    Full (deposit \u2265 principal): auto-splits principal + interest.",
        "    Partial (deposit < principal): prompts for manual breakdown.",
    ]
    gen_text.insert("1.0", "\n".join(help_lines))
    gen_text.config(state="disabled")

    # ======================================================================
    # TAB 2: BUDGET HEADS
    # ======================================================================
    try:
        bh_rows = _db_get_bh_with_parents()
    except Exception as exc:
        logger.warning("budget heads fetch failed: %s", exc)
        bh_rows = []

    tab_budget = tk.Frame(notebook, bg="#f0f9ff")
    notebook.add(tab_budget, text="Budget Heads Reference")

    search_frame = tk.Frame(tab_budget, bg="#e0f2fe", pady=5)
    search_frame.pack(fill="x", padx=10, pady=(6, 0))
    tk.Label(
        search_frame,
        text="Search:",
        font=("Helvetica", 11, "bold"),
        bg="#e0f2fe",
        fg="#0369a1",
    ).pack(side="left", padx=(6, 4))

    search_var = tk.StringVar()
    search_entry = tk.Entry(
        search_frame,
        textvariable=search_var,
        font=("Helvetica", 12),
        width=32,
        bg="#fff",
        fg="#0c4a6e",
        insertbackground="#0369a1",
        relief="solid",
        bd=1,
    )
    search_entry.pack(side="left", padx=4)

    clear_btn = tk.Button(
        search_frame,
        text="✕",
        font=("Helvetica", 10, "bold"),
        bg="#bae6fd",
        fg="#0369a1",
        bd=0,
        padx=6,
        pady=2,
        cursor="hand2",
        command=lambda: search_var.set(""),
    )
    apply_button_animations(clear_btn, "#bae6fd", "#a5d8ff")
    clear_btn.pack(side="left", padx=2)
    match_label = tk.Label(
        search_frame, text="", font=("Helvetica", 10), bg="#e0f2fe", fg="#0369a1"
    )
    match_label.pack(side="left", padx=8)

    text_frame = tk.Frame(tab_budget, bg="#f0f9ff")
    text_frame.pack(fill="both", expand=True, padx=10, pady=6)
    scrollbar = tk.Scrollbar(text_frame)
    scrollbar.pack(side="right", fill="y")

    bh_text_widget = tk.Text(
        text_frame,
        wrap="word",
        bg="#f8fafc",
        fg="#0c4a6e",
        font=("Helvetica", 11),
        padx=10,
        pady=8,
        bd=1,
        relief="solid",
        yscrollcommand=scrollbar.set,
        state="disabled",
    )
    bh_text_widget.pack(fill="both", expand=True)
    scrollbar.config(command=bh_text_widget.yview)

    bh_text_widget.tag_configure(
        "section", font=("Helvetica", 12, "bold"), foreground="#0369a1"
    )
    bh_text_widget.tag_configure(
        "header", font=("Helvetica", 10, "bold"), foreground="#64748b"
    )
    bh_text_widget.tag_configure("income", font=("Helvetica", 11), foreground="#166534")
    bh_text_widget.tag_configure(
        "expense", font=("Helvetica", 11), foreground="#9a3412"
    )
    bh_text_widget.tag_configure(
        "highlight", background="#fef08a", foreground="#0c4a6e"
    )

    income_rows = [
        (desc, parent) for _, desc, btype, parent in bh_rows if btype == "INCOME"
    ]
    expense_rows = [
        (desc, parent) for _, desc, btype, parent in bh_rows if btype == "EXPENSE"
    ]

    bh_text_widget.config(state="normal")
    bh_text_widget.insert("end", "\u2500" * 20 + " Income items\n", "section")
    bh_text_widget.insert(
        "end", "IBH  Income Budget Head          IPH  Income Parent Head\n\n", "header"
    )
    for desc, parent in income_rows:
        bh_text_widget.insert("end", f"  (IBH {desc}    IPH {parent})\n", "income")
    bh_text_widget.insert("end", "\n" + "\u2500" * 20 + " Expense items\n", "section")
    bh_text_widget.insert(
        "end", "EBH  Expense Budget Head         EPH  Expense Parent Head\n\n", "header"
    )
    for desc, parent in expense_rows:
        bh_text_widget.insert("end", f"  (EBH {desc}    EPH {parent})\n", "expense")
    bh_text_widget.config(state="disabled")

    def _do_search(*_args):
        term = search_var.get().strip()
        bh_text_widget.tag_remove("highlight", "1.0", "end")
        if not term:
            match_label.config(text="")
            return
        count = 0
        start = "1.0"
        while True:
            pos = bh_text_widget.search(term, start, stopindex="end", nocase=True)
            if not pos:
                break
            end = f"{pos}+{len(term)}c"
            bh_text_widget.tag_add("highlight", pos, end)
            start = end
            count += 1
        if count:
            first = bh_text_widget.search(term, "1.0", stopindex="end", nocase=True)
            if first:
                bh_text_widget.see(first)
            match_label.config(text=f"{count} match{'es' if count != 1 else ''}")
        else:
            match_label.config(text="No matches")

    search_var.trace_add("write", _do_search)

    # ======================================================================
    # TAB 3: FAQ
    # ======================================================================
    tab_faq = tk.Frame(notebook, bg=_THEME["help_bg"], padx=12, pady=12)
    notebook.add(tab_faq, text="FAQ")

    faq_text = tk.Text(
        tab_faq,
        wrap="word",
        bg=_THEME["help_bg"],
        bd=0,
        padx=6,
        pady=6,
        font=("Helvetica", 11),
    )
    faq_text.pack(fill="both", expand=True)

    faq_lines = [
        "Frequently Asked Questions",
        "--------------------------",
        "",
        "Q: How do I map a new bank statement entry to a Budget Head?",
        "A: Think of every transaction as a directional flow of money. Do not "
        "use negative numbers.",
        "",
        "   1. Money leaving the account (Outflow):",
        "      - Put the amount in the 'Withdrawal' field.",
        "      - Put 0 in 'Deposit'.",
        "      - Select an EXPENSE budget head (e.g., 'Electricity', 'Groceries').",
        "",
        "   2. Money entering the account (Inflow):",
        "      - Put 0 in 'Withdrawal'.",
        "      - Put the amount in the 'Deposit' field.",
        "      - Select an INCOME budget head (e.g., 'Pension', 'Savings Bank "
        "Interest').",
        "",
        "   3. Money moving between your own accounts (Transfers/Liability Payoffs):",
        "      - Select '(none)' for the Budget Head.",
        "      - The system will treat it as a TRANSFER.",
        "      - Link it using the 'Module Type' and 'Module Ref' (e.g., CC for "
        "Credit Card Bills).",
        "",
        "Q: How do I map an ATM Cash Withdrawal?",
        "A: Since cash is tracked as its own account, a withdrawal is not an "
        "expense. Treat it as a TRANSFER. First, enter a transaction in your "
        "Savings account for the Withdrawal amount, set the Budget Head to "
        "'(none)', and the Entry Type to 'TRANSFER'. Submit it. Then, log a "
        "second transaction in your 'Petty Cash' account for the identical "
        "Deposit amount, set Entry Type to 'TRANSFER', click 'Select' next to "
        "Pair ID, and pick the Savings withdrawal you just created to link them.",
        "",
        "Q: How do I map a Cash Deposit into my bank account?",
        "A: Just like a withdrawal, this is a TRANSFER, but in reverse. First, "
        "enter a transaction in your 'Petty Cash' account for the Withdrawal "
        "amount, set the Budget Head to '(none)', and the Entry Type to "
        "'TRANSFER'. Submit it. Then, log a second transaction in your Savings "
        "account for the identical Deposit amount, set Entry Type to 'TRANSFER', "
        "click 'Select' next to Pair ID, and pick the Petty Cash withdrawal to "
        "link them.",
        "",
        "Q: How do I map my Credit Card bill payment (e.g., auto-debited from "
        "savings)?",
        "A: A credit card payment is a transfer to a liability, not a standard "
        "expense. Set up the form exactly as follows:",
        "   • Account: Select your Savings/Current Account.",
        "   • Withdrawal: The exact bill amount paid.",
        "   • Deposit: 0.00",
        "   • Pair ID: Leave blank.",
        "   • Budget Head: Select '(none)'.",
        "   • Entry Type: TRANSFER (Auto-selected when you choose none).",
        "   • Module Type: CC",
        "   • Module Ref / Master ID: Select your specific Credit Card.",
        "Note: Because Module Type is CC, the system knows this goes to the credit "
        "card ledger and will not ask you to auto-fill a receiving bank account.",
        "",
        "Q: How do I map a historical Credit Card bill payment if I don't have the "
        "statement to enter individual expenses?",
        "A: Treat it as a standard expense to balance your cash flow, rather than "
        "a CC transfer. Select the 'Historical CC Payment' budget head (under "
        "'General & Uncategorized'). Leave the Module Type as '(none)' so the "
        "system does not look for a matching credit card ledger entry. If you find "
        "the statement later, you can edit this transaction, change the Module Type "
        "to 'CC', and link it to the newly entered CC statement.",
        "",
        "",
        "Q: How do I map a cheque payment for a Life Insurance premium?",
        "A: A premium payment is an outward flow of money (an expense). Map it as "
        "follows:",
        "",
        "   - Cheque No: Enter the cheque number (e.g., 238633).",
        "   - Bank Remark: The payee from the statement (e.g., 'LIC OF INDIA').",
        "   - Withdrawal: The exact deduction amount (e.g., 10000).",
        "   - Deposit: 0",
        "   - Budget Head: Select an Expense head like 'Life Insurance - Self'.",
        "   - User Desc: A personal note (e.g., 'Life Insurance').",
        "   - Entry Type: Select the 'EXPENSE' radio button. (Crucial for correct "
        "math!)",
        "   - Module Type: Leave blank. (It is an external expense, not an internal "
        "transfer).",
        "More FAQs will be added here over time...",
    ]
    faq_text.insert("1.0", "\n".join(faq_lines))
    faq_text.config(state="disabled")

    # ── Close Logistics ───────────────────────────────────────────────────
    def close_help(_e=None):
        style.theme_use(original_theme)
        safe_close_modal(help_win, win)
        win.bind("<Escape>", on_escape)
        return "break"

    help_win.bind("<Escape>", close_help)
    help_win.protocol("WM_DELETE_WINDOW", close_help)

    close_help_btn = tk.Button(
        help_win,
        text="Close",
        command=close_help,
        font=("Helvetica", 11, "bold"),
        bg=BANK_TRANSACTION_ADD_UI_THEME["help_btn_bg"],
        fg="white",
        padx=12,
        pady=6,
        cursor="hand2",
    )
    close_help_btn.pack(side="bottom", pady=10)
    apply_button_animations(
        close_help_btn,
        BANK_TRANSACTION_ADD_UI_THEME["help_btn_bg"],
        BANK_TRANSACTION_ADD_UI_THEME["hover_bg"],
    )


def show_session_transactions(
    win: tk.Toplevel,
    current_session_txns: dict,
    on_escape,
) -> None:
    """Launch the session transactions viewer sub-window."""
    if not current_session_txns:
        try:
            show_colorful_info(
                win,
                "No Transactions",
                "No transactions have been recorded in this session yet.",
            )
        except tk.TclError:
            pass
        return

    win.unbind("<Escape>")

    session_entries = list(current_session_txns.items())
    idx = {"i": 0}

    viewer = tk.Toplevel(win)
    viewer.title("Session Transactions Viewer")
    viewer.transient(win)
    viewer.grab_set()
    viewer.resizable(False, False)
    viewer.geometry("620x400")
    push_window(viewer, win)
    try:
        viewer.focus_set()
    except tk.TclError:
        pass

    content = tk.Frame(viewer)
    content.pack(fill="both", expand=True, padx=10, pady=10)

    left_btn = tk.Button(content, text="◀", width=3)
    left_btn.pack(side="left", padx=(10, 5), pady=6)
    apply_button_animations(left_btn, "#f0f0f0", "#dcdcdc")
    right_btn = tk.Button(content, text="▶", width=3)
    right_btn.pack(side="right", padx=(5, 10), pady=6)
    apply_button_animations(right_btn, "#f0f0f0", "#dcdcdc")

    info_text = tk.Text(
        content,
        wrap="word",
        height=16,
        bg=BANK_TRANSACTION_ADD_UI_THEME["session_bg"],
        bd=0,
        relief="flat",
    )
    info_text.pack(fill="both", expand=True, padx=10, pady=6)
    info_text.tag_configure(
        "label",
        font=("Helvetica", 11, "bold"),
        foreground=BANK_TRANSACTION_ADD_UI_THEME["session_label_fg"],
    )
    info_text.tag_configure(
        "value",
        font=("Helvetica", 11),
        foreground=BANK_TRANSACTION_ADD_UI_THEME["session_value_fg"],
    )
    # Added the alert tag back in case it's used elsewhere in update_view
    info_text.tag_configure(
        "net",
        font=("Helvetica", 11, "bold"),
        foreground=BANK_TRANSACTION_ADD_UI_THEME["session_alert_fg"],
    )
    info_text.config(state="disabled")

    status_label = tk.Label(
        content,
        text="",
        font=("Helvetica", 10, "bold"),
        bg=BANK_TRANSACTION_ADD_UI_THEME["session_bg"],
    )
    status_label.pack(side="bottom", pady=(0, 6))

    def update_view():
        i = idx["i"]
        sr, t = session_entries[i]
        info_text.config(state="normal")
        info_text.delete("1.0", "end")
        info_text.insert("end", "Sr. No: ", "label")
        info_text.insert("end", f"{sr}\n", "value")
        info_text.insert("end", "Account: ", "label")
        info_text.insert("end", f"{t.get('Account')}\n", "value")
        info_text.insert("end", "Value Date: ", "label")
        info_text.insert("end", f"{t.get('ValueDt')}\n", "value")
        info_text.insert("end", "Trans Date: ", "label")
        info_text.insert("end", f"{t.get('TransDt')}\n", "value")
        info_text.insert("end", "Withdrawal: ", "label")
        info_text.insert("end", f"{t.get('Withdrawal')}\n", "value")
        info_text.insert("end", "Deposit: ", "label")
        info_text.insert("end", f"{t.get('Deposit')}\n", "value")
        info_text.insert("end", "Balance: ", "label")
        info_text.insert("end", f"{t.get('Balance')}\n", "value")
        info_text.insert("end", "Bank Remark: ", "label")
        info_text.insert("end", f"{t.get('BankRemark') or '—'}\n", "value")
        info_text.insert("end", "Serial No: ", "label")
        info_text.insert("end", f"{t.get('SerialNo') or '—'}\n", "value")
        info_text.insert("end", "Module Type: ", "label")
        info_text.insert("end", f"{t.get('ModuleType')}\n", "value")
        info_text.config(state="disabled")

        left_btn.config(state="disabled" if i == 0 else "normal")
        if i >= len(session_entries) - 1:
            right_btn.config(state="disabled")
            status_label.config(
                text="Last Entry",
                fg=BANK_TRANSACTION_ADD_UI_THEME["session_alert_fg"],
                font=("Helvetica", 10, "bold"),
            )
        else:
            right_btn.config(state="normal")
            status_label.config(
                text="", fg=BANK_TRANSACTION_ADD_UI_THEME["session_ok_fg"]
            )

    def go_prev(_event=None):
        if idx["i"] > 0:
            idx["i"] -= 1
            update_view()

    def go_next(_event=None):
        if idx["i"] < len(session_entries) - 1:
            idx["i"] += 1
            update_view()

    left_btn.config(command=go_prev)
    right_btn.config(command=go_next)
    viewer.bind("<Left>", lambda e: go_prev())
    viewer.bind("<Right>", lambda e: go_next())

    def close_viewer(_event=None):
        safe_close_modal(viewer, win)
        win.bind("<Escape>", on_escape)
        return "break"

    viewer.bind("<Escape>", close_viewer)
    viewer.protocol("WM_DELETE_WINDOW", close_viewer)
    viewer.bind("<Return>", close_viewer)

    ok_btn = tk.Button(content, text="OK", width=10, command=close_viewer)
    ok_btn.pack(side="bottom", pady=(0, 8))
    apply_button_animations(ok_btn, "#f0f0f0", "#dcdcdc")
    try:
        ok_btn.focus_set()
    except tk.TclError:
        pass
    update_view()


# ---------------------------------------------------------------------------
# Pair ID selection modal
# ---------------------------------------------------------------------------


def show_pair_select_modal(
    win: tk.Toplevel,
    account_id: int,
    pair_id_var: tk.StringVar,
    on_escape,
) -> None:
    """Modal to browse and select a historical transaction as the pair_id."""
    win.unbind("<Escape>")

    rows = []
    try:
        rows = get_transactions_for_pairing(account_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("pair fetch failed: %s", exc)

    modal = tk.Toplevel(win)
    modal.title("Select Pair Transaction")
    modal.transient(win)
    modal.grab_set()
    modal.geometry("860x460")
    modal.resizable(False, False)
    modal.configure(bg="#1e293b")
    push_window(modal, win)
    try:
        modal.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        modal,
        text="Select a transaction to pair with:",
        font=("Helvetica", 13, "bold"),
        bg="#1e293b",
        fg="yellow",
        pady=6,
    ).pack(fill="x", padx=10)

    cols = ("trans_id", "serial_no", "trans_date", "bank_desc", "withdrawal", "deposit")
    tree_frame = tk.Frame(modal, bg="#1e293b")
    tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

    vsb = ttk.Scrollbar(tree_frame, orient="vertical")
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        height=14,
        yscrollcommand=vsb.set,
    )
    vsb.config(command=tree.yview)
    vsb.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)

    for col, heading, width in [
        ("trans_id", "Trans ID", 70),
        ("serial_no", "Serial No", 90),
        ("trans_date", "Trans Date", 110),
        ("bank_desc", "Remark", 310),
        ("withdrawal", "Withdrawal", 100),
        ("deposit", "Deposit", 100),
    ]:
        tree.heading(col, text=heading, command=lambda _c=col: universal_tree_sort(tree, _c, False))
        tree.column(col, width=width, anchor="center")

    for row in rows:
        tree.insert(
            "",
            "end",
            values=(
                row[0],
                row[1] if row[1] else "—",
                row[2],
                row[3] if row[3] else "—",
                f"{row[4]:.2f}",
                f"{row[5]:.2f}",
            ),
        )

    btn_row = tk.Frame(modal, bg="#1e293b")
    btn_row.pack(fill="x", padx=10, pady=8)

    def _do_select(_e=None):
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0], "values")
        pair_id_var.set(str(vals[0]))
        _close()

    def _close(_e=None):
        safe_close_modal(modal, win)
        win.bind("<Escape>", on_escape)
        return "break"

    tree.bind("<Double-1>", _do_select)
    tree.bind("<Return>", _do_select)

    select_btn = tk.Button(
        btn_row,
        text="✅ Select",
        command=_do_select,
        font=("Helvetica", 11, "bold"),
        bg="#22c55e",
        fg="white",
        cursor="hand2",
        padx=10,
    )
    select_btn.pack(side="left", padx=5)
    apply_button_animations(select_btn, "#22c55e", "#16a34a")

    cancel_button = tk.Button(
        btn_row,
        text="❌ Cancel",
        command=_close,
        font=("Helvetica", 11, "bold"),
        bg="#ef4444",
        fg="white",
        cursor="hand2",
        padx=10,
    )
    cancel_button.pack(side="left", padx=5)
    apply_button_animations(cancel_button, "#ef4444", "#b91c1c")

    modal.bind("<Escape>", _close)
    modal.protocol("WM_DELETE_WINDOW", _close)

    if rows:
        tree.selection_set(tree.get_children()[0])
        try:
            tree.focus_set()
        except tk.TclError:
            pass


# ---------------------------------------------------------------------------
# New FD modal
# ---------------------------------------------------------------------------


def show_fd_new_modal(
    win: tk.Toplevel,
    account_id: int,
    on_escape,
    on_fd_saved,  # callback(fd_master_id, fd_number)
) -> None:
    """Modal to create a new fd_master entry and auto-select it in the parent."""
    win.unbind("<Escape>")

    modal = tk.Toplevel(win)
    modal.title("New Fixed Deposit")
    modal.transient(win)
    modal.grab_set()
    modal.geometry("500x460")
    modal.resizable(False, False)
    modal.configure(bg="#1e293b")
    push_window(modal, win)
    try:
        modal.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        modal,
        text="New Fixed Deposit",
        font=("Helvetica", 14, "bold"),
        bg="#784212",
        fg="white",
        pady=8,
    ).pack(fill="x")

    form = tk.Frame(modal, bg="#1e293b", padx=16, pady=12)
    form.pack(fill="both", expand=True)

    _fields = [
        ("FD Number:", "fd_number", "entry"),
        ("Principal Amount:", "principal_amount", "entry"),
        ("Interest Rate %:", "interest_rate", "entry"),
        ("Open Date:", "open_dt", "date"),
        ("Maturity Date:", "maturity_dt", "date"),
    ]
    _widgets: dict = {}
    for r, (lbl, key, wtype) in enumerate(_fields):
        tk.Label(
            form,
            text=lbl,
            font=("Helvetica", 14),
            bg="#1e293b",
            fg="yellow",
            anchor="e",
        ).grid(row=r, column=0, sticky="e", padx=(4, 8), pady=8)
        if wtype == "date":
            w = DateEntry(
                form, date_pattern="dd-mm-yyyy", width=18, font=("Helvetica", 14)
            )
        else:
            w = tk.Entry(form, width=28, font=("Helvetica", 14))
        apply_entry_theme(w)
        w.grid(row=r, column=1, sticky="w", padx=4, pady=8)
        _widgets[key] = w

    _keys = [f[1] for f in _fields]
    for _i, _k in enumerate(_keys[:-1]):
        _nxt = _keys[_i + 1]
        _widgets[_k].bind("<Return>", lambda e, n=_nxt: _widgets[n].focus_set())

    btn_row = tk.Frame(modal, bg="#1e293b")
    btn_row.pack(fill="x", padx=16, pady=12)

    def _save(_e=None):
        fd_number = _widgets["fd_number"].get().strip()
        principal_s = _widgets["principal_amount"].get().strip().replace(",", "")
        rate_s = _widgets["interest_rate"].get().strip().replace(",", "")
        if not fd_number:
            show_colorful_error(modal, "Validation", "FD Number is required.")
            _widgets["fd_number"].focus_set()
            return
        try:
            principal = float(principal_s)
            if principal <= 0:
                raise ValueError
        except ValueError:
            show_colorful_error(
                modal, "Validation", "Principal must be a positive number."
            )
            _widgets["principal_amount"].focus_set()
            return
        try:
            rate = float(rate_s)
            if rate < 0:
                raise ValueError
        except ValueError:
            show_colorful_error(
                modal, "Validation", "Interest Rate must be a non-negative number."
            )
            _widgets["interest_rate"].focus_set()
            return
        open_dt = _widgets["open_dt"].get_date().strftime("%Y-%m-%d")
        maturity_dt = _widgets["maturity_dt"].get_date().strftime("%Y-%m-%d")
        if maturity_dt <= open_dt:
            show_colorful_error(
                modal, "Validation", "Maturity Date must be after Open Date."
            )
            _widgets["maturity_dt"].focus_set()
            return
        try:
            new_id = _db_add_fd_master(
                {
                    "account_id": account_id,
                    "fd_number": fd_number,
                    "principal_amount": principal,
                    "interest_rate": rate,
                    "open_dt": open_dt,
                    "maturity_dt": maturity_dt,
                }
            )
            _close()
            on_fd_saved(new_id, fd_number)
        except Exception as exc:  # noqa: BLE001
            show_colorful_error(modal, "Error", f"Failed to save FD: {exc}")

    def _close(_e=None):
        safe_close_modal(modal, win)
        win.bind("<Escape>", on_escape)
        return "break"

    save_btn = tk.Button(
        btn_row,
        text="✅ Save FD",
        command=_save,
        font=("Helvetica", 11, "bold"),
        bg="#22c55e",
        fg="white",
        cursor="hand2",
        padx=10,
    )
    save_btn.pack(side="left", padx=5)
    apply_button_animations(save_btn, "#22c55e", "#2563eb")

    cancel_button = tk.Button(
        btn_row,
        text="❌ Cancel",
        command=_close,
        font=("Helvetica", 11, "bold"),
        bg="#ef4444",
        fg="white",
        cursor="hand2",
        padx=10,
    )
    cancel_button.pack(side="left", padx=5)
    apply_button_animations(cancel_button, "#ef4444", "#b91c1c")
    modal.bind("<Escape>", _close)
    modal.protocol("WM_DELETE_WINDOW", _close)
    _widgets["fd_number"].focus_set()


# ---------------------------------------------------------------------------
# FD partial-withdrawal breakdown modal
# ---------------------------------------------------------------------------


def show_fd_partial_modal(
    win: tk.Toplevel,
    deposit_amount: float,
    on_escape,
    on_confirmed,  # callback(principal_comp, interest_comp)
) -> None:
    """Prompt for principal / interest breakdown on a partial FD withdrawal."""
    win.unbind("<Escape>")

    modal = tk.Toplevel(win)
    modal.title("FD Partial Withdrawal Breakdown")
    modal.transient(win)
    modal.grab_set()
    modal.geometry("440x310")
    modal.resizable(False, False)
    modal.configure(bg="#1e293b")
    push_window(modal, win)
    try:
        modal.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        modal,
        text=f"Partial FD Withdrawal  —  \u20b9{deposit_amount:,.2f}",
        font=("Helvetica", 13, "bold"),
        bg="#784212",
        fg="white",
        pady=8,
    ).pack(fill="x")

    body = tk.Frame(modal, bg="#1e293b", padx=18, pady=14)
    body.pack(fill="both", expand=True)

    tk.Label(
        body,
        text=(
            "Allocate the received amount between principal\n"
            "repaid and interest earned:"
        ),
        font=("Helvetica", 11),
        bg="#1e293b",
        fg="#e2e8f0",
        justify="left",
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

    tk.Label(
        body,
        text="Principal Component:",
        font=("Helvetica", 14),
        bg="#1e293b",
        fg="yellow",
        anchor="e",
    ).grid(row=1, column=0, sticky="e", padx=(0, 10), pady=8)
    principal_e = tk.Entry(body, width=20, font=("Helvetica", 14))
    principal_e.grid(row=1, column=1, sticky="w", pady=8)
    apply_entry_theme(principal_e)

    tk.Label(
        body,
        text="Interest Component:",
        font=("Helvetica", 14),
        bg="#1e293b",
        fg="yellow",
        anchor="e",
    ).grid(row=2, column=0, sticky="e", padx=(0, 10), pady=8)
    interest_e = tk.Entry(body, width=20, font=("Helvetica", 14))
    interest_e.grid(row=2, column=1, sticky="w", pady=8)
    apply_entry_theme(interest_e)
    interest_e.insert(0, "0.0")

    principal_e.bind("<Return>", lambda e: interest_e.focus_set())

    btn_row = tk.Frame(modal, bg="#1e293b")
    btn_row.pack(fill="x", padx=18, pady=10)

    def _confirm(_e=None):
        try:
            p = float(principal_e.get().strip().replace(",", ""))
            i = float(interest_e.get().strip().replace(",", ""))
            if p < 0 or i < 0:
                raise ValueError
        except ValueError:
            show_colorful_error(
                modal, "Validation", "Enter valid non-negative numbers."
            )
            principal_e.focus_set()
            return
        if abs(p + i - deposit_amount) > 0.01:
            show_colorful_error(
                modal,
                "Validation",
                f"Principal ({p:.2f}) + Interest ({i:.2f}) must equal "
                f"the deposit amount ({deposit_amount:.2f}).",
            )
            return
        _close()
        on_confirmed(p, i)

    def _close(_e=None):
        safe_close_modal(modal, win)
        win.bind("<Escape>", on_escape)
        return "break"

    confirm_btn = tk.Button(
        btn_row,
        text="✅ Confirm",
        command=_confirm,
        font=("Helvetica", 11, "bold"),
        bg="#22c55e",
        fg="white",
        cursor="hand2",
        padx=10,
    )
    confirm_btn.pack(side="left", padx=5)
    apply_button_animations(confirm_btn, "#22c55e", "#2563eb")

    cancel_button = tk.Button(
        btn_row,
        text="❌ Cancel",
        command=_close,
        font=("Helvetica", 11, "bold"),
        bg="#ef4444",
        fg="white",
        cursor="hand2",
        padx=10,
    )
    cancel_button.pack(side="left", padx=5)
    apply_button_animations(cancel_button, "#ef4444", "#b91c1c")
    principal_e.focus_set()


# ---------------------------------------------------------------------------
# Balance auto-fill helper
# ---------------------------------------------------------------------------


def _update_balance_default(
    win: tk.Toplevel,
    prev_balance: list,
    withdrawal_entry: tk.Entry,
    deposit_entry: tk.Entry,
    balance_entry: tk.Entry,
    _event=None,
) -> None:
    """Compute and fill balance_entry from the previous account balance.

    Formula: prev_balance + deposit - withdrawal.
    Shows a colorful error warning when the result is negative.
    """
    prev = prev_balance[0]
    if prev is None:
        return
    try:
        w = float(withdrawal_entry.get().strip().replace(",", "") or "0")
        d = float(deposit_entry.get().strip().replace(",", "") or "0")
    except ValueError:
        return
    computed = round(prev + d - w, 2)
    balance_entry.delete(0, tk.END)
    balance_entry.insert(0, f"{computed:.2f}")
    if computed < 0:
        show_colorful_error(
            win,
            "Balance Warning",
            f"Computed balance is negative (\u20b9{computed:,.2f}). "
            "Please verify the amounts.",
        )


def _fmt_amount_on_focus_out(entry: tk.Entry, _event=None) -> None:
    """Reformat an amount entry to 2 decimal places when focus leaves it."""
    try:
        val = float(entry.get().strip().replace(",", "") or "0")
        entry.delete(0, tk.END)
        entry.insert(0, f"{val:.2f}")
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def add_bank_transaction_main(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
    *,
    prefill_pair_id: int | None = None,
    prefill_withdrawal: float | None = None,
    prefill_deposit: float | None = None,
    prefill_val_date: str | None = None,
    prefill_trans_date: str | None = None,
    prefill_serial: int | None = None,
    prefill_cheque: str | None = None,
    prefill_bank_desc: str | None = None,
    prefill_user_desc: str | None = None,
    prefill_bh_id: int | None = None,
) -> None:
    """Main function to launch the Add Bank Transaction window."""

    # ── Button colour constants ───────────────────────────────────────────
    _SUB_BG = "#22c55e"
    _SUB_ACT = "#16a34a"
    _CAN_BG = "#ef4444"
    _CAN_ACT = "#b91c1c"

    # ── Lookup data ───────────────────────────────────────────────────────
    accounts = get_all_accounts()
    account_map = {
        f"{a[1]} : [{a[3]}]": a[0] for a in accounts if a[2] != "CREDIT_CARD"
    }

    bh_rows = sorted(get_all_budget_heads(), key=lambda r: r[1])
    budget_map = {r[1]: r[0] for r in bh_rows}
    bh_type_map = {r[1]: r[2] for r in bh_rows}
    bh_values = ["(none)"] + [r[1] for r in bh_rows]

    fd_map: dict = {}  # fd_number → fd_master_id
    cc_map: dict = {}  # display_label → card_master_id
    _prev_balance: list = [None]  # mutable container so closures can update it

    # Build prev-balance lookup: last transaction balance, or curr_balance fallback
    _prev_bal: dict[str, float | None] = {}

    def _rebuild_prev_bal() -> None:
        _prev_bal.clear()
        for _lbl, _aid in account_map.items():
            _b = get_last_balance(_aid)
            if _b is None:
                _b = get_account_curr_balance(_aid)
            _prev_bal[_lbl] = _b

    _rebuild_prev_bal()

    # ── Window setup ──────────────────────────────────────────────────────
    disable_parent(parent, calling_button=calling_button)

    current_session_txns: dict = {}

    win = tk.Toplevel(parent)
    win.title("💳 Add Bank Transaction 💳")
    win.geometry("1100x630")
    win.resizable(False, False)
    win.configure(bg=BANK_TRANSACTION_ADD_UI_THEME["main_bg"])
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    try:
        push_window(win, parent)
    except (RuntimeError, tk.TclError) as _exc:
        logger.debug("push_window failed: %s", _exc)

    # ── Footer tooltip (packed first so it anchors to the absolute bottom) ─
    tooltip_var = setup_footer_tooltip(win)

    # ── Closure helpers ───────────────────────────────────────────────────
    def cleanup_and_close(_event=None):
        return safe_close_modal(win, parent, calling_button)

    def on_escape(_event=None):
        return cleanup_and_close()

    # ── Header ────────────────────────────────────────────────────────────
    header_frame = tk.Frame(
        win, bg=BANK_TRANSACTION_ADD_UI_THEME["header_bg"], relief="raised", bd=3
    )
    header_frame.pack(fill="x", padx=5, pady=0)

    tk.Label(
        header_frame,
        text="💳 Add Bank Transaction 💳",
        font=("Helvetica", 18, "bold"),
        bg=BANK_TRANSACTION_ADD_UI_THEME["header_bg"],
        fg=BANK_TRANSACTION_ADD_UI_THEME["header_fg"],
        relief="ridge",
        bd=2,
    ).pack(fill="x", pady=10)

    # ── Form body ─────────────────────────────────────────────────────────
    # Follows trade_add.py pattern: coloured band frames, each with a
    # label_row (top) and entry_row (bottom). Multiple fields share one band.
    # ---------------------------------------------------------------------------
    _F = ("Helvetica", 14)  # field font
    _FB = ("Helvetica", 14, "bold")  # bold variant for amounts
    _MAIN_BG = BANK_TRANSACTION_ADD_UI_THEME["main_bg"]
    _BTN_BG = BANK_TRANSACTION_ADD_UI_THEME["button_bg"]
    _BTN_FG = BANK_TRANSACTION_ADD_UI_THEME["button_fg"]

    # Band background colours (warm palette to complement peach chrome)
    _C_ACCT = "#e0f2fe"  # sky-blue   — Account
    _C_REF = "#dbeafe"  # indigo-50  — Serial + Cheque
    _C_REMARK = "#fef3c7"  # amber-100  — Value Dt + Trans Dt
    _C_AMT = "#ede9fe"  # violet-100 — Bank Remark
    # _C_AMT = "#ffedd5"  # orange-100 — Withdrawal + Deposit + Balance
    _C_MOD = "#d1fae5"  # emerald-100 — Pair ID + Budget Head
    # _C_MOD = "#fce7f3"  # pink-100   — Module Type + Module Ref

    form_body = tk.Frame(win, bg=_MAIN_BG)
    form_body.pack(fill="x", padx=12, pady=4)

    # ── Band 1: Account ───────────────────────────────────────────────────
    acct_band, acct_lrow, acct_erow = _make_band(form_body, _C_ACCT)
    acct_band.pack(fill="x", pady=(0, 4))

    _band_label(acct_lrow, "Account", _C_ACCT, _F)
    _band_label(acct_lrow, "Sr No. ", _C_ACCT, _F, padx=230)
    _band_label(acct_lrow, "Cheque No", _C_ACCT, _F, padx=20)
    _band_label(acct_lrow, "Value Dt", _C_ACCT, _F, padx=20)
    _band_label(acct_lrow, "Trans Dt", _C_ACCT, _F, padx=90)

    account_combo = ttk.Combobox(
        acct_erow, width=25, values=list(account_map.keys()), font=_F
    )
    account_combo.pack(side="left", padx=(0, 4))
    apply_entry_theme(account_combo)
    progressive_selection(account_combo, list(account_map.keys()))
    bind_tooltip(account_combo, tooltip_var, "Select the bank account.")

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

    # Validation callback to allow an empty string OR digits only
    def validate_spinbox_numeric(P):
        return P == "" or P.isdigit()

    vcmd = (win.register(validate_spinbox_numeric), "%P")

    # Creating Spinbox that ranges from 1 to 999999, defaulting to empty
    serial_no_entry = tk.Spinbox(
        acct_erow,
        from_=1,
        to=9999,
        width=5,
        font=_F,
        validate="key",
        validatecommand=vcmd,
    )
    # Clear the default '1' or '0' value to keep it blank/NULL initially
    serial_no_entry.delete(0, tk.END)
    serial_no_entry.pack(side="left", padx=(20, 0))
    apply_entry_theme(serial_no_entry)
    bind_tooltip(
        serial_no_entry,
        tooltip_var,
        "Optional bank serial / reference number. Leave blank for NULL.",
    )

    _default_acct: str | None = None
    if _last_used_account and _last_used_account in account_map:
        _default_acct = _last_used_account
    else:
        _last_ac_id = get_last_used_account_id()
        if _last_ac_id is not None:
            _default_acct = next(
                (lbl for lbl, aid in account_map.items() if aid == _last_ac_id), None
            )
        if _default_acct is None:
            _default_acct = next(
                (lbl for lbl in account_map if "0085001101" in lbl), None
            )
        if _default_acct is None and account_map:
            _default_acct = next(iter(account_map))
    if _default_acct:
        account_combo.set(_default_acct)

    cheque_no_entry = tk.Entry(acct_erow, width=10, font=_F)
    cheque_no_entry.pack(side="left", padx=(20, 0))
    apply_entry_theme(cheque_no_entry)
    bind_tooltip(
        cheque_no_entry, tooltip_var, "Cheque number for cheque-based transactions."
    )

    value_dt = DateEntry(acct_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    value_dt.pack(side="left", padx=(20, 0))
    apply_entry_theme(value_dt)
    bind_tooltip(
        value_dt, tooltip_var, "Value date — bank effective date (calendar picker)."
    )

    trans_dt = DateEntry(acct_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    trans_dt.pack(side="left", padx=(20, 0))
    apply_entry_theme(trans_dt)
    bind_tooltip(
        trans_dt,
        tooltip_var,
        "Transaction date — calendar date the event was initiated.",
    )

    # ── Band 3: Value Dt + Trans Dt ───────────────────────────────────────
    remark_band, remark_lrow, remark_erow = _make_band(form_body, _C_REMARK)
    remark_band.pack(fill="x", pady=(0, 4))

    _band_label(remark_lrow, "Bank Remark", _C_REMARK, _F)
    bank_remark_entry = tk.Entry(remark_erow, width=60, font=_F)
    bank_remark_entry.pack(side="left")
    apply_entry_theme(bank_remark_entry)
    bind_tooltip(
        bank_remark_entry, tooltip_var, "Narration as it appears on the bank statement."
    )

    # _band_label(date_lrow, "Value Dt", _C_DATE, _F)
    # _band_label(date_lrow, "Trans Dt", _C_DATE, _F, padx=138)

    # value_dt = DateEntry(date_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    # value_dt.pack(side="left", padx=(0, 30))
    # apply_entry_theme(value_dt)
    # bind_tooltip(
    #     value_dt, tooltip_var, "Value date — bank effective date (calendar picker)."
    # )

    # trans_dt = DateEntry(date_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    # trans_dt.pack(side="left")
    # apply_entry_theme(trans_dt)
    # bind_tooltip(
    #     trans_dt,
    #     tooltip_var,
    #     "Transaction date — calendar date the event was initiated.",
    # )

    # ── Band 4: Bank Remark ───────────────────────────────────────────────
    # rmrk_band, rmrk_lrow, rmrk_erow = _make_band(form_body, _C_RMRK)
    # rmrk_band.pack(fill="x", pady=(0, 4))

    # _band_label(rmrk_lrow, "Bank Remark", _C_RMRK, _F)
    # bank_remark_entry = tk.Entry(rmrk_erow, width=90, font=_F)
    # bank_remark_entry.pack(side="left")
    # apply_entry_theme(bank_remark_entry)
    # bind_tooltip(
    #     bank_remark_entry, tooltip_var, "Narration as it appears on the bank statement."
    # )

    # ── Band 5: Withdrawal + Deposit + Balance ────────────────────────────
    amt_band, amt_lrow, amt_erow = _make_band(form_body, _C_AMT)
    amt_band.pack(fill="x", pady=(0, 4))

    _band_label(amt_lrow, "Withdrawal", _C_AMT, _F)
    _band_label(amt_lrow, "Deposit", _C_AMT, _F, padx=45)
    _band_label(amt_lrow, "Balance", _C_AMT, _F, padx=70)
    _band_label(amt_lrow, "Pair ID", _C_AMT, _F, padx=80)
    _band_label(amt_lrow, "Budget Head", _C_AMT, _F, padx=190)

    withdrawal_entry = tk.Entry(amt_erow, width=11, font=_FB)
    withdrawal_entry.insert(0, "0.00")
    withdrawal_entry.pack(side="left", padx=(0, 30))
    apply_entry_theme(withdrawal_entry)
    bind_tooltip(
        withdrawal_entry,
        tooltip_var,
        "Amount leaving the account (debit). Enter 0 if N/A.",
    )

    deposit_entry = tk.Entry(amt_erow, width=11, font=_FB)
    deposit_entry.insert(0, "0.00")
    deposit_entry.pack(side="left", padx=(0, 30))
    apply_entry_theme(deposit_entry)
    bind_tooltip(
        deposit_entry,
        tooltip_var,
        "Amount entering the account (credit). Enter 0 if N/A.",
    )

    balance_entry = tk.Entry(amt_erow, width=11, font=_FB)
    balance_entry.pack(side="left", padx=(0, 30))
    apply_entry_theme(balance_entry)
    bind_tooltip(
        balance_entry, tooltip_var, "Running account balance after this transaction."
    )

    pair_id_var = tk.StringVar()
    pair_id_display = tk.Entry(
        amt_erow, textvariable=pair_id_var, width=14, font=_F, state="readonly"
    )
    pair_id_display.pack(side="left", padx=(0, 4))
    apply_entry_theme(pair_id_display, is_readonly=True)
    bind_tooltip(
        pair_id_display,
        tooltip_var,
        "ID of the paired transfer transaction. Click Select to browse.",
    )

    def _open_pair_modal():
        acct_name = account_combo.get()
        if not acct_name or acct_name not in account_map:
            show_colorful_error(
                win, "Validation", "Select an account before choosing a Pair ID."
            )
            return
        show_pair_select_modal(win, account_map[acct_name], pair_id_var, on_escape)

    select_pair_btn = tk.Button(
        amt_erow,
        text="Select",
        command=_open_pair_modal,
        font=("Helvetica", 11, "bold"),
        bg=_BTN_BG,
        fg=_BTN_FG,
        cursor="hand2",
        padx=6,
        pady=1,
        relief="raised",
        bd=2,
    )
    select_pair_btn.pack(side="left", padx=(0, 40))
    apply_button_animations(
        select_pair_btn,
        _BTN_BG,
        BANK_TRANSACTION_ADD_UI_THEME["hover_bg"],
    )

    budget_head_combo = ttk.Combobox(amt_erow, width=15, values=bh_values, font=_F)
    budget_head_combo.set("(none)")
    budget_head_combo.pack(side="left")
    apply_entry_theme(budget_head_combo)
    progressive_selection(budget_head_combo, bh_values)
    bind_tooltip(
        budget_head_combo, tooltip_var, "Budget category for analysis reports."
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
            entry_type_var.set("TRANSFER")
            return
        if typed not in bh_values:
            response = show_colorful_yesno(
                win,
                "Budget Category Not Found",
                f"'{typed}' was not found. Add a new budget category "
                "now?",
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
                return
        bh_type = bh_type_map.get(typed)
        if bh_type == "INCOME":
            entry_type_var.set("INCOME")
        elif bh_type == "EXPENSE":
            entry_type_var.set("EXPENSE")

    budget_head_combo.bind("<FocusOut>", on_budget_head_focus_out, add="+")

    def _widen_bh_popup(pd_name, min_width):
        try:
            geo = str(budget_head_combo.tk.call("wm", "geometry", pd_name))
            # geo is like "150x200+100+300"
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

    # ── Band 7: Module Type + Module Ref ──────────────────────────────────
    mod_band = tk.Frame(form_body, bg=_C_MOD, relief="ridge", bd=2, padx=10, pady=6)
    mod_band.pack(fill="x", pady=(0, 4))

    # — Entry Type sub-row —
    entry_type_lrow = tk.Frame(mod_band, bg=_C_MOD)
    entry_type_lrow.pack(fill="x", pady=(0, 2))
    entry_type_erow = tk.Frame(mod_band, bg=_C_MOD)
    entry_type_erow.pack(fill="x", pady=(0, 6))

    _band_label(entry_type_lrow, "Entry Type", _C_MOD, _F)
    _band_label(entry_type_lrow, "User Desc", _C_MOD, _F, padx=250)
    entry_type_var = tk.StringVar(value="INCOME")
    et_radios: list[tk.Radiobutton] = []
    for _et_val in ("INCOME", "EXPENSE", "TRANSFER"):
        _rb = tk.Radiobutton(
            entry_type_erow,
            text=_et_val,
            variable=entry_type_var,
            value=_et_val,
            font=("Helvetica", 11),
            bg=_C_MOD,
        )
        _rb.pack(side="left", padx=8)
        et_radios.append(_rb)

    user_desc_combo = ttk.Combobox(entry_type_erow, width=58, font=_F)
    user_desc_combo.pack(side="left", padx=(20, 0))
    apply_entry_theme(user_desc_combo)
    bind_tooltip(
        user_desc_combo,
        tooltip_var,
        "Your own note or description for this transaction.",
    )

    def _on_user_desc_focus(*_):
        try:
            descs = get_all_user_descriptions()
            user_desc_combo["values"] = descs
            progressive_selection(user_desc_combo, descs)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to fetch user descriptions: %s", exc)

    user_desc_combo.bind("<FocusIn>", _on_user_desc_focus, add="+")

    # — Module Type sub-row —
    mod_type_lrow = tk.Frame(mod_band, bg=_C_MOD)
    mod_type_lrow.pack(fill="x", pady=(0, 2))
    mod_type_erow = tk.Frame(mod_band, bg=_C_MOD)
    mod_type_erow.pack(fill="x", pady=(0, 6))

    _band_label(mod_type_lrow, "Module Type", _C_MOD, _F)

    module_type_var = tk.StringVar(value="NONE")
    _module_types = [
        "NONE",
        "FD",
        "CC",
        "LOAN",
        "PPF",
        "STOCK_COMP",
        "STOCK_ACTU",
        "MF",
    ]
    mt_radios: list[tk.Radiobutton] = []
    for _col, _mt in enumerate(_module_types[:4]):
        _rb = tk.Radiobutton(
            mod_type_erow,
            text=_mt,
            variable=module_type_var,
            value=_mt,
            font=("Helvetica", 11),
            bg=_C_MOD,
        )
        _rb.pack(side="left", padx=8)
        mt_radios.append(_rb)
    tk.Frame(mod_type_erow, bg=_C_MOD, width=20).pack(side="left")  # spacer
    for _mt in _module_types[4:]:
        _rb = tk.Radiobutton(
            mod_type_erow,
            text=_mt,
            variable=module_type_var,
            value=_mt,
            font=("Helvetica", 11),
            bg=_C_MOD,
        )
        _rb.pack(side="left", padx=8)
        mt_radios.append(_rb)

    # — Module Ref sub-row —
    mod_ref_lrow = tk.Frame(mod_band, bg=_C_MOD)
    mod_ref_lrow.pack(fill="x", pady=(0, 2))
    mod_ref_erow = tk.Frame(mod_band, bg=_C_MOD)
    mod_ref_erow.pack(fill="x", pady=(0, 2))

    _band_label(mod_ref_lrow, "Module Ref / Master ID", _C_MOD, _F)

    module_ref_cell = tk.Frame(mod_ref_erow, bg=_C_MOD)
    module_ref_cell.pack(side="left", fill="x", expand=True)

    # Plain entry — default (non-FD)
    module_ref_entry = tk.Entry(module_ref_cell, width=50, font=_F)
    module_ref_entry.pack(side="left")
    apply_entry_theme(module_ref_entry)
    bind_tooltip(
        module_ref_entry,
        tooltip_var,
        "Integer product ID (e.g. loan_master_id). Not required for NONE.",
    )

    # FD sub-frame — hidden until FD is selected
    fd_cell = tk.Frame(module_ref_cell, bg=_C_MOD)

    fd_combo = ttk.Combobox(fd_cell, width=40)
    fd_combo.pack(side="left", padx=(0, 6))
    apply_entry_theme(fd_combo)
    bind_tooltip(fd_combo, tooltip_var, "Select an active Fixed Deposit product.")

    def _rebuild_fd_combo():
        nonlocal fd_map
        fd_rows = get_active_fd_masters()
        fd_map = {r[1]: r[0] for r in fd_rows}
        fd_combo["values"] = list(fd_map.keys())
        progressive_selection(fd_combo, list(fd_map.keys()))
        if fd_combo["values"]:
            fd_combo.set(fd_combo["values"][0])
        else:
            fd_combo.set("")

    def _open_fd_new():
        acct_name = account_combo.get()
        if not acct_name or acct_name not in account_map:
            show_colorful_error(
                win, "Validation", "Select an account before adding a new FD."
            )
            return

        def _on_fd_saved(_new_id, fd_number):
            _rebuild_fd_combo()
            fd_combo.set(fd_number)

        show_fd_new_modal(win, account_map[acct_name], on_escape, _on_fd_saved)

    new_fd_btn = tk.Button(
        fd_cell,
        text="New",
        command=_open_fd_new,
        font=("Helvetica", 11, "bold"),
        bg=_BTN_BG,
        fg=_BTN_FG,
        cursor="hand2",
        padx=8,
        pady=2,
        relief="raised",
        bd=2,
    )
    new_fd_btn.pack(side="left")
    apply_button_animations(
        new_fd_btn,
        _BTN_BG,
        BANK_TRANSACTION_ADD_UI_THEME["hover_bg"],
    )

    # CC sub-frame — hidden until CC is selected
    cc_cell = tk.Frame(module_ref_cell, bg=_C_MOD)

    cc_combo = ttk.Combobox(cc_cell, width=40)
    cc_combo.pack(side="left", padx=(0, 6))
    apply_entry_theme(cc_combo)
    bind_tooltip(cc_combo, tooltip_var, "Select an active Credit Card.")

    def _rebuild_cc_combo():
        nonlocal cc_map
        cc_rows = _db_get_all_card_masters()
        # label: "CardName (xxxx)" using last 4 digits of card number
        cc_map = {
            f"{r[1]} ({str(r[2])[-4:] if r[2] else 'N/A'})": r[0] for r in cc_rows
        }
        cc_combo["values"] = list(cc_map.keys())
        progressive_selection(cc_combo, list(cc_map.keys()))
        if cc_combo["values"]:
            cc_combo.set(cc_combo["values"][0])
        else:
            cc_combo.set("")

    # ── Module-type change handler ─────────────────────────────────────────
    def _on_module_type_change(*_):
        if module_type_var.get() == "FD":
            module_ref_entry.pack_forget()
            cc_cell.pack_forget()
            _rebuild_fd_combo()
            fd_cell.pack(side="left")
        elif module_type_var.get() == "CC":
            module_ref_entry.pack_forget()
            fd_cell.pack_forget()
            _rebuild_cc_combo()
            cc_cell.pack(side="left")
        else:
            fd_cell.pack_forget()
            cc_cell.pack_forget()
            module_ref_entry.pack(side="left")

    module_type_var.trace_add("write", _on_module_type_change)

    # ── Value Dt → Trans Dt sync ──────────────────────────────────────────
    def _sync_trans_dt(*_):
        try:
            trans_dt.set_date(value_dt.get_date())
        except Exception:  # noqa: BLE001
            pass

    value_dt.bind("<<DateEntrySelected>>", _sync_trans_dt)
    value_dt.bind("<FocusOut>", _sync_trans_dt)

    # ── Date Spinbox Helper ───────────────────────────────────────────────
    bind_date_spin(value_dt, callback=_sync_trans_dt)
    bind_date_spin(trans_dt)

    # ── Account change → Value Dt default ─────────────────────────────────
    # ── Account change → Value Dt default ─────────────────────────────────
    def _on_account_change(*_):
        acct_name = account_combo.get()
        if not acct_name or acct_name not in account_map:
            return

        # --- NEW GUARD ---
        # If Pair ID is populated (e.g., via auto-fill), we are completing a transfer.
        # Do NOT auto-advance the dates; they must strictly match the originating side.
        if not pair_id_var.get().strip():
            try:
                last_dt = get_last_trans_date(account_map[acct_name])
                default_dt = (
                    _next_working_day(last_dt)
                    if last_dt
                    else _next_working_day(_date.today())
                )
                value_dt.set_date(default_dt)
                trans_dt.set_date(default_dt)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Value Dt default failed: %s", exc)
        # -----------------

        try:
            last_serial = get_last_serial_no(account_map[acct_name])
            serial_no_entry.delete(0, tk.END)
            if last_serial is not None:
                serial_no_entry.insert(0, str(last_serial + 1))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Serial No default failed: %s", exc)
        try:
            _prev_balance[0] = _prev_bal.get(acct_name)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Last balance fetch failed: %s", exc)
        _update_balance_default(
            win, _prev_balance, withdrawal_entry, deposit_entry, balance_entry
        )

    account_combo.bind("<<ComboboxSelected>>", _on_account_change)
    win.after(50, _on_account_change)

    # ── Auto-fill Balance ─────────────────────────────────────────────────
    _bal_updater = lambda e=None: _update_balance_default(
        win, _prev_balance, withdrawal_entry, deposit_entry, balance_entry, e
    )
    withdrawal_entry.bind("<FocusOut>", _bal_updater, add="+")
    deposit_entry.bind("<FocusOut>", _bal_updater, add="+")
    withdrawal_entry.bind("<KeyRelease>", _bal_updater, add="+")
    deposit_entry.bind("<KeyRelease>", _bal_updater, add="+")

    # Normalize all three amount fields to 2 d.p. on focus-out
    withdrawal_entry.bind(
        "<FocusOut>", lambda e: _fmt_amount_on_focus_out(withdrawal_entry), add="+"
    )
    deposit_entry.bind(
        "<FocusOut>", lambda e: _fmt_amount_on_focus_out(deposit_entry), add="+"
    )
    balance_entry.bind(
        "<FocusOut>", lambda e: _fmt_amount_on_focus_out(balance_entry), add="+"
    )

    # ── Reset form ────────────────────────────────────────────────────────
    def _reset_form():
        cheque_no_entry.delete(0, tk.END)
        bank_remark_entry.delete(0, tk.END)
        user_desc_combo.set("")
        withdrawal_entry.delete(0, tk.END)
        withdrawal_entry.insert(0, "0.00")
        deposit_entry.delete(0, tk.END)
        deposit_entry.insert(0, "0.00")
        balance_entry.delete(0, tk.END)
        pair_id_var.set("")
        budget_head_combo.set("(none)")
        module_type_var.set("NONE")
        module_ref_entry.delete(0, tk.END)
        entry_type_var.set("INCOME")
        _rebuild_prev_bal()
        _on_account_change()
        account_combo.focus_set()

    # ── Commit to database ────────────────────────────────────────────────
    def _do_commit(
        account_name,
        value_date_str,
        trans_date_str,
        serial_no,
        cheque_no,
        bank_desc,
        user_desc,
        withdrawal_amount,
        deposit_amount,
        balance_after,
        pair_id,
        bh_id,
        module_type,
        master_id,
        fd_kwargs,
    ):
        data = {
            "account_id": account_map[account_name],
            "serial_no": serial_no,
            "value_date": value_date_str,
            "trans_date": trans_date_str,
            "cheque_no": cheque_no,
            "bank_desc": bank_desc,
            "user_desc": user_desc,
            "withdrawal_amount": withdrawal_amount,
            "deposit_amount": deposit_amount,
            "balance_after": balance_after,
            "pair_id": pair_id,
            "bh_id": bh_id,
            "module_type": module_type,
            "master_id": master_id,
            "entry_type": entry_type_var.get(),
        }
        data.update(fd_kwargs)
        try:
            new_trans_id = _db_add_transaction(data)
        except Exception as exc:  # noqa: BLE001
            show_colorful_error(win, "Error", f"Failed to add transaction: {exc}")
            return

        sr_no = len(current_session_txns) + 1
        current_session_txns[sr_no] = {
            "Account": account_name,
            "ValueDt": value_date_str,
            "TransDt": trans_date_str,
            "Withdrawal": withdrawal_amount,
            "Deposit": deposit_amount,
            "Balance": balance_after,
            "BankRemark": bank_desc,
            "SerialNo": serial_no,
            "ModuleType": module_type,
        }
        global _last_used_account
        _last_used_account = account_name

        if entry_type_var.get() == "TRANSFER" and not pair_id and module_type == "NONE":
            do_auto_fill = show_colorful_yesno(
                win,
                "Transfer Saved",
                "Transaction added successfully!\n\nWould you like to "
                "auto-fill the receiving side of this transfer?",
            )
            if do_auto_fill:
                withdrawal_entry.delete(0, tk.END)
                withdrawal_entry.insert(0, f"{deposit_amount:.2f}")
                deposit_entry.delete(0, tk.END)
                deposit_entry.insert(0, f"{withdrawal_amount:.2f}")
                pair_id_var.set(str(new_trans_id))
                account_combo.set("")
                balance_entry.delete(0, tk.END)
                _prev_balance[0] = None
                account_combo.focus_set()
                return

        show_colorful_info(win, "Success", "Transaction added successfully.")
        _reset_form()

    # ── Submit / validation ────────────────────────────────────────────────
    def on_submit(_event=None):
        account_name = account_combo.get()
        if not account_name or account_name not in account_map:
            show_colorful_error(
                win, "Validation Error", "Please select a valid account."
            )
            flash_error(account_combo)
            return

        value_date_str = value_dt.get_date().strftime("%Y-%m-%d")
        trans_date_str = trans_dt.get_date().strftime("%Y-%m-%d")

        # Convert empty spinbox text string directly into an integer or None (NULL)
        serial_no_raw = serial_no_entry.get().strip()
        serial_no = int(serial_no_raw) if serial_no_raw else None

        cheque_no = cheque_no_entry.get().strip() or None
        bank_desc = bank_remark_entry.get().strip() or None
        user_desc = user_desc_combo.get().strip() or None

        try:
            withdrawal_str = withdrawal_entry.get().strip().replace(",", "")
            withdrawal_amount = float(withdrawal_str or "0")
            if withdrawal_amount < 0:
                raise ValueError
        except ValueError:
            show_colorful_error(
                win, "Validation Error", "Withdrawal must be a non-negative number."
            )
            flash_error(withdrawal_entry)
            return

        try:
            deposit_str = deposit_entry.get().strip().replace(",", "")
            deposit_amount = float(deposit_str or "0")
            if deposit_amount < 0:
                raise ValueError
        except ValueError:
            show_colorful_error(
                win, "Validation Error", "Deposit must be a non-negative number."
            )
            flash_error(deposit_entry)
            return

        if withdrawal_amount == 0.0 and deposit_amount == 0.0:
            show_colorful_error(
                win,
                "Validation Error",
                "At least one of Withdrawal or Deposit must be "
                "non-zero.",
            )
            flash_error(withdrawal_entry)
            return

        entry_type = entry_type_var.get()

        if entry_type == "INCOME":
            if deposit_amount <= 0 or withdrawal_amount != 0.0:
                show_colorful_error(
                    win,
                    "Validation Error",
                    "INCOME requires Deposit > 0 and Withdrawal = 0.",
                )
                flash_error(deposit_entry)
                return
        elif entry_type == "EXPENSE":
            if withdrawal_amount <= 0 or deposit_amount != 0.0:
                show_colorful_error(
                    win,
                    "Validation Error",
                    "EXPENSE requires Withdrawal > 0 and Deposit = 0.",
                )
                flash_error(withdrawal_entry)
                return
        # TRANSFER: inter-account movements may carry withdrawal, deposit, or
        # both sides simultaneously; pair_id links the counterpart row.
        # Mutual-exclusivity is not enforced for TRANSFER.

        try:
            balance_after = float(balance_entry.get().strip().replace(",", "") or "0")
        except ValueError:
            show_colorful_error(
                win, "Validation Error", "Balance must be a valid number."
            )
            flash_error(balance_entry)
            return

        if balance_after < 0:
            show_colorful_error(
                win,
                "Validation Error",
                f"Balance cannot be negative (\u20b9{balance_after:,.2f}). "
                "Please verify the amounts.",
            )
            flash_error(balance_entry)
            return

        pair_id_raw = pair_id_var.get().strip()
        pair_id: int | None = None
        if pair_id_raw:
            try:
                pair_id = int(pair_id_raw)
            except ValueError:
                show_colorful_error(
                    win, "Validation Error", "Pair ID must be an integer."
                )
                return

        bh_desc = budget_head_combo.get().strip()
        bh_id: int | None = budget_map.get(bh_desc)

        module_type = module_type_var.get()
        master_id: int | None = None

        if module_type == "FD":
            fd_number = fd_combo.get().strip()
            if not fd_number or fd_number not in fd_map:
                show_colorful_error(
                    win,
                    "Validation Error",
                    "Please select a valid FD from the dropdown.",
                )
                flash_error(fd_combo)
                return
            master_id = fd_map[fd_number]

        elif module_type == "CC":
            cc_label = cc_combo.get().strip()
            if not cc_label or cc_label not in cc_map:
                show_colorful_error(
                    win,
                    "Validation Error",
                    "Please select a valid Credit Card from the dropdown.",
                )
                flash_error(cc_combo)
                return
            master_id = cc_map[cc_label]

        elif module_type == "PPF":
            # Auto-resolve: expects exactly one row in ppf_master
            master_id = _db_get_ppf_master_id()
            if master_id is None:
                show_colorful_error(
                    win,
                    "Validation Error",
                    "Could not determine PPF account. "
                    "Ensure exactly one entry exists in ppf_master.",
                )
                return

        elif module_type != "NONE":
            ref_val = module_ref_entry.get().strip()
            if not ref_val:
                show_colorful_error(
                    win,
                    "Validation Error",
                    "Module Ref / Master ID is required when a module "
                    "type is selected.",
                )
                flash_error(module_ref_entry)
                return
            try:
                master_id = int(ref_val)
            except ValueError:
                show_colorful_error(
                    win,
                    "Validation Error",
                    "Module Ref / Master ID must be a whole number.",
                )
                flash_error(module_ref_entry)
                return

        # ── FD sub-ledger routing ─────────────────────────────────────────
        if module_type == "FD" and master_id is not None:

            if withdrawal_amount > 0:
                # Deposit INTO FD (bank account debited)
                _do_commit(
                    account_name,
                    value_date_str,
                    trans_date_str,
                    serial_no,
                    cheque_no,
                    bank_desc,
                    user_desc,
                    withdrawal_amount,
                    deposit_amount,
                    balance_after,
                    pair_id,
                    bh_id,
                    module_type,
                    master_id,
                    fd_kwargs={
                        "fd_saving": withdrawal_amount,
                        "fd_withdrawal": 0.0,
                        "fd_principal": 0.0,
                        "fd_int": 0.0,
                    },
                )
                return

            # Withdrawal FROM FD (bank account credited)
            principal_amount = _db_get_fd_principal(master_id)
            if principal_amount is None:
                show_colorful_error(
                    win,
                    "Error",
                    "Could not fetch FD principal amount. Check the FD record.",
                )
                return

            if deposit_amount >= principal_amount:
                # Full withdrawal / maturity
                _do_commit(
                    account_name,
                    value_date_str,
                    trans_date_str,
                    serial_no,
                    cheque_no,
                    bank_desc,
                    user_desc,
                    withdrawal_amount,
                    deposit_amount,
                    balance_after,
                    pair_id,
                    bh_id,
                    module_type,
                    master_id,
                    fd_kwargs={
                        "fd_saving": 0.0,
                        "fd_withdrawal": deposit_amount,
                        "fd_principal": principal_amount,
                        "fd_int": round(deposit_amount - principal_amount, 4),
                    },
                )
            else:
                # Partial withdrawal — prompt for manual breakdown
                def _on_partial(
                    p_comp,
                    i_comp,
                    _an=account_name,
                    _vd=value_date_str,
                    _td=trans_date_str,
                    _sn=serial_no,
                    _cn=cheque_no,
                    _bd=bank_desc,
                    _ud=user_desc,
                    _wa=withdrawal_amount,
                    _da=deposit_amount,
                    _ba=balance_after,
                    _pi=pair_id,
                    _bhi=bh_id,
                    _mt=module_type,
                    _mid=master_id,
                ):
                    _do_commit(
                        _an,
                        _vd,
                        _td,
                        _sn,
                        _cn,
                        _bd,
                        _ud,
                        _wa,
                        _da,
                        _ba,
                        _pi,
                        _bhi,
                        _mt,
                        _mid,
                        fd_kwargs={
                            "fd_saving": 0.0,
                            "fd_withdrawal": _da,
                            "fd_principal": p_comp,
                            "fd_int": i_comp,
                        },
                    )

                show_fd_partial_modal(win, deposit_amount, on_escape, _on_partial)
            return

        # ── PPF sub-ledger routing ────────────────────────────────────────
        if module_type == "PPF" and master_id is not None:
            last_ppf_bal = _db_get_last_ppf_balance(master_id)
            if withdrawal_amount > 0:
                new_ppf_bal = round(last_ppf_bal + withdrawal_amount, 2)
                _do_commit(
                    account_name,
                    value_date_str,
                    trans_date_str,
                    serial_no,
                    cheque_no,
                    bank_desc,
                    user_desc,
                    withdrawal_amount,
                    deposit_amount,
                    balance_after,
                    pair_id,
                    bh_id,
                    module_type,
                    master_id,
                    fd_kwargs={
                        "ppf_saving": withdrawal_amount,
                        "ppf_withdrawal": 0.0,
                        "ppf_description": "saving",
                        "ppf_balance": new_ppf_bal,
                    },
                )
            else:
                new_ppf_bal = round(last_ppf_bal - deposit_amount, 2)
                _do_commit(
                    account_name,
                    value_date_str,
                    trans_date_str,
                    serial_no,
                    cheque_no,
                    bank_desc,
                    user_desc,
                    withdrawal_amount,
                    deposit_amount,
                    balance_after,
                    pair_id,
                    bh_id,
                    module_type,
                    master_id,
                    fd_kwargs={
                        "ppf_saving": 0.0,
                        "ppf_withdrawal": deposit_amount,
                        "ppf_description": "withdrawal",
                        "ppf_balance": new_ppf_bal,
                    },
                )
            return

        # ── Non-FD commit ─────────────────────────────────────────────────
        _do_commit(
            account_name,
            value_date_str,
            trans_date_str,
            serial_no,
            cheque_no,
            bank_desc,
            user_desc,
            withdrawal_amount,
            deposit_amount,
            balance_after,
            pair_id,
            bh_id,
            module_type,
            master_id,
            fd_kwargs={},
        )

    # ── Button frame ──────────────────────────────────────────────────────
    btn_frame = tk.Frame(
        win,
        pady=8,
        bg=BANK_TRANSACTION_ADD_UI_THEME["main_bg"],
        relief="ridge",
        bd=2,
    )
    btn_frame.pack(fill="x", anchor="e", padx=10)

    submit_button = tk.Button(
        btn_frame,
        text="✅ SUBMIT ✅",
        width=12,
        # height=1,
        font=("Comic Sans MS", 12, "bold"),
        bg=_SUB_BG,
        fg="white",
        activebackground=_SUB_ACT,
        activeforeground="white",
        relief="raised",
        bd=3,
        cursor="hand2",
        command=on_submit,
    )
    submit_button.pack(side="right", padx=5, pady=6)
    apply_button_animations(submit_button, _SUB_BG, "#2563eb")

    cancel_btn = tk.Button(
        btn_frame,
        text="❌ Cancel ❌",
        width=12,
        # height=1,
        font=("Comic Sans MS", 12, "bold"),
        bg=_CAN_BG,
        fg="white",
        activebackground=_CAN_ACT,
        activeforeground="white",
        relief="raised",
        bd=3,
        cursor="hand2",
        # pady=10,
        command=cleanup_and_close,
    )
    cancel_btn.pack(side="right", padx=5, pady=6)
    apply_button_animations(cancel_btn, _CAN_BG, _CAN_ACT)

    # ── Hint frame ────────────────────────────────────────────────────────
    hint_frame = tk.Frame(
        win,
        pady=6,
        bg=BANK_TRANSACTION_ADD_UI_THEME["main_bg"],
        relief="ridge",
        bd=2,
    )
    hint_frame.pack(fill="x", anchor="e", padx=10)

    tk.Label(
        hint_frame,
        text="Press F1 for help, F2 for session transactions, Esc to "
        "close.",
        font=("Helvetica", 16),
        bg=BANK_TRANSACTION_ADD_UI_THEME["main_bg"],
    ).pack(side="left", padx=8)

    # ── Radio-button keyboard navigation (Left/Right cycle+select, Space select, Return advance) ──
    def _bind_radio_group(
        radios: list,
        var: tk.StringVar,
        values: list,
        next_focus_fn,
    ) -> None:
        """Bind Left/Right/Space/Return keyboard navigation on a group of "
        "radio buttons."""

        def _on_key(event):
            focused = event.widget
            try:
                idx = radios.index(focused)
            except ValueError:
                return
            keysym = event.keysym
            if keysym == "space":
                var.set(values[idx])
                focused.select()
            elif keysym == "Right":
                nxt = (idx + 1) % len(radios)
                radios[nxt].focus_set()
                var.set(values[nxt])
                radios[nxt].select()
            elif keysym == "Left":
                prv = (idx - 1) % len(radios)
                radios[prv].focus_set()
                var.set(values[prv])
                radios[prv].select()
            elif keysym == "Return":
                next_focus_fn()

        for _rb in radios:
            _rb.bind("<Key>", _on_key)

    def _mt_next_focus():
        if module_type_var.get() == "FD":
            fd_combo.focus_set()
        else:
            module_ref_entry.focus_set()

    _bind_radio_group(
        et_radios,
        entry_type_var,
        ["INCOME", "EXPENSE", "TRANSFER"],
        mt_radios[0].focus_set,
    )
    _bind_radio_group(mt_radios, module_type_var, _module_types, _mt_next_focus)

    # ── Return-key focus traversal (rows 0 → 12 → Submit) ────────────────
    account_combo.bind("<Return>", lambda e: serial_no_entry.focus_set())
    serial_no_entry.bind("<Return>", lambda e: value_dt.focus_set())
    value_dt.bind("<Return>", lambda e: trans_dt.focus_set())
    trans_dt.bind("<Return>", lambda e: cheque_no_entry.focus_set())
    cheque_no_entry.bind("<Return>", lambda e: bank_remark_entry.focus_set())
    bank_remark_entry.bind("<Return>", lambda e: withdrawal_entry.focus_set())
    withdrawal_entry.bind("<Return>", lambda e: deposit_entry.focus_set())
    deposit_entry.bind("<Return>", lambda e: balance_entry.focus_set())
    balance_entry.bind("<Return>", lambda e: pair_id_display.focus_set())
    pair_id_display.bind("<Return>", lambda e: budget_head_combo.focus_set())
    budget_head_combo.bind("<Return>", lambda e: user_desc_combo.focus_set())
    user_desc_combo.bind("<Return>", lambda e: et_radios[0].focus_set())
    module_ref_entry.bind("<Return>", lambda e: submit_button.focus_set())
    fd_combo.bind("<Return>", lambda e: submit_button.focus_set())
    submit_button.bind("<Return>", lambda e: on_submit())

    # ── Global hotkeys ────────────────────────────────────────────────────
    win.bind("<F1>", lambda e: show_master_help(win, on_escape))
    win.bind(
        "<F2>",
        lambda e: show_session_transactions(win, current_session_txns, on_escape),
    )
    # F3 is now obsolete since Budget Heads are inside the F1 notebook
    win.bind("<F3>", lambda e: "break")
    win.bind("<Escape>", on_escape)
    win.protocol("WM_DELETE_WINDOW", cleanup_and_close)

    # ── Prefill application ────────────────────────────────────────────────
    if prefill_withdrawal is not None:
        withdrawal_entry.delete(0, tk.END)
        withdrawal_entry.insert(0, f"{prefill_withdrawal:.2f}")
    if prefill_deposit is not None:
        deposit_entry.delete(0, tk.END)
        deposit_entry.insert(0, f"{prefill_deposit:.2f}")
    if prefill_pair_id is not None:
        pair_id_var.set(str(prefill_pair_id))
    if prefill_val_date is not None:
        try:
            value_dt.set_date(datetime.strptime(prefill_val_date, "%Y-%m-%d"))
        except Exception:
            pass
    if prefill_trans_date is not None:
        try:
            trans_dt.set_date(datetime.strptime(prefill_trans_date, "%Y-%m-%d"))
        except Exception:
            pass
    if prefill_serial is not None:
        serial_no_entry.delete(0, tk.END)
        serial_no_entry.insert(0, str(prefill_serial))
    if prefill_cheque:
        cheque_no_entry.delete(0, tk.END)
        cheque_no_entry.insert(0, prefill_cheque)
    if prefill_bank_desc:
        bank_remark_entry.delete(0, tk.END)
        bank_remark_entry.insert(0, prefill_bank_desc)
    if prefill_user_desc:
        user_desc_combo.set(prefill_user_desc)
    if prefill_bh_id is not None:
        bh_name = next((name for name, bid in budget_map.items() if bid == prefill_bh_id), None)
        if bh_name:
            budget_head_combo.set(bh_name)
            if bh_type_map.get(bh_name) == "INCOME":
                entry_type_var.set("INCOME")
            elif bh_type_map.get(bh_name) == "EXPENSE":
                entry_type_var.set("EXPENSE")
        else:
            budget_head_combo.set("(none)")
            entry_type_var.set("TRANSFER")
    elif prefill_pair_id is not None:
        entry_type_var.set("TRANSFER")

    # ── Initial focus ─────────────────────────────────────────────────────
    win.after(100, account_combo.focus_set)
