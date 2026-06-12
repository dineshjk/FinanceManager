# -*- coding: utf-8 -*-
# C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\BankMan\bank_db_utils.py

"""
Database utility functions for the BankMan module.
"""

import sqlite3
from datetime import date
from Shared.globals import BANK_DB_PATH, get_db_connection


def get_all_banks():
    """Fetches all banks from the database.

    Returns rows of (b_id, name, branch, IFSC, MICR) ordered by name.
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT b_id, name, branch, IFSC, MICR " "FROM banks ORDER BY name"
        )
        return cursor.fetchall()


def get_all_accounts(acct_type: str | None = None) -> list:
    """Return accounts as (ac_id, bank_name, type, ac_number).

    If acct_type is provided, filters the results by the 'type' column
    (e.g., 'CREDIT_CARD', 'SAVINGS').
    Ordered by bank name then account number for display in dropdowns.
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        if acct_type:
            cursor.execute(
                "SELECT a.ac_id, b.name, a.type, a.ac_number "
                "FROM accounts a "
                "JOIN banks b ON a.b_id = b.b_id "
                "WHERE a.type = ? "
                "ORDER BY b.name, a.ac_number",
                (acct_type,),
            )
        else:
            cursor.execute(
                "SELECT a.ac_id, b.name, a.type, a.ac_number "
                "FROM accounts a "
                "JOIN banks b ON a.b_id = b.b_id "
                "ORDER BY b.name, a.ac_number"
            )
        return cursor.fetchall()


def db_add_bank(
    name: str,
    branch: str = "",
    ifsc: str = "",
    micr: str = "",
) -> None:
    """Insert a new bank record into the ``banks`` table.

    Parameters
    ----------
    name:
        Full legal name of the institution (required, must be non-empty).
    branch:
        Branch name or location; may be empty for online-only institutions.
    ifsc:
        11-character IFSC code assigned by the RBI; stored as TEXT.
    micr:
        9-digit MICR code from cheque leaves; stored as TEXT.
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO banks (name, branch, IFSC, MICR)
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                branch or None,
                ifsc.strip() or None,
                micr.strip() or None,
            ),
        )
        conn.commit()


def db_update_bank(
    b_id: int,
    name: str,
    branch: str | None,
    ifsc: str | None,
    micr: str | None,
) -> None:
    """Update an existing bank record in the ``banks`` table.

    Parameters
    ----------
    b_id:
        Primary key of the row to update.
    name:
        Full legal name of the institution (required, must be non-empty).
    branch:
        Branch name or location; ``None`` clears the existing value.
    ifsc:
        11-character IFSC code; ``None`` clears the existing value.
    micr:
        9-digit MICR code; ``None`` clears the existing value.
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE banks
               SET name   = ?,
                   branch = ?,
                   IFSC   = ?,
                   MICR   = ?
             WHERE b_id   = ?
            """,
            (
                name,
                branch or None,
                ifsc.strip() if ifsc else None,
                micr.strip() if micr else None,
                b_id,
            ),
        )
        conn.commit()


def get_all_budget_heads() -> list:
    """Return all budget head rows as (bh_id, bh_description, bh_type).

    Results are ordered by type then description, making it easy to
    populate parent-category dropdowns in the UI.
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT bh_id, bh_description, bh_type "
            "FROM budget_head "
            "ORDER BY bh_type, bh_description"
        )
        return cursor.fetchall()


def get_budget_heads_with_parents() -> list:
    """Return child budget heads joined with their parent name.

    Each row is: (bh_id, bh_description, bh_type, parent_description).
    Rows without a parent (top-level categories) are excluded.
    Results are ordered by type then parent then child description.
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT c.bh_id, c.bh_description, c.bh_type, p.bh_description "
            "FROM budget_head c "
            "JOIN budget_head p ON c.parent_bh_id = p.bh_id "
            "ORDER BY c.bh_type, p.bh_description, c.bh_description"
        )
        return cursor.fetchall()


def get_all_user_descriptions() -> list:
    """Return a list of all unique user descriptions."""
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT user_desc FROM bank_transactions "
            "WHERE user_desc IS NOT NULL AND user_desc != '' "
            "ORDER BY user_desc"
        )
        return [row[0] for row in cursor.fetchall()]


def add_budget_head(
    description: str,
    bh_type: str,
    parent_bh_id: int | None = None,
) -> None:
    """Insert a new row into the ``budget_head`` table.

    Parameters
    ----------
    description:
        Human-readable label for this budget category (required).
    bh_type:
        Must be ``'INCOME'`` or ``'EXPENSE'`` — enforced by a DB CHECK.
    parent_bh_id:
        ``bh_id`` of the parent row for sub-categories; ``None`` for
        top-level categories.
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO budget_head (bh_description, bh_type, parent_bh_id)
            VALUES (?, ?, ?)
            """,
            (description, bh_type, parent_bh_id),
        )
        conn.commit()


def add_account(data):
    """Adds a new account to the accounts table."""
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        open_dt = data.get("open_dt") or date.today().isoformat()
        curr_balance_dt = data.get("curr_balance_dt") or None
        cursor.execute(
            """
            INSERT INTO accounts
                (b_id, open_dt, ac_number, type, curr_balance,
                 curr_balance_dt, is_joint, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["bank_id"],
                open_dt,
                data["number"],
                data["type"],
                data["balance"],
                curr_balance_dt,
                1 if data["is_joint"] else 0,
                1 if data.get("is_active", True) else 0,
            ),
        )
        conn.commit()


