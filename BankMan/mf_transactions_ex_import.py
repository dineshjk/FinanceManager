# -*- coding: utf-8 -*-
# BankMan/mf_transactions_ex_import.py

"""mf_transactions_ex_import.py

Export and import the ``mf_transactions`` table (MF transactions).

Export format
-------------
Each line is a Python tuple literal (produced by ``repr(tuple(...))``).
The first element is the row type ``'MFT'``::

    ('MFT', folio_number, mf_trans_dt, mf_description,
             mf_purchase, mf_redemption, units, nav)

``folio_number`` (UNIQUE on ``mf_master``) identifies the parent MF
account portably across databases.  ``account_id`` is derived from the
mf_master record and is never stored in the file.

Import behaviour
----------------
* Lines starting with ``#`` and blank lines are silently ignored.
* The parent MF account is resolved by ``folio_number``; the row is
  skipped when the account is not found.  ``account_id`` is taken from the
  mf_master record.
* Duplicate detection uses
  ``(mf_master_id, mf_trans_dt, mf_purchase, mf_redemption, units, nav)``
  ; a matching row is skipped.
* DB and file errors are reported via the GUI and logged; processing
  continues for the remaining lines.

Output / input file
-------------------
``C:\\Data\\Personal\\Finance_and_Investment\\finprog\\FinanceManager\\data\\all_mf_transactions.txt``

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
_EXPORT_FILE = os.path.join(_DATA_DIR, "all_mf_transactions.txt")
_BACKUP_NAME = "all_mf_transactions.backup.txt"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _prepare_export_file() -> str:
    """Ensure the export file and its ``Backup/`` directory exist.

    Copies the previous file to ``data/Backup/`` before overwriting.
    Returns the absolute path to ``all_mf_transactions.txt``.
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


