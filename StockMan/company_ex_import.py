# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\company_export.py

"""company_export.py

Reads company data from the database and exports it to a text file where each
row is written as a Python tuple literal (one tuple per line).
"""

import sqlite3
import tkinter as tk
from typing import Union
import os
import shutil
import ast

# Project-specific imports
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
)
from Shared.globals import STOCK_DB_PATH, get_db_connection
from .helpers import list_all_id_stk

from Shared.globals import logger


def prepare_companies_export_file(db_path: str) -> str:
    """
    Ensure an export file is ready in the same directory as `db_path`.

    Behavior:
    - Data dir is dirname(db_path).
    - If `all_companies.txt` exists, copy it to `Backup/` with suffix
      `.backup.txt` and return the path to `all_companies.txt` for export.
    - Else create an empty `all_companies.txt` and return its path.
    """
    data_dir = os.path.dirname(os.path.abspath(db_path))
    backup_dir = os.path.join(data_dir, "Backup")
    os.makedirs(backup_dir, exist_ok=True)

    primary = os.path.join(data_dir, "all_companies.txt")
    backup_name = "all_companies.backup.txt"
    backup_path = os.path.join(backup_dir, backup_name)

    # If primary exists, back it up and use it
    if os.path.exists(primary):
        try:
            shutil.copy2(primary, backup_path)
        except OSError:
            # If backup fails, continue and still use primary path for writing
            logger.exception(
                "prepare_companies_export_file: failed to backup %s", primary
            )
        return primary

    # Neither exists: create primary and return it
    open(primary, "w", encoding="utf-8").close()
    return primary


def export_company(
    parent: Union[tk.Toplevel, tk.Tk], calling_button: tk.Widget | None = None
) -> None:
    """Exports company data to a text file where each row is a tuple.

    The order of rows follows the `all_ids` returned by `list_all_id_stk()`.
    Each line of the output file contains a Python tuple literal produced with
    repr(tuple(row)), so strings are quoted and numeric types are preserved.
    """
    export_file = prepare_companies_export_file(STOCK_DB_PATH)

    # Get the ordered list of stock ids we should export
    all_ids = list_all_id_stk(parent)
    if not all_ids:
        show_colorful_info(parent, "No Data", "No stocks found to export.")
        return

    # Columns requested (in this order):
    cols = (
        "stk_code",
        "isin",
        "company_name",
        "short_name",
        "ticker",  # <-- NEW FIELD
        "sector",
        "face_value",
        "tick",
        "is_active",
        "is_etf",
        "note_stk",
    )

    exported_count = 0
    try:
        with get_db_connection() as conn, open(
            export_file, "w", encoding="utf-8"
        ) as f:
            cursor = conn.cursor()

            # iterate in the order provided by all_ids
            # and write each row as a tuple
            for id_stk in all_ids:
                cursor.execute(
                    f"SELECT {', '.join(cols)} FROM stocks WHERE id_stk = ?",
                    (id_stk,),
                )
                row = cursor.fetchone()
                if row is None:
                    # skip missing rows but continue with others
                    continue

                # Write the row as a Python tuple literal on its own line
                # Use repr(tuple(row)) so strings are quoted
                # and non-strings appear as-is
                f.write(repr(tuple(row)) + "\n")
                exported_count += 1

    except sqlite3.Error as exc:
        show_colorful_error(
            parent, "DB Error", f"Failed to read from DB: {exc}"
        )
        logger.exception("export_company_data: DB error %s", exc)
        return
    except OSError as exc:
        show_colorful_error(
            parent, "File Error", f"Failed to write export file: {exc}"
        )
        logger.exception("export_company_data: file error %s", exc)
        return

    show_colorful_info(
        parent,
        "Export Complete",
        f"Exported {exported_count} rows to:\n{export_file}",
    )