def db_get_all_accounts_for_edit() -> list:
    """Return full account rows for the edit treeview.

    Each row: (ac_id, b_id, bank_name, type, ac_number,
                open_dt, curr_balance, curr_balance_dt, is_joint, is_active)
    Ordered by bank name then account number.
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT a.ac_id, a.b_id, b.name, a.type, a.ac_number, "
            "       a.open_dt, a.curr_balance, a.curr_balance_dt, "
            "       a.is_joint, a.is_active "
            "FROM accounts a "
            "JOIN banks b ON a.b_id = b.b_id "
            "ORDER BY b.name, a.ac_number"
        )
        return cursor.fetchall()


def db_update_account(
    ac_id: int,
    b_id: int,
    open_dt: str,
    ac_number: str,
    type_: str,
    curr_balance: float,
    curr_balance_dt: str | None,
    is_joint: int,
    is_active: int,
) -> None:
    """Update an existing row in the ``accounts`` table.

    Parameters
    ----------
    ac_id:
        Primary key of the account to update.
    b_id:
        FK to ``banks.b_id`` — the holding institution.
    open_dt:
        Account opening date in YYYY-MM-DD format.
    ac_number:
        Account number (must remain unique within the same bank).
    type_:
        One of 'SAVINGS', 'CURRENT', 'OVERDRAFT'.
    curr_balance:
        Latest known balance snapshot.
    curr_balance_dt:
        Date of the balance snapshot (YYYY-MM-DD) or None.
    is_joint:
        1 for joint account, 0 for sole ownership.
    is_active:
        1 while account is operational, 0 after closure.
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE accounts
               SET b_id            = ?,
                   open_dt         = ?,
                   ac_number       = ?,
                   type            = ?,
                   curr_balance    = ?,
                   curr_balance_dt = ?,
                   is_joint        = ?,
                   is_active       = ?
             WHERE ac_id           = ?
            """,
            (
                b_id,
                open_dt,
                ac_number,
                type_,
                curr_balance,
                curr_balance_dt or None,
                is_joint,
                is_active,
                ac_id,
            ),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Private sub-ledger helpers (invoked within add_bank_transaction's connection)
# ---------------------------------------------------------------------------


def _insert_fd_sub(
    cursor: sqlite3.Cursor,
    fd_master_id: int,
    account_id: int,
    trans_date: str,
    amount: float,
    drcr: str,
) -> int:
    """Insert into fd_transactions; return the new fd_trans_id."""
    fd_saving = amount if drcr == "CR" else 0.0
    fd_withdrawal = amount if drcr == "DR" else 0.0
    cursor.execute(
        "INSERT INTO fd_transactions"
        " (fd_master_id, account_id, fd_trans_dt,"
        " fd_saving, fd_withdrawal)"
        " VALUES (?, ?, ?, ?, ?)",
        (fd_master_id, account_id, trans_date, fd_saving, fd_withdrawal),
    )
    return cursor.lastrowid


def _insert_cc_sub(
    cursor: sqlite3.Cursor,
    card_master_id: int,
    account_id: int,
    trans_date: str,
    amount: float,
    drcr: str,
    party: str,
) -> int:
    """Insert into cc_transactions; return the new cc_trans_id."""
    expense = amount if drcr == "DR" else 0.0
    cc_credit = amount if drcr == "CR" else 0.0
    cursor.execute(
        "INSERT INTO cc_transactions"
        " (card_master_id, account_id, cc_trans_dt,"
        " party, expense, cc_credit)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            card_master_id,
            account_id,
            trans_date,
            party,
            expense,
            cc_credit,
        ),
    )
    return cursor.lastrowid


def _insert_loan_sub(
    cursor: sqlite3.Cursor,
    loan_master_id: int,
    account_id: int,
    trans_date: str,
    amount: float,
    drcr: str,
) -> int:
    """Insert into loan_transactions; return the new loan_trans_id."""
    loan_credit = amount if drcr == "CR" else 0.0
    loan_payment = amount if drcr == "DR" else 0.0
    cursor.execute(
        "INSERT INTO loan_transactions"
        " (loan_master_id, account_id, loan_trans_dt,"
        " prevailing_interest_rate,"
        " loan_credit, loan_payment, principal_due)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            loan_master_id,
            account_id,
            trans_date,
            0.0,
            loan_credit,
            loan_payment,
            0.0,
        ),
    )
    return cursor.lastrowid


def _insert_ppf_sub(
    cursor: sqlite3.Cursor,
    ppf_master_id: int,
    account_id: int,
    trans_date: str,
    amount: float,
    drcr: str,
) -> int:
    """Insert into ppf_transactions; return the new ppf_trans_id."""
    ppf_saving = amount if drcr == "CR" else 0.0
    ppf_withdrawal = amount if drcr == "DR" else 0.0
    cursor.execute(
        "INSERT INTO ppf_transactions"
        " (ppf_master_id, account_id, ppf_trans_dt,"
        " ppf_saving, ppf_withdrawal, ppf_balance)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            ppf_master_id,
            account_id,
            trans_date,
            ppf_saving,
            ppf_withdrawal,
            0.0,
        ),
    )
    return cursor.lastrowid


def add_bank_transaction(data: dict) -> None:
    """Write a bank_transactions row plus an optional sub-ledger row.

    For FD / CC / LOAN / PPF a row is first inserted into the respective
    specialist table; the resulting primary key becomes ``module_ref_id``
    in ``bank_transactions``.  For STOCK_COMP / STOCK_ACTU / MF the
    ``master_id`` value is stored directly.  For NONE no secondary write
    is performed.

    Parameters (``data`` dict keys)
    --------------------------------
    account_id  : int
    trans_date  : str   – YYYY-MM-DD
    amount      : float
    drcr        : str   – 'DR' or 'CR'
    bank_desc   : str | None  – narration / remarks
    serial_no   : int | None
    pair_id     : int | None
    module_type : str   – 'NONE' | 'FD' | 'CC' | 'LOAN' | 'PPF'
                          | 'STOCK_COMP' | 'STOCK_ACTU' | 'MF'
    master_id   : int | None  – master product PK used by the
                                sub-ledger insert (fd_master_id,
                                card_master_id, etc.)
    """
    account_id = data["account_id"]
    trans_date = data["trans_date"]
    amount = data["amount"]
    drcr = data["drcr"]
    module_type = data.get("module_type", "NONE")
    master_id = data.get("master_id")

    withdrawal_amount = amount if drcr == "DR" else 0.0
    deposit_amount = amount if drcr == "CR" else 0.0

    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        module_ref_id: int | None = None
        if module_type == "FD" and master_id is not None:
            module_ref_id = _insert_fd_sub(
                cursor,
                master_id,
                account_id,
                trans_date,
                amount,
                drcr,
            )
        elif module_type == "CC" and master_id is not None:
            party = data.get("bank_desc") or "N/A"
            module_ref_id = _insert_cc_sub(
                cursor,
                master_id,
                account_id,
                trans_date,
                amount,
                drcr,
                party,
            )
        elif module_type == "LOAN" and master_id is not None:
            module_ref_id = _insert_loan_sub(
                cursor,
                master_id,
                account_id,
                trans_date,
                amount,
                drcr,
            )
        elif module_type == "PPF" and master_id is not None:
            module_ref_id = _insert_ppf_sub(
                cursor,
                master_id,
                account_id,
                trans_date,
                amount,
                drcr,
            )
        elif module_type in ("STOCK_COMP", "STOCK_ACTU", "MF"):
            module_ref_id = master_id

        cursor.execute(
            "INSERT INTO bank_transactions ("
            "account_id, serial_no, value_date, trans_date,"
            " bank_desc, withdrawal_amount, deposit_amount,"
            " balance_after, pair_id, module_type, module_ref_id"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                account_id,
                data.get("serial_no"),
                trans_date,
                trans_date,
                data.get("bank_desc"),
                withdrawal_amount,
                deposit_amount,
                0.0,
                data.get("pair_id"),
                module_type,
                module_ref_id,
            ),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# FD master helpers
# ---------------------------------------------------------------------------


def get_active_fd_masters() -> list:
    """Return active FD master rows as (fd_master_id, fd_number, principal_amount).

    Results are ordered alphabetically by fd_number.
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT fd_master_id, fd_number, principal_amount "
            "FROM fd_master "
            "WHERE is_active = 1 "
            "ORDER BY fd_number"
        )
        return cursor.fetchall()


