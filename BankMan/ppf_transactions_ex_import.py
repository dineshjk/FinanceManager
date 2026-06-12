# -*- coding: utf-8 -*-
# BankMan/ppf_transactions_ex_import.py

"""ppf_transactions_ex_import.py

Export and import the ``ppf_transactions`` table (PPF transactions).

Export format
-------------
Each line is a Python tuple literal (produced by ``repr(tuple(...))``).
The first element is the row type ``'PPFT'``::

    ('PPFT', ppf_account_number, ppf_trans_dt, ppf_description,
             ppf_saving, ppf_withdrawal, ppf_balance)

``ppf_account_number`` (UNIQUE on ``ppf_master``) identifies the parent PPF
account portably across databases.  ``account_id`` is derived from the
ppf_master record and is never stored in the file.

Import behaviour
----------------
* Lines starting with ``#`` and blank lines are silently ignored.
* The parent PPF account is resolved by ``ppf_account_number``; the row is
  skipped when the account is not found.  ``account_id`` is taken from the
  ppf_master record.
* Duplicate detection uses
  ``(ppf_master_id, ppf_trans_dt, ppf_saving, ppf_withdrawal, ppf_balance)``
  ; a matching row is skipped.
* DB and file errors are reported via the GUI and logged; processing
  continues for the remaining lines.

Output / input file
-------------------
``C:\\Data\\Personal\\Finance_and_Investment\\finprog\\FinanceManager\\data\\all_ppf_transactions.txt``

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
_EXPORT_FILE = os.path.join(_DATA_DIR, "all_ppf_transactions.txt")
_BACKUP_NAME = "all_ppf_transactions.backup.txt"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _prepare_export_file() -> str:
    """Ensure the export file and its ``Backup/`` directory exist.

    Copies the previous file to ``data/Backup/`` before overwriting.
    Returns the absolute path to ``all_ppf_transactions.txt``.
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