def _resolve_mf_master(
    cursor: sqlite3.Cursor,
    folio_number: str,
    cache: dict,
) -> tuple[int, int] | None:
    """Return ``(mf_master_id, account_id)`` for *folio_number*.

    Checks *cache* first (keyed on ``folio_number``), then queries
    the DB.  Returns ``None`` when the MF account cannot be found.
    """
    if folio_number in cache:
        return cache[folio_number]

    cursor.execute(
        "SELECT mf_master_id, account_id"
        " FROM mf_master WHERE folio_number = ? LIMIT 1",
        (folio_number,),
    )
    row = cursor.fetchone()
    if row:
        cache[folio_number] = (row[0], row[1])
        return (row[0], row[1])

    logger.warning(
        "_resolve_mf_master: folio_number %r not found in DB",
        folio_number,
    )
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def export_mf_transactions(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Export ``mf_transactions`` to ``all_mf_transactions.txt``.

    Each row is written as a Python tuple literal::

        ('MFT', folio_number, mf_trans_dt, mf_description,
                 mf_purchase, mf_redemption, units, nav)

    Rows are ordered by ``mf_trans_id`` so the original insertion order is
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
                    pm.folio_number,
                    t.mf_trans_dt,
                    t.mf_description,
                    t.mf_purchase,
                    t.mf_redemption,
                    t.units,
                    t.nav
                FROM mf_transactions t
                JOIN mf_master pm ON t.mf_master_id = pm.mf_master_id
                ORDER BY t.mf_trans_id
            """)
            rows = cursor.fetchall()

            if not rows:
                show_colorful_info(
                    parent,
                    "No Data",
                    "No MF transactions found to export.",
                )
                return

            fh.write("# mf_transactions\n")
            for (
                folio_number,
                mf_trans_dt,
                mf_description,
                mf_purchase,
                mf_redemption,
                units,
            ) in rows:
                fh.write(
                    repr(
                        (
                            "MFT",
                            folio_number,
                            mf_trans_dt,
                            mf_description,
                            mf_purchase,
                            mf_redemption,
                            units,
                            nav,
                        )
                    )
                    + "\n"
                )
                exported_count += 1

    except sqlite3.Error as exc:
        show_colorful_error(parent, "DB Error", f"Failed to read from DB:\n{exc}")
        logger.exception("export_mf_transactions: DB error: %s", exc)
        return
    except OSError as exc:
        msg = f"Failed to write export file:\n{exc}"
        show_colorful_error(parent, "File Error", msg)
        logger.exception("export_mf_transactions: file error: %s", exc)
        return

    show_colorful_info(
        parent,
        "Export Complete",
        f"Exported {exported_count} MF transaction(s) to:\n{export_file}",
    )


def import_mf_transactions(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Import ``mf_transactions`` from ``all_mf_transactions.txt``.

    Expected tuple format per line::

        ('MFT', folio_number, mf_trans_dt, mf_description,
                 mf_purchase, mf_redemption, units, nav)

    A row is **skipped** when:

    * The parent MF account cannot be resolved by ``folio_number``.
    * A ``mf_transactions`` row with the same
      ``(mf_master_id, mf_trans_dt, mf_purchase, mf_redemption,
      units)`` already exists.

    ``account_id`` is taken from the mf_master record.
    ``mf_description`` may be ``None`` (stored as ``NULL``).
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

    # folio_number → (mf_master_id, account_id)
    mf_cache: dict[str, tuple[int, int]] = {}

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
                        "import_mf_transactions: parse error line %d: %s",
                        lineno,
                        exc,
                    )
                    malformed += 1
                    continue

                if not isinstance(value, (list, tuple)) or len(value) < 8:
                    logger.warning(
                        "import_mf_transactions: short tuple line %d: %r",
                        lineno,
                        value,
                    )
                    malformed += 1
                    continue

                (
                    row_type,
                    folio_number,
                    mf_trans_dt,
                    mf_description,
                    mf_purchase,
                    mf_redemption,
                    units,
                    nav,
                ) = value[:8]

                if row_type != "MFT":
                    logger.warning(
                        "import_mf_transactions: unexpected row type" " %r on line %d",
                        row_type,
                        lineno,
                    )
                    malformed += 1
                    continue

                if not folio_number or not mf_trans_dt:
                    logger.warning(
                        "import_mf_transactions: missing required field" " on line %d",
                        lineno,
                    )
                    malformed += 1
                    continue

                # ── Resolve parent MF account ────────────────────────────
                mf_ids = _resolve_mf_master(cursor, folio_number, mf_cache)
                if mf_ids is None:
                    logger.warning(
                        "import_mf_transactions: skipping line %d"
                        " — folio_number %r not found",
                        lineno,
                        folio_number,
                    )
                    skipped += 1
                    continue
                mf_master_id, account_id = mf_ids

                try:
                    # ── Duplicate check ───────────────────────────────────
                    cursor.execute(
                        """
                        SELECT mf_trans_id FROM mf_transactions
                        WHERE mf_master_id  = ?
                          AND mf_trans_dt   = ?
                          AND mf_purchase     = ?
                          AND mf_redemption = ?
                          AND units    = ?
                        LIMIT 1
                        """,
                        (
                            mf_master_id,
                            mf_trans_dt,
                            mf_purchase,
                            mf_redemption,
                            units,
                            nav,
                        ),
                    )
                    if cursor.fetchone():
                        skipped += 1
                        continue

                    # ── Insert ────────────────────────────────────────────
                    cursor.execute(
                        """
                        INSERT INTO mf_transactions
                            (mf_master_id, account_id, mf_trans_dt,
                             mf_description, mf_purchase,
                             mf_redemption, units, nav)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            mf_master_id,
                            account_id,
                            mf_trans_dt,
                            mf_description,
                            mf_purchase,
                            mf_redemption,
                            units,
                            nav,
                        ),
                    )
                    inserted += 1

                except sqlite3.Error as exc:
                    logger.exception(
                        "import_mf_transactions: DB error line %d: %s", lineno, exc
                    )
                    msg = f"DB error on line {lineno}: {exc}"
                    show_colorful_error(parent, "DB Error", msg)

            try:
                conn.commit()
            except Exception:
                pass  # connection may auto-commit

    except OSError as exc:
        logger.exception("import_mf_transactions: file error: %s", exc)
        msg = f"Failed to open import file:\n{exc}"
        show_colorful_error(parent, "File Error", msg)
        return

    show_colorful_info(
        parent,
        "Import Complete",
        f"MF Transactions — inserted: {inserted}, skipped: {skipped}\n"
        f"Malformed lines: {malformed}\n"
        f"Source: {_EXPORT_FILE}",
    )