def get_fd_principal(fd_master_id: int) -> float | None:
    """Return the principal_amount for the given fd_master_id, or None."""
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT principal_amount FROM fd_master WHERE fd_master_id = ?",
            (fd_master_id,),
        )
        row = cursor.fetchone()
        return float(row[0]) if row else None


def db_add_fd_master(data: dict) -> int:
    """Insert a new row into fd_master and return the new fd_master_id.

    data keys: account_id, fd_number, principal_amount, interest_rate,
               open_dt, maturity_dt
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO fd_master "
            "(account_id, fd_number, principal_amount, interest_rate, open_dt, maturity_dt) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                data["account_id"],
                data["fd_number"],
                data["principal_amount"],
                data["interest_rate"],
                data["open_dt"],
                data["maturity_dt"],
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_all_fd_masters_for_display() -> list:
    """Return active fd_master rows as
    (fd_master_id[0], fd_number[1], principal_amount[2],
     account_id[3], bank_name[4], interest_rate[5]).
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fm.fd_master_id, fm.fd_number, fm.principal_amount,
                   fm.account_id, b.name, fm.interest_rate
            FROM fd_master fm
            JOIN accounts a ON a.ac_id = fm.account_id
            JOIN banks b ON b.b_id = a.b_id
            WHERE fm.is_active = 1
            ORDER BY b.name, fm.fd_number
            """)
        return cursor.fetchall()


def db_add_fd_transaction(data: dict) -> int:
    """Insert a new standalone row into fd_transactions; return fd_trans_id.

    data keys
    ---------
    fd_master_id  : int
    account_id    : int
    fd_trans_dt   : str   (YYYY-MM-DD)
    fd_saving     : float (deposit/top-up; default 0.0)
    fd_withdrawal : float (withdrawal/closure; default 0.0)
    fd_principal  : float (principal component; default 0.0)
    fd_int        : float (interest component; default 0.0)
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute(
            """
            INSERT INTO fd_transactions
                (fd_master_id, account_id, fd_trans_dt, fd_description,
                 fd_saving, fd_withdrawal, fd_principal, fd_int)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["fd_master_id"],
                data["account_id"],
                data["fd_trans_dt"],
                data.get("fd_description"),
                float(data.get("fd_saving", 0.0)),
                float(data.get("fd_withdrawal", 0.0)),
                float(data.get("fd_principal", 0.0)),
                float(data.get("fd_int", 0.0)),
            ),
        )
        conn.commit()
        return cursor.lastrowid


# ---------------------------------------------------------------------------
# Transaction helpers for pairing and date defaults
# ---------------------------------------------------------------------------


def get_transactions_for_pairing(account_id: int, limit: int = 100) -> list:
    """Return recent bank_transactions eligible for pair_id selection.

    Returns rows of (trans_id, serial_no, trans_date, bank_desc,
    withdrawal_amount, deposit_amount) ordered newest-first.
    Only rows with pair_id IS NULL are included.
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT trans_id, serial_no, trans_date, bank_desc, "
            "withdrawal_amount, deposit_amount "
            "FROM bank_transactions "
            "WHERE account_id = ? AND pair_id IS NULL "
            "ORDER BY trans_date DESC, trans_id DESC "
            "LIMIT ?",
            (account_id, limit),
        )
        return cursor.fetchall()


