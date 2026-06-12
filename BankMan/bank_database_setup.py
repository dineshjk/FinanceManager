# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\BankMan\bank_database_setup.py

"""Database schema and initialization for BankMan.

This module defines the complete SQLite schema — tables, indexes, and
constraints — used by the BankMan application, and exposes the
``create_bankman_database`` helper which initializes the database file at
``BANK_DB_PATH``.  Tests may override ``BANK_DB_PATH`` before calling
``create_bankman_database`` to use ephemeral or in-memory databases.

────────────────────────────────────────────────────────────────────────────
Schema Overview (creation order respects foreign-key dependencies)
────────────────────────────────────────────────────────────────────────────

GROUP 1 — Independent master tables (no outgoing foreign keys)
  • banks         – Financial institutions (name, branch, IFSC, MICR).
  • budget_head   – Hierarchical income/expense categories; a row can point
                    to a parent row in the same table (self-join).

GROUP 2 — Account and product master tables (all depend on ``accounts``)
  • accounts      – Individual bank accounts; links to ``banks``.
  • fd_master     – Fixed-deposit products; links to ``accounts``.
  • card_master   – Credit/debit card products; links to ``accounts``.
  • loan_master   – Loan products; links to ``accounts``.
  • ppf_master    – Public Provident Fund accounts; links to ``accounts``.

GROUP 3 — Transaction and ledger tables
  • bank_transactions  – Primary ledger for every account movement.
                         Uses a *polymorphic association* pair
                         (``module_type`` + ``module_ref_id``) to reference
                         rows in any of the specialist transaction tables
                         without hard-coding individual foreign keys.
  • fd_transactions    – FD deposit / withdrawal / interest ledger.
  • cc_transactions    – Credit-card spend and payment ledger.
  • loan_transactions  – Loan repayment (principal + interest) ledger.
  • ppf_transactions   – PPF deposit, withdrawal, and balance ledger.

────────────────────────────────────────────────────────────────────────────
Date convention
────────────────────────────────────────────────────────────────────────────
All date columns are stored as TEXT in the format ``YYYY-MM-DD`` and are
validated with a CHECK constraint that verifies:
  • Exact length of 10 characters.
  • Hyphen separators at positions 5 and 8.
  • Digits in every other position (using SQLite's GLOB operator).

Nullable date columns additionally allow NULL and wrap the pattern check
inside ``col IS NULL OR ( … )``.

────────────────────────────────────────────────────────────────────────────
Polymorphic association  (bank_transactions)
────────────────────────────────────────────────────────────────────────────
``module_type`` is an enumerated TEXT column that identifies *which*
specialist table a row relates to.  ``module_ref_id`` stores the primary key
of the matching row in that table.  When no specialist linkage applies, set
``module_type = 'NONE'`` and leave ``module_ref_id`` NULL.

  module_type value  →  specialist table / system
  ─────────────────────────────────────────────────
  'FD'          →  fd_transactions.fd_trans_id
  'CC'          →  cc_transactions.cc_trans_id
  'LOAN'        →  loan_transactions.loan_trans_id
  'PPF'         →  ppf_transactions.ppf_trans_id
  'STOCK_COMP'  →  StockMan.computed_bank.id_comp_bt
  'STOCK_ACTU'  →  StockMan.actual_bank.id_actu_bt
  'MF'          →  (future mutual-fund transaction table)
  'NONE'        →  no external linkage

────────────────────────────────────────────────────────────────────────────
"""

import os
import sqlite3
import sys
from typing import Tuple

# Ensure the project root is on sys.path so absolute package imports work
# regardless of how the module is invoked.
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

from Shared.globals import BANK_DB_PATH, logger

# ---------------------------------------------------------------------------
# Internal schema helpers
# ---------------------------------------------------------------------------


