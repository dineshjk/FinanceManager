# -*- coding: utf-8 -*-
# BankMan/ins_transactions_ex_import.py

"""ins_transactions_ex_import.py

Export and import the ``ins_transactions`` table (INS transactions).

Export format
-------------
Each line is a Python tuple literal (produced by ``repr(tuple(...))``).
The first element is the row type ``'INST'``::

    ('INST', policy_number, ins_trans_dt, ins_description,
             premium_paid, payout_received)

``policy_number`` (UNIQUE on ``ins_master``) identifies the parent INS
account portably across databases.  ``account_id`` is derived from the
ins_master record and is never stored in the file.

Import behaviour
----------------
* Lines starting with ``#`` and blank lines are silently ignored.
* The parent INS account is resolved by ``policy_number``; the row is
  skipped when the account is not found.  ``account_id`` is taken from the
  ins_master record.
* Duplicate detection uses
  ``(ins_master_id, ins_trans_dt, premium_paid, payout_received)``
  ; a matching row is skipped.
* DB and file errors are reported via the GUI and logged; processing
  continues for the remaining lines.

Output / input file
-------------------
``C:\\Data\\Personal\\Finance_and_Investment\\finprog\\FinanceManager\\data\\all_ins_transactions.txt``

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
_EXPORT_FILE = os.path.join(_DATA_DIR, "all_ins_transactions.txt")
_BACKUP_NAME = "all_ins_transactions.backup.txt"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _prepare_export_file() -> str:
    """Ensure the export file and its ``Backup/`` directory exist.

    Copies the previous file to ``data/Backup/`` before overwriting.
    Returns the absolute path to ``all_ins_transactions.txt``.
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


