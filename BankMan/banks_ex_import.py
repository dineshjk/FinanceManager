# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\BankMan\banks_ex_import.py

"""banks_ex_import.py

Export and import the ``banks`` and ``accounts`` tables, preserving the
foreign-key relationship between them.

Export format
-------------
Each line is a Python tuple literal (produced by ``repr(tuple(...))``).
The first element of every tuple is a single-character *row type*:

``'B'`` — a bank row::

    ('B', name, branch, IFSC, MICR)

``'A'`` — an account row::

    ('A', bank_key, open_dt, ac_number, type,
          curr_balance, curr_balance_dt, is_joint, is_active)

``bank_key`` is the bank's ``IFSC`` when it is non-NULL, otherwise the
bank's ``name``.  All bank rows are emitted before any account rows so
that a single-pass import always resolves FKs correctly.

Import behaviour
----------------
* Lines starting with ``#`` and blank lines are silently ignored.
* **Bank rows (``'B'``)**: a row is skipped when a bank with the same
  ``IFSC`` already exists (or, for banks without an IFSC, when a bank with
  the same ``name`` and no IFSC exists).  The newly inserted or matched
  ``b_id`` is cached so following account rows can resolve their FK
  immediately without an extra DB round-trip.
* **Account rows (``'A'``)**: a row is skipped when ``(b_id, ac_number)``
  already exists (the unique constraint ``UNIQUE(b_id, ac_number)``).
* DB and file errors are reported via the GUI and logged; processing
  continues for the remaining lines.

Output / input file
-------------------
``C:\\Data\\Personal\\Finance_and_Investment\\finprog\\FinanceManager\\data\\all_banks_and_accounts.txt``

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
_EXPORT_FILE = os.path.join(_DATA_DIR, "all_banks_and_accounts.txt")
_BACKUP_NAME = "all_banks_and_accounts.backup.txt"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _prepare_export_file() -> str:
    """Ensure the export file and its ``Backup/`` directory exist.

    If the primary file already exists it is copied to ``data/Backup/``
    before being overwritten, matching the pattern used by
    ``budget_head_ex_import.py``.

    Returns the absolute path to ``all_banks_and_accounts.txt``.
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
    """Canonical bank identifier used to link account rows to bank rows.

    Returns ``IFSC`` when the bank has one (IFSC is unique), otherwise
    falls back to ``name``.
    """
    return ifsc if ifsc else name


