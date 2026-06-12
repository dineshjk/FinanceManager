# -*- coding: utf-8 -*-
# BankMan/loan_transactions_ex_import.py

"""loan_transactions_ex_import.py

Export and import the ``loan_transactions`` table (Loan transactions).

Export format
-------------
Each line is a Python tuple literal (produced by ``repr(tuple(...))``).
The first element is the row type ``'LNT'``::

    ('LNT', loan_account_number, loan_trans_dt, loan_description,
            prevailing_interest_rate, loan_credit, principal,
            interest, charges, loan_payment, principal_due)

``loan_account_number`` (UNIQUE on ``loan_master``) identifies the parent
loan portably across databases.  ``account_id`` is derived from the
loan_master record and is never stored in the file.

Import behaviour
----------------
* Lines starting with ``#`` and blank lines are silently ignored.
* The parent loan is resolved by ``loan_account_number``; the row is skipped
  when the loan is not found.  ``account_id`` is taken from the loan_master
  record.
* Duplicate detection uses
  ``(loan_master_id, loan_trans_dt, principal, interest, loan_payment)``; a
  matching row is skipped.
* DB and file errors are reported via the GUI and logged; processing
  continues for the remaining lines.

Output / input file
-------------------
``C:\\Data\\Personal\\Finance_and_Investment\\finprog\\FinanceManager\\data\\all_loan_transactions.txt``

A ``Backup/`` copy is made before every export.
"""

import ast
import os
import shutil
import sqlite3
import tkinter as tk
from typing import Union

from Shared.dialog_utils import show_colorful_error, show_colorful_info
from Shared.globals import BANK_DB_PATH, get_db_connection, logger, PROJECT_ROOT

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DATA_DIR = os.path.join(PROJECT_ROOT, "data")
_EXPORT_FILE = os.path.join(_DATA_DIR, "all_loan_transactions.txt")
_BACKUP_NAME = "all_loan_transactions.backup.txt"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _prepare_export_file() -> str:
    """Ensure the export file and its ``Backup/`` directory exist.

    Copies the previous file to ``data/Backup/`` before overwriting.
    Returns the absolute path to ``all_loan_transactions.txt``.
    """
    data_dir = os.path.dirname(_EXPORT_FILE)
    backup_dir = os.path.join(data_dir, "Backup")
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, _BACKUP_NAME)

    if os.path.exists(_EXPORT_FILE):
        try:
            shutil.copy2(_EXPORT_FILE, backup_path)
        except OSError:
            logger.exception("_prepare_export_file: failed to back up %s", _EXPORT_FILE)
    else:
        open(_EXPORT_FILE, "w", encoding="utf-8").close()

    return _EXPORT_FILE


def _resolve_loan_master(
    cursor: sqlite3.Cursor,
    loan_account_number: str,
    cache: dict,
) -> tuple[int, int] | None:
    """Return ``(loan_master_id, account_id)`` for *loan_account_number*.

    Checks *cache* first (keyed on ``loan_account_number``), then queries
    the DB.  Returns ``None`` when the loan cannot be found.
    """
    if loan_account_number in cache:
        return cache[loan_account_number]

    cursor.execute(
        "SELECT loan_master_id, account_id"
        " FROM loan_master WHERE loan_account_number = ? LIMIT 1",
        (loan_account_number,),
    )
    row = cursor.fetchone()
    if row:
        cache[loan_account_number] = (row[0], row[1])
        return (row[0], row[1])

    logger.warning(
        "_resolve_loan_master: loan_account_number %r not found in DB",
        loan_account_number,
    )
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def export_loan_transactions(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Export ``loan_transactions`` to ``all_loan_transactions.txt``.

    Each row is written as a Python tuple literal::

        ('LNT', loan_account_number, loan_trans_dt, loan_description,
                prevailing_interest_rate, loan_credit, principal,
                interest, charges, loan_payment, principal_due)

    Rows are ordered by ``loan_trans_id`` so the original insertion order is
    preserved on re-import.  A backup of any previous export file is created
    automatically.
    """
    export_file = _prepare_export_file()
    exported_count = 0

    try:
        with get_db_connection(BANK_DB_PATH) as conn, open(
            export_file, "w", encoding="utf-8"
        ) as fh:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    lm.loan_account_number,
                    t.loan_trans_dt,
                    t.loan_description,
                    t.prevailing_interest_rate,
                    t.loan_credit,
                    t.principal,
                    t.interest,
                    t.charges,
                    t.loan_payment,
                    t.principal_due
                FROM loan_transactions t
                JOIN loan_master lm ON t.loan_master_id = lm.loan_master_id
                ORDER BY t.loan_trans_id
            """)
            rows = cursor.fetchall()

            if not rows:
                show_colorful_info(
                    parent,
                    "No Data",
                    "No loan transactions found to export.",
                )
                return

            fh.write("# loan_transactions\n")
            for (
                loan_account_number,
                loan_trans_dt,
                loan_description,
                prevailing_interest_rate,
                loan_credit,
                principal,
                interest,
                charges,
                loan_payment,
                principal_due,
            ) in rows:
                fh.write(
                    repr(
                        (
                            "LNT",
                            loan_account_number,
                            loan_trans_dt,
                            loan_description,
                            prevailing_interest_rate,
                            loan_credit,
                            principal,
                            interest,
                            charges,
                            loan_payment,
                            principal_due,
                        )
                    )
                    + "\n"
                )
                exported_count += 1

    except sqlite3.Error as exc:
        show_colorful_error(parent, "DB Error", f"Failed to read from DB:\n{exc}")
        logger.exception("export_loan_transactions: DB error: %s", exc)
        return
    except OSError as exc:
        msg = f"Failed to write export file:\n{exc}"
        show_colorful_error(parent, "File Error", msg)
        logger.exception("export_loan_transactions: file error: %s", exc)
        return

    show_colorful_info(
        parent,
        "Export Complete",
        f"Exported {exported_count} loan transaction(s) to:\n{export_file}",
    )


