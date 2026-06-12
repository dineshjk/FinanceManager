# -*- coding: utf-8 -*-
# File: BankMan\fd_transactions_ex_import.py

"""fd_transactions_ex_import.py

Export and import the ``fd_transactions`` table (Fixed Deposit transactions).

Export format
-------------
Each line is a Python tuple literal (produced by ``repr(tuple(...))``).
The first element is the row type ``'FDT'``::

    ('FDT', fd_number, fd_trans_dt, fd_description,
            fd_saving, fd_withdrawal, fd_principal, fd_int)

``fd_number`` (UNIQUE on ``fd_master``) identifies the parent FD portably
across databases.  ``account_id`` is derived from the fd_master record and
is never stored in the file.

Import behaviour
----------------
* Lines starting with ``#`` and blank lines are silently ignored.
* The parent FD is resolved by ``fd_number``; the row is skipped when the FD
  is not found.  ``account_id`` is taken from the fd_master record.
* Duplicate detection uses
  ``(fd_master_id, fd_trans_dt, fd_saving, fd_withdrawal, fd_principal,
  fd_int)``; a matching row is skipped.
* DB and file errors are reported via the GUI and logged; processing
  continues for the remaining lines.

Output / input file
-------------------
``C:\\Data\\Personal\\Finance_and_Investment\\finprog\\FinanceManager\\data\\all_fd_transactions.txt``

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
_EXPORT_FILE = os.path.join(_DATA_DIR, "all_fd_transactions.txt")
_BACKUP_NAME = "all_fd_transactions.backup.txt"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _prepare_export_file() -> str:
    """Ensure the export file and its ``Backup/`` directory exist.

    Copies the previous file to ``data/Backup/`` before overwriting.
    Returns the absolute path to ``all_fd_transactions.txt``.
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