def _resolve_ins_master(
    cursor: sqlite3.Cursor,
    policy_number: str,
    cache: dict,
) -> tuple[int, int] | None:
    """Return ``(ins_master_id, account_id)`` for *policy_number*.

    Checks *cache* first (keyed on ``policy_number``), then queries
    the DB.  Returns ``None`` when the INS account cannot be found.
    """
    if policy_number in cache:
        return cache[policy_number]

    cursor.execute(
        "SELECT ins_master_id, account_id"
        " FROM ins_master WHERE policy_number = ? LIMIT 1",
        (policy_number,),
    )
    row = cursor.fetchone()
    if row:
        cache[policy_number] = (row[0], row[1])
        return (row[0], row[1])

    logger.warning(
        "_resolve_ins_master: policy_number %r not found in DB",
        policy_number,
    )
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def export_ins_transactions(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Export ``ins_transactions`` to ``all_ins_transactions.txt``.

    Each row is written as a Python tuple literal::

        ('INST', policy_number, ins_trans_dt, ins_description,
                 premium_paid, payout_received)

    Rows are ordered by ``ins_trans_id`` so the original insertion order is
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
                    pm.policy_number,
                    t.ins_trans_dt,
                    t.ins_description,
                    t.premium_paid,
                    t.payout_received
                FROM ins_transactions t
                JOIN ins_master pm ON t.ins_master_id = pm.ins_master_id
                ORDER BY t.ins_trans_id
            """)
            rows = cursor.fetchall()

            if not rows:
                show_colorful_info(
                    parent,
                    "No Data",
                    "No INS transactions found to export.",
                )
                return

            fh.write("# ins_transactions\n")
            for (
                policy_number,
                ins_trans_dt,
                ins_description,
                premium_paid,
                payout_received,
            ) in rows:
                fh.write(
                    repr(
                        (
                            "INST",
                            policy_number,
                            ins_trans_dt,
                            ins_description,
                            premium_paid,
                            payout_received,
                        )
                    )
                    + "\n"
                )
                exported_count += 1

    except sqlite3.Error as exc:
        show_colorful_error(parent, "DB Error", f"Failed to read from DB:\n{exc}")
        logger.exception("export_ins_transactions: DB error: %s", exc)
        return
    except OSError as exc:
        msg = f"Failed to write export file:\n{exc}"
        show_colorful_error(parent, "File Error", msg)
        logger.exception("export_ins_transactions: file error: %s", exc)
        return

    show_colorful_info(
        parent,
        "Export Complete",
        f"Exported {exported_count} INS transaction(s) to:\n{export_file}",
    )


def import_ins_transactions(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Import ``ins_transactions`` from ``all_ins_transactions.txt``.

    Expected tuple format per line::

        ('INST', policy_number, ins_trans_dt, ins_description,
                 premium_paid, payout_received)

    A row is **skipped** when:

    * The parent INS account cannot be resolved by ``policy_number``.
    * A ``ins_transactions`` row with the same
      ``(ins_master_id, ins_trans_dt, premium_paid, payout_received,
      ins_balance)`` already exists.

    ``account_id`` is taken from the ins_master record.
    ``ins_description`` may be ``None`` (stored as ``NULL``).
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

    # policy_number → (ins_master_id, account_id)
    ins_cache: dict[str, tuple[int, int]] = {}

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
                        "import_ins_transactions: parse error line %d: %s",
                        lineno,
                        exc,
                    )
                    malformed += 1
                    continue

                if not isinstance(value, (list, tuple)) or len(value) < 6:
                    logger.warning(
                        "import_ins_transactions: short tuple line %d: %r",
                        lineno,
                        value,
                    )
                    malformed += 1
                    continue

                (
                    row_type,
                    policy_number,
                    ins_trans_dt,
                    ins_description,
                    premium_paid,
                    payout_received,
                    ins_balance,
                ) = value[:7]

                if row_type != "INST":
                    logger.warning(
                        "import_ins_transactions: unexpected row type" " %r on line %d",
                        row_type,
                        lineno,
                    )
                    malformed += 1
                    continue

                if not policy_number or not ins_trans_dt:
                    logger.warning(
                        "import_ins_transactions: missing required field" " on line %d",
                        lineno,
                    )
                    malformed += 1
                    continue

                # ── Resolve parent INS account ────────────────────────────
                ins_ids = _resolve_ins_master(cursor, policy_number, ins_cache)
                if ins_ids is None:
                    logger.warning(
                        "import_ins_transactions: skipping line %d"
                        " — policy_number %r not found",
                        lineno,
                        policy_number,
                    )
                    skipped += 1
                    continue
                ins_master_id, account_id = ins_ids

                try:
                    # ── Duplicate check ───────────────────────────────────
                    cursor.execute(
                        """
                        SELECT ins_trans_id FROM ins_transactions
                        WHERE ins_master_id  = ?
                          AND ins_trans_dt   = ?
                          AND premium_paid     = ?
                          AND payout_received = ?
                          AND ins_balance    = ?
                        LIMIT 1
                        """,
                        (
                            ins_master_id,
                            ins_trans_dt,
                            premium_paid,
                            payout_received,
                        ),
                    )
                    if cursor.fetchone():
                        skipped += 1
                        continue

                    # ── Insert ────────────────────────────────────────────
                    cursor.execute(
                        """
                        INSERT INTO ins_transactions
                            (ins_master_id, account_id, ins_trans_dt,
                             ins_description, premium_paid,
                             payout_received)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            ins_master_id,
                            account_id,
                            ins_trans_dt,
                            ins_description,
                            premium_paid,
                            payout_received,
                        ),
                    )
                    inserted += 1

                except sqlite3.Error as exc:
                    logger.exception(
                        "import_ins_transactions: DB error line %d: %s", lineno, exc
                    )
                    msg = f"DB error on line {lineno}: {exc}"
                    show_colorful_error(parent, "DB Error", msg)

            try:
                conn.commit()
            except Exception:
                pass  # connection may auto-commit

    except OSError as exc:
        logger.exception("import_ins_transactions: file error: %s", exc)
        msg = f"Failed to open import file:\n{exc}"
        show_colorful_error(parent, "File Error", msg)
        return

    show_colorful_info(
        parent,
        "Import Complete",
        f"INS Transactions — inserted: {inserted}, skipped: {skipped}\n"
        f"Malformed lines: {malformed}\n"
        f"Source: {_EXPORT_FILE}",
    )
