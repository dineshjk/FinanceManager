# -*- coding: utf-8 -*-
# BankMan/loan_ex_import.py

"""loan_ex_import.py

Export and import the ``loan_master`` table (Loan master records).

Export format
-------------
Each line is a Python tuple literal (produced by ``repr(tuple(...))``).
The first element is the row type ``'LN'``::

    ('LN', bank_key, ac_number, loan_type, loan_account_number,
            principal_amount, interest_rate, emi_amount,
            start_dt, end_dt, is_active)

``bank_key`` is the linked account's bank IFSC when non-NULL, otherwise the
bank's ``name``.  Together with ``ac_number`` this uniquely identifies the
linked account portably across databases.  ``loan_account_number`` (UNIQUE on
``loan_master``) is used as the portable loan identifier for transaction rows.

Import behaviour
----------------
* Lines starting with ``#`` and blank lines are silently ignored.
* **LN rows (``'LN'``)**: the linked account is resolved via
  ``(bank_key, ac_number)``.  A row is skipped when a loan with the same
  ``loan_account_number`` already exists
  (the unique constraint ``UNIQUE(loan_account_number)``).
* DB and file errors are reported via the GUI and logged; processing
  continues for the remaining lines.

Output / input file
-------------------
``C:\\Data\\Personal\\Finance_and_Investment\\finprog\\FinanceManager\\data\\all_loan_master.txt``

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
_EXPORT_FILE = os.path.join(_DATA_DIR, "all_loan_master.txt")
_BACKUP_NAME = "all_loan_master.backup.txt"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _prepare_export_file() -> str:
    """Ensure the export file and its ``Backup/`` directory exist.

    Copies the previous file to ``data/Backup/`` before overwriting.
    Returns the absolute path to ``all_loan_master.txt``.
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


def _bank_key(name: str, ifsc: str | None) -> str:
    """Canonical bank identifier: IFSC when available, otherwise bank name."""
    return ifsc if ifsc else name