def _table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    """Return True if *table_name* already exists in the database."""
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def _column_exists(cursor: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    """Return True if *column_name* exists in *table_name*."""
    cursor.execute(f"PRAGMA table_info({table_name});")
    return any(row[1] == column_name for row in cursor.fetchall())


def _seed_default_budget_heads(cursor: sqlite3.Cursor) -> None:
    """Populates the budget_head table with initial default categories."""

    # Check if table already has data to prevent duplicate inserts
    cursor.execute("SELECT COUNT(*) FROM budget_head;")
    if cursor.fetchone()[0] > 0:
        return

    default_categories = [
        # INCOME Categories
        ("Retirement & Salary", "INCOME", ["Pension", "Exam Work"]),
        (
            "Investments & Interest",
            "INCOME",
            ["Savings Bank Interest", "Fixed Deposit Interest"],
        ),
        ("Solar & Energy", "INCOME", ["Solar Power Sales"]),
        (
            "Rewards & Miscellaneous",
            "INCOME",
            ["Credit Card Cashback", "Reversals & Refunds"],
        ),
        ("Inflow Adjustment", "INCOME", ["Cash Deposit (From Hand)"]),
        # EXPENSE Categories
        (
            "Housing & Utilities",
            "EXPENSE",
            ["Electricity (MGVCL)", "Internet & Broadband", "Mobile & Telephony"],
        ),
        (
            "Household & Living",
            "EXPENSE",
            [
                "Groceries & Daily Needs",
                "Appliance Maintenance",
                "Electronics & Appliances",
                "Furniture & Decor",
            ],
        ),
        ("Food & Dining", "EXPENSE", ["Food Delivery", "Dining Out"]),
        (
            "Transportation & Auto",
            "EXPENSE",
            ["Car Fuel (Petrol/Diesel)", "Car Maintenance", "Travel & Transit"],
        ),
        (
            "Insurance & Protection",
            "EXPENSE",
            [
                "Health Insurance",
                "Life Insurance - Self",
                "Life Insurance - Family",
                "Auto Insurance",
            ],
        ),
        (
            "Entertainment & Leisure",
            "EXPENSE",
            ["Digital Subscriptions", "Books & Education"],
        ),
        (
            "Giving & Charity",
            "EXPENSE",
            ["Medical Donations", "Education Charity", "General Charity"],
        ),
        (
            "Banking & Finance",
            "EXPENSE",
            ["Credit Card Fees", "Bank Charges", "Taxes Paid"],
        ),
        ("Shopping & Lifestyle", "EXPENSE", ["Online Shopping", "Personal Care"]),
        (
            "Capital Assets (Big Ticket)",
            "EXPENSE",
            ["Property / House", "Car Purchase"],
        ),
        (
            "General & Uncategorized",
            "EXPENSE",
            ["Historical CC Payment", "Uncategorized Expense"],
        ),
        ("Outflow Adjustment", "EXPENSE", ["Cash Withdrawal (To Hand)"]),
    ]

    for parent, bh_type, children in default_categories:
        # Insert the Parent Category
        cursor.execute(
            "INSERT INTO budget_head (bh_description, parent_bh_id, bh_type) VALUES (?, NULL, ?)",
            (parent, bh_type),
        )
        parent_id = cursor.lastrowid  # Grab the newly created parent ID

        # Insert the Child Categories linked to the Parent ID
        for child in children:
            cursor.execute(
                "INSERT INTO budget_head (bh_description, parent_bh_id, bh_type) VALUES (?, ?, ?)",
                (child, parent_id, bh_type),
            )

    logger.info("Default budget heads seeded successfully.")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def create_bankman_database(_parent=None) -> Tuple[bool, str]:
    """Create ``mybanks.db`` and initialize the full BankMan schema.

    If the database file already exists the function delegates to
    ``run_bank_schema_migrations`` to apply any missing columns, tables,
    or indexes idempotently — mirroring the behaviour of
    ``create_stockman_database`` in the StockMan module.

    Parameters
    ----------
    _parent:
        Optional reference to a parent Tkinter widget; accepted for
        interface compatibility with ``create_stockman_database`` but not
        used internally.

    Returns
    -------
    Tuple[bool, str]
        ``(True, message)``  — database was created or already existed (with migration summary).
        ``(False, message)`` — creation failed; *message* contains details.
    """
    if os.path.exists(BANK_DB_PATH):
        logger.info(
            "BankMan database already exists at %s — running migrations.", BANK_DB_PATH
        )
        result = run_bank_schema_migrations()
        applied = result.get("migrations", [])
        skipped = result.get("skipped", [])
        if applied:
            summary = (
                f"Migrations applied ({len(applied)}): "
                + ", ".join(applied)
                + f"\nAlready present ({len(skipped)}): "
                + (", ".join(skipped) if skipped else "none")
            )
        else:
            summary = "No migrations were needed. Schema is up to date."
        return True, f"Database already exists.\n{summary}"

    # Ensure the containing directory exists so sqlite3.connect does not fail.
    os.makedirs(os.path.dirname(BANK_DB_PATH), exist_ok=True)

    conn = None
    try:
        conn = sqlite3.connect(BANK_DB_PATH)
        cursor = conn.cursor()

        # Enforce referential integrity on every statement in this connection.
        cursor.execute("PRAGMA foreign_keys = ON;")

        logger.info("Creating BankMan database at %s …", BANK_DB_PATH)

        # ── GROUP 1 ─── Independent master tables ────────────────────────

        # ----------------------------------------------------------------
        # Table: banks
        # Stores the financial institutions (banks, NBFCs, post offices, …)
        # that the user holds accounts with.  Every account in ``accounts``
        # must reference exactly one row here.
        # ----------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS banks (
                b_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                -- Full legal name of the institution, e.g. "State Bank of India".
                name   TEXT    NOT NULL,
                -- Branch name or location, e.g. "Vallabh Vidyanagar Branch".
                -- Optional; NULL is acceptable for online-only institutions.
                branch TEXT,
                -- IFSC (Indian Financial System Code) — 11-character alphanumeric
                -- code assigned by the RBI; stored as TEXT to preserve leading
                -- characters and avoid numeric coercion.
                IFSC   TEXT    UNIQUE,
                -- MICR (Magnetic Ink Character Recognition) code — 9-digit code
                -- printed at the bottom of cheque leaves; stored as TEXT to
                -- preserve any leading zeros.
                MICR   TEXT
            );
        """)

        # ----------------------------------------------------------------
        # Table: budget_head
        # Hierarchical chart-of-accounts for labelling transactions.
        # Top-level nodes have parent_bh_id = NULL; sub-categories point
        # to their parent row in the same table (adjacency-list pattern).
        #
        # Examples:
        #   bh_id=1, bh_description='Salary',      parent=NULL,  bh_type='INCOME'
        #   bh_id=2, bh_description='Food',         parent=NULL,  bh_type='EXPENSE'
        #   bh_id=3, bh_description='Groceries',    parent=2,     bh_type='EXPENSE'
        #   bh_id=4, bh_description='Dining Out',   parent=2,     bh_type='EXPENSE'
        # ----------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budget_head (
                bh_id          INTEGER PRIMARY KEY AUTOINCREMENT,
                -- Human-readable label for this budget category,
                -- e.g. "Utilities", "EMI – Home Loan", "Freelance Income".
                bh_description TEXT    NOT NULL,
                -- Self-referential foreign key: the parent category.
                -- NULL for top-level categories; set to an existing bh_id
                -- for sub-categories.
                parent_bh_id   INTEGER DEFAULT NULL,
                -- Broad direction of cash flow: 'INCOME' for money coming in,
                -- 'EXPENSE' for money going out.
                bh_type        TEXT    NOT NULL
                    CHECK(bh_type IN ('INCOME', 'EXPENSE')),
                FOREIGN KEY (parent_bh_id)
                    REFERENCES budget_head(bh_id) ON DELETE SET NULL
            );
        """)

        logger.info("Group 1 tables created: banks, budget_head")

        # ── GROUP 2 ─── Account & product master tables ──────────────────

        # ----------------------------------------------------------------
        # Table: accounts
        # Central registry for all financial accounts owned by the user.
        # Every specialist product table (fd_master, card_master, …) and
        # the main transaction ledger (bank_transactions) references this
        # table, making it the structural hub of the BankMan schema.
        # ----------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                ac_id           INTEGER PRIMARY KEY AUTOINCREMENT,
                -- Foreign key to banks.b_id — identifies the holding institution.
                b_id            INTEGER NOT NULL,
                -- Date on which the account was opened.
                -- Stored as TEXT in YYYY-MM-DD format; validated by CHECK.
                open_dt         TEXT    NOT NULL CHECK (
                    length(open_dt)    = 10 AND
                    substr(open_dt, 5, 1) = '-' AND
                    substr(open_dt, 8, 1) = '-' AND
                    open_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                ),
                -- Account number stored as TEXT to preserve leading zeros and
                -- accommodate non-numeric characters (e.g. alphanumeric ISBNs).
                ac_number       TEXT    NOT NULL,
                -- Account product type.
                type            TEXT    NOT NULL
                    CHECK(type IN ('SAVINGS', 'CURRENT', 'OVERDRAFT', 'CREDIT_CARD')),
                -- Snapshot of the account balance, updated by the application
                -- whenever a statement is imported or a transaction is posted.
                curr_balance    REAL    NOT NULL DEFAULT 0.0,
                -- Date of the most recent balance snapshot; NULL until the first
                -- reconciliation is performed.  When not NULL it must conform to
                -- the YYYY-MM-DD format.
                curr_balance_dt TEXT    CHECK (
                    curr_balance_dt IS NULL OR (
                        length(curr_balance_dt)    = 10 AND
                        substr(curr_balance_dt, 5, 1) = '-' AND
                        substr(curr_balance_dt, 8, 1) = '-' AND
                        curr_balance_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    )
                ),
                -- 1 if the account is held jointly with one or more other
                -- persons; 0 for sole-ownership accounts.
                is_joint        INTEGER NOT NULL DEFAULT 0
                    CHECK(is_joint  IN (0, 1)),
                -- 1 while the account is operational; 0 after closure.
                -- Closed accounts are retained for historical reporting.
                is_active       INTEGER NOT NULL DEFAULT 1
                    CHECK(is_active IN (0, 1)),
                -- An account number must be unique within a bank.
                UNIQUE(b_id, ac_number),
                FOREIGN KEY (b_id)
                    REFERENCES banks(b_id) ON DELETE RESTRICT
            );
        """)

        # ----------------------------------------------------------------
        # Table: fd_master
        # One row per Fixed Deposit product.  Multiple FDs can be linked
        # to the same savings/current account (the funding source).
        # Transactions against an FD are recorded in fd_transactions.
        # ----------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fd_master (
                fd_master_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                -- The savings or current account from which this FD was
                -- funded (and to which maturity proceeds are credited).
                account_id      INTEGER NOT NULL,
                -- Bank-assigned FD reference / receipt number.
                -- Stored as TEXT to preserve leading zeros and alphanumeric IDs.
                fd_number       TEXT    NOT NULL,
                -- Amount originally deposited to open this FD (in INR).
                principal_amount REAL   NOT NULL,
                -- Annual interest rate applicable to this FD (percentage,
                -- e.g. 7.25 represents 7.25 % p.a.).
                interest_rate   REAL    NOT NULL,
                -- Date on which the FD was opened; YYYY-MM-DD.
                open_dt         TEXT    NOT NULL CHECK (
                    length(open_dt)    = 10 AND
                    substr(open_dt, 5, 1) = '-' AND
                    substr(open_dt, 8, 1) = '-' AND
                    open_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                ),
                -- Date on which the FD matures and the principal + interest
                -- are credited back to the linked account; YYYY-MM-DD.
                maturity_dt     TEXT    NOT NULL CHECK (
                    length(maturity_dt)    = 10 AND
                    substr(maturity_dt, 5, 1) = '-' AND
                    substr(maturity_dt, 8, 1) = '-' AND
                    maturity_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                ),
                -- 1 while the FD is active (not yet matured or prematurely
                -- closed); 0 after closure.
                is_active       INTEGER NOT NULL DEFAULT 1
                    CHECK(is_active IN (0, 1)),
                -- FD receipt/reference numbers are globally unique.
                UNIQUE(fd_number),
                FOREIGN KEY (account_id)
                    REFERENCES accounts(ac_id) ON DELETE RESTRICT
            );
        """)

        # ----------------------------------------------------------------
        # Table: card_master
        # One row per credit or charge card product.  A card is typically
        # linked to the current/savings account to which bill payments are
        # debited.  Spending entries live in cc_transactions.
        # ----------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS card_master (
                card_master_id  INTEGER PRIMARY KEY AUTOINCREMENT,
                -- The account that services this card's bill payments.
                account_id      INTEGER NOT NULL,
                -- Descriptive name, e.g. "HDFC Regalia" or "SBI SimplyCLICK".
                card_name       TEXT    NOT NULL,
                -- Full card number stored as TEXT to preserve leading zeros
                -- and to avoid integer overflow on 16-digit numbers.
                -- For security, consider storing only the last four digits.
                card_number     TEXT    NOT NULL,
                -- Maximum approved credit limit on this card (in INR).
                credit_limit    REAL    NOT NULL,
                -- Day of the month on which the billing cycle closes and the
                -- statement is generated (1 – 31).
                billing_cycle_day INTEGER NOT NULL
                    CHECK(billing_cycle_day BETWEEN 1 AND 31),
                -- 1 while the card is valid and usable; 0 after expiry or
                -- cancellation.
                is_active       INTEGER NOT NULL DEFAULT 1
                    CHECK(is_active IN (0, 1)),
                -- Credit card numbers are globally unique.
                UNIQUE(card_number),
                FOREIGN KEY (account_id)
                    REFERENCES accounts(ac_id) ON DELETE RESTRICT
            );
        """)

        # ----------------------------------------------------------------
        # Table: loan_master
        # One row per loan facility (home loan, personal loan, auto loan,
        # education loan, etc.).  Repayment entries live in loan_transactions.
        # ----------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loan_master (
                loan_master_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                -- The account through which EMI payments are debited.
                account_id          INTEGER NOT NULL,
                -- Loan product category, e.g. 'HOME LOAN', 'PERSONAL LOAN',
                -- 'AUTO LOAN', 'EDUCATION LOAN'.
                loan_type           TEXT    NOT NULL,
                -- Bank-assigned loan account number; TEXT to preserve any
                -- leading zeros or alphanumeric identifiers.
                loan_account_number TEXT    NOT NULL,
                -- Original loan amount sanctioned by the bank (in INR).
                principal_amount    REAL    NOT NULL,
                -- Annual interest rate at origination (percentage, e.g. 8.5).
                -- For floating-rate loans, record the rate-at-origination here
                -- and track rate changes in loan_transactions.
                interest_rate       REAL    NOT NULL,
                -- Fixed monthly instalment amount (principal + interest component
                -- as per the repayment schedule); in INR.
                emi_amount          REAL    NOT NULL,
                -- Disbursement / first repayment date; YYYY-MM-DD.
                start_dt            TEXT    NOT NULL CHECK (
                    length(start_dt)    = 10 AND
                    substr(start_dt, 5, 1) = '-' AND
                    substr(start_dt, 8, 1) = '-' AND
                    start_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                ),
                -- Scheduled loan closure / final EMI date; YYYY-MM-DD.
                end_dt              TEXT    NOT NULL CHECK (
                    length(end_dt)    = 10 AND
                    substr(end_dt, 5, 1) = '-' AND
                    substr(end_dt, 8, 1) = '-' AND
                    end_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                ),
                -- 1 while outstanding principal remains; 0 after full closure.
                is_active           INTEGER NOT NULL DEFAULT 1
                    CHECK(is_active IN (0, 1)),
                -- Loan account numbers are globally unique.
                UNIQUE(loan_account_number),
                FOREIGN KEY (account_id)
                    REFERENCES accounts(ac_id) ON DELETE RESTRICT
            );
        """)

        # ----------------------------------------------------------------
        # Table: ppf_master
        # One row per Public Provident Fund account.  PPF accounts are
        # government-backed long-term savings instruments with a 15-year
        # lock-in; they may be extended in 5-year blocks thereafter.
        # Deposits and interest credits are tracked in ppf_transactions.
        # ----------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ppf_master (
                ppf_master_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                -- The bank/post-office account through which PPF deposits are
                -- routed (usually a linked savings account).
                account_id          INTEGER NOT NULL,
                -- PPF account number assigned by the bank or post office;
                -- stored as TEXT to preserve leading zeros (e.g. "0123456789").
                ppf_account_number  TEXT    NOT NULL,
                -- Name of the PPF account holder (may differ from the primary
                -- account holder for minor or HUF PPF accounts).
                holder_name         TEXT    NOT NULL,
                -- Date on which the PPF account was opened; YYYY-MM-DD.
                open_dt             TEXT    NOT NULL CHECK (
                    length(open_dt)    = 10 AND
                    substr(open_dt, 5, 1) = '-' AND
                    substr(open_dt, 8, 1) = '-' AND
                    open_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                ),
                -- Original maturity date (open_dt + 15 years); may be updated
                -- if the account is extended in 5-year blocks; YYYY-MM-DD.
                maturity_dt         TEXT    NOT NULL CHECK (
                    length(maturity_dt)    = 10 AND
                    substr(maturity_dt, 5, 1) = '-' AND
                    substr(maturity_dt, 8, 1) = '-' AND
                    maturity_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                ),
                -- 1 while the account is still in the accumulation or extension
                -- phase; 0 after full closure and withdrawal.
                is_active           INTEGER NOT NULL DEFAULT 1
                    CHECK(is_active IN (0, 1)),
                -- PPF account numbers are globally unique.
                UNIQUE(ppf_account_number),
                FOREIGN KEY (account_id)
                    REFERENCES accounts(ac_id) ON DELETE RESTRICT
            );
        """)

        logger.info(
            "Group 2 tables created: accounts, fd_master, card_master, "
            "loan_master, ppf_master"
        )

        # ── GROUP 3 ─── Transaction & ledger tables ───────────────────────

        # ----------------------------------------------------------------
        # Table: bank_transactions
        # The primary double-entry ledger for all movements in every bank
        # account.  Each row corresponds to one line of a bank statement.
        #
        # Polymorphic association columns
        # ────────────────────────────────
        # ``module_type``   — identifies which specialist subsystem (FD,
        #                     credit card, loan, PPF, StockMan, mutual
        #                     funds, or none) this transaction belongs to.
        # ``module_ref_id`` — the primary key of the corresponding row in
        #                     that subsystem's transaction table.
        #
        # This design avoids a combinatorial explosion of nullable foreign
        # keys while still allowing precise cross-module linkage.  The
        # application layer is responsible for enforcing referential
        # integrity between module_ref_id and the target table identified
        # by module_type.
        # ----------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bank_transactions (
                trans_id          INTEGER PRIMARY KEY AUTOINCREMENT,
                -- The account whose ledger this row belongs to.
                account_id        INTEGER NOT NULL,
                -- Optional sequential line number assigned by the bank
                -- (useful for reconciliation with printed statements).
                serial_no         INTEGER,
                -- Value date: the date on which the bank considered the
                -- transaction effective for interest calculation; YYYY-MM-DD.
                value_date        TEXT    NOT NULL CHECK (
                    length(value_date)    = 10 AND
                    substr(value_date, 5, 1) = '-' AND
                    substr(value_date, 8, 1) = '-' AND
                    value_date GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                ),
                -- Transaction date: the calendar date on which the event
                -- was initiated (may differ from value_date by a few days
                -- for cheques and NEFT/RTGS); YYYY-MM-DD.
                trans_date        TEXT    NOT NULL CHECK (
                    length(trans_date)    = 10 AND
                    substr(trans_date, 5, 1) = '-' AND
                    substr(trans_date, 8, 1) = '-' AND
                    trans_date GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                ),
                -- Cheque number for cheque-based transactions; NULL for
                -- electronic or cash transactions.
                cheque_no         TEXT,
                -- Narration or description as it appears on the bank statement,
                -- e.g. "UPI/123456/AMAZON INDIA" or "ATM WDL CHARGES".
                bank_desc         TEXT,
                -- User's own note or personal description for this transaction,
                -- e.g. "Grocery run", "Netflix subscription".
                user_desc         TEXT,
                -- Amount debited (leaving the account) for this transaction.
                -- Must be 0.0 when deposit_amount > 0; the application layer
                -- should enforce mutual exclusivity.
                withdrawal_amount REAL    NOT NULL DEFAULT 0.0,
                -- Amount credited (entering the account) for this transaction.
                -- Must be 0.0 when withdrawal_amount > 0.
                deposit_amount    REAL    NOT NULL DEFAULT 0.0,
                -- Running account balance as reported by the bank immediately
                -- after this transaction; used for statement reconciliation.
                balance_after     REAL    NOT NULL,
                -- Self-referential link used to pair the two sides of an
                -- internal fund transfer.  Both the debit row (in the source
                -- account) and the credit row (in the destination account)
                -- are given the same pair_id so they can be identified as a
                -- single transfer event.  NULL for non-transfer transactions.
                pair_id           INTEGER,
                -- Budget category assigned to this transaction for budgeting
                -- and expense-analysis reports.
                bh_id             INTEGER,
                -- Polymorphic-association discriminator: identifies which
                -- specialist subsystem this transaction is linked to.
                -- 'NONE' means no external linkage (ordinary transaction).
                module_type       TEXT    NOT NULL DEFAULT 'NONE'
                    CHECK(module_type IN (
                        'FD', 'CC', 'LOAN', 'PPF',
                        'STOCK_COMP', 'STOCK_ACTU', 'MF', 'NONE'
                    )),
                -- Primary key of the specialist transaction row identified
                -- by module_type.  NULL when module_type = 'NONE'.
                module_ref_id     INTEGER,
                -- Classifies the economic direction of this transaction:
                -- INCOME  — money received into the account (salary, interest, etc.)
                -- EXPENSE — money paid out of the account (bills, purchases, etc.)
                -- TRANSFER — internal movement between two owned accounts; both
                --            sides are linked by pair_id.
                entry_type        TEXT    NOT NULL
                    CHECK(entry_type IN ('INCOME', 'EXPENSE', 'TRANSFER')),
                FOREIGN KEY (account_id)
                    REFERENCES accounts(ac_id) ON DELETE RESTRICT,
                FOREIGN KEY (bh_id)
                    REFERENCES budget_head(bh_id) ON DELETE SET NULL
            );
        """)

        # ----------------------------------------------------------------
        # Table: fd_transactions
        # Records every financial event against a Fixed Deposit: initial
        # deposit, periodic interest credits, premature withdrawals, and
        # maturity proceeds.  Linked back to bank_transactions via the
        # polymorphic pair (module_type='FD', module_ref_id=fd_trans_id).
        # ----------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fd_transactions (
                fd_trans_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                -- The Fixed Deposit product this row belongs to.
                fd_master_id   INTEGER NOT NULL,
                -- Redundant reference to the savings/current account for
                -- faster joins when querying by account without going
                -- through fd_master.
                account_id     INTEGER NOT NULL,
                -- Date of this FD event; YYYY-MM-DD.
                fd_trans_dt    TEXT    NOT NULL CHECK (
                    length(fd_trans_dt)    = 10 AND
                    substr(fd_trans_dt, 5, 1) = '-' AND
                    substr(fd_trans_dt, 8, 1) = '-' AND
                    fd_trans_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                ),
                -- Optional description or narration for this FD event,
                -- e.g. 'FD Deposit', 'FD Interest Credit', 'FD Maturity Proceeds'.
                fd_description TEXT,
                -- Amount deposited into or added to the FD during this event
                -- (e.g. initial deposit or top-up for cumulative FDs).
                fd_saving      REAL    NOT NULL DEFAULT 0.0,
                -- Amount withdrawn from the FD (e.g. premature closure
                -- or partial withdrawal where permitted).
                fd_withdrawal  REAL    NOT NULL DEFAULT 0.0,
                -- Principal component of this event's transaction
                -- (relevant for maturity/redemption breakdowns).
                fd_principal   REAL    NOT NULL DEFAULT 0.0,
                -- Interest component credited during this event
                -- (periodic payout for non-cumulative FDs, or total
                -- interest at maturity for cumulative FDs).
                fd_int         REAL    NOT NULL DEFAULT 0.0,
                FOREIGN KEY (fd_master_id)
                    REFERENCES fd_master(fd_master_id) ON DELETE RESTRICT,
                FOREIGN KEY (account_id)
                    REFERENCES accounts(ac_id) ON DELETE RESTRICT
            );
        """)

        # ----------------------------------------------------------------
        # Table: cc_transactions
        # Records every credit-card spend, reversal, cashback, and
        # payment event.  One row per statement line.  Linked back to
        # bank_transactions via (module_type='CC', module_ref_id=cc_trans_id).
        # ----------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cc_transactions (
                cc_trans_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                -- The credit card product this row belongs to.
                card_master_id  INTEGER NOT NULL,
                -- The bank account through which this card's bill is paid,
                -- included here for direct account-level queries.
                account_id      INTEGER NOT NULL,
                -- Date the transaction was posted to the credit-card account
                -- by the card network; YYYY-MM-DD.
                cc_trans_dt     TEXT    NOT NULL CHECK (
                    length(cc_trans_dt)    = 10 AND
                    substr(cc_trans_dt, 5, 1) = '-' AND
                    substr(cc_trans_dt, 8, 1) = '-' AND
                    cc_trans_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                ),
                -- Merchant name or description of the credit-card transaction,
                -- e.g. "SWIGGY", "IRCTC RAIL", "AMAZON PRIME RENEWAL".
                party           TEXT    NOT NULL,
                -- Amount charged (debit) to the credit-card account for a
                -- purchase; 0.0 for payment and credit rows.
                expense         REAL    NOT NULL DEFAULT 0.0,
                -- Amount credited to the card account — bill payment,
                -- reversal, or cashback; 0.0 for purchase rows.
                cc_credit       REAL    NOT NULL DEFAULT 0.0,
                -- Budget head category for this transaction (nullable).
                bh_id           INTEGER,
                FOREIGN KEY (card_master_id)
                    REFERENCES card_master(card_master_id) ON DELETE RESTRICT,
                FOREIGN KEY (account_id)
                    REFERENCES accounts(ac_id) ON DELETE RESTRICT,
                FOREIGN KEY (bh_id)
                    REFERENCES budget_head(bh_id) ON DELETE SET NULL
            );
        """)

        # ----------------------------------------------------------------
        # Table: loan_transactions
        # Records every repayment instalment (EMI), pre-payment, fee, or
        # balance adjustment against a loan account.  Linked back to
        # bank_transactions via (module_type='LOAN', module_ref_id=loan_trans_id).
        # ----------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loan_transactions (
                loan_trans_id           INTEGER PRIMARY KEY AUTOINCREMENT,
                -- The loan product this row belongs to.
                loan_master_id          INTEGER NOT NULL,
                -- The savings/current account from which the EMI is debited,
                -- included here for direct account-level queries.
                account_id              INTEGER NOT NULL,
                -- Date of this loan event (EMI due date or payment date);
                -- YYYY-MM-DD.
                loan_trans_dt           TEXT    NOT NULL CHECK (
                    length(loan_trans_dt)    = 10 AND
                    substr(loan_trans_dt, 5, 1) = '-' AND
                    substr(loan_trans_dt, 8, 1) = '-' AND
                    loan_trans_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                ),
                -- Optional narration for this event, e.g. "EMI #36",
                -- "Prepayment", "Late-payment penalty".
                loan_description        TEXT,
                -- Annual interest rate prevailing for *this* instalment.
                -- Captured per row to accommodate floating-rate loans where
                -- the rate changes during the repayment tenure.
                prevailing_interest_rate REAL   NOT NULL,
                -- Any amount credited to the loan account (e.g. an overpayment
                -- reversal or a subsidy credit from a government scheme).
                loan_credit             REAL    NOT NULL DEFAULT 0.0,
                -- Principal repaid in this instalment (reduces outstanding loan).
                principal               REAL    NOT NULL DEFAULT 0.0,
                -- Interest charged for this instalment period.
                interest                REAL    NOT NULL DEFAULT 0.0,
                -- Processing fees, late-payment charges, or any other ancillary
                -- charges levied in this instalment.
                charges                 REAL    NOT NULL DEFAULT 0.0,
                -- Total cash outflow from the borrower's account for this event
                -- (should equal principal + interest + charges for a normal EMI).
                loan_payment            REAL    NOT NULL DEFAULT 0.0,
                -- Outstanding principal balance remaining after this instalment.
                principal_due           REAL    NOT NULL,
                FOREIGN KEY (loan_master_id)
                    REFERENCES loan_master(loan_master_id) ON DELETE RESTRICT,
                FOREIGN KEY (account_id)
                    REFERENCES accounts(ac_id) ON DELETE RESTRICT
            );
        """)

        # ----------------------------------------------------------------
        # Table: ppf_transactions
        # Records every deposit, interest credit, partial withdrawal, and
        # final closure against a PPF account.  Linked back to
        # bank_transactions via (module_type='PPF', module_ref_id=ppf_trans_id).
        # ----------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ppf_transactions (
                ppf_trans_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                -- The PPF account product this row belongs to.
                ppf_master_id   INTEGER NOT NULL,
                -- The savings account through which PPF deposits are routed,
                -- included here for direct account-level queries.
                account_id      INTEGER NOT NULL,
                -- Date of this PPF event (deposit date, interest credit date,
                -- or withdrawal date); YYYY-MM-DD.
                ppf_trans_dt    TEXT    NOT NULL CHECK (
                    length(ppf_trans_dt)    = 10 AND
                    substr(ppf_trans_dt, 5, 1) = '-' AND
                    substr(ppf_trans_dt, 8, 1) = '-' AND
                    ppf_trans_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                ),
                -- Optional description for this event, e.g. "Annual deposit
                -- FY2025", "Interest credit @ 7.1%", "Partial withdrawal".
                ppf_description TEXT,
                -- Amount deposited into the PPF account during this event.
                -- Zero for interest-credit or withdrawal rows.
                ppf_saving      REAL    NOT NULL DEFAULT 0.0,
                -- Amount withdrawn from the PPF account (permitted only after
                -- year 7 of each block under the PPF rules).
                -- Zero for deposit or interest-credit rows.
                ppf_withdrawal  REAL    NOT NULL DEFAULT 0.0,
                -- PPF account balance immediately after this transaction,
                -- as reported on the passbook or online statement.
                ppf_balance     REAL    NOT NULL,
                FOREIGN KEY (ppf_master_id)
                    REFERENCES ppf_master(ppf_master_id) ON DELETE RESTRICT,
                FOREIGN KEY (account_id)
                    REFERENCES accounts(ac_id) ON DELETE RESTRICT
            );
        """)

        # ----------------------------------------------------------------
        # Table: rewards_points
        # Dedicated statement-level ledger for tracking credit card loyalty
        # points. Solves out-of-order statement entries.
        # ----------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rewards_points (
                reward_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                -- The Liability Account (e.g., ICICI Shared)
                account_id      INTEGER NOT NULL,
                -- The physical card (e.g., Visa)
                card_master_id  INTEGER NOT NULL,
                -- Statement Date (YYYY-MM-DD)
                statement_dt    TEXT    NOT NULL CHECK (
                    length(statement_dt)    = 10 AND
                    substr(statement_dt, 5, 1) = '-' AND
                    substr(statement_dt, 8, 1) = '-' AND
                    statement_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                ),
                points_earned   INTEGER NOT NULL DEFAULT 0,
                points_redeemed INTEGER NOT NULL DEFAULT 0,
                -- Computed sequentially by reward_automation.py
                computed_balance INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (account_id)
                    REFERENCES accounts(ac_id) ON DELETE RESTRICT,
                FOREIGN KEY (card_master_id)
                    REFERENCES card_master(card_master_id) ON DELETE RESTRICT
            );
        """)

        logger.info(
            "Group 3 tables created: bank_transactions, fd_transactions, "
            "cc_transactions, loan_transactions, ppf_transactions, rewards_points"
        )

        # ── Indexes ───────────────────────────────────────────────────────

        # budget_head — composite unique across description + parent + type.
        # A plain UNIQUE table constraint cannot handle NULL parent_bh_id
        # correctly in SQLite (two NULLs are treated as distinct), so a
        # unique index with IFNULL is used instead.
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_bh_unique "
            "ON budget_head(bh_description, IFNULL(parent_bh_id, 0), bh_type);"
        )

        # accounts — fast lookup by bank and by account number
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_accounts_b_id " "ON accounts(b_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_accounts_ac_number "
            "ON accounts(ac_number);"
        )

        # bank_transactions — the most frequently queried table
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_btrans_account_id "
            "ON bank_transactions(account_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_btrans_trans_date "
            "ON bank_transactions(trans_date);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_btrans_value_date "
            "ON bank_transactions(value_date);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_btrans_bh_id "
            "ON bank_transactions(bh_id);"
        )
        # Composite index to accelerate polymorphic lookups
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_btrans_module "
            "ON bank_transactions(module_type, module_ref_id);"
        )

        # fd_transactions
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_fd_trans_fd_master_id "
            "ON fd_transactions(fd_master_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_fd_trans_account_id "
            "ON fd_transactions(account_id);"
        )

        # cc_transactions
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_cc_trans_card_master_id "
            "ON cc_transactions(card_master_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_cc_trans_account_id "
            "ON cc_transactions(account_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_cc_trans_bh_id "
            "ON cc_transactions(bh_id);"
        )

        # loan_transactions
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_loan_trans_loan_master_id "
            "ON loan_transactions(loan_master_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_loan_trans_account_id "
            "ON loan_transactions(account_id);"
        )

        # ppf_transactions
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ppf_trans_ppf_master_id "
            "ON ppf_transactions(ppf_master_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ppf_trans_account_id "
            "ON ppf_transactions(account_id);"
        )

        # rewards_points
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_rewards_card_master_id "
            "ON rewards_points(card_master_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_rewards_account_id "
            "ON rewards_points(account_id);"
        )

        # ── loan_schedule_history ─────────────────────────────────────────
        # Records each change in interest rate or EMI amount for a loan,
        # allowing the system to reconstruct the exact repayment schedule
        # that was in force at any point in time.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loan_schedule_history (
                history_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                -- Points back to the unchanging unique loan account
                loan_master_id  INTEGER NOT NULL,
                -- The date this new rate or EMI structure becomes effective
                effective_dt    TEXT    NOT NULL CHECK (
                    length(effective_dt)    = 10 AND
                    substr(effective_dt, 5, 1) = '-' AND
                    substr(effective_dt, 8, 1) = '-' AND
                    effective_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                ),
                interest_rate   REAL    NOT NULL,
                emi_amount      REAL    NOT NULL,
                FOREIGN KEY (loan_master_id)
                    REFERENCES loan_master(loan_master_id) ON DELETE RESTRICT
            );
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_lsh_lookup "
            "ON loan_schedule_history(loan_master_id, effective_dt);"
        )

        logger.info("All indexes created.")

        # --- ADD THIS LINE ---
        _seed_default_budget_heads(cursor)
        # ---------------------

        conn.commit()
        logger.info("BankMan database created successfully at %s", BANK_DB_PATH)
        return True, "BankMan database created successfully!"

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error("BankMan database creation failed: %s", e, exc_info=True)
        return False, f"Database creation failed: {e}"
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Schema migrations  (for existing databases)
# ---------------------------------------------------------------------------


def run_bank_schema_migrations(db_path: str | None = None) -> dict:
    """Apply any missing schema changes to an existing BankMan database.

    Safe to call repeatedly — every step is guarded by an existence check so
    it is idempotent.  New tables and indexes are added with
    ``CREATE … IF NOT EXISTS``; new columns are added only when absent.

    Parameters
    ----------
    db_path:
        Override the database file path.  When *None* (the default) the
        module-level ``BANK_DB_PATH`` is used.  Pass an explicit path to
        target a test or backup database.

    Returns
    -------
    dict with keys:
        ``"migrations"`` — list of str: names of steps that were applied.
        ``"skipped"``    — list of str: names of steps already present.
    """
    target_path = db_path or BANK_DB_PATH
    if not os.path.exists(target_path):
        logger.warning(
            "run_bank_schema_migrations: database not found at %s — "
            "nothing to migrate.",
            target_path,
        )
        return {"migrations": [], "skipped": []}

    conn = None
    migrations_applied: list[str] = []
    steps_skipped: list[str] = []

    def _apply(name: str, sql: str) -> None:
        """Execute *sql* and record the step name as applied."""
        conn.cursor().execute(sql)  # type: ignore[union-attr]
        migrations_applied.append(name)
        logger.info("Migration applied: %s", name)

    def _skip(name: str) -> None:
        steps_skipped.append(name)
        logger.debug("Migration skipped (already present): %s", name)

    try:
        conn = sqlite3.connect(target_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        # ── loan_schedule_history table ───────────────────────────────────
        if not _table_exists(cursor, "loan_schedule_history"):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS loan_schedule_history (
                    history_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    loan_master_id  INTEGER NOT NULL,
                    effective_dt    TEXT    NOT NULL CHECK (
                        length(effective_dt)    = 10 AND
                        substr(effective_dt, 5, 1) = '-' AND
                        substr(effective_dt, 8, 1) = '-' AND
                        effective_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    interest_rate   REAL    NOT NULL,
                    emi_amount      REAL    NOT NULL,
                    FOREIGN KEY (loan_master_id)
                        REFERENCES loan_master(loan_master_id) ON DELETE RESTRICT
                );
            """)
            migrations_applied.append("loan_schedule_history table created")
        else:
            _skip("loan_schedule_history table")

        # ── idx_lsh_lookup index ──────────────────────────────────────────
        # CREATE INDEX IF NOT EXISTS is always safe to re-run.
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_lsh_lookup "
            "ON loan_schedule_history(loan_master_id, effective_dt);"
        )

        # ── bank_transactions.user_desc column ────────────────────────────
        if not _column_exists(cursor, "bank_transactions", "user_desc"):
            _apply(
                "bank_transactions.user_desc column added",
                "ALTER TABLE bank_transactions ADD COLUMN user_desc TEXT;",
            )
        else:
            _skip("bank_transactions.user_desc column")

        # ── fd_transactions.fd_description column ─────────────────────────
        if not _column_exists(cursor, "fd_transactions", "fd_description"):
            _apply(
                "fd_transactions.fd_description column added",
                "ALTER TABLE fd_transactions ADD COLUMN fd_description TEXT;",
            )
        else:
            _skip("fd_transactions.fd_description column")

        # ── cc_transactions.bh_id column ──────────────────────────────────
        if not _column_exists(cursor, "cc_transactions", "bh_id"):
            _apply(
                "cc_transactions.bh_id column added",
                "ALTER TABLE cc_transactions ADD COLUMN bh_id INTEGER "
                "REFERENCES budget_head(bh_id) ON DELETE SET NULL;",
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_cc_trans_bh_id "
                "ON cc_transactions(bh_id);"
            )
        else:
            _skip("cc_transactions.bh_id column")

        # ── rewards_points table ──────────────────────────────────────────
        if not _table_exists(cursor, "rewards_points"):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rewards_points (
                    reward_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id      INTEGER NOT NULL,
                    card_master_id  INTEGER NOT NULL,
                    statement_dt    TEXT    NOT NULL CHECK (
                        length(statement_dt)    = 10 AND
                        substr(statement_dt, 5, 1) = '-' AND
                        substr(statement_dt, 8, 1) = '-' AND
                        statement_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    points_earned   INTEGER NOT NULL DEFAULT 0,
                    points_redeemed INTEGER NOT NULL DEFAULT 0,
                    computed_balance INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (account_id)
                        REFERENCES accounts(ac_id) ON DELETE RESTRICT,
                    FOREIGN KEY (card_master_id)
                        REFERENCES card_master(card_master_id) ON DELETE RESTRICT
                );
            """)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_rewards_card_master_id ON rewards_points(card_master_id);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_rewards_account_id ON rewards_points(account_id);"
            )
            migrations_applied.append("rewards_points table created")
        else:
            _skip("rewards_points table")

        conn.commit()

        if migrations_applied:
            logger.info(
                "BankMan schema migrations applied: %s",
                ", ".join(migrations_applied),
            )
        else:
            logger.info("BankMan schema: no migrations were needed.")

        return {"migrations": migrations_applied, "skipped": steps_skipped}

    except sqlite3.Error as exc:
        if conn:
            conn.rollback()
        logger.error("BankMan schema migration failed: %s", exc, exc_info=True)
        raise
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Convenience entry-point (mirrors create_stockman_database behaviour)
# ---------------------------------------------------------------------------


def setup_bankman_database(_parent=None) -> Tuple[bool, str]:
    """Create the database if absent, or migrate an existing one.

    This is a convenience wrapper that mirrors the behaviour of
    ``create_stockman_database``:

    * **New database** — delegates to ``create_bankman_database``, which
      builds the full schema including ``loan_schedule_history``.
    * **Existing database** — delegates to ``run_bank_schema_migrations``,
      which applies only the missing pieces idempotently.

    Parameters
    ----------
    _parent:
        Optional Tkinter parent widget; accepted for interface compatibility.

    Returns
    -------
    Tuple[bool, str]
        ``(True, message)``  — success (created or migrated).
        ``(False, message)`` — failure; *message* contains details.
    """
    if not os.path.exists(BANK_DB_PATH):
        return create_bankman_database(_parent)

    try:
        result = run_bank_schema_migrations()
        applied = result.get("migrations", [])
        skipped = result.get("skipped", [])
        if applied:
            summary = (
                f"Migrations applied ({len(applied)}): "
                + ", ".join(applied)
                + f"\nAlready present ({len(skipped)}): "
                + (", ".join(skipped) if skipped else "none")
            )
        else:
            summary = (
                "Database is up to date — no migrations were needed.\n"
                f"Checked ({len(skipped)}): "
                + (", ".join(skipped) if skipped else "none")
            )
        return True, summary
    except sqlite3.Error as exc:
        return False, f"Migration failed: {exc}"
