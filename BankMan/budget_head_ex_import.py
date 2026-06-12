# -*- coding: utf-8 -*-
# BankMan/budget_head_ex_import.py

"""budget_head_ex_import.py

Reads budget-head (income/expense category) data from the BankMan database
and exports it to a text file, or imports from that same file back into the
database.

Export format
-------------
Each line is a Python tuple literal (produced by ``repr(tuple(...))``) with
three fields in this order::

    (bh_description, bh_type, parent_description)

``parent_description`` is the ``bh_description`` of the parent budget head,
or ``None`` for top-level categories.  Using the description instead of the
raw ``parent_bh_id`` integer makes the file portable across databases (IDs
are auto-assigned and differ between installations).

Rows are exported ordered by ``bh_id`` so that parent rows always appear
before their children, which allows a single-pass import.

Import behaviour
----------------
* Lines starting with ``#`` and blank lines are ignored.
* For each row the parent is resolved by looking up ``parent_description``
  in the current database (or in rows already inserted during this run).
* A row is skipped (not inserted) if a budget head with the same
  ``(bh_description, bh_type, parent_bh_id)`` already exists — this matches
  the unique index ``uix_budget_head`` in the schema.
* DB and file errors are reported via the GUI and logged; processing
  continues for remaining lines.

Output / input file
-------------------
``C:\\Data\\Personal\\Finance_and_Investment\\finprog\\FinanceManager\\data\\all_budget_heads.txt``

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
_EXPORT_FILE = os.path.join(_DATA_DIR, "all_budget_heads.txt")
_BACKUP_NAME = "all_budget_heads.backup.txt"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _prepare_export_file() -> str:
    """Ensure the export file and its backup directory exist.

    If the file already exists it is copied to ``data/Backup/`` before being
    overwritten, matching the pattern used by ``company_ex_import.py``.

    Returns the absolute path to ``all_budget_heads.txt``.
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