def _resolve_account_id(
    cursor: sqlite3.Cursor,
    bank_key: str,
    ac_number: str,
    cache: dict,
) -> int | None:
    """Return ``account_id`` for the given ``(bank_key, ac_number)`` pair.

    Checks *cache* first, then queries the live database.
    Returns ``None`` when the account cannot be found.
    """
    cache_key = (bank_key, ac_number)
    if cache_key in cache:
        return cache[cache_key]

    # Try IFSC-based lookup first (IFSC is unique).
    cursor.execute(
        """
        SELECT a.ac_id
        FROM accounts a
        JOIN banks b ON a.b_id = b.b_id
        WHERE b.IFSC = ? AND a.ac_number = ?
        LIMIT 1
        """,
        (bank_key, ac_number),
    )
    row = cursor.fetchone()
    if row:
        cache[cache_key] = row[0]
        return row[0]

    # Fallback: name-based lookup (for banks without an IFSC).
    cursor.execute(
        """
        SELECT a.ac_id
        FROM accounts a
        JOIN banks b ON a.b_id = b.b_id
        WHERE b.name = ? AND a.ac_number = ?
        LIMIT 1
        """,
        (bank_key, ac_number),
    )
    row = cursor.fetchone()
    if row:
        cache[cache_key] = row[0]
        return row[0]

    logger.warning(
        "_resolve_account_id: account (bank_key=%r, ac_number=%r) not found",
        bank_key,
        ac_number,
    )
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def export_loan(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Export the ``loan_master`` table to ``all_loan_master.txt``.

    Each row is written as a Python tuple literal::

        ('LN', bank_key, ac_number, loan_type, loan_account_number,
                principal_amount, interest_rate, emi_amount,
                start_dt, end_dt, is_active)

    A backup of any previous export file is created automatically.
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
                    b.IFSC,
                    b.name,
                    a.ac_number,
                    lm.loan_type,
                    lm.loan_account_number,
                    lm.principal_amount,
                    lm.interest_rate,
                    lm.emi_amount,
                    lm.start_dt,
                    lm.end_dt,
                    lm.is_active
                FROM loan_master lm
                JOIN accounts a ON lm.account_id = a.ac_id
                JOIN banks    b ON a.b_id = b.b_id
                ORDER BY lm.loan_master_id
            """)
            rows = cursor.fetchall()

            if not rows:
                show_colorful_info(
                    parent, "No Data", "No loan master records found to export."
                )
                return

            fh.write("# loan_master\n")
            for (
                bank_ifsc,
                bank_name,
                ac_number,
                loan_type,
                loan_account_number,
                principal_amount,
                interest_rate,
                emi_amount,
                start_dt,
                end_dt,
                is_active,
            ) in rows:
                key = _bank_key(bank_name, bank_ifsc)
                fh.write(
                    repr(
                        (
                            "LN",
                            key,
                            ac_number,
                            loan_type,
                            loan_account_number,
                            principal_amount,
                            interest_rate,
                            emi_amount,
                            start_dt,
                            end_dt,
                            is_active,
                        )
                    )
                    + "\n"
                )
                exported_count += 1

    except sqlite3.Error as exc:
        show_colorful_error(parent, "DB Error", f"Failed to read from DB:\n{exc}")
        logger.exception("export_loan: DB error: %s", exc)
        return
    except OSError as exc:
        msg = f"Failed to write export file:\n{exc}"
        show_colorful_error(parent, "File Error", msg)
        logger.exception("export_loan: file error: %s", exc)
        return

    show_colorful_info(
        parent,
        "Export Complete",
        f"Exported {exported_count} loan master record(s) to:\n{export_file}",
    )


def import_loan(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Import ``loan_master`` rows from ``all_loan_master.txt``.

    Expected tuple format per line::

        ('LN', bank_key, ac_number, loan_type, loan_account_number,
                principal_amount, interest_rate, emi_amount,
                start_dt, end_dt, is_active)

    A row is **skipped** when a loan with the same ``loan_account_number``
    already exists (unique constraint ``UNIQUE(loan_account_number)``).
    The linked account is resolved by ``(bank_key, ac_number)``; the row is
    skipped (and logged) when the account cannot be found.
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

    # Cache (bank_key, ac_number) → account_id to avoid repeated DB queries.
    account_cache: dict[tuple, int] = {}

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
                    logger.warning("import_loan: parse error line %d: %s", lineno, exc)
                    malformed += 1
                    continue

                if not isinstance(value, (list, tuple)) or len(value) < 11:
                    logger.warning(
                        "import_loan: short tuple line %d: %r", lineno, value
                    )
                    malformed += 1
                    continue

                (
                    row_type,
                    bank_key,
                    ac_number,
                    loan_type,
                    loan_account_number,
                    principal_amount,
                    interest_rate,
                    emi_amount,
                    start_dt,
                    end_dt,
                    is_active,
                ) = value[:11]

                if row_type != "LN":
                    logger.warning(
                        "import_loan: unexpected row type %r on line %d",
                        row_type,
                        lineno,
                    )
                    malformed += 1
                    continue

                if not loan_account_number or not start_dt or not end_dt:
                    logger.warning(
                        "import_loan: missing required field on line %d",
                        lineno,
                    )
                    malformed += 1
                    continue

                # ── Resolve linked account ────────────────────────────────
                account_id = _resolve_account_id(
                    cursor, bank_key, ac_number, account_cache
                )
                if account_id is None:
                    logger.warning(
                        "import_loan: skipping line %d — account not found"
                        " (bank_key=%r, ac_number=%r)",
                        lineno,
                        bank_key,
                        ac_number,
                    )
                    skipped += 1
                    continue

                try:
                    # ── Duplicate check on loan_account_number (UNIQUE) ───
                    cursor.execute(
                        "SELECT loan_master_id FROM loan_master"
                        " WHERE loan_account_number = ? LIMIT 1",
                        (loan_account_number,),
                    )
                    if cursor.fetchone():
                        skipped += 1
                        continue

                    # ── Insert ────────────────────────────────────────────
                    cursor.execute(
                        """
                        INSERT INTO loan_master
                            (account_id, loan_type, loan_account_number,
                             principal_amount, interest_rate, emi_amount,
                             start_dt, end_dt, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            account_id,
                            loan_type,
                            loan_account_number,
                            principal_amount,
                            interest_rate,
                            emi_amount,
                            start_dt,
                            end_dt,
                            is_active,
                        ),
                    )
                    inserted += 1

                except sqlite3.Error as exc:
                    logger.exception(
                        "import_loan: DB error on line %d: %s", lineno, exc
                    )
                    msg = f"DB error on line {lineno}: {exc}"
                    show_colorful_error(parent, "DB Error", msg)

            try:
                conn.commit()
            except Exception:
                pass  # connection may auto-commit

    except OSError as exc:
        logger.exception("import_loan: file error: %s", exc)
        msg = f"Failed to open import file:\n{exc}"
        show_colorful_error(parent, "File Error", msg)
        return

    show_colorful_info(
        parent,
        "Import Complete",
        f"Loan Master — inserted: {inserted}, skipped: {skipped}\n"
        f"Malformed lines: {malformed}\n"
        f"Source: {_EXPORT_FILE}",
    )