def _resolve_bank_id(
    cursor: sqlite3.Cursor,
    bank_key: str,
    key_to_id: dict,
) -> int | None:
    """Return the ``b_id`` for *bank_key*, checking the session cache first.

    *bank_key* is IFSC when non-empty, otherwise the bank name.  ``None``
    is returned when the bank cannot be found in either the cache or the DB.
    """
    if bank_key in key_to_id:
        return key_to_id[bank_key]

    # Try IFSC lookup first — IFSC is UNIQUE so the result is unambiguous.
    cursor.execute("SELECT b_id FROM banks WHERE IFSC = ? LIMIT 1", (bank_key,))
    row = cursor.fetchone()
    if row:
        key_to_id[bank_key] = row[0]
        return row[0]

    # Fallback: name lookup (used when the bank has no IFSC).
    cursor.execute("SELECT b_id FROM banks WHERE name = ? LIMIT 1", (bank_key,))
    row = cursor.fetchone()
    if row:
        key_to_id[bank_key] = row[0]
        return row[0]

    logger.warning("_resolve_bank_id: bank key '%s' not found in DB", bank_key)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def export_banks(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Export the ``banks`` and ``accounts`` tables to a text file.

    Bank rows (prefix ``'B'``) are written first, followed by account rows
    (prefix ``'A'``), so a single-pass import always resolves FKs correctly.
    A backup of any previous export file is created automatically.
    """
    export_file = _prepare_export_file()
    banks_count = 0
    accounts_count = 0

    try:
        with get_db_connection(BANK_DB_PATH) as conn, open(
            export_file, "w", encoding="utf-8"
        ) as fh:
            cursor = conn.cursor()

            # ── Bank rows ─────────────────────────────────────────────────
            fh.write("# banks\n")
            cursor.execute(
                "SELECT b_id, name, branch, IFSC, MICR" " FROM banks ORDER BY b_id"
            )
            bank_rows = cursor.fetchall()

            if not bank_rows:
                show_colorful_info(parent, "No Data", "No banks found to export.")
                return

            for _b_id, name, branch, ifsc, micr in bank_rows:
                fh.write(repr(("B", name, branch, ifsc, micr)) + "\n")
                banks_count += 1

            # ── Account rows ──────────────────────────────────────────────
            fh.write("# accounts\n")
            cursor.execute("""
                SELECT
                    a.open_dt,
                    a.ac_number,
                    a.type,
                    a.curr_balance,
                    a.curr_balance_dt,
                    a.is_joint,
                    a.is_active,
                    b.IFSC,
                    b.name
                FROM accounts a
                JOIN banks b ON a.b_id = b.b_id
                ORDER BY a.b_id, a.ac_id
            """)
            for row in cursor.fetchall():
                (
                    open_dt,
                    ac_number,
                    acc_type,
                    curr_balance,
                    curr_balance_dt,
                    is_joint,
                    is_active,
                    bank_ifsc,
                    bank_name,
                ) = row
                key = _bank_key(bank_name, bank_ifsc)
                fh.write(
                    repr(
                        (
                            "A",
                            key,
                            open_dt,
                            ac_number,
                            acc_type,
                            curr_balance,
                            curr_balance_dt,
                            is_joint,
                            is_active,
                        )
                    )
                    + "\n"
                )
                accounts_count += 1

    except sqlite3.Error as exc:
        show_colorful_error(parent, "DB Error", f"Failed to read from DB:\n{exc}")
        logger.exception("export_banks: DB error: %s", exc)
        return
    except OSError as exc:
        msg = f"Failed to write export file:\n{exc}"
        show_colorful_error(parent, "File Error", msg)
        logger.exception("export_banks: file error: %s", exc)
        return

    show_colorful_info(
        parent,
        "Export Complete",
        f"Exported {banks_count} bank(s) and {accounts_count} "
        f"account(s) to:\n{export_file}",
    )


def import_banks(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Import ``banks`` and ``accounts`` from ``all_banks_and_accounts.txt``.

    Expected tuple format per line:

    Bank row::

        ('B', name, branch, IFSC, MICR)

    Account row::

        ('A', bank_key, open_dt, ac_number, type,
              curr_balance, curr_balance_dt, is_joint, is_active)

    A bank row is skipped when a bank with the same ``IFSC`` already exists
    (or, for banks without an IFSC, when ``name`` matches and both have no
    IFSC).  An account row is skipped when ``(b_id, ac_number)`` already
    exists.
    """
    if not os.path.exists(_EXPORT_FILE):
        show_colorful_info(
            parent,
            "No File",
            f"Import file not found:\n{_EXPORT_FILE}",
        )
        return

    banks_inserted = 0
    banks_skipped = 0
    accounts_inserted = 0
    accounts_skipped = 0
    malformed = 0

    # Maps bank_key → b_id for rows already in the DB or inserted this run,
    # so account rows can resolve their FK without repeated DB queries.
    key_to_id: dict[str, int] = {}

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

                # ── Parse the tuple literal ───────────────────────────────
                try:
                    value = ast.literal_eval(line)
                except Exception as exc:
                    logger.warning(
                        "import_banks: failed to parse line %d: %s",
                        lineno,
                        exc,
                    )
                    malformed += 1
                    continue

                if not isinstance(value, (list, tuple)) or len(value) < 2:
                    logger.warning(
                        "import_banks: short tuple on line %d: %r",
                        lineno,
                        value,
                    )
                    malformed += 1
                    continue

                row_type = value[0]

                # ── Bank row ('B') ────────────────────────────────────────
                if row_type == "B":
                    if len(value) < 5:
                        msg = "import_banks: bank tuple too short on line %d"
                        logger.warning(msg, lineno)
                        malformed += 1
                        continue

                    _, name, branch, ifsc, micr = value[:5]

                    if not name:
                        msg = "import_banks: empty bank name on line %d"
                        logger.warning(msg, lineno)
                        malformed += 1
                        continue

                    try:
                        # Duplicate check using IFSC (unique) when present,
                        # else name + no-IFSC combination.
                        if ifsc:
                            cursor.execute(
                                "SELECT b_id FROM banks" " WHERE IFSC = ? LIMIT 1",
                                (ifsc,),
                            )
                        else:
                            cursor.execute(
                                "SELECT b_id FROM banks"
                                " WHERE name = ? AND IFSC IS NULL LIMIT 1",
                                (name,),
                            )
                        existing = cursor.fetchone()

                        if existing:
                            key = _bank_key(name, ifsc)
                            key_to_id[key] = existing[0]
                            banks_skipped += 1
                            continue

                        cursor.execute(
                            "INSERT INTO banks (name, branch, IFSC, MICR)"
                            " VALUES (?, ?, ?, ?)",
                            (name, branch, ifsc, micr),
                        )
                        new_id = cursor.lastrowid
                        key_to_id[_bank_key(name, ifsc)] = new_id
                        banks_inserted += 1

                    except sqlite3.Error as exc:
                        logger.exception(
                            "import_banks: DB error on bank line %d: %s",
                            lineno,
                            exc,
                        )
                        msg = f"DB error on line {lineno} (bank): {exc}"
                        show_colorful_error(parent, "DB Error", msg)

                # ── Account row ('A') ─────────────────────────────────────
                elif row_type == "A":
                    if len(value) < 9:
                        msg = "import_banks: account tuple too short on line %d"
                        logger.warning(msg, lineno)
                        malformed += 1
                        continue

                    (
                        _,
                        bank_key,
                        open_dt,
                        ac_number,
                        acc_type,
                        curr_balance,
                        curr_balance_dt,
                        is_joint,
                        is_active,
                    ) = value[:9]

                    b_id = _resolve_bank_id(cursor, bank_key, key_to_id)
                    if b_id is None:
                        logger.warning(
                            "import_banks: cannot resolve bank key '%s' on line %d",
                            bank_key,
                            lineno,
                        )
                        accounts_skipped += 1
                        continue

                    try:
                        cursor.execute(
                            "SELECT 1 FROM accounts"
                            " WHERE b_id = ? AND ac_number = ? LIMIT 1",
                            (b_id, ac_number),
                        )
                        if cursor.fetchone():
                            accounts_skipped += 1
                            continue

                        cursor.execute(
                            "INSERT INTO accounts (b_id, open_dt, ac_number, "
                            "type, curr_balance, curr_balance_dt, is_joint, "
                            "is_active)"
                            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                b_id,
                                open_dt,
                                ac_number,
                                acc_type,
                                curr_balance,
                                curr_balance_dt,
                                is_joint,
                                is_active,
                            ),
                        )
                        accounts_inserted += 1

                    except sqlite3.Error as exc:
                        logger.exception(
                            "import_banks: DB error on account line %d: %s",
                            lineno,
                            exc,
                        )
                        msg = f"DB error on line {lineno} (account): {exc}"
                        show_colorful_error(parent, "DB Error", msg)

                else:
                    logger.warning(
                        "import_banks: unknown row type '%s' on line %d",
                        row_type,
                        lineno,
                    )
                    malformed += 1

            try:
                conn.commit()
            except Exception:
                pass  # connection may auto-commit

    except OSError as exc:
        logger.exception("import_banks: file error: %s", exc)
        msg = f"Failed to open import file:\n{exc}"
        show_colorful_error(parent, "File Error", msg)
        return

    show_colorful_info(
        parent,
        "Import Complete",
        f"Banks    — inserted: {banks_inserted}, skipped: {banks_skipped}\n"
        f"Accounts — inserted: {accounts_inserted}, skipped: {accounts_skipped}\n"
        f"Malformed lines: {malformed}\n"
        f"Source: {_EXPORT_FILE}",
    )
