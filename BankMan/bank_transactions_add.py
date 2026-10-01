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
from Shared.help_utils import show_standard_help
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
    get_last_ppf_balance as _db_get_last_ppf_balance,
    get_budget_heads_with_parents as _db_get_bh_with_parents,
    get_all_card_masters as _db_get_all_card_masters,
    get_all_user_descriptions,
    get_active_ppf_masters as get_all_ppf_masters,
    db_add_ppf_master,
    get_all_loan_masters_for_display,
    get_stock_computed_bank_entries,
    get_stock_actual_bank_entries,
    db_add_stock_actual_bank,
    get_active_mf_masters,
    db_add_mf_master,
    get_active_ins_masters,
    db_add_ins_master,
)
from Shared.globals import logger, UI_THEME
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


def show_master_help(
    win: tk.Toplevel,
    on_escape,
    focus_back_widget: tk.Widget | None = None,
) -> None:
    """Launch a standardized tabbed help window for Bank Transactions."""
    
    guide_lines = [
        "• This form records a new bank statement transaction.",
        "",
        "Fields:",
        "  Account      — Select the bank account.  Defaults to last-used.",
        "  Serial No    — Optional bank serial / reference number.",
        "  Value Dt     — Date the bank applied this transaction for interest purposes.",
        "  Trans Dt     — Calendar date the event was initiated. Auto-syncs to Value Dt.",
        "  Cheque No    — Cheque reference for cheque-based transactions.",
        "  Bank Remark  — Narration as printed on the bank statement.",
        "  Withdrawal   — Amount leaving the account (debit). Enter 0 if N/A.",
        "  Deposit      — Amount entering the account (credit). Enter 0 if N/A.",
        "  Balance      — Running balance after this transaction.",
        "  Pair ID      — Links this row to an opposite transfer row. Click 'Select' to browse.",
        "  Budget Head  — Budget category for analysis reports.",
        "  Module Type  — NONE for plain transactions; choose FD, CC, LOAN, PPF, STOCK_COMP, STOCK_ACTU, MF, or INS to link to a specialist sub-ledger.",
        "  Module Ref   — Select the active product from the dynamic dropdown (FD, CC, LOAN, PPF, STOCK_COMP, STOCK_ACTU, MF, or INS). Use the 'New' button to create a new master record on the fly.",
        "",
        "FD Logic:",
        "  Withdrawal > 0  →  Deposit into FD (fd_saving entry).",
        "  Deposit > 0     →  Maturity / partial withdrawal from FD.",
        "    Full (deposit ≥ principal): auto-splits principal + interest.",
        "    Partial (deposit < principal): prompts for manual breakdown.",
    ]

    faq_data = [
        (
            "Q1 [General]: How do I decide between INCOME, EXPENSE, and TRANSFER?",
            "A: Ask yourself whether your net worth changed or if money simply moved between two places you own/track:\n\n"
            "   1. INCOME (Money earned/received from outside):\n"
            "      - Enter amount in 'Deposit', 0 in 'Withdrawal'.\n"
            "      - Pick an INCOME Budget Head (e.g., Pension, SB Interest, Dividend).\n"
            "      - Entry Type: INCOME.\n\n"
            "   2. EXPENSE (Money spent permanently):\n"
            "      - Enter amount in 'Withdrawal', 0 in 'Deposit'.\n"
            "      - Pick an EXPENSE Budget Head (e.g., Electricity, Groceries).\n"
            "      - Entry Type: EXPENSE.\n\n"
            "   3. TRANSFER (Money moving between your own accounts, investments, or loans):\n"
            "      - Set Budget Head to '(none)' and Entry Type to 'TRANSFER'.\n"
            "      - Either pair it with another bank/cash account using 'Pair ID', OR link it to a specialist sub-ledger using 'Module Type' (FD, CC, LOAN, PPF, STOCK_COMP, STOCK_ACTU, MF, INS)."
        ),
        (
            "Q2 [A1 - PPF]: How do I record PPF deposits, withdrawals, and multiple PPF accounts over time?",
            "A: PPF is an asset transfer, not an expense.\n\n"
            "   1. Set Budget Head = '(none)' and Entry Type = 'TRANSFER'.\n"
            "   2. Select Module Type = 'PPF'.\n"
            "   3. From the dropdown, select the specific PPF account (active or historical). If you opened a new PPF account, click 'New' next to the dropdown to register it on the fly.\n"
            "   4. For a deposit into PPF: enter the amount in 'Withdrawal' (money leaving savings).\n"
            "   5. For a maturity/partial withdrawal from PPF: enter the amount in 'Deposit' (money entering savings)."
        ),
        (
            "Q3 [A2 - Fixed Deposits & Auto-Sweep]: How do I record normal FDs and Flexible (Auto-Sweep) FDs?",
            "A: Both standard FDs and Flexible/Auto-Sweep FDs use Module Type = 'FD':\n\n"
            "   1. Opening / Sweep-Out (Savings -> FD):\n"
            "      - Enter the amount in 'Withdrawal', Deposit = 0.\n"
            "      - Budget Head = '(none)', Entry Type = 'TRANSFER', Module Type = 'FD'.\n"
            "      - Click 'New' to create the FD if it is a new receipt, or pick the existing FD.\n\n"
            "   2. Partial Sweep-In (Flexible FD -> Savings when balance drops below threshold):\n"
            "      - Enter the amount received in 'Deposit', Withdrawal = 0.\n"
            "      - Select Module Type = 'FD' and pick the Flexible FD.\n"
            "      - Because Deposit < Remaining Principal, a popup will automatically ask you to split the amount between Principal Repaid and Interest Earned!\n\n"
            "   3. Full Maturity (FD -> Savings):\n"
            "      - Enter total maturity amount in 'Deposit', select the FD, and submit. The system automatically splits Remaining Principal and Interest!"
        ),
        (
            "Q4 [A3 - Mutual Funds]: How do I record SIPs, Lump-Sum Purchases, and Redemptions across AMCs/CAMS?",
            "A: Mutual Fund investments are asset transfers:\n\n"
            "   1. Set Budget Head = '(none)', Entry Type = 'TRANSFER', and Module Type = 'MF'.\n"
            "   2. Select the AMC/Scheme/Folio from the dropdown, or click 'New' to register a new folio (specifying AMC like ICICI Pru, HDFC, Nippon, and RTA like CAMS or KFintech).\n"
            "   3. Purchase / SIP: Put the amount in 'Withdrawal' (logged as mf_purchase).\n"
            "   4. Redemption: Put the amount in 'Deposit' (logged as mf_redemption)."
        ),
        (
            "Q5 [A4 - Insurance]: How do I handle Term Life, Health, Vehicle, and General Insurance vs. Endowment/ULIP plans?",
            "A: All insurance policies can be linked using Module Type = 'INS' (click 'New' to record Company, Category, Policy No, Proposer, and Life Assured / Vehicle), but their Entry Type depends on whether they build a cash value:\n\n"
            "   1. Pure Protection (Term Life, Health, Car/Vehicle, General Insurance):\n"
            "      - These do not return principal. Record Withdrawal > 0, pick an EXPENSE Budget Head ('Life Insurance - Self/Family', 'Health Insurance', 'Auto Insurance'), set Entry Type = 'EXPENSE', and set Module Type = 'INS' to link the policy!\n\n"
            "   2. Savings / Investment Policies (LIC Endowment, Money-Back, ULIP, TATA AIG, Kotak, ICICI Pru):\n"
            "      - If you want to track premiums as an expense: map like (1) above.\n"
            "      - If you want to track accumulated principal as an Asset: set Budget Head = '(none)', Entry Type = 'TRANSFER', and Module Type = 'INS' (Category: LIFE_SAVINGS)."
        ),
        (
            "Q6 [A5 - STOCK_COMP (Computed Bank)]: What is STOCK_COMP and how do I record entries for it?",
            "A: STOCK_COMP links a bank passbook entry to 'computed_bank' in StockMan (which holds exact, system-calculated obligations from Contract Notes, Dividends, IPO/Rights Allotments, and Merger Refunds).\n\n"
            "   • WHEN TO USE IT:\n"
            "     1. Dividends credited directly to your bank account.\n"
            "     2. IPO / Rights Issue (ASBA) bank debits or fractional share refunds.\n"
            "     3. 3-in-1 accounts (like ICICI Direct) where the exact bill of a single Contract Note is debited/credited directly in your bank passbook.\n\n"
            "   • HOW TO ENTER:\n"
            "     1. First, ensure the Trade, Dividend, or Allotment is already recorded in StockMan (StockMan automatically creates the 'computed_bank' entry; hence there is no 'New' button here).\n"
            "     2. In BankMan, enter the Withdrawal or Deposit amount.\n"
            "     3. Set Budget Head = '(none)' and Entry Type = 'TRANSFER' (or pick an INCOME head for Dividends if you track dividend income in BankMan).\n"
            "     4. Select Module Type = 'STOCK_COMP' and pick the matching Contract Note / Dividend row (#ID | Date | Type | Amount | Cont_No) from the dropdown.\n"
            "     5. Click Submit. BankMan stores 'id_comp_bt' in 'module_ref_id', linking your bank passbook directly to that StockMan event!"
        ),
        (
            "Q7 [A5 - STOCK_ACTU (Actual Bank)]: What is STOCK_ACTU and how do I record Broker Transfers (Zerodha, Jhaveri Sec, ICICI Sec)?",
            "A: STOCK_ACTU links a bank passbook entry to 'actual_bank' in StockMan (which tracks lump-sum funds transferred to or withdrawn from your stockbroker's trading wallet/ledger).\n\n"
            "   • WHEN TO USE IT:\n"
            "     Whenever you transfer a lump sum (pay-in) to a broker like Zerodha, Jhaveri Securities, or ICICI Securities, or receive a lump-sum payout back from the broker into your bank account.\n\n"
            "   • HOW TO ENTER & MECHANISM:\n"
            "     1. In BankMan, enter the lump-sum pay-in in 'Withdrawal' (or payout in 'Deposit').\n"
            "     2. Set Budget Head = '(none)' and Entry Type = 'TRANSFER'.\n"
            "     3. Select Module Type = 'STOCK_ACTU'.\n"
            "     4. If you haven't logged this transfer in StockMan yet, click the 'New' button next to the dropdown! A modal will open pre-filled with the Date, Type (DEBIT for bank withdrawal / CREDIT for bank deposit), Amount, and Broker Description.\n"
            "     5. Click Save in the modal—this directly inserts a new row into StockMan's 'actual_bank' table and auto-selects it in the dropdown.\n"
            "     6. Click Submit on the main form to save the bank transaction with 'id_actu_bt' linked in 'module_ref_id'!"
        ),
        (
            "Q8 [B - Petty Cash]: How do I map ATM Cash Withdrawals and Cash Deposits?",
            "A: Cash in hand is tracked via your 'Petty Cash' account (Bank: My Home), so moving cash between Bank and Hand is a TRANSFER:\n\n"
            "   - ATM Withdrawal: Enter a Withdrawal in your Savings account with Budget Head = '(none)' and Entry Type = 'TRANSFER'. Submit and click 'Yes' on the auto-fill prompt to record the matching Deposit into 'Petty Cash'.\n"
            "   - Cash Deposit into Bank: Enter a Withdrawal from 'Petty Cash' with Entry Type = 'TRANSFER', and pair it with a Deposit in your Savings account."
        ),
        (
            "Q9 [B - Negative Petty Cash]: My Petty Cash or Suspense account shows a negative balance. Is that okay?",
            "A: Yes! At the start of historical data entry, you may not know your exact opening cash in hand, or a suspense/reversal entry may temporarily dip below zero. When the balance turns red/negative, click 'Yes' on the Negative Balance Warning prompt to allow it."
        ),
        (
            "Q10 [C - Credit Cards]: How do I map Credit Card bill payments when multiple cards share an account?",
            "A: A credit card bill payment pays off a liability, so it is a TRANSFER (individual card swipes are already recorded as Expenses in the CC ledger):\n\n"
            "   - Account: Your Savings/Current Account.\n"
            "   - Withdrawal: Exact bill amount paid (Deposit = 0).\n"
            "   - Budget Head: '(none)' (Entry Type auto-sets to TRANSFER).\n"
            "   - Module Type: 'CC'.\n"
            "   - Module Ref: Select the specific Credit Card from the dropdown.\n"
            "   (Note: For old historical CC bills where you don't have the statement, choose Budget Head = 'Historical CC Payment', Entry Type = 'EXPENSE', and Module Type = 'NONE')."
        ),
        (
            "Q11 [D - Bank Loans]: How do I record Loan EMIs or prepayments?",
            "A: Select your Savings account, enter the EMI in 'Withdrawal', set Budget Head = '(none)', Entry Type = 'TRANSFER', and Module Type = 'LOAN'. Then select the active Loan account from the Module Ref dropdown."
        ),
        (
            "Q12 [E - Friends & Family]: How do I record money lent to or borrowed from friends/family, or transfers from a minor child's account?",
            "A: Money exchanged with friends or transferred within the family corpus is NOT an income or expense—treat it as a TRANSFER:\n\n"
            "   1. Setup: Create a Bank called 'Friends & Family Ledger' (or 'My Home' for family) and add an Account for that person (or a general 'Friendly Loans' account, noting the person's name in 'User Desc').\n"
            "   2. Lending / Giving temporary funds: Record a Withdrawal from your Savings/Petty Cash (Budget Head = '(none)', Entry Type = 'TRANSFER') and pair it with a Deposit into their ledger account.\n"
            "   3. Receiving repayment / Borrowing / Child Account Transfer: Record a Deposit into your Savings account (Entry Type = 'TRANSFER') and pair it with a Withdrawal from their ledger account (allow negative balance if you borrowed first)."
        ),
        (
            "Q13 [F - Cash Expenses]: How do I record specific expenses paid in cash?",
            "A: Select your 'Petty Cash' account in the Account dropdown! Enter the amount spent in 'Withdrawal', Deposit = 0, pick the relevant EXPENSE Budget Head (e.g., 'Groceries & Daily Needs' or 'Miscellaneous Cash Expenses'), and set Entry Type = 'EXPENSE'."
        ),
        (
            "Q14 [G - Social Obligations]: How do I record cash blessings or gifts given to younger relatives on festivals/marriages?",
            "A: Whether given in cash (from 'Petty Cash' account) or via bank/UPI (from your Savings account):\n\n"
            "   - Enter the amount in 'Withdrawal' (Deposit = 0).\n"
            "   - Select Budget Head = 'Festival Blessings & Cash Gifts' or 'Marriage & Event Gifts' (under 'Social & Family Obligations').\n"
            "   - Set Entry Type = 'EXPENSE' and add the relative's name/event in 'User Desc'."
        ),
        (
            "Q15 [H - Social Responsibilities]: How do I record charitable donations made on various occasions?",
            "A: Select the account used (Savings or Petty Cash), enter the amount in 'Withdrawal', select the appropriate EXPENSE Budget Head under 'Giving & Charity' ('Social Responsibilities & Occasions', 'Medical Donations', 'Education Charity', or 'General Charity'), and set Entry Type = 'EXPENSE'."
        ),
        (
            "Q16 [Reversals & Bank Mistakes]: How do I map an erroneous bank charge or failed transaction that is reversed later?",
            "A: Mapping the debit as an Expense and the credit as Income would artificially inflate your totals. Instead, use your 'ReverseEntry' (Account 1234) suspense account:\n\n"
            "   1. Wrong Debit: Record a Withdrawal in Savings with Budget Head = '(none)' and Entry Type = 'TRANSFER', paired with a Deposit in 'ReverseEntry'.\n"
            "   2. Bank Reversal/Refund: Record a Deposit in Savings with Budget Head = '(none)' and Entry Type = 'TRANSFER', paired with a Withdrawal from 'ReverseEntry'."
        ),
    ]

    # We use a custom callback to build the Budget Heads Reference tab
    def inject_budget_heads_tab(notebook):
        try:
            bh_rows = _db_get_bh_with_parents()
        except Exception as exc:
            logger.warning("budget heads fetch failed: %s", exc)
            bh_rows = []

        tab_budget = tk.Frame(notebook, bg="#f0f9ff")
        notebook.add(tab_budget, text="Budget Heads Reference")

        search_frame = tk.Frame(tab_budget, bg="#e0f2fe", pady=5)
        search_frame.pack(fill="x", padx=10, pady=(6, 0))
        tk.Label(search_frame, text="Search:", font=("Helvetica", 11, "bold"), bg="#e0f2fe", fg="#0369a1").pack(side="left", padx=(6, 4))
        
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var, font=("Helvetica", 12), width=32, bg="#fff", fg="#0c4a6e", insertbackground="#0369a1", relief="solid", bd=1)
        search_entry.pack(side="left", padx=4)

        clear_btn = tk.Button(search_frame, text="✕", font=("Helvetica", 10, "bold"), bg="#bae6fd", fg="#0369a1", bd=0, padx=6, pady=2, cursor="hand2", command=lambda: search_var.set(""))
        apply_button_animations(clear_btn, "#bae6fd", "#a5d8ff")
        clear_btn.pack(side="left", padx=2)
        match_label = tk.Label(search_frame, text="", font=("Helvetica", 10), bg="#e0f2fe", fg="#0369a1")
        match_label.pack(side="left", padx=8)

        text_frame = tk.Frame(tab_budget, bg="#f0f9ff")
        text_frame.pack(fill="both", expand=True, padx=10, pady=6)
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        bh_text_widget = tk.Text(text_frame, wrap="word", bg="#f8fafc", fg="#0c4a6e", font=("Helvetica", 11), padx=10, pady=8, bd=1, relief="solid", yscrollcommand=scrollbar.set, state="disabled")
        bh_text_widget.pack(fill="both", expand=True)
        scrollbar.config(command=bh_text_widget.yview)

        bh_text_widget.tag_configure("section", font=("Helvetica", 12, "bold"), foreground="#0369a1")
        bh_text_widget.tag_configure("header", font=("Helvetica", 10, "bold"), foreground="#64748b")
        bh_text_widget.tag_configure("income", font=("Helvetica", 11), foreground="#166534")
        bh_text_widget.tag_configure("expense", font=("Helvetica", 11), foreground="#9a3412")
        bh_text_widget.tag_configure("highlight", background="#fef08a", foreground="#0c4a6e")

        income_rows = [(desc, parent) for _, desc, btype, parent in bh_rows if btype == "INCOME"]
        expense_rows = [(desc, parent) for _, desc, btype, parent in bh_rows if btype == "EXPENSE"]

        bh_text_widget.config(state="normal")
        bh_text_widget.insert("end", "─" * 20 + " Income items\n", "section")
        bh_text_widget.insert("end", "IBH  Income Budget Head          IPH  Income Parent Head\n\n", "header")
        for desc, parent in income_rows:
            bh_text_widget.insert("end", f"  (IBH {desc}    IPH {parent})\n", "income")
        bh_text_widget.insert("end", "\n" + "─" * 20 + " Expense items\n", "section")
        bh_text_widget.insert("end", "EBH  Expense Budget Head         EPH  Expense Parent Head\n\n", "header")
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

    # Let the user still trigger submit with Ctrl+Return from within help
    # if it was bound originally on the parent
    def _override_escape_in_help(nb):
        pass # The standardized help binds escape properly

    show_standard_help(
        parent=win,
        title="Bank Transaction Help Center",
        guide_lines=guide_lines,
        faq_data=faq_data,
        extra_tabs_callback=inject_budget_heads_tab
    )