def import_loan_transactions(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Import ``loan_transactions`` from ``all_loan_transactions.txt``.

    Expected tuple format per line::

        ('LNT', loan_account_number, loan_trans_dt, loan_description,
                prevailing_interest_rate, loan_credit, principal,
                interest, charges, loan_payment, principal_due)

    A row is **skipped** when:

    * The parent loan cannot be resolved by ``loan_account_number``.
    * A ``loan_transactions`` row with the same
      ``(loan_master_id, loan_trans_dt, principal, interest, loan_payment)``
      already exists.

    ``account_id`` is taken from the loan_master record.
    ``loan_description`` may be ``None`` (stored as ``NULL``).
    """
    if not os.path.exists(_EXPORT_FILE):
        show_colorful_info(
            parent,
            "No File",
            f"Import file not found:\n{_EXPORT_FILE}",
        )
        return

    inserted = 0
    skipped = 0
    malformed = 0

    # loan_account_number → (loan_master_id, account_id)
    loan_cache: dict[str, tuple[int, int]] = {}

    try:
        with open(_EXPORT_FILE, "r", encoding="utf-8") as fh, get_db_connection(
            BANK_DB_PATH
        ) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")

            for lineno, raw in enumerate(fh, start=1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue

                # ── Parse tuple literal ───────────────────────────────────
                try:
                    value = ast.literal_eval(line)
                except Exception as exc:
                    logger.warning(
                        "import_loan_transactions: parse error line %d: %s",
                        lineno,
                        exc,
                    )
                    malformed += 1
                    continue

                if not isinstance(value, (list, tuple)) or len(value) < 11:
                    logger.warning(
                        "import_loan_transactions: short tuple line %d: %r",
                        lineno,
                        value,
                    )
                    malformed += 1
                    continue

                (
                    row_type,
                    loan_account_number,
                    loan_trans_dt,
                    loan_description,
                    prevailing_interest_rate,
                    loan_credit,
                    principal,
                    interest,
                    charges,
                    loan_payment,
                    principal_due,
                ) = value[:11]

                if row_type != "LNT":
                    logger.warning(
                        "import_loan_transactions: unexpected row type %r"
                        " on line %d",
                        row_type,
                        lineno,
                    )
                    malformed += 1
                    continue

                if not loan_account_number or not loan_trans_dt:
                    logger.warning(
                        "import_loan_transactions: missing required field"
                        " on line %d",
                        lineno,
                    )
                    malformed += 1
                    continue

                # ── Resolve parent loan ───────────────────────────────────
                loan_ids = _resolve_loan_master(cursor, loan_account_number, loan_cache)
                if loan_ids is None:
                    logger.warning(
                        "import_loan_transactions: skipping line %d"
                        " — loan_account_number %r not found",
                        lineno,
                        loan_account_number,
                    )
                    skipped += 1
                    continue
                loan_master_id, account_id = loan_ids

                try:
                    # ── Duplicate check ───────────────────────────────────
                    cursor.execute(
                        """
                        SELECT loan_trans_id FROM loan_transactions
                        WHERE loan_master_id = ?
                          AND loan_trans_dt  = ?
                          AND principal      = ?
                          AND interest       = ?
                          AND loan_payment   = ?
                        LIMIT 1
                        """,
                        (
                            loan_master_id,
                            loan_trans_dt,
                            principal,
                            interest,
                            loan_payment,
                        ),
                    )
                    if cursor.fetchone():
                        skipped += 1
                        continue

                    # ── Insert ────────────────────────────────────────────
                    cursor.execute(
                        """
                        INSERT INTO loan_transactions
                            (loan_master_id, account_id, loan_trans_dt,
                             loan_description, prevailing_interest_rate,
                             loan_credit, principal, interest,
                             charges, loan_payment, principal_due)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            loan_master_id,
                            account_id,
                            loan_trans_dt,
                            loan_description,
                            prevailing_interest_rate,
                            loan_credit,
                            principal,
                            interest,
                            charges,
                            loan_payment,
                            principal_due,
                        ),
                    )
                    inserted += 1

                except sqlite3.Error as exc:
                    logger.exception(
                        "import_loan_transactions: DB error line %d: %s", lineno, exc
                    )
                    msg = f"DB error on line {lineno}: {exc}"
                    show_colorful_error(parent, "DB Error", msg)

            try:
                conn.commit()
            except Exception:
                pass  # connection may auto-commit

    except OSError as exc:
        logger.exception("import_loan_transactions: file error: %s", exc)
        msg = f"Failed to open import file:\n{exc}"
        show_colorful_error(parent, "File Error", msg)
        return

    show_colorful_info(
        parent,
        "Import Complete",
        f"Loan Transactions — inserted: {inserted}, skipped: {skipped}\n"
        f"Malformed lines: {malformed}\n"
        f"Source: {_EXPORT_FILE}",
    )