def get_last_trans_date(account_id: int):
    """Return the latest trans_date (as a date object) for the account, or None."""
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MAX(trans_date) FROM bank_transactions WHERE account_id = ?",
            (account_id,),
        )
        row = cursor.fetchone()
        if row and row[0]:
            return date.fromisoformat(row[0])
        return None


def get_last_serial_no(account_id: int) -> int | None:
    """Return the maximum serial_no stored for the account, or None if absent."""
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MAX(serial_no) FROM bank_transactions WHERE account_id = ?",
            (account_id,),
        )
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else None


def get_last_balance(account_id: int) -> float | None:
    """Return the balance_after of the most recent transaction for the account, or None."""
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT balance_after FROM bank_transactions
            WHERE account_id = ?
            ORDER BY trans_date DESC, trans_id DESC
            LIMIT 1
            """,
            (account_id,),
        )
        row = cursor.fetchone()
        return float(row[0]) if row and row[0] is not None else None


def get_account_curr_balance(account_id: int) -> float | None:
    """Return curr_balance from the accounts table, or None."""
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT curr_balance FROM accounts WHERE ac_id = ?", (account_id,)
        )
        row = cursor.fetchone()
        return float(row[0]) if row and row[0] is not None else None


def get_last_used_account_id() -> int | None:
    """Return the account_id from the most recent bank transaction, or None."""
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT account_id FROM bank_transactions "
            "ORDER BY trans_date DESC, trans_id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return row[0] if row else None


def get_single_ppf_master_id() -> int | None:
    """Return the ppf_master_id when exactly one row exists in ppf_master, else None."""
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ppf_master_id FROM ppf_master")
        rows = cursor.fetchall()
        if len(rows) == 1:
            return rows[0][0]
        return None


def get_all_ppf_masters() -> list:
    """Return all ppf_master rows as
    (ppf_master_id, ppf_account_number, holder_name, open_dt, maturity_dt,
     is_active, bank_name, ac_number, account_id).

    Joins accounts + banks for display.  Ordered by open_dt ascending.
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.ppf_master_id,
                   p.ppf_account_number,
                   p.holder_name,
                   p.open_dt,
                   p.maturity_dt,
                   p.is_active,
                   b.name  AS bank_name,
                   a.ac_number,
                   p.account_id
            FROM   ppf_master p
            JOIN   accounts   a ON a.ac_id = p.account_id
            JOIN   banks      b ON b.b_id  = a.b_id
            ORDER  BY p.open_dt
            """)
        return cursor.fetchall()


def db_add_ppf_master(data: dict) -> int:
    """Insert a new row into ppf_master and return the new ppf_master_id.

    data keys
    ---------
    account_id          : int
    ppf_account_number  : str
    holder_name         : str
    open_dt             : str  (YYYY-MM-DD)
    maturity_dt         : str  (YYYY-MM-DD)
    is_active           : int  (1 = active, 0 = closed; default 1)
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute(
            """
            INSERT INTO ppf_master
                (account_id, ppf_account_number, holder_name,
                 open_dt, maturity_dt, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data["account_id"],
                data["ppf_account_number"],
                data["holder_name"],
                data["open_dt"],
                data["maturity_dt"],
                int(data.get("is_active", 1)),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def add_card_master(data: dict) -> int:
    """Insert a new row into card_master and return the new card_master_id.

    data keys
    ---------
    account_id        : int   (FK → accounts.ac_id)
    card_name         : str   (e.g. "HDFC Regalia")
    card_number       : str   (store last 4 digits for security)
    credit_limit      : float (approved limit in INR)
    billing_cycle_day : int   (1–31, day the statement is generated)
    is_active         : int   (1 = active, 0 = cancelled; default 1)
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute(
            """
            INSERT INTO card_master
                (account_id, card_name, card_number,
                 credit_limit, billing_cycle_day, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data["account_id"],
                data["card_name"],
                data["card_number"],
                float(data["credit_limit"]),
                int(data["billing_cycle_day"]),
                int(data.get("is_active", 1)),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_all_card_masters() -> list:
    """Return active card_master rows as
    (card_master_id[0], card_name[1], card_number[2],
     account_id[3], bank_name[4], ac_number[5]).
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cm.card_master_id, cm.card_name, cm.card_number,
                   cm.account_id, b.name, a.ac_number
            FROM card_master cm
            JOIN accounts a ON a.ac_id = cm.account_id
            JOIN banks b ON b.b_id = a.b_id
            WHERE cm.is_active = 1
            ORDER BY b.name, cm.card_name
            """)
        return cursor.fetchall()


def db_add_cc_transaction(data: dict) -> int:
    """Insert a new row into cc_transactions and return cc_trans_id.

    data keys
    ---------
    card_master_id  : int
    account_id      : int
    cc_trans_dt     : str  (YYYY-MM-DD)
    party           : str  (merchant / description)
    expense         : float (charge; 0.0 for payments)
    cc_credit       : float (payment/cashback; 0.0 for purchases)
    bh_id           : int | None
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute(
            """
            INSERT INTO cc_transactions
                (card_master_id, account_id, cc_trans_dt, party,
                 expense, cc_credit, bh_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["card_master_id"],
                data["account_id"],
                data["cc_trans_dt"],
                data["party"],
                float(data.get("expense", 0.0)),
                float(data.get("cc_credit", 0.0)),
                data.get("bh_id"),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_last_ppf_balance(ppf_master_id: int) -> float:
    """Return the ppf_balance of the most recent ppf_transactions row, or 0.0."""
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT ppf_balance FROM ppf_transactions
            WHERE ppf_master_id = ?
            ORDER BY ppf_trans_dt DESC, ppf_trans_id DESC
            LIMIT 1
            """,
            (ppf_master_id,),
        )
        row = cursor.fetchone()
        return float(row[0]) if row and row[0] is not None else 0.0


# ---------------------------------------------------------------------------
# Loan master helpers
# ---------------------------------------------------------------------------


def db_add_loan_master(data: dict) -> int:
    """Insert a new row into loan_master; return the new loan_master_id.

    data keys
    ---------
    account_id          : int
    loan_type           : str  (e.g. 'HOME LOAN', 'PERSONAL LOAN')
    loan_account_number : str
    principal_amount    : float
    interest_rate       : float
    emi_amount          : float
    start_dt            : str  (YYYY-MM-DD)
    end_dt              : str  (YYYY-MM-DD)
    is_active           : int  (1 = active, 0 = closed; default 1)
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute(
            """
            INSERT INTO loan_master
                (account_id, loan_type, loan_account_number,
                 principal_amount, interest_rate, emi_amount,
                 start_dt, end_dt, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["account_id"],
                data["loan_type"],
                data["loan_account_number"],
                float(data["principal_amount"]),
                float(data["interest_rate"]),
                float(data["emi_amount"]),
                data["start_dt"],
                data["end_dt"],
                int(data.get("is_active", 1)),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_all_loan_masters_for_display() -> list:
    """Return active loan_master rows as
    (loan_master_id[0], loan_type[1], loan_account_number[2],
     principal_amount[3], account_id[4], bank_name[5], interest_rate[6]).
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT lm.loan_master_id, lm.loan_type, lm.loan_account_number,
                   lm.principal_amount, lm.account_id, b.name, lm.interest_rate
            FROM loan_master lm
            JOIN accounts a ON a.ac_id = lm.account_id
            JOIN banks b ON b.b_id = a.b_id
            WHERE lm.is_active = 1
            ORDER BY b.name, lm.loan_type
            """)
        return cursor.fetchall()


def db_get_all_loan_masters_for_edit() -> list:
    """Return ALL loan_master rows (active + closed) for the edit treeview.

    Each row:
    (loan_master_id, account_id, bank_name, ac_number,
     loan_type, loan_account_number, principal_amount,
     interest_rate, emi_amount, start_dt, end_dt, is_active)
    Ordered by bank name then loan type.
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT lm.loan_master_id, lm.account_id, "
            "       b.name, a.ac_number, "
            "       lm.loan_type, lm.loan_account_number, "
            "       lm.principal_amount, lm.interest_rate, "
            "       lm.emi_amount, lm.start_dt, lm.end_dt, lm.is_active "
            "FROM loan_master lm "
            "JOIN accounts a ON a.ac_id = lm.account_id "
            "JOIN banks    b ON b.b_id  = a.b_id "
            "ORDER BY b.name, lm.loan_type, lm.loan_account_number"
        )
        return cursor.fetchall()


def db_update_loan_master(
    loan_master_id: int,
    account_id: int,
    loan_type: str,
    loan_account_number: str,
    principal_amount: float,
    interest_rate: float,
    emi_amount: float,
    start_dt: str,
    end_dt: str,
    is_active: int,
) -> None:
    """Update an existing row in the ``loan_master`` table.

    Parameters
    ----------
    loan_master_id:
        Primary key of the row to update.
    account_id:
        FK to ``accounts.ac_id`` — the EMI debit account.
    loan_type:
        Product category string (e.g. 'HOME LOAN').
    loan_account_number:
        Bank-assigned loan reference number (must remain globally unique).
    principal_amount:
        Original sanctioned loan amount in INR.
    interest_rate:
        Annual interest rate at origination (%, e.g. 8.5).
    emi_amount:
        Fixed monthly instalment amount in INR.
    start_dt:
        Disbursement / first EMI date in YYYY-MM-DD format.
    end_dt:
        Scheduled final EMI / closure date in YYYY-MM-DD format.
    is_active:
        1 while outstanding, 0 after full closure.
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE loan_master
               SET account_id          = ?,
                   loan_type           = ?,
                   loan_account_number = ?,
                   principal_amount    = ?,
                   interest_rate       = ?,
                   emi_amount          = ?,
                   start_dt            = ?,
                   end_dt              = ?,
                   is_active           = ?
             WHERE loan_master_id      = ?
            """,
            (
                account_id,
                loan_type,
                loan_account_number,
                float(principal_amount),
                float(interest_rate),
                float(emi_amount),
                start_dt,
                end_dt,
                int(is_active),
                loan_master_id,
            ),
        )
        conn.commit()


def get_last_loan_principal_due(loan_master_id: int) -> float:
    """Return the principal_due of the most recent loan_transactions row.

    Falls back to loan_master.principal_amount when no transactions exist.
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT principal_due FROM loan_transactions
            WHERE loan_master_id = ?
            ORDER BY loan_trans_dt DESC, loan_trans_id DESC
            LIMIT 1
            """,
            (loan_master_id,),
        )
        row = cursor.fetchone()
        if row and row[0] is not None:
            return float(row[0])
        # Fall back to the original sanctioned principal
        cursor.execute(
            "SELECT principal_amount FROM loan_master WHERE loan_master_id = ?",
            (loan_master_id,),
        )
        mrow = cursor.fetchone()
        return float(mrow[0]) if mrow else 0.0


def db_add_loan_transaction(data: dict) -> int:
    """Insert a new row into loan_transactions; return loan_trans_id.

    data keys
    ---------
    loan_master_id           : int
    account_id               : int
    loan_trans_dt            : str   (YYYY-MM-DD)
    loan_description         : str | None
    prevailing_interest_rate : float
    loan_credit              : float (default 0.0)
    principal                : float (default 0.0)
    interest                 : float (default 0.0)
    charges                  : float (default 0.0)
    loan_payment             : float (default 0.0)
    principal_due            : float
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute(
            """
            INSERT INTO loan_transactions
                (loan_master_id, account_id, loan_trans_dt,
                 loan_description, prevailing_interest_rate,
                 loan_credit, principal, interest, charges,
                 loan_payment, principal_due)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["loan_master_id"],
                data["account_id"],
                data["loan_trans_dt"],
                data.get("loan_description") or None,
                float(data["prevailing_interest_rate"]),
                float(data.get("loan_credit", 0.0)),
                float(data.get("principal", 0.0)),
                float(data.get("interest", 0.0)),
                float(data.get("charges", 0.0)),
                float(data.get("loan_payment", 0.0)),
                float(data["principal_due"]),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def db_add_ppf_transaction(data: dict) -> int:
    """Insert a standalone row into ppf_transactions; return ppf_trans_id.

    Use this for PPF events that have no corresponding bank statement line
    (e.g. interest credits, balance corrections).  For events triggered by
    a bank withdrawal/deposit, use add_bank_transaction_v2 with
    module_type='PPF' instead.

    data keys
    ---------
    ppf_master_id   : int
    account_id      : int
    ppf_trans_dt    : str  (YYYY-MM-DD)
    ppf_description : str | None
    ppf_saving      : float  (default 0.0)
    ppf_withdrawal  : float  (default 0.0)
    ppf_balance     : float
    """
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute(
            """
            INSERT INTO ppf_transactions
                (ppf_master_id, account_id, ppf_trans_dt,
                 ppf_description, ppf_saving, ppf_withdrawal, ppf_balance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["ppf_master_id"],
                data["account_id"],
                data["ppf_trans_dt"],
                data.get("ppf_description") or None,
                float(data.get("ppf_saving", 0.0)),
                float(data.get("ppf_withdrawal", 0.0)),
                float(data["ppf_balance"]),
            ),
        )
        conn.commit()
        return cursor.lastrowid


# ---------------------------------------------------------------------------
# New-signature transaction writer (v2)
# ---------------------------------------------------------------------------


def add_bank_transaction_v2(data: dict) -> int:
    """Write bank_transactions plus an optional fd_transactions row atomically.

    This is the full-field version that accepts withdrawal_amount and
    deposit_amount separately (no drcr flag), separate value_date / trans_date,
    and cheque_no / bh_id.  For FD entries the caller pre-computes
    fd_saving / fd_withdrawal / fd_principal / fd_int.

    Required data keys
    ------------------
    account_id        : int
    serial_no         : str | None
    value_date        : str  (YYYY-MM-DD)
    trans_date        : str  (YYYY-MM-DD)
    cheque_no         : str | None
    bank_desc         : str | None
    withdrawal_amount : float
    deposit_amount    : float
    balance_after     : float
    pair_id           : int | None
    bh_id             : int | None
    module_type       : str  ('NONE' | 'FD' | 'CC' | 'LOAN' | 'PPF' | ...)
    master_id         : int | None

    Additional keys when module_type == 'FD'
    -----------------------------------------
    fd_saving      : float
    fd_withdrawal  : float
    fd_principal   : float
    fd_int         : float

    Returns
    -------
    int — the newly created trans_id.
    """
    account_id = data["account_id"]
    serial_no = data.get("serial_no")
    value_date = data["value_date"]
    trans_date = data["trans_date"]
    cheque_no = data.get("cheque_no")
    bank_desc = data.get("bank_desc")
    withdrawal_amount = float(data.get("withdrawal_amount", 0.0))
    deposit_amount = float(data.get("deposit_amount", 0.0))
    balance_after = float(data.get("balance_after", 0.0))
    pair_id = data.get("pair_id")
    bh_id = data.get("bh_id")
    module_type = data.get("module_type", "NONE")
    master_id = data.get("master_id")
    entry_type = data.get("entry_type", "INCOME")

    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        module_ref_id: int | None = None

        if module_type == "FD" and master_id is not None:
            cursor.execute(
                "INSERT INTO fd_transactions "
                "(fd_master_id, account_id, fd_trans_dt, "
                "fd_saving, fd_withdrawal, fd_principal, fd_int) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    master_id,
                    account_id,
                    trans_date,
                    float(data.get("fd_saving", 0.0)),
                    float(data.get("fd_withdrawal", 0.0)),
                    float(data.get("fd_principal", 0.0)),
                    float(data.get("fd_int", 0.0)),
                ),
            )
            module_ref_id = cursor.lastrowid

        elif module_type == "CC" and master_id is not None:
            if withdrawal_amount > 0:
                # Bank withdrawal = CC bill payment → credit the CC account
                module_ref_id = _insert_cc_sub(
                    cursor,
                    master_id,
                    account_id,
                    trans_date,
                    withdrawal_amount,
                    "CR",
                    "",
                )
            else:
                party = bank_desc or "N/A"
                module_ref_id = _insert_cc_sub(
                    cursor,
                    master_id,
                    account_id,
                    trans_date,
                    deposit_amount,
                    "DR",
                    party,
                )

        elif module_type == "LOAN" and master_id is not None:
            amt = withdrawal_amount if withdrawal_amount > 0 else deposit_amount
            drcr = "DR" if withdrawal_amount > 0 else "CR"
            module_ref_id = _insert_loan_sub(
                cursor,
                master_id,
                account_id,
                trans_date,
                amt,
                drcr,
            )

        elif module_type == "PPF" and master_id is not None:
            ppf_saving = float(data.get("ppf_saving", 0.0))
            ppf_withdrawal = float(data.get("ppf_withdrawal", 0.0))
            ppf_description = data.get("ppf_description") or ""
            ppf_balance_val = float(data.get("ppf_balance", 0.0))
            if ppf_saving == 0.0 and ppf_withdrawal == 0.0:
                # Fallback for callers that don't pass explicit ppf fields
                amt = withdrawal_amount if withdrawal_amount > 0 else deposit_amount
                if withdrawal_amount > 0:
                    ppf_saving = amt
                else:
                    ppf_withdrawal = amt
            cursor.execute(
                "INSERT INTO ppf_transactions"
                " (ppf_master_id, account_id, ppf_trans_dt,"
                " ppf_description, ppf_saving, ppf_withdrawal, ppf_balance)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    master_id,
                    account_id,
                    trans_date,
                    ppf_description,
                    ppf_saving,
                    ppf_withdrawal,
                    ppf_balance_val,
                ),
            )
            module_ref_id = cursor.lastrowid

        elif module_type in ("STOCK_COMP", "STOCK_ACTU", "MF"):
            module_ref_id = master_id

        cursor.execute(
            "INSERT INTO bank_transactions ("
            "account_id, serial_no, value_date, trans_date, cheque_no,"
            " bank_desc, user_desc, withdrawal_amount, deposit_amount,"
            " balance_after, pair_id, bh_id, module_type, module_ref_id, entry_type"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                account_id,
                serial_no,
                value_date,
                trans_date,
                cheque_no,
                bank_desc,
                data.get("user_desc"),
                withdrawal_amount,
                deposit_amount,
                balance_after,
                pair_id,
                bh_id,
                module_type,
                module_ref_id,
                entry_type,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def db_update_bank_transaction(
    trans_id: int,
    *,
    serial_no: int | None,
    value_date: str,
    trans_date: str,
    cheque_no: str | None,
    bank_desc: str | None,
    user_desc: str | None,
    withdrawal_amount: float,
    deposit_amount: float,
    balance_after: float,
    pair_id: int | None,
    bh_id: int | None,
    module_type: str | None,
    module_ref_id: int | None,
    entry_type: str,
    old_withdrawal: float,
    old_deposit: float,
    old_trans_date: str,
    old_pair_id: int | None,
    old_module_type: str | None,
    old_module_ref_id: int | None,
    account_id: int,
) -> dict:
    """Update a bank_transactions row and apply all cascading effects.

    Returns a dict describing every cascade action that was taken so the
    caller can display a meaningful confirmation message.

    Cascade 1 — Downstream balance chain
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    If the net amount changes (deposit − withdrawal ≠ old net), every
    subsequent row for the same account (same ``account_id``, later
    ``trans_date`` or same date with higher ``trans_id``) has its
    ``balance_after`` adjusted by the same delta.

    Cascade 2 — Pair partner synchronisation
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    * If ``pair_id`` is cleared (was set, now None): the old partner row's
      ``pair_id`` is also set to NULL so neither side has a dangling link.
    * If ``pair_id`` is changed to a new value: the old partner is unlinked
      and the new partner's ``pair_id`` is set to ``trans_id``.

    Cascade 3 — Sub-ledger row synchronisation
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    When the row has a linked sub-ledger entry (``module_type`` ∈ FD / CC /
    LOAN / PPF) identified by ``module_ref_id``, the sub-ledger row's
    date field and primary amount field are updated to reflect changes to
    ``trans_date``, ``withdrawal_amount`` and ``deposit_amount``.

    Sub-ledger date columns
        FD   → ``fd_transactions.fd_trans_dt``
        CC   → ``cc_transactions.cc_trans_dt``
        LOAN → ``loan_transactions.loan_trans_dt``
        PPF  → ``ppf_transactions.ppf_trans_dt``

    Sub-ledger amount columns (mapped from bank debit/credit direction):
        FD   → ``fd_saving`` (deposit side) / ``fd_withdrawal`` (withdrawal side)
        CC   → ``expense`` (withdrawal side) / ``cc_credit`` (deposit side)
        LOAN → ``loan_payment`` (withdrawal side) / ``loan_credit`` (deposit side)
        PPF  → ``ppf_saving`` (deposit side) / ``ppf_withdrawal`` (withdrawal side)

    CC sub-ledger ``bh_id`` is also updated to match the bank row.

    If ``module_type`` changed (e.g. from FD to NONE, or FD to CC), the
    *old* sub-ledger link is left untouched — removing entries in another
    product's ledger is too destructive to do silently.  The cascade summary
    will note this so the user can fix it manually.
    """
    old_net = (old_deposit or 0.0) - (old_withdrawal or 0.0)
    new_net = (deposit_amount or 0.0) - (withdrawal_amount or 0.0)
    adjustment = round(new_net - old_net, 10)

    cascades: dict = {
        "balance_rows_adjusted": 0,
        "old_pair_unlinked": False,
        "new_pair_linked": False,
        "subledger_updated": False,
        "subledger_module": None,
        "subledger_module_changed": False,
    }

    # Normalise: treat empty string same as None
    new_module = module_type or None
    old_module = old_module_type or None

    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()

        # ── 1. Update the main bank_transactions row ──────────────────────
        cursor.execute(
            """
            UPDATE bank_transactions
               SET serial_no         = ?,
                   value_date        = ?,
                   trans_date        = ?,
                   cheque_no         = ?,
                   bank_desc         = ?,
                   user_desc         = ?,
                   withdrawal_amount = ?,
                   deposit_amount    = ?,
                   balance_after     = ?,
                   pair_id           = ?,
                   bh_id             = ?,
                   module_type       = ?,
                   module_ref_id     = ?,
                   entry_type        = ?
             WHERE trans_id          = ?
            """,
            (
                serial_no,
                value_date,
                trans_date,
                cheque_no or None,
                bank_desc or None,
                user_desc or None,
                withdrawal_amount,
                deposit_amount,
                balance_after,
                pair_id,
                bh_id,
                new_module,
                module_ref_id,
                entry_type,
                trans_id,
            ),
        )

        # ── Cascade 1: Downstream balance recalculation ───────────────────
        # Anchor the downstream sweep on the *old* date so that rows that
        # fall between old_trans_date and trans_date are also adjusted when
        # the date itself moved.
        anchor_date = min(old_trans_date, trans_date)
        if abs(adjustment) > 1e-9:
            cursor.execute(
                """
                UPDATE bank_transactions
                   SET balance_after = balance_after + ?
                 WHERE account_id = ?
                   AND trans_id  != ?
                   AND (
                         trans_date > ?
                         OR (trans_date = ? AND trans_id > ?)
                       )
                """,
                (adjustment, account_id, trans_id, anchor_date, anchor_date, trans_id),
            )
            cascades["balance_rows_adjusted"] = cursor.rowcount

        # ── Cascade 2: Pair partner synchronisation ───────────────────────
        if old_pair_id != pair_id:
            # Unlink the old partner (if any) so it no longer has a
            # dangling pair_id pointing at this row.
            if old_pair_id is not None:
                cursor.execute(
                    "UPDATE bank_transactions SET pair_id = NULL "
                    "WHERE trans_id = ? AND pair_id = ?",
                    (old_pair_id, trans_id),
                )
                if cursor.rowcount:
                    cascades["old_pair_unlinked"] = True

            # Link the new partner (if any) back to this row.
            if pair_id is not None:
                cursor.execute(
                    "UPDATE bank_transactions SET pair_id = ? " "WHERE trans_id = ?",
                    (trans_id, pair_id),
                )
                if cursor.rowcount:
                    cascades["new_pair_linked"] = True

        # ── Cascade 3: Sub-ledger row synchronisation ─────────────────────
        # Only sync when module_type is unchanged and a valid ref exists.
        if new_module and new_module == old_module and module_ref_id:
            date_changed = trans_date != old_trans_date
            amount_changed = abs(adjustment) > 1e-9

            if new_module == "FD":
                if date_changed:
                    cursor.execute(
                        "UPDATE fd_transactions SET fd_trans_dt = ? "
                        "WHERE fd_trans_id = ?",
                        (trans_date, module_ref_id),
                    )
                if amount_changed:
                    cursor.execute(
                        "UPDATE fd_transactions "
                        "   SET fd_saving     = ?, "
                        "       fd_withdrawal = ? "
                        " WHERE fd_trans_id   = ?",
                        (deposit_amount, withdrawal_amount, module_ref_id),
                    )
                if date_changed or amount_changed:
                    cascades["subledger_updated"] = True
                    cascades["subledger_module"] = "FD"

            elif new_module == "CC":
                if date_changed:
                    cursor.execute(
                        "UPDATE cc_transactions SET cc_trans_dt = ? "
                        "WHERE cc_trans_id = ?",
                        (trans_date, module_ref_id),
                    )
                if amount_changed:
                    cursor.execute(
                        "UPDATE cc_transactions "
                        "   SET expense   = ?, "
                        "       cc_credit = ? "
                        " WHERE cc_trans_id = ?",
                        (withdrawal_amount, deposit_amount, module_ref_id),
                    )
                # Always sync bh_id to keep CC category in step.
                cursor.execute(
                    "UPDATE cc_transactions SET bh_id = ? " "WHERE cc_trans_id = ?",
                    (bh_id, module_ref_id),
                )
                if date_changed or amount_changed:
                    cascades["subledger_updated"] = True
                    cascades["subledger_module"] = "CC"

            elif new_module == "LOAN":
                if date_changed:
                    cursor.execute(
                        "UPDATE loan_transactions SET loan_trans_dt = ? "
                        "WHERE loan_trans_id = ?",
                        (trans_date, module_ref_id),
                    )
                if amount_changed:
                    cursor.execute(
                        "UPDATE loan_transactions "
                        "   SET loan_payment = ?, "
                        "       loan_credit  = ? "
                        " WHERE loan_trans_id = ?",
                        (withdrawal_amount, deposit_amount, module_ref_id),
                    )
                if date_changed or amount_changed:
                    cascades["subledger_updated"] = True
                    cascades["subledger_module"] = "LOAN"

            elif new_module == "PPF":
                if date_changed:
                    cursor.execute(
                        "UPDATE ppf_transactions SET ppf_trans_dt = ? "
                        "WHERE ppf_trans_id = ?",
                        (trans_date, module_ref_id),
                    )
                if amount_changed:
                    cursor.execute(
                        "UPDATE ppf_transactions "
                        "   SET ppf_saving     = ?, "
                        "       ppf_withdrawal = ? "
                        " WHERE ppf_trans_id   = ?",
                        (deposit_amount, withdrawal_amount, module_ref_id),
                    )
                if date_changed or amount_changed:
                    cascades["subledger_updated"] = True
                    cascades["subledger_module"] = "PPF"

        elif (old_module and old_module != new_module) and old_module_ref_id:
            # Module type was changed — cannot safely modify the old
            # sub-ledger row automatically.
            cascades["subledger_module_changed"] = True

        conn.commit()

    return cascades


def db_add_rewards_points(data: dict) -> int:
    """Insert a new statement-level reward points record."""
    with get_db_connection(BANK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute(
            """
            INSERT INTO rewards_points
                (account_id, card_master_id, statement_dt, points_earned, points_redeemed)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                data["account_id"],
                data["card_master_id"],
                data["statement_dt"],
                data["points_earned"],
                data["points_redeemed"],
            ),
        )
        conn.commit()
        return cursor.lastrowid


# Add more functions here for other tables as needed.