def show_session_transactions(
    win: tk.Toplevel,
    current_session_txns: dict,
    on_escape,
    focus_back_widget: tk.Widget | None = None,
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
        win.bind("<Control-Return>", lambda e: submit_button.invoke())

        win.bind("<Escape>", on_escape)
        if focus_back_widget:
            try:
                focus_back_widget.focus_set()
            except Exception:
                pass
        return "break"

    viewer.bind("<Control-Return>", lambda e: submit_button.invoke())
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
        win.bind("<Control-Return>", lambda e: submit_button.invoke())

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

    modal.bind("<Control-Return>", lambda e: submit_button.invoke())
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
        win.bind("<Control-Return>", lambda e: submit_button.invoke())

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
    modal.bind("<Control-Return>", lambda e: submit_button.invoke())
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
        win.bind("<Control-Return>", lambda e: submit_button.invoke())

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
        balance_entry.config(foreground="red")
    else:
        try:
            balance_entry.config(foreground=UI_THEME["fg_input"])
        except (NameError, KeyError, tk.TclError):
            balance_entry.config(foreground="yellow")


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



# ---------------------------------------------------------------------------
# New PPF modal
# ---------------------------------------------------------------------------

def show_ppf_new_modal(
    win,
    account_id: int,
    on_escape,
    on_ppf_saved,  # callback(ppf_master_id, display_label)
) -> None:
    """Modal to create a new ppf_master entry and auto-select it in the parent."""
    win.unbind("<Escape>")

    modal = tk.Toplevel(win)
    modal.title("New PPF Account")
    modal.transient(win)
    modal.grab_set()
    modal.geometry("500x400")
    modal.resizable(False, False)
    modal.configure(bg="#1e293b")
    push_window(modal, win)
    try:
        modal.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        modal,
        text="New PPF Account",
        font=("Helvetica", 14, "bold"),
        bg="#784212",
        fg="white",
        pady=8,
    ).pack(fill="x")

    form = tk.Frame(modal, bg="#1e293b", padx=16, pady=12)
    form.pack(fill="both", expand=True)

    _fields = [
        ("PPF Account No:", "ppf_account_number", "entry"),
        ("Holder Name:", "holder_name", "entry"),
        ("Open Date:", "open_dt", "date"),
        ("Maturity Date:", "maturity_dt", "date"),
    ]
    _widgets = {}
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
        ppf_number = _widgets["ppf_account_number"].get().strip()
        holder = _widgets["holder_name"].get().strip()
        if not ppf_number:
            show_colorful_error(modal, "Validation", "PPF Account Number is required.")
            _widgets["ppf_account_number"].focus_set()
            return
        if not holder:
            show_colorful_error(modal, "Validation", "Holder Name is required.")
            _widgets["holder_name"].focus_set()
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
            new_id = db_add_ppf_master(
                {
                    "account_id": account_id,
                    "ppf_account_number": ppf_number,
                    "holder_name": holder,
                    "open_dt": open_dt,
                    "maturity_dt": maturity_dt,
                    "is_active": 1,
                }
            )
            _close()
            display_label = f"{ppf_number} - {holder} (Active)"
            on_ppf_saved(new_id, display_label)
        except Exception as exc:
            show_colorful_error(modal, "Error", f"Failed to save PPF: {exc}")

    def _close(_e=None):
        safe_close_modal(modal, win)
        win.bind("<Control-Return>", lambda e: win.event_generate("<<InvokeSubmit>>"))
        win.bind("<Escape>", on_escape)
        return "break"

    save_btn = tk.Button(
        btn_row,
        text="💾 Save PPF",
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
    modal.bind("<Control-Return>", lambda e: _save())
    modal.bind("<Escape>", _close)
    modal.protocol("WM_DELETE_WINDOW", _close)
    _widgets["ppf_account_number"].focus_set()



# ---------------------------------------------------------------------------
# Stock Actual Bank modal
# ---------------------------------------------------------------------------

def show_stock_actu_new_modal(
    win: tk.Toplevel,
    default_dt_str: str,
    withdrawal_amt: float,
    deposit_amt: float,
    default_desc: str,
    on_escape,
    on_saved,  # callback(new_id)
) -> None:
    """Modal to create a new actual_bank entry in StockMan."""
    win.unbind("<Escape>")

    modal = tk.Toplevel(win)
    modal.title("New Stock Actual Bank Entry")
    modal.transient(win)
    modal.grab_set()
    modal.geometry("500x380")
    modal.resizable(False, False)
    modal.configure(bg="#1e293b")
    push_window(modal, win)
    try:
        modal.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        modal,
        text="New Stock Actual Bank Entry",
        font=("Helvetica", 14, "bold"),
        bg="#784212",
        fg="white",
        pady=8,
    ).pack(fill="x")

    form = tk.Frame(modal, bg="#1e293b", padx=16, pady=12)
    form.pack(fill="both", expand=True)

    # Pre-populate
    default_type = "DEBIT" if withdrawal_amt > 0 else "CREDIT"
    default_amt = withdrawal_amt if withdrawal_amt > 0 else deposit_amt

    _fields = [
        ("Date:", "actu_bt_dt", "date"),
        ("Type (CREDIT/DEBIT):", "actu_bt_type", "entry"),
        ("Amount:", "actu_bt_amt", "entry"),
        ("Demat Broker/Desc:", "actu_bt_desc", "entry"),
    ]
    _widgets = {}
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
            try:
                from datetime import datetime
                w.set_date(datetime.strptime(default_dt_str, "%Y-%m-%d").date())
            except:
                pass
        else:
            w = tk.Entry(form, width=28, font=("Helvetica", 14))
        apply_entry_theme(w)
        w.grid(row=r, column=1, sticky="w", padx=4, pady=8)
        _widgets[key] = w

    _widgets["actu_bt_type"].insert(0, default_type)
    _widgets["actu_bt_amt"].insert(0, str(default_amt))
    _widgets["actu_bt_desc"].insert(0, default_desc)

    _keys = [f[1] for f in _fields]
    for _i, _k in enumerate(_keys[:-1]):
        _nxt = _keys[_i + 1]
        _widgets[_k].bind("<Return>", lambda e, n=_nxt: _widgets[n].focus_set())

    btn_row = tk.Frame(modal, bg="#1e293b")
    btn_row.pack(fill="x", padx=16, pady=12)

    def _save(_e=None):
        dt = _widgets["actu_bt_dt"].get_date().strftime("%Y-%m-%d")
        b_type = _widgets["actu_bt_type"].get().strip().upper()
        amt_str = _widgets["actu_bt_amt"].get().strip()
        desc = _widgets["actu_bt_desc"].get().strip()
        
        if b_type not in ("CREDIT", "DEBIT"):
            show_colorful_error(modal, "Validation", "Type must be CREDIT or DEBIT.")
            _widgets["actu_bt_type"].focus_set()
            return
            
        try:
            amt = float(amt_str)
        except ValueError:
            show_colorful_error(modal, "Validation", "Amount must be a number.")
            _widgets["actu_bt_amt"].focus_set()
            return

        try:
            new_id = db_add_stock_actual_bank(dt, b_type, amt, desc)
            _close()
            on_saved(new_id)
        except Exception as exc:
            show_colorful_error(modal, "Error", f"Failed to save: {exc}")

    def _close(_e=None):
        safe_close_modal(modal, win)
        win.bind("<Control-Return>", lambda e: win.event_generate("<<InvokeSubmit>>"))
        win.bind("<Escape>", on_escape)
        return "break"

    save_btn = tk.Button(
        btn_row,
        text="💾 Save",
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
    modal.bind("<Control-Return>", lambda e: _save())
    modal.bind("<Escape>", _close)
    modal.protocol("WM_DELETE_WINDOW", _close)
    _widgets["actu_bt_desc"].focus_set()



# ---------------------------------------------------------------------------
# MF / INS modals
# ---------------------------------------------------------------------------

def show_mf_new_modal(
    win: tk.Toplevel,
    account_id: int,
    on_escape,
    on_mf_saved,
) -> None:
    win.unbind("<Escape>")
    modal = tk.Toplevel(win)
    modal.title("New Mutual Fund")
    modal.transient(win)
    modal.grab_set()
    modal.geometry("500x380")
    modal.resizable(False, False)
    modal.configure(bg="#1e293b")
    push_window(modal, win)
    try:
        modal.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        modal,
        text="New Mutual Fund",
        font=("Helvetica", 14, "bold"),
        bg="#784212",
        fg="white",
        pady=8,
    ).pack(fill="x")

    form = tk.Frame(modal, bg="#1e293b", padx=16, pady=12)
    form.pack(fill="both", expand=True)

    _fields = [
        ("AMC Name:", "amc_name", "entry"),
        ("RTA (CAMS/KFintech/Direct):", "rta_name", "entry"),
        ("Folio Number:", "folio_number", "entry"),
        ("Scheme Name:", "scheme_name", "entry"),
    ]
    _widgets = {}
    for r, (lbl, key, wtype) in enumerate(_fields):
        tk.Label(
            form, text=lbl, font=("Helvetica", 14), bg="#1e293b", fg="yellow", anchor="e"
        ).grid(row=r, column=0, sticky="e", padx=(4, 8), pady=8)
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
        amc = _widgets["amc_name"].get().strip()
        rta = _widgets["rta_name"].get().strip() or "CAMS"
        folio = _widgets["folio_number"].get().strip()
        scheme = _widgets["scheme_name"].get().strip()
        
        if not amc or not folio or not scheme:
            show_colorful_error(modal, "Validation", "AMC, Folio, and Scheme are required.")
            return

        try:
            new_id = db_add_mf_master({
                "account_id": account_id,
                "amc_name": amc,
                "rta_name": rta,
                "folio_number": folio,
                "scheme_name": scheme,
                "is_active": 1,
            })
            _close()
            display_label = f"{amc} | {scheme} [Folio: {folio} - {rta}]"
            on_mf_saved(new_id, display_label)
        except Exception as exc:
            show_colorful_error(modal, "Error", f"Failed to save MF: {exc}")

    def _close(_e=None):
        safe_close_modal(modal, win)
        win.bind("<Control-Return>", lambda e: win.event_generate("<<InvokeSubmit>>"))
        win.bind("<Escape>", on_escape)
        return "break"

    save_btn = tk.Button(
        btn_row, text="💾 Save", command=_save, font=("Helvetica", 11, "bold"),
        bg="#22c55e", fg="white", cursor="hand2", padx=10
    )
    save_btn.pack(side="left", padx=5)
    apply_button_animations(save_btn, "#22c55e", "#2563eb")

    cancel_btn = tk.Button(
        btn_row, text="❌ Cancel", command=_close, font=("Helvetica", 11, "bold"),
        bg="#ef4444", fg="white", cursor="hand2", padx=10
    )
    cancel_btn.pack(side="left", padx=5)
    apply_button_animations(cancel_btn, "#ef4444", "#b91c1c")
    modal.bind("<Control-Return>", lambda e: _save())
    modal.bind("<Escape>", _close)
    modal.protocol("WM_DELETE_WINDOW", _close)
    _widgets["amc_name"].focus_set()

