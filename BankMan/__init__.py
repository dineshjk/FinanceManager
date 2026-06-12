# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\BankMan\__init__.py

"""
BankMan Package Initialization.

Exposes every public entry point, database utility, menu function, and
export/import helper so callers can do::

    from BankMan import add_bank_transaction_main, export_banks, ...

Organisation
------------
1. Database setup & migrations
2. Main application menu
3. Top-level navigation menus  (data entry, export, import)
4. Sub-menus  (bank, CC, FD, loan, PPF)
5. GUI add / edit dialogs
6. Export / import helpers
7. Database utility functions
   (db_add_* aliases are used where a GUI function shares a bare name)
"""

# ---------------------------------------------------------------------------
# 1. Database setup & migrations
# ---------------------------------------------------------------------------
from .bank_database_setup import (
    create_bankman_database,
    run_bank_schema_migrations,
    setup_bankman_database,
)

# ---------------------------------------------------------------------------
# 2. Main application menu
# ---------------------------------------------------------------------------
from .banks import (
    create_bank_database_gui,
    show_bank_main_menu,
)

# ---------------------------------------------------------------------------
# 3. Top-level navigation menus
# ---------------------------------------------------------------------------
from .data_entry_menu import show_top_data_entry_menu
from .export_menu import show_export_menu
from .import_menu import show_import_menu

# ---------------------------------------------------------------------------
# 4. Sub-menus
# ---------------------------------------------------------------------------
from .bank_data_entry_menu import show_data_entry_menu
from .cc_data_entry_menu import show_cc_data_entry_menu
from .fd_data_entry_menu import show_fd_data_entry_menu
from .loan_data_entry_menu import show_loan_data_entry_menu
from .ppf_data_entry_menu import show_ppf_data_entry_menu

# ---------------------------------------------------------------------------
# 5. GUI add / edit dialogs
# ---------------------------------------------------------------------------
from .banks_add import add_bank
from .accounts_add import add_account_main
from .budget_head_add import add_account_type_main
from .bank_transactions_add import add_bank_transaction_main
from .fd_master_add import add_fd_master_main
from .fd_transactions_add import add_fd_transaction_main
from .cc_master_add import add_cc_master_main
from .cc_transactions_add import add_cc_transaction_main
from .loan_master_add import add_loan_master_main
from .loan_transactions_add import add_loan_transaction_main
from .ppf_master_add import add_ppf_master_main
from .ppf_transactions_add import add_ppf_transaction_main

# ---------------------------------------------------------------------------
# 6. Export / import helpers
# ---------------------------------------------------------------------------
from .banks_ex_import import export_banks, import_banks
from .budget_head_ex_import import export_budget_head, import_budget_head

# ---------------------------------------------------------------------------
# 7. Database utility functions
# ---------------------------------------------------------------------------
from .bank_db_utils import (
    get_all_banks,
    get_all_accounts,
    db_add_bank,
    get_all_budget_heads,
    add_budget_head,
    add_account,
    add_bank_transaction,  # v1 legacy helper
    add_bank_transaction_v2,
    get_active_fd_masters,
    get_fd_principal,
    db_add_fd_master,
    get_all_fd_masters_for_display,
    db_add_fd_transaction,
    get_transactions_for_pairing,
    get_last_trans_date,
    get_last_serial_no,
    get_last_balance,
    get_single_ppf_master_id,
    get_all_ppf_masters,
    db_add_ppf_master,
    db_add_ppf_transaction,
    get_last_ppf_balance,
    add_card_master,
    get_all_card_masters,
    db_add_cc_transaction,
    db_add_loan_master,
    get_all_loan_masters_for_display,
    get_last_loan_principal_due,
    db_add_loan_transaction,
)

__all__ = [
    # database setup
    "create_bankman_database",
    "run_bank_schema_migrations",
    "setup_bankman_database",
    # main menu
    "create_bank_database_gui",
    "show_bank_main_menu",
    # top-level menus
    "show_top_data_entry_menu",
    "show_export_menu",
    "show_import_menu",
    # sub-menus
    "show_data_entry_menu",
    "show_cc_data_entry_menu",
    "show_fd_data_entry_menu",
    "show_loan_data_entry_menu",
    "show_ppf_data_entry_menu",
    # GUI dialogs
    "add_bank",
    "add_account_main",
    "add_account_type_main",
    "add_bank_transaction_main",
    "add_fd_master_main",
    "add_fd_transaction_main",
    "add_cc_master_main",
    "add_cc_transaction_main",
    "add_loan_master_main",
    "add_loan_transaction_main",
    "add_ppf_master_main",
    "add_ppf_transaction_main",
    # export / import
    "export_banks",
    "import_banks",
    "export_budget_head",
    "import_budget_head",
    # db utilities
    "get_all_banks",
    "get_all_accounts",
    "db_add_bank",
    "get_all_budget_heads",
    "add_budget_head",
    "add_account",
    "add_bank_transaction",
    "add_bank_transaction_v2",
    "get_active_fd_masters",
    "get_fd_principal",
    "db_add_fd_master",
    "get_all_fd_masters_for_display",
    "db_add_fd_transaction",
    "get_transactions_for_pairing",
    "get_last_trans_date",
    "get_last_serial_no",
    "get_last_balance",
    "get_single_ppf_master_id",
    "get_all_ppf_masters",
    "db_add_ppf_master",
    "db_add_ppf_transaction",
    "get_last_ppf_balance",
    "add_card_master",
    "get_all_card_masters",
    "db_add_cc_transaction",
    "db_add_loan_master",
    "get_all_loan_masters_for_display",
    "get_last_loan_principal_due",
    "db_add_loan_transaction",
]