def _resolve_fd_master(
    cursor: sqlite3.Cursor,
    fd_number: str,
    cache: dict,
) -> tuple[int, int] | None:
    """Return ``(fd_master_id, account_id)`` for the given *fd_number*.

    Checks *cache* first (keyed on ``fd_number``), then queries the DB.
    Returns ``None`` when the FD cannot be found.
    """
    if fd_number in cache:
        return cache[fd_number]

    cursor.execute(
        "SELECT fd_master_id, account_id" " FROM fd_master WHERE fd_number = ? LIMIT 1",
        (fd_number,),
    )
    row = cursor.fetchone()
    if row:
        cache[fd_number] = (row[0], row[1])
        return (row[0], row[1])

    logger.warning("_resolve_fd_master: fd_number %r not found in DB", fd_number)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def export_fd_transactions(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Export ``fd_transactions`` to ``all_fd_transactions.txt``.

    Each row is written as a Python tuple literal::

        ('FDT', fd_number, fd_trans_dt, fd_description,
                fd_saving, fd_withdrawal, fd_principal, fd_int)

    Rows are ordered by ``fd_trans_id`` so the original insertion order is
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
                    fm.fd_number,
                    t.fd_trans_dt,
                    t.fd_description,
                    t.fd_saving,
                    t.fd_withdrawal,
                    t.fd_principal,
                    t.fd_int
                FROM fd_transactions t
                JOIN fd_master fm ON t.fd_master_id = fm.fd_master_id
                ORDER BY t.fd_trans_id
            """)
            rows = cursor.fetchall()

            if not rows:
                show_colorful_info(
                    parent,
                    "No Data",
                    "No FD transactions found to export.",
                )
                return

            fh.write("# fd_transactions\n")
            for (
                fd_number,
                fd_trans_dt,
                fd_description,
                fd_saving,
                fd_withdrawal,
                fd_principal,
                fd_int,
            ) in rows:
                fh.write(
                    repr(
                        (
                            "FDT",
                            fd_number,
                            fd_trans_dt,
                            fd_description,
                            fd_saving,
                            fd_withdrawal,
                            fd_principal,
                            fd_int,
                        )
                    )
                    + "\n"
                )
                exported_count += 1

    except sqlite3.Error as exc:
        show_colorful_error(parent, "DB Error", f"Failed to read from DB:\n{exc}")
        logger.exception("export_fd_transactions: DB error: %s", exc)
        return
    except OSError as exc:
        msg = f"Failed to write export file:\n{exc}"
        show_colorful_error(parent, "File Error", msg)
        logger.exception("export_fd_transactions: file error: %s", exc)
        return

    show_colorful_info(
        parent,
        "Export Complete",
        f"Exported {exported_count} FD transaction(s) to:\n{export_file}",
    )


def import_fd_transactions(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Import ``fd_transactions`` from ``all_fd_transactions.txt``.

    Expected tuple format per line::

        ('FDT', fd_number, fd_trans_dt, fd_description,
                fd_saving, fd_withdrawal, fd_principal, fd_int)

    A row is **skipped** when:

    * The parent FD cannot be resolved by ``fd_number``.
    * A ``fd_transactions`` row with the same
      ``(fd_master_id, fd_trans_dt, fd_saving, fd_withdrawal,
      fd_principal, fd_int)`` already exists.

    ``account_id`` is taken from the fd_master record.
    ``fd_description`` may be ``None`` (stored as ``NULL``).
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

    # fd_number → (fd_master_id, account_id)
    fd_cache: dict[str, tuple[int, int]] = {}

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
                        "import_fd_transactions: parse error line %d: %s",
                        lineno,
                        exc,
                    )
                    malformed += 1
                    continue

                if not isinstance(value, (list, tuple)) or len(value) < 8:
                    logger.warning(
                        "import_fd_transactions: short tuple line %d: %r",
                        lineno,
                        value,
                    )
                    malformed += 1
                    continue

                (
                    row_type,
                    fd_number,
                    fd_trans_dt,
                    fd_description,
                    fd_saving,
                    fd_withdrawal,
                    fd_principal,
                    fd_int,
                ) = value[:8]

                if row_type != "FDT":
                    logger.warning(
                        "import_fd_transactions: unexpected row type %r" " on line %d",
                        row_type,
                        lineno,
                    )
                    malformed += 1
                    continue

                if not fd_number or not fd_trans_dt:
                    logger.warning(
                        "import_fd_transactions: missing required field" " on line %d",
                        lineno,
                    )
                    malformed += 1
                    continue

                # ── Resolve parent FD ─────────────────────────────────────
                fd_ids = _resolve_fd_master(cursor, fd_number, fd_cache)
                if fd_ids is None:
                    logger.warning(
                        "import_fd_transactions: skipping line %d"
                        " — fd_number %r not found",
                        lineno,
                        fd_number,
                    )
                    skipped += 1
                    continue
                fd_master_id, account_id = fd_ids

                try:
                    # ── Duplicate check ───────────────────────────────────
                    cursor.execute(
                        """
                        SELECT fd_trans_id FROM fd_transactions
                        WHERE fd_master_id  = ?
                          AND fd_trans_dt   = ?
                          AND fd_saving     = ?
                          AND fd_withdrawal = ?
                          AND fd_principal  = ?
                          AND fd_int        = ?
                        LIMIT 1
                        """,
                        (
                            fd_master_id,
                            fd_trans_dt,
                            fd_saving,
                            fd_withdrawal,
                            fd_principal,
                            fd_int,
                        ),
                    )
                    if cursor.fetchone():
                        skipped += 1
                        continue

                    # ── Insert ────────────────────────────────────────────
                    cursor.execute(
                        """
                        INSERT INTO fd_transactions
                            (fd_master_id, account_id, fd_trans_dt,
                             fd_description, fd_saving, fd_withdrawal,
                             fd_principal, fd_int)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            fd_master_id,
                            account_id,
                            fd_trans_dt,
                            fd_description,
                            fd_saving,
                            fd_withdrawal,
                            fd_principal,
                            fd_int,
                        ),
                    )
                    inserted += 1

                except sqlite3.Error as exc:
                    logger.exception(
                        "import_fd_transactions: DB error line %d: %s", lineno, exc
                    )
                    msg = f"DB error on line {lineno}: {exc}"
                    show_colorful_error(parent, "DB Error", msg)

            try:
                conn.commit()
            except Exception:
                pass  # connection may auto-commit

    except OSError as exc:
        logger.exception("import_fd_transactions: file error: %s", exc)
        msg = f"Failed to open import file:\n{exc}"
        show_colorful_error(parent, "File Error", msg)
        return

    show_colorful_info(
        parent,
        "Import Complete",
        f"FD Transactions — inserted: {inserted}, skipped: {skipped}\n"
        f"Malformed lines: {malformed}\n"
        f"Source: {_EXPORT_FILE}",
    )
