# -*- coding: utf-8 -*-
# File: BankMan\cc_transactions_ex_import.py

"""cc_transactions_ex_import.py

Export and import the ``cc_transactions`` table (Credit Card transactions).

Export format
-------------
Each line is a Python tuple literal (produced by ``repr(tuple(...))``).
The first element is the row type ``'CCT'``::

    ('CCT', card_number, cc_trans_dt, party, expense, cc_credit,
            bh_description_or_None)

``card_number`` (UNIQUE on ``card_master``) identifies the card portably
across databases.  ``bh_description`` replaces the raw ``bh_id`` integer so
the file works across installations where auto-assigned IDs differ.

Import behaviour
----------------
* Lines starting with ``#`` and blank lines are silently ignored.
* The card is resolved by ``card_number``; the row is skipped when the card
  is not found.  ``account_id`` is derived from the card master record and
  never stored in the file.
* ``bh_description`` is resolved to ``bh_id``; a ``None`` description maps to
  a ``NULL`` ``bh_id``.  An unrecognised description is logged and treated as
  ``NULL`` (rather than skipping the row).
* Duplicate detection uses ``(card_master_id, cc_trans_dt, party, expense,
  cc_credit)``; a matching row is skipped.
* DB and file errors are reported via the GUI and logged; processing
  continues for the remaining lines.

Output / input file
-------------------
``C:\\Data\\Personal\\Finance_and_Investment\\finprog\\FinanceManager\\data\\all_cc_transactions.txt``

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
_EXPORT_FILE = os.path.join(_DATA_DIR, "all_cc_transactions.txt")
_BACKUP_NAME = "all_cc_transactions.backup.txt"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _prepare_export_file() -> str:
    """Ensure the export file and its ``Backup/`` directory exist.

    Copies the previous file to ``data/Backup/`` before overwriting.
    Returns the absolute path to ``all_cc_transactions.txt``.
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


def _resolve_card_master(
    cursor: sqlite3.Cursor,
    card_number: str,
    cache: dict,
) -> tuple[int, int] | None:
    """Return ``(card_master_id, account_id)`` for the given *card_number*.

    Checks *cache* first (keyed on ``card_number``), then queries the DB.
    Returns ``None`` when the card cannot be found.
    """
    if card_number in cache:
        return cache[card_number]

    cursor.execute(
        "SELECT card_master_id, account_id"
        " FROM card_master WHERE card_number = ? LIMIT 1",
        (card_number,),
    )
    row = cursor.fetchone()
    if row:
        cache[card_number] = (row[0], row[1])
        return (row[0], row[1])

    logger.warning("_resolve_card_master: card_number %r not found in DB", card_number)
    return None