def import_company(parent):
    """Import companies from the data directory `all_companies.txt`.

    The file is expected to contain one Python tuple literal per line with the
    fields in this order: stk_code, isin, company_name, short_name, sector,
    face_value, tick, is_active, is_etf, note_stk

    For each tuple, insert a row into `stocks` only if a row with the same
    `stk_code` or `isin` does not already exist. Reports counts on completion.
    """

    data_dir = os.path.dirname(os.path.abspath(STOCK_DB_PATH))
    src_file = os.path.join(data_dir, "all_companies.txt")

    if not os.path.exists(src_file):
        show_colorful_info(
            parent, "No File", f"No import file found: {src_file}"
        )
        return

    inserted = 0
    skipped = 0
    malformed = 0

    try:
        with open(
            src_file, "r", encoding="utf-8"
        ) as fh, get_db_connection() as conn:
            cursor = conn.cursor()

            for lineno, raw in enumerate(fh, start=1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue

                try:
                    value = ast.literal_eval(line)
                except Exception as exc:  # pragma: no cover - malformed file
                    logger.exception(
                        "import_company: failed to parse line %s: %s",
                        lineno,
                        exc,
                    )
                    malformed += 1
                    continue

                if not isinstance(value, (list, tuple)) or len(value) < 10:
                    logger.warning(
                        "import_company: unexpected tuple on line %s: %r",
                        lineno,
                        value,
                    )
                    malformed += 1
                    continue

                # Support both old backups (10 items) and new backups (11 items)
                if len(value) >= 11:
                    (
                        stk_code,
                        isin,
                        company_name,
                        short_name,
                        ticker,  # <-- NEW FIELD
                        sector,
                        face_value,
                        tick,
                        is_active,
                        is_etf,
                        note_stk,
                    ) = value[:11]
                else:
                    (
                        stk_code,
                        isin,
                        company_name,
                        short_name,
                        sector,
                        face_value,
                        tick,
                        is_active,
                        is_etf,
                        note_stk,
                    ) = value[:10]
                    ticker = ""  # <-- Default for old backups

                # Skip completely empty identifiers
                if (not stk_code) and (not isin):
                    skipped += 1
                    continue

                try:
                    # Check existence by stk_code first, fallback to isin
                    exists = False
                    if stk_code:
                        cursor.execute(
                            "SELECT 1 FROM stocks WHERE stk_code = ? LIMIT 1",
                            (stk_code,),
                        )
                        if cursor.fetchone():
                            exists = True

                    if (not exists) and isin:
                        cursor.execute(
                            "SELECT 1 FROM stocks WHERE isin = ? LIMIT 1",
                            (isin,),
                        )
                        if cursor.fetchone():
                            exists = True

                    if exists:
                        skipped += 1
                        continue

                    # Insert missing row
                    cursor.execute(
                        "INSERT INTO stocks (stk_code, isin, company_name, "
                        "short_name, ticker, sector, face_value, tick, is_active, "  # <-- added ticker
                        "is_etf, note_stk) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, "  # <-- added one '?'
                        "?, ?)",
                        (
                            stk_code,
                            isin,
                            company_name,
                            short_name,
                            ticker,  # <-- NEW FIELD
                            sector,
                            face_value,
                            tick,
                            is_active,
                            is_etf,
                            note_stk,
                        ),
                    )
                    inserted += 1

                except sqlite3.Error as exc:
                    # Log and continue with other lines
                    logger.exception(
                        "import_company: DB error on line %s: %s", lineno, exc
                    )
                    show_colorful_error(
                        parent,
                        "DB Error",
                        f"DB error while importing line {lineno}: {exc}",
                    )

            # commit the transaction if the connection wrapper
            # doesn't auto-commit
            try:
                conn.commit()
            except Exception:
                # ignore; connection may auto-commit
                pass

    except OSError as exc:
        logger.exception("import_company: file error %s", exc)
        show_colorful_error(
            parent, "File Error", f"Failed to open import file: {exc}"
        )
        return

    show_colorful_info(
        parent,
        "Import Complete",
        f"Inserted: {inserted}\nSkipped (already present or blank): "
        f"{skipped}\nMalformed lines: {malformed}\nSource: {src_file}",
    )


# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\company_export.py ends here