def _resolve_parent_id(
    cursor: sqlite3.Cursor,
    parent_description: str | None,
    description_to_id: dict,
) -> int | None:
    """Return the ``bh_id`` for *parent_description*, or ``None``.

    First checks *description_to_id* (rows inserted in the current session),
    then queries the live database so that pre-existing parents are found too.
    Returns ``None`` when *parent_description* is ``None`` or not found.
    """
    if parent_description is None:
        return None

    # Fast path: already inserted / seen in this session
    if parent_description in description_to_id:
        return description_to_id[parent_description]

    # Fallback: query the database
    cursor.execute(
        "SELECT bh_id FROM budget_head WHERE bh_description = ? LIMIT 1",
        (parent_description,),
    )
    row = cursor.fetchone()
    if row:
        description_to_id[parent_description] = row[0]
        return row[0]

    logger.warning(
        "_resolve_parent_id: parent '%s' not found in DB", parent_description
    )
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def export_budget_head(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Export all budget heads to ``all_budget_heads.txt``.

    Each row is written as a Python tuple literal::

        (bh_description, bh_type, parent_description_or_None)

    Rows are ordered by ``bh_id`` so parents always precede their children.
    A backup of any previous export file is created automatically.
    """
    export_file = _prepare_export_file()
    exported_count = 0

    try:
        with get_db_connection(BANK_DB_PATH) as conn, open(
            export_file, "w", encoding="utf-8"
        ) as fh:
            cursor = conn.cursor()

            # Join to resolve parent_bh_id → parent bh_description.
            # ORDER BY bh_id guarantees parents come before their children.
            cursor.execute("""
                SELECT
                    b.bh_description,
                    b.bh_type,
                    p.bh_description  AS parent_description
                FROM budget_head b
                LEFT JOIN budget_head p ON b.parent_bh_id = p.bh_id
                ORDER BY b.bh_id
                """)
            rows = cursor.fetchall()

            if not rows:
                show_colorful_info(
                    parent, "No Data", "No budget heads found to export."
                )
                return

            for row in rows:
                fh.write(repr(tuple(row)) + "\n")
                exported_count += 1

    except sqlite3.Error as exc:
        show_colorful_error(parent, "DB Error", f"Failed to read from DB:\n{exc}")
        logger.exception("export_budget_head: DB error: %s", exc)
        return
    except OSError as exc:
        msg = f"Failed to write export file:\n{exc}"
        show_colorful_error(parent, "File Error", msg)
        logger.exception("export_budget_head: file error: %s", exc)
        return

    show_colorful_info(
        parent,
        "Export Complete",
        f"Exported {exported_count} budget head(s) to:\n{export_file}",
    )


def import_budget_head(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Import budget heads from ``all_budget_heads.txt`` into the database.

    Expected tuple format per line::

        (bh_description, bh_type, parent_description_or_None)

    A row is **skipped** when a budget head with the same
    ``(bh_description, bh_type, parent_bh_id)`` already exists (duplicate
    detection uses the unique index ``uix_budget_head``).

    Parent rows must appear before their children in the file (the exporter
    guarantees this by ordering on ``bh_id``).
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

    # Maps bh_description → newly assigned bh_id for rows inserted during
    # this session, so child rows can resolve their parent immediately.
    description_to_id: dict[str, int] = {}

    try:
        with open(_EXPORT_FILE, "r", encoding="utf-8") as fh, get_db_connection(
            BANK_DB_PATH
        ) as conn:
            cursor = conn.cursor()

            for lineno, raw in enumerate(fh, start=1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue

                # --- Parse the tuple literal ---
                try:
                    value = ast.literal_eval(line)
                except Exception as exc:
                    logger.warning(
                        "import_budget_head: failed to parse line %d: %s",
                        lineno,
                        exc,
                    )
                    malformed += 1
                    continue

                if not isinstance(value, (list, tuple)) or len(value) < 3:
                    logger.warning(
                        "import_budget_head: unexpected format on line %d: %r",
                        lineno,
                        value,
                    )
                    malformed += 1
                    continue

                bh_description, bh_type, parent_description = value[:3]

                if not bh_description or not bh_type:
                    skipped += 1
                    continue

                # --- Resolve parent ---
                parent_bh_id = _resolve_parent_id(
                    cursor, parent_description, description_to_id
                )

                try:
                    # Check for duplicate using the same criteria as the
                    # unique index: (bh_description, IFNULL(parent_bh_id, 0), bh_type)
                    cursor.execute(
                        """
                        SELECT bh_id FROM budget_head
                        WHERE bh_description = ?
                          AND bh_type        = ?
                          AND IFNULL(parent_bh_id, 0) = IFNULL(?, 0)
                        LIMIT 1
                        """,
                        (bh_description, bh_type, parent_bh_id),
                    )
                    existing = cursor.fetchone()
                    if existing:
                        # Record existing id so children can still resolve it
                        description_to_id[bh_description] = existing[0]
                        skipped += 1
                        continue

                    # Insert the new row
                    cursor.execute(
                        """
                        INSERT INTO budget_head (bh_description, bh_type, parent_bh_id)
                        VALUES (?, ?, ?)
                        """,
                        (bh_description, bh_type, parent_bh_id),
                    )
                    new_id = cursor.lastrowid
                    description_to_id[bh_description] = new_id
                    inserted += 1

                except sqlite3.Error as exc:
                    logger.exception(
                        "import_budget_head: DB error on line %d: %s",
                        lineno,
                        exc,
                    )
                    msg = f"DB error while importing line {lineno}:\n{exc}"
                    show_colorful_error(parent, "DB Error", msg)

            try:
                conn.commit()
            except Exception:
                pass  # Connection may auto-commit

    except OSError as exc:
        logger.exception("import_budget_head: file error: %s", exc)
        msg = f"Failed to open import file:\n{exc}"
        show_colorful_error(parent, "File Error", msg)
        return

    show_colorful_info(
        parent,
        "Import Complete",
        f"Inserted: {inserted}\n"
        f"Skipped (already present or blank): {skipped}\n"
        f"Malformed lines: {malformed}\n"
        f"Source: {_EXPORT_FILE}",
    )