def _resolve_ppf_master(
    cursor: sqlite3.Cursor,
    ppf_account_number: str,
    cache: dict,
) -> tuple[int, int] | None:
    """Return ``(ppf_master_id, account_id)`` for *ppf_account_number*.

    Checks *cache* first (keyed on ``ppf_account_number``), then queries
    the DB.  Returns ``None`` when the PPF account cannot be found.
    """
    if ppf_account_number in cache:
        return cache[ppf_account_number]

    cursor.execute(
        "SELECT ppf_master_id, account_id"
        " FROM ppf_master WHERE ppf_account_number = ? LIMIT 1",
        (ppf_account_number,),
    )
    row = cursor.fetchone()
    if row:
        cache[ppf_account_number] = (row[0], row[1])
        return (row[0], row[1])

    logger.warning(
        "_resolve_ppf_master: ppf_account_number %r not found in DB",
        ppf_account_number,
    )
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def export_ppf_transactions(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Export ``ppf_transactions`` to ``all_ppf_transactions.txt``.

    Each row is written as a Python tuple literal::

        ('PPFT', ppf_account_number, ppf_trans_dt, ppf_description,
                 ppf_saving, ppf_withdrawal, ppf_balance)

    Rows are ordered by ``ppf_trans_id`` so the original insertion order is
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
                    pm.ppf_account_number,
                    t.ppf_trans_dt,
                    t.ppf_description,
                    t.ppf_saving,
                    t.ppf_withdrawal,
                    t.ppf_balance
                FROM ppf_transactions t
                JOIN ppf_master pm ON t.ppf_master_id = pm.ppf_master_id
                ORDER BY t.ppf_trans_id
            """)
            rows = cursor.fetchall()

            if not rows:
                show_colorful_info(
                    parent,
                    "No Data",
                    "No PPF transactions found to export.",
                )
                return

            fh.write("# ppf_transactions\n")
            for (
                ppf_account_number,
                ppf_trans_dt,
                ppf_description,
                ppf_saving,
                ppf_withdrawal,
                ppf_balance,
            ) in rows:
                fh.write(
                    repr(
                        (
                            "PPFT",
                            ppf_account_number,
                            ppf_trans_dt,
                            ppf_description,
                            ppf_saving,
                            ppf_withdrawal,
                            ppf_balance,
                        )
                    )
                    + "\n"
                )
                exported_count += 1

    except sqlite3.Error as exc:
        show_colorful_error(parent, "DB Error", f"Failed to read from DB:\n{exc}")
        logger.exception("export_ppf_transactions: DB error: %s", exc)
        return
    except OSError as exc:
        msg = f"Failed to write export file:\n{exc}"
        show_colorful_error(parent, "File Error", msg)
        logger.exception("export_ppf_transactions: file error: %s", exc)
        return

    show_colorful_info(
        parent,
        "Export Complete",
        f"Exported {exported_count} PPF transaction(s) to:\n{export_file}",
    )


def import_ppf_transactions(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Import ``ppf_transactions`` from ``all_ppf_transactions.txt``.

    Expected tuple format per line::

        ('PPFT', ppf_account_number, ppf_trans_dt, ppf_description,
                 ppf_saving, ppf_withdrawal, ppf_balance)

    A row is **skipped** when:

    * The parent PPF account cannot be resolved by ``ppf_account_number``.
    * A ``ppf_transactions`` row with the same
      ``(ppf_master_id, ppf_trans_dt, ppf_saving, ppf_withdrawal,
      ppf_balance)`` already exists.

    ``account_id`` is taken from the ppf_master record.
    ``ppf_description`` may be ``None`` (stored as ``NULL``).
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

    # ppf_account_number → (ppf_master_id, account_id)
    ppf_cache: dict[str, tuple[int, int]] = {}

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
                        "import_ppf_transactions: parse error line %d: %s",
                        lineno,
                        exc,
                    )
                    malformed += 1
                    continue

                if not isinstance(value, (list, tuple)) or len(value) < 7:
                    logger.warning(
                        "import_ppf_transactions: short tuple line %d: %r",
                        lineno,
                        value,
                    )
                    malformed += 1
                    continue

                (
                    row_type,
                    ppf_account_number,
                    ppf_trans_dt,
                    ppf_description,
                    ppf_saving,
                    ppf_withdrawal,
                    ppf_balance,
                ) = value[:7]

                if row_type != "PPFT":
                    logger.warning(
                        "import_ppf_transactions: unexpected row type" " %r on line %d",
                        row_type,
                        lineno,
                    )
                    malformed += 1
                    continue

                if not ppf_account_number or not ppf_trans_dt:
                    logger.warning(
                        "import_ppf_transactions: missing required field" " on line %d",
                        lineno,
                    )
                    malformed += 1
                    continue

                # ── Resolve parent PPF account ────────────────────────────
                ppf_ids = _resolve_ppf_master(cursor, ppf_account_number, ppf_cache)
                if ppf_ids is None:
                    logger.warning(
                        "import_ppf_transactions: skipping line %d"
                        " — ppf_account_number %r not found",
                        lineno,
                        ppf_account_number,
                    )
                    skipped += 1
                    continue
                ppf_master_id, account_id = ppf_ids

                try:
                    # ── Duplicate check ───────────────────────────────────
                    cursor.execute(
                        """
                        SELECT ppf_trans_id FROM ppf_transactions
                        WHERE ppf_master_id  = ?
                          AND ppf_trans_dt   = ?
                          AND ppf_saving     = ?
                          AND ppf_withdrawal = ?
                          AND ppf_balance    = ?
                        LIMIT 1
                        """,
                        (
                            ppf_master_id,
                            ppf_trans_dt,
                            ppf_saving,
                            ppf_withdrawal,
                            ppf_balance,
                        ),
                    )
                    if cursor.fetchone():
                        skipped += 1
                        continue

                    # ── Insert ────────────────────────────────────────────
                    cursor.execute(
                        """
                        INSERT INTO ppf_transactions
                            (ppf_master_id, account_id, ppf_trans_dt,
                             ppf_description, ppf_saving,
                             ppf_withdrawal, ppf_balance)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            ppf_master_id,
                            account_id,
                            ppf_trans_dt,
                            ppf_description,
                            ppf_saving,
                            ppf_withdrawal,
                            ppf_balance,
                        ),
                    )
                    inserted += 1

                except sqlite3.Error as exc:
                    logger.exception(
                        "import_ppf_transactions: DB error line %d: %s", lineno, exc
                    )
                    msg = f"DB error on line {lineno}: {exc}"
                    show_colorful_error(parent, "DB Error", msg)

            try:
                conn.commit()
            except Exception:
                pass  # connection may auto-commit

    except OSError as exc:
        logger.exception("import_ppf_transactions: file error: %s", exc)
        msg = f"Failed to open import file:\n{exc}"
        show_colorful_error(parent, "File Error", msg)
        return

    show_colorful_info(
        parent,
        "Import Complete",
        f"PPF Transactions — inserted: {inserted}, skipped: {skipped}\n"
        f"Malformed lines: {malformed}\n"
        f"Source: {_EXPORT_FILE}",
    )