def show_ins_new_modal(
    win: tk.Toplevel,
    account_id: int,
    on_escape,
    on_ins_saved,
) -> None:
    win.unbind("<Escape>")
    modal = tk.Toplevel(win)
    modal.title("New Insurance Policy")
    modal.transient(win)
    modal.grab_set()
    modal.geometry("500x550")
    modal.resizable(False, False)
    modal.configure(bg="#1e293b")
    push_window(modal, win)
    try:
        modal.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        modal,
        text="New Insurance Policy",
        font=("Helvetica", 14, "bold"),
        bg="#784212",
        fg="white",
        pady=8,
    ).pack(fill="x")

    form = tk.Frame(modal, bg="#1e293b", padx=16, pady=12)
    form.pack(fill="both", expand=True)

    _fields = [
        ("Company Name:", "company_name", "entry"),
        ("Category:", "ins_category", "combo"),
        ("Policy Number:", "policy_number", "entry"),
        ("Plan Name:", "plan_name", "entry"),
        ("Proposer Name:", "proposer_name", "entry"),
        ("Life Assured / Vehicle:", "assured_item", "entry"),
        ("Premium Amount:", "premium_amount", "entry"),
        ("Start Date:", "start_dt", "date"),
        ("Maturity/Renewal Date:", "maturity_dt", "date"),
    ]
    _widgets = {}
    for r, (lbl, key, wtype) in enumerate(_fields):
        tk.Label(
            form, text=lbl, font=("Helvetica", 11), bg="#1e293b", fg="yellow", anchor="e"
        ).grid(row=r, column=0, sticky="e", padx=(4, 8), pady=6)
        if wtype == "date":
            w = DateEntry(form, date_pattern="dd-mm-yyyy", width=18, font=("Helvetica", 11))
        elif wtype == "combo":
            w = ttk.Combobox(form, values=['LIFE_TERM', 'LIFE_SAVINGS', 'HEALTH', 'VEHICLE', 'GENERAL'], width=24, font=("Helvetica", 11))
            w.set("LIFE_TERM")
        else:
            w = tk.Entry(form, width=26, font=("Helvetica", 11))
        if wtype != "combo":
            apply_entry_theme(w)
        w.grid(row=r, column=1, sticky="w", padx=4, pady=6)
        _widgets[key] = w

    _keys = [f[1] for f in _fields]
    for _i, _k in enumerate(_keys[:-1]):
        _nxt = _keys[_i + 1]
        _widgets[_k].bind("<Return>", lambda e, n=_nxt: _widgets[n].focus_set())

    btn_row = tk.Frame(modal, bg="#1e293b")
    btn_row.pack(fill="x", padx=16, pady=12)

    def _save(_e=None):
        company = _widgets["company_name"].get().strip()
        cat = _widgets["ins_category"].get().strip()
        pol = _widgets["policy_number"].get().strip()
        plan = _widgets["plan_name"].get().strip()
        proposer = _widgets["proposer_name"].get().strip()
        assured = _widgets["assured_item"].get().strip()
        amt_str = _widgets["premium_amount"].get().strip()
        sdt = _widgets["start_dt"].get_date().strftime("%Y-%m-%d")
        mdt = _widgets["maturity_dt"].get_date().strftime("%Y-%m-%d")
        
        if not company or not pol or not plan or not proposer or not assured:
            show_colorful_error(modal, "Validation", "Missing required fields.")
            return

        try:
            amt = float(amt_str) if amt_str else 0.0
        except ValueError:
            show_colorful_error(modal, "Validation", "Premium must be a number.")
            return

        try:
            new_id = db_add_ins_master({
                "account_id": account_id,
                "company_name": company,
                "ins_category": cat,
                "policy_number": pol,
                "plan_name": plan,
                "proposer_name": proposer,
                "assured_item": assured,
                "premium_amount": amt,
                "start_dt": sdt,
                "maturity_dt": mdt,
                "is_active": 1,
            })
            _close()
            display_label = f"{company} ({cat}) | Pol: {pol} | Assured: {assured}"
            on_ins_saved(new_id, display_label)
        except Exception as exc:
            show_colorful_error(modal, "Error", f"Failed to save INS: {exc}")

    def _close(_e=None):
        safe_close_modal(modal, win)
        win.bind("<Control-Return>", lambda e: win.event_generate("<<InvokeSubmit>>"))
        win.bind("<Escape>", on_escape)
        return "break"

    save_btn = tk.Button(
        btn_row, text="💾 Save", command=_save, font=("Helvetica", 11, "bold"),
        bg="#22c55e", fg="white", cursor="hand2", padx=10
    )
    save_btn.pack(side="left", padx=5)
    apply_button_animations(save_btn, "#22c55e", "#2563eb")

    cancel_btn = tk.Button(
        btn_row, text="❌ Cancel", command=_close, font=("Helvetica", 11, "bold"),
        bg="#ef4444", fg="white", cursor="hand2", padx=10
    )
    cancel_btn.pack(side="left", padx=5)
    apply_button_animations(cancel_btn, "#ef4444", "#b91c1c")
    modal.bind("<Control-Return>", lambda e: _save())
    modal.bind("<Escape>", _close)
    modal.protocol("WM_DELETE_WINDOW", _close)
    _widgets["company_name"].focus_set()


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
    cc_map: dict = {}
    ppf_map: dict = {}
    loan_map: dict = {}
    stock_comp_map: dict = {}
    stock_actu_map: dict = {}
    mf_map: dict = {}
    ins_map: dict = {}
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

    def _filter_budget_heads(_event=None):
        try:
            w_val = float(withdrawal_entry.get().strip().replace(",", "") or "0")
        except ValueError:
            w_val = 0.0
        try:
            d_val = float(deposit_entry.get().strip().replace(",", "") or "0")
        except ValueError:
            d_val = 0.0

        filtered = ["(none)"]
        for name in bh_values:
            if name == "(none)":
                continue
            btype = bh_type_map.get(name)
            if w_val > 0.0 and d_val == 0.0:
                if btype == "EXPENSE":
                    filtered.append(name)
            elif d_val > 0.0 and w_val == 0.0:
                if btype == "INCOME":
                    filtered.append(name)
            else:
                filtered.append(name)

        budget_head_combo["values"] = filtered
        progressive_selection(budget_head_combo, filtered)

        curr = budget_head_combo.get().strip()
        if curr and curr not in filtered:
            budget_head_combo.set("(none)")
            entry_type_var.set("TRANSFER")

    def _refresh_budget_head_combo():
        new_bh = sorted(get_all_budget_heads(), key=lambda r: r[1])
        budget_map.clear()
        budget_map.update({r[1]: r[0] for r in new_bh})
        bh_type_map.clear()
        bh_type_map.update({r[1]: r[2] for r in new_bh})
        bh_values.clear()
        bh_values.extend(["(none)"] + [r[1] for r in new_bh])
        _filter_budget_heads()

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
        "INS",
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

    # Plain entry — disabled placeholder when Module Type is NONE
    module_ref_entry = tk.Entry(module_ref_cell, width=50, font=_F)
    module_ref_entry.pack(side="left")
    apply_entry_theme(module_ref_entry, is_readonly=True)
    module_ref_entry.config(state="disabled")
    bind_tooltip(
        module_ref_entry,
        tooltip_var,
        "Not required when Module Type is NONE. Select a Module Type above to choose from a dropdown.",
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

    # PPF sub-frame - hidden until PPF is selected
    ppf_cell = tk.Frame(module_ref_cell, bg=_C_MOD)

    ppf_combo = ttk.Combobox(ppf_cell, width=40)
    ppf_combo.pack(side="left", padx=(0, 6))
    apply_entry_theme(ppf_combo)
    bind_tooltip(ppf_combo, tooltip_var, "Select an active PPF Account.")

    def _rebuild_ppf_combo():
        nonlocal ppf_map
        ppf_rows = get_all_ppf_masters()
        ppf_map = {
            f"{r[1]} - {r[2]} ({'Active' if r[4] else 'Closed'})": r[0] for r in ppf_rows
        }
        ppf_combo["values"] = list(ppf_map.keys())
        progressive_selection(ppf_combo, list(ppf_map.keys()))
        if ppf_combo["values"]:
            ppf_combo.set(ppf_combo["values"][0])
        else:
            ppf_combo.set("")

    def _open_ppf_new():
        acct_name = account_combo.get()
        if not acct_name or acct_name not in account_map:
            show_colorful_error(
                win, "Validation", "Select an account before adding a new PPF."
            )
            return

        def _on_ppf_saved(_new_id, display_label):
            _rebuild_ppf_combo()
            ppf_combo.set(display_label)

        show_ppf_new_modal(win, account_map[acct_name], on_escape, _on_ppf_saved)

    new_ppf_btn = tk.Button(
        ppf_cell,
        text="New",
        command=_open_ppf_new,
        font=("Helvetica", 11, "bold"),
        bg=_BTN_BG,
        fg=_BTN_FG,
        cursor="hand2",
        padx=8,
        pady=2,
        relief="raised",
        bd=2,
    )
    new_ppf_btn.pack(side="left")
    apply_button_animations(
        new_ppf_btn,
        _BTN_BG,
        BANK_TRANSACTION_ADD_UI_THEME["hover_bg"],
    )

    # LOAN sub-frame - hidden until LOAN is selected
    loan_cell = tk.Frame(module_ref_cell, bg=_C_MOD)

    loan_combo = ttk.Combobox(loan_cell, width=40)
    loan_combo.pack(side="left", padx=(0, 6))
    apply_entry_theme(loan_combo)
    bind_tooltip(loan_combo, tooltip_var, "Select an active Loan Account.")

    def _rebuild_loan_combo():
        nonlocal loan_map
        loan_rows = get_all_loan_masters_for_display()
        loan_map = {
            f"{r[1]} [{r[2]}] - {r[5]}": r[0] for r in loan_rows
        }
        loan_combo["values"] = list(loan_map.keys())
        progressive_selection(loan_combo, list(loan_map.keys()))
        if loan_combo["values"]:
            loan_combo.set(loan_combo["values"][0])
        else:
            loan_combo.set("")

    # STOCK_COMP sub-frame
    stock_comp_cell = tk.Frame(module_ref_cell, bg=_C_MOD)

    stock_comp_combo = ttk.Combobox(stock_comp_cell, width=52)
    stock_comp_combo.pack(side="left", padx=(0, 6))
    apply_entry_theme(stock_comp_combo)
    bind_tooltip(stock_comp_combo, tooltip_var, "Select a Computed Bank Entry from StockMan.")

    def _rebuild_stock_comp_combo():
        nonlocal stock_comp_map
        rows = get_stock_computed_bank_entries()
        stock_comp_map = {
            f"#{r[0]} | {r[1]} | {r[2]} ₹{r[3]:.2f} | {r[4] or ''} {r[5] or ''}".strip(): r[0]
            for r in rows
        }
        stock_comp_combo["values"] = list(stock_comp_map.keys())
        progressive_selection(stock_comp_combo, list(stock_comp_map.keys()))
        if stock_comp_combo["values"]:
            stock_comp_combo.set(stock_comp_combo["values"][0])
        else:
            stock_comp_combo.set("")

    # STOCK_ACTU sub-frame
    stock_actu_cell = tk.Frame(module_ref_cell, bg=_C_MOD)

    stock_actu_combo = ttk.Combobox(stock_actu_cell, width=44)
    stock_actu_combo.pack(side="left", padx=(0, 6))
    apply_entry_theme(stock_actu_combo)
    bind_tooltip(stock_actu_combo, tooltip_var, "Select an Actual Bank Entry from StockMan.")

    def _rebuild_stock_actu_combo():
        nonlocal stock_actu_map
        rows = get_stock_actual_bank_entries()
        stock_actu_map = {
            f"#{r[0]} | {r[1]} | {r[2]} ₹{r[3]:.2f} | {r[4] or ''}".strip(): r[0]
            for r in rows
        }
        stock_actu_combo["values"] = list(stock_actu_map.keys())
        progressive_selection(stock_actu_combo, list(stock_actu_map.keys()))
        if stock_actu_combo["values"]:
            stock_actu_combo.set(stock_actu_combo["values"][0])
        else:
            stock_actu_combo.set("")

    # MF sub-frame
    mf_cell = tk.Frame(module_ref_cell, bg=_C_MOD)

    mf_combo = ttk.Combobox(mf_cell, width=44)
    mf_combo.pack(side="left", padx=(0, 6))
    apply_entry_theme(mf_combo)
    bind_tooltip(mf_combo, tooltip_var, "Select an active Mutual Fund folio.")

    def _rebuild_mf_combo():
        nonlocal mf_map
        rows = get_active_mf_masters()
        mf_map = {
            f"{r[1]} | {r[4]} [Folio: {r[3]} - {r[2]}]": r[0]
            for r in rows
        }
        mf_combo["values"] = list(mf_map.keys())
        progressive_selection(mf_combo, list(mf_map.keys()))
        if mf_combo["values"]:
            mf_combo.set(mf_combo["values"][0])
        else:
            mf_combo.set("")

    def _open_mf_new():
        acct_name = account_combo.get()
        if not acct_name or acct_name not in account_map:
            show_colorful_error(win, "Validation", "Select an account before adding a new MF.")
            return

        def _on_mf_saved(_new_id, display_label):
            _rebuild_mf_combo()
            mf_combo.set(display_label)

        show_mf_new_modal(win, account_map[acct_name], on_escape, _on_mf_saved)

    new_mf_btn = tk.Button(
        mf_cell, text="New", command=_open_mf_new, font=("Helvetica", 11, "bold"),
        bg=_BTN_BG, fg=_BTN_FG, cursor="hand2", padx=8, pady=2, relief="raised", bd=2
    )
    new_mf_btn.pack(side="left")
    apply_button_animations(new_mf_btn, _BTN_BG, BANK_TRANSACTION_ADD_UI_THEME["hover_bg"])

    # INS sub-frame
    ins_cell = tk.Frame(module_ref_cell, bg=_C_MOD)

    ins_combo = ttk.Combobox(ins_cell, width=44)
    ins_combo.pack(side="left", padx=(0, 6))
    apply_entry_theme(ins_combo)
    bind_tooltip(ins_combo, tooltip_var, "Select an active Insurance policy.")

    def _rebuild_ins_combo():
        nonlocal ins_map
        rows = get_active_ins_masters()
        ins_map = {
            f"{r[1]} ({r[2]}) | Pol: {r[3]} | Assured: {r[6]}": r[0]
            for r in rows
        }
        ins_combo["values"] = list(ins_map.keys())
        progressive_selection(ins_combo, list(ins_map.keys()))
        if ins_combo["values"]:
            ins_combo.set(ins_combo["values"][0])
        else:
            ins_combo.set("")

    def _open_ins_new():
        acct_name = account_combo.get()
        if not acct_name or acct_name not in account_map:
            show_colorful_error(win, "Validation", "Select an account before adding a new INS.")
            return

        def _on_ins_saved(_new_id, display_label):
            _rebuild_ins_combo()
            ins_combo.set(display_label)

        show_ins_new_modal(win, account_map[acct_name], on_escape, _on_ins_saved)

    new_ins_btn = tk.Button(
        ins_cell, text="New", command=_open_ins_new, font=("Helvetica", 11, "bold"),
        bg=_BTN_BG, fg=_BTN_FG, cursor="hand2", padx=8, pady=2, relief="raised", bd=2
    )
    new_ins_btn.pack(side="left")
    apply_button_animations(new_ins_btn, _BTN_BG, BANK_TRANSACTION_ADD_UI_THEME["hover_bg"])

    def _open_stock_actu_new():
        try:
            w_amt = float(withdrawal_entry.get().strip().replace(",", "") or "0")
        except:
            w_amt = 0.0
        try:
            d_amt = float(deposit_entry.get().strip().replace(",", "") or "0")
        except:
            d_amt = 0.0
            
        desc = bank_remark_entry.get().strip() or user_desc_combo.get().strip()
        dt_str = trans_dt.get_date().strftime("%Y-%m-%d")

        def _on_saved(_new_id):
            _rebuild_stock_actu_combo()
            for k, v in stock_actu_map.items():
                if v == _new_id:
                    stock_actu_combo.set(k)
                    break

        show_stock_actu_new_modal(win, dt_str, w_amt, d_amt, desc, on_escape, _on_saved)

    new_stock_actu_btn = tk.Button(
        stock_actu_cell,
        text="New",
        command=_open_stock_actu_new,
        font=("Helvetica", 11, "bold"),
        bg=_BTN_BG,
        fg=_BTN_FG,
        cursor="hand2",
        padx=8,
        pady=2,
        relief="raised",
        bd=2,
    )
    new_stock_actu_btn.pack(side="left")
    apply_button_animations(
        new_stock_actu_btn,
        _BTN_BG,
        BANK_TRANSACTION_ADD_UI_THEME["hover_bg"],
    )

    # ── Module-type change handler ─────────────────────────────────────────
    def _on_module_type_change(*_):
        for _w in (
            module_ref_entry,
            fd_cell,
            cc_cell,
            ppf_cell,
            loan_cell,
            stock_comp_cell,
            stock_actu_cell,
            mf_cell,
            ins_cell,
        ):
            _w.pack_forget()

        mt = module_type_var.get()
        if mt == "FD":
            _rebuild_fd_combo()
            fd_cell.pack(side="left")
        elif mt == "CC":
            _rebuild_cc_combo()
            cc_cell.pack(side="left")
        elif mt == "PPF":
            _rebuild_ppf_combo()
            ppf_cell.pack(side="left")
        elif mt == "LOAN":
            _rebuild_loan_combo()
            loan_cell.pack(side="left")
        elif mt == "STOCK_COMP":
            _rebuild_stock_comp_combo()
            stock_comp_cell.pack(side="left")
        elif mt == "STOCK_ACTU":
            _rebuild_stock_actu_combo()
            stock_actu_cell.pack(side="left")
        elif mt == "MF":
            _rebuild_mf_combo()
            mf_cell.pack(side="left")
        elif mt == "INS":
            _rebuild_ins_combo()
            ins_cell.pack(side="left")
        else:
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
    def _bal_updater(e=None):
        return _update_balance_default(
            win, _prev_balance, withdrawal_entry, deposit_entry, balance_entry, e
        )
    withdrawal_entry.bind("<FocusOut>", _bal_updater, add="+")
    deposit_entry.bind("<FocusOut>", _bal_updater, add="+")
    withdrawal_entry.bind("<KeyRelease>", _bal_updater, add="+")
    deposit_entry.bind("<KeyRelease>", _bal_updater, add="+")

    withdrawal_entry.bind("<FocusOut>", _filter_budget_heads, add="+")
    deposit_entry.bind("<FocusOut>", _filter_budget_heads, add="+")
    withdrawal_entry.bind("<KeyRelease>", _filter_budget_heads, add="+")
    deposit_entry.bind("<KeyRelease>", _filter_budget_heads, add="+")

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
            proceed = show_colorful_yesno(
                win,
                "Negative Balance Warning",
                f"The resulting balance is negative (\u20b9{balance_after:,.2f}).\n\n"
                "Normally, standard bank accounts cannot go below zero unless it is an overdraft, "
                "cash, or suspense account.\n\n"
                "Do you want to proceed and allow this negative balance?",
            )
            if not proceed:
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
            ppf_label = ppf_combo.get().strip()
            if not ppf_label or ppf_label not in ppf_map:
                show_colorful_error(
                    win,
                    "Validation Error",
                    "Please select a valid PPF Account from the dropdown.",
                )
                flash_error(ppf_combo)
                return
            master_id = ppf_map[ppf_label]

        elif module_type == "LOAN":
            loan_label = loan_combo.get().strip()
            if not loan_label or loan_label not in loan_map:
                show_colorful_error(
                    win,
                    "Validation Error",
                    "Please select a valid Loan Account from the dropdown.",
                )
                flash_error(loan_combo)
                return
            master_id = loan_map[loan_label]

        elif module_type == "STOCK_COMP":
            label = stock_comp_combo.get().strip()
            if not label or label not in stock_comp_map:
                show_colorful_error(
                    win,
                    "Validation Error",
                    "Please select a valid Computed Bank entry from the dropdown.",
                )
                flash_error(stock_comp_combo)
                return
            master_id = stock_comp_map[label]

        elif module_type == "STOCK_ACTU":
            label = stock_actu_combo.get().strip()
            if not label or label not in stock_actu_map:
                show_colorful_error(
                    win,
                    "Validation Error",
                    "Please select a valid Actual Bank entry from the dropdown.",
                )
                flash_error(stock_actu_combo)
                return
            master_id = stock_actu_map[label]

        elif module_type == "MF":
            label = mf_combo.get().strip()
            if not label or label not in mf_map:
                show_colorful_error(
                    win,
                    "Validation Error",
                    "Please select a valid MF entry from the dropdown.",
                )
                flash_error(mf_combo)
                return
            master_id = mf_map[label]

        elif module_type == "INS":
            label = ins_combo.get().strip()
            if not label or label not in ins_map:
                show_colorful_error(
                    win,
                    "Validation Error",
                    "Please select a valid INS entry from the dropdown.",
                )
                flash_error(ins_combo)
                return
            master_id = ins_map[label]

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
        mt = module_type_var.get()
        if mt == "FD":
            fd_combo.focus_set()
        elif mt == "CC":
            cc_combo.focus_set()
        elif mt == "PPF":
            ppf_combo.focus_set()
        elif mt == "LOAN":
            loan_combo.focus_set()
        elif mt == "STOCK_COMP":
            stock_comp_combo.focus_set()
        elif mt == "STOCK_ACTU":
            stock_actu_combo.focus_set()
        elif mt == "MF":
            mf_combo.focus_set()
        elif mt == "INS":
            ins_combo.focus_set()
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
    cc_combo.bind("<Return>", lambda e: submit_button.focus_set())
    ppf_combo.bind("<Return>", lambda e: submit_button.focus_set())
    loan_combo.bind("<Return>", lambda e: submit_button.focus_set())
    stock_comp_combo.bind("<Return>", lambda e: submit_button.focus_set())
    stock_actu_combo.bind("<Return>", lambda e: submit_button.focus_set())
    mf_combo.bind("<Return>", lambda e: submit_button.focus_set())
    ins_combo.bind("<Return>", lambda e: submit_button.focus_set())
    submit_button.bind("<Return>", lambda e: on_submit())

    # ── Global hotkeys ────────────────────────────────────────────────────
    win.bind("<F1>", lambda e: None if (getattr(e, "state", 0) & 0x0004) else show_master_help(win, on_escape, win.focus_get()))
    win.bind(
        "<F2>",
        lambda e: show_session_transactions(win, current_session_txns, on_escape, win.focus_get()),
    )
    # F3 is now obsolete since Budget Heads are inside the F1 notebook
    win.bind("<F3>", lambda e: "break")
    win.bind("<Control-Return>", lambda e: submit_button.invoke())
    win.bind("<<InvokeSubmit>>", lambda e: submit_button.invoke())

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

    # ── Modal wait ────────────────────────────────────────────────────────
    parent.wait_window(win)