def _resolve_bh_id(
    cursor: sqlite3.Cursor,
    bh_description: str | None,
    cache: dict,
) -> int | None:
    """Return ``bh_id`` for *bh_description*, or ``None`` for ``NULL``.

    Checks *cache* first, then queries ``budget_head``.  An unrecognised
    description is logged and returns ``None`` (stored as ``NULL``).
    """
    if bh_description is None:
        return None

    if bh_description in cache:
        return cache[bh_description]

    cursor.execute(
        "SELECT bh_id FROM budget_head" " WHERE bh_description = ? LIMIT 1",
        (bh_description,),
    )
    row = cursor.fetchone()
    if row:
        cache[bh_description] = row[0]
        return row[0]

    logger.warning(
        "_resolve_bh_id: bh_description %r not found; storing NULL",
        bh_description,
    )
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def export_cc_transactions(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Export ``cc_transactions`` to ``all_cc_transactions.txt``.

    Each row is written as a Python tuple literal::

        ('CCT', card_number, cc_trans_dt, party, expense, cc_credit,
                point_earned, points_balance, points_redeemed,
                bh_description_or_None)

    Rows are ordered by ``cc_trans_id`` so the original insertion order is
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
                    cm.card_number,
                    t.cc_trans_dt,
                    t.party,
                    t.expense,
                    t.cc_credit,
                    bh.bh_description
                FROM cc_transactions t
                JOIN  card_master cm ON t.card_master_id = cm.card_master_id
                LEFT JOIN budget_head bh ON t.bh_id = bh.bh_id
                ORDER BY t.cc_trans_id
            """)
            rows = cursor.fetchall()

            if not rows:
                show_colorful_info(
                    parent,
                    "No Data",
                    "No CC transactions found to export.",
                )
                return

            fh.write("# cc_transactions\n")
            for (
                card_number,
                cc_trans_dt,
                party,
                expense,
                cc_credit,
                bh_description,
            ) in rows:
                fh.write(
                    repr(
                        (
                            "CCT",
                            card_number,
                            cc_trans_dt,
                            party,
                            expense,
                            cc_credit,
                            bh_description,
                        )
                    )
                    + "\n"
                )
                exported_count += 1

    except sqlite3.Error as exc:
        show_colorful_error(parent, "DB Error", f"Failed to read from DB:\n{exc}")
        logger.exception("export_cc_transactions: DB error: %s", exc)
        return
    except OSError as exc:
        msg = f"Failed to write export file:\n{exc}"
        show_colorful_error(parent, "File Error", msg)
        logger.exception("export_cc_transactions: file error: %s", exc)
        return

    show_colorful_info(
        parent,
        "Export Complete",
        f"Exported {exported_count} CC transaction(s) to:\n{export_file}",
    )


def import_cc_transactions(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Import ``cc_transactions`` from ``all_cc_transactions.txt``.

    Expected tuple format per line::

        ('CCT', card_number, cc_trans_dt, party, expense, cc_credit,
                bh_description_or_None)

    A row is **skipped** when:

    * The card cannot be resolved by ``card_number``.
    * A ``cc_transactions`` row with the same
      ``(card_master_id, cc_trans_dt, party, expense, cc_credit)`` already
      exists.

    ``account_id`` is taken from the card master record.
    ``bh_id`` is resolved by ``bh_description``; unknown descriptions are
    stored as ``NULL`` rather than aborting the row.
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

    # card_number → (card_master_id, account_id)
    card_cache: dict[str, tuple[int, int]] = {}
    # bh_description → bh_id
    bh_cache: dict[str, int] = {}

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
                        "import_cc_transactions: parse error line %d: %s",
                        lineno,
                        exc,
                    )
                    malformed += 1
                    continue

                if not isinstance(value, (list, tuple)) or len(value) < 7:
                    logger.warning(
                        "import_cc_transactions: short tuple line %d: %r",
                        lineno,
                        value,
                    )
                    malformed += 1
                    continue

                (
                    row_type,
                    card_number,
                    cc_trans_dt,
                    party,
                    expense,
                    cc_credit,
                    bh_description,
                ) = value[:7]

                if row_type != "CCT":
                    logger.warning(
                        "import_cc_transactions: unexpected row type %r" " on line %d",
                        row_type,
                        lineno,
                    )
                    malformed += 1
                    continue

                if not card_number or not cc_trans_dt or not party:
                    logger.warning(
                        "import_cc_transactions: missing required field" " on line %d",
                        lineno,
                    )
                    malformed += 1
                    continue

                # ── Resolve card master ───────────────────────────────────
                card_ids = _resolve_card_master(cursor, card_number, card_cache)
                if card_ids is None:
                    logger.warning(
                        "import_cc_transactions: skipping line %d"
                        " — card_number %r not found",
                        lineno,
                        card_number,
                    )
                    skipped += 1
                    continue
                card_master_id, account_id = card_ids

                # ── Resolve budget head (NULL-safe) ───────────────────────
                bh_id = _resolve_bh_id(cursor, bh_description, bh_cache)

                try:
                    # ── Duplicate check ───────────────────────────────────
                    cursor.execute(
                        """
                        SELECT cc_trans_id FROM cc_transactions
                        WHERE card_master_id = ?
                          AND cc_trans_dt    = ?
                          AND party          = ?
                          AND expense        = ?
                          AND cc_credit      = ?
                        LIMIT 1
                        """,
                        (
                            card_master_id,
                            cc_trans_dt,
                            party,
                            expense,
                            cc_credit,
                        ),
                    )
                    if cursor.fetchone():
                        skipped += 1
                        continue

                    # ── Insert ────────────────────────────────────────────
                    cursor.execute(
                        """
                        INSERT INTO cc_transactions
                            (card_master_id, account_id, cc_trans_dt,
                             party, expense, cc_credit, bh_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            card_master_id,
                            account_id,
                            cc_trans_dt,
                            party,
                            expense,
                            cc_credit,
                            bh_id,
                        ),
                    )
                    inserted += 1

                except sqlite3.Error as exc:
                    logger.exception(
                        "import_cc_transactions: DB error line %d: %s", lineno, exc
                    )
                    msg = f"DB error on line {lineno}: {exc}"
                    show_colorful_error(parent, "DB Error", msg)

            try:
                conn.commit()
            except Exception:
                pass  # connection may auto-commit

    except OSError as exc:
        logger.exception("import_cc_transactions: file error: %s", exc)
        msg = f"Failed to open import file:\n{exc}"
        show_colorful_error(parent, "File Error", msg)
        return

    show_colorful_info(
        parent,
        "Import Complete",
        f"CC Transactions — inserted: {inserted}, skipped: {skipped}\n"
        f"Malformed lines: {malformed}\n"
        f"Source: {_EXPORT_FILE}",
    )
