# -*- coding: utf-8 -*-
# StockMan/watchlist_from_file.py

"""
watchlist_from_file.py
----------------------
Imports watchlist data from a legacy database into the current database.
"""

import os
import sqlite3
from Shared.globals import get_db_connection, logger, PROJECT_ROOT
from Shared.dialog_utils import show_colorful_info, show_colorful_error

SRC_LEGACY_DB = os.path.join(PROJECT_ROOT, "data", "mystocks_old.db")


def import_watchlist_from_file(
    parent, src_db_path: str = SRC_LEGACY_DB
) -> None:
    """Imports all watchlist records from the legacy database."""

    # Follow the existing project pattern: forcefully use the absolute path
    # to ensure it resolves regardless of the working directory.
    src_db_path = SRC_LEGACY_DB

    if not os.path.exists(src_db_path):
        show_colorful_error(
            parent,
            "File Not Found",
            f"Could not find legacy database at:\n{src_db_path}",
        )
        return

    imported_count = 0
    skipped_count = 0

    try:
        # 1. Fetch from the Old Database
        old_conn = sqlite3.connect(src_db_path)
        old_cur = old_conn.cursor()

        # Verify the table exists in the old database
        old_cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='watchlist'"
        )
        if not old_cur.fetchone():
            show_colorful_error(
                parent,
                "Old DB Error",
                "The legacy database does not have a 'watchlist' table.",
            )
            old_conn.close()
            return

        # Join with stocks in the old DB to get the company_name instead of relying on old id_stk
        old_cur.execute("""
            SELECT w.target_buy_price, w.target_sell_price, w.notes, s.company_name
            FROM watchlist w
            JOIN stocks s ON w.id_stk = s.id_stk
        """)
        legacy_watchlist = old_cur.fetchall()
        old_conn.close()

        if not legacy_watchlist:
            show_colorful_info(
                parent,
                "Done",
                "No watchlist entries found in the legacy database.",
            )
            return

        # 2. Insert into the New Database
        with get_db_connection() as new_conn:
            new_cur = new_conn.cursor()
            new_cur.execute("PRAGMA foreign_keys = ON")

            for t_buy, t_sell, notes, company_name in legacy_watchlist:
                # Find the matching stock ID in the current database
                new_cur.execute(
                    "SELECT id_stk FROM stocks WHERE company_name = ?",
                    (company_name,),
                )
                stock_res = new_cur.fetchone()

                if stock_res:
                    new_id_stk = stock_res[0]
                    # Insert or update if it already exists
                    new_cur.execute(
                        """
                        INSERT INTO watchlist (id_stk, target_buy_price, target_sell_price, notes)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(id_stk) DO UPDATE SET
                            target_buy_price = excluded.target_buy_price,
                            target_sell_price = excluded.target_sell_price,
                            notes = excluded.notes;
                    """,
                        (new_id_stk, t_buy, t_sell, notes),
                    )
                    imported_count += 1
                else:
                    skipped_count += 1

            new_conn.commit()

        # 3. Show Results
        show_colorful_info(
            parent,
            "Import Complete",
            f"Watchlist import successful.\n\nRecords imported/updated: {imported_count}\nRecords skipped (stock missing): {skipped_count}",
        )

    except sqlite3.Error as e:
        logger.error(f"Watchlist import failed: {e}", exc_info=True)
        show_colorful_error(
            parent, "Import Error", f"Failed to import watchlist:\n{e}"
        )
