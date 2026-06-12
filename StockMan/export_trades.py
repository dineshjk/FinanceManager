# -*- coding: utf-8 -*-
# StockMan/export_trades.py

"""
This module contains the function to export all database tables to an Excel file.
"""

import os
import shutil
import sqlite3
from typing import Any

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

from Shared.globals import get_db_connection, STOCK_DB_PATH, logger
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno,
)


def export_trades(parent: Any) -> None:
    """
    Exports all tables from the database to an Excel file.

    The function creates 'dinesh_stocks.xlsx' in the same directory as the
    database. If the file already exists, it is backed up to a 'Backup'
    subdirectory. Each table is exported to a separate sheet in the
    Excel file.
    """
    if pd is None or openpyxl is None:
        show_colorful_error(
            parent,
            "Dependency Missing",
            "The 'pandas' and 'openpyxl' libraries are required for this feature.\n"
            "Please install them using: pip install pandas openpyxl",
        )
        return

    data_dir = os.path.dirname(os.path.abspath(STOCK_DB_PATH))
    output_filename = "dinesh_stocks.xlsx"
    output_path = os.path.join(data_dir, output_filename)

    try:
        backup_dir = os.path.join(data_dir, "Backup")
        os.makedirs(backup_dir, exist_ok=True)

        if os.path.exists(output_path):
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(
                backup_dir, f"dinesh_stocks_{timestamp}.xlsx.bak"
            )
            shutil.copy2(output_path, backup_path)
            logger.info(f"Backed up existing file to {backup_path}")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            )
            tables = [table[0] for table in cursor.fetchall()]

            with pd.ExcelWriter(
                output_path,
                engine="openpyxl",
                datetime_format="DD-MM-YYYY",
            ) as writer:
                for table_name in tables:
                    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)

                    # Convert columns ending in '_dt' to datetime objects so
                    # they are written as dates in Excel.
                    for col in df.columns:
                        if col.endswith("_dt"):
                            df[col] = pd.to_datetime(df[col], errors="coerce")

                    # Convert potential large number ID columns to strings to prevent
                    # scientific notation in Excel.
                    for col in ["ord_no", "trd_no", "settle_no"]:
                        if col in df.columns:
                            # Format as integer string if not null, else empty string.
                            df[col] = df[col].apply(
                                lambda x: f"{int(x)}" if pd.notna(x) else ""
                            )

                    sheet_name = table_name[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

        logger.info(f"Successfully exported all tables to {output_path}")
        if show_colorful_yesno(
            parent,
            "Export Successful",
            f"All tables have been exported to:\n{output_path}\n\n"
            "Do you want to open the file now?",
        ):
            try:
                os.startfile(output_path)
            except Exception as e:
                show_colorful_error(
                    parent, "File Open Error", f"Could not open the file:\n{e}"
                )
                logger.error(
                    f"Failed to open exported file {output_path}: {e}",
                    exc_info=True,
                )

    except PermissionError:
        show_colorful_error(
            parent,
            "File In Use",
            f"The file '{output_filename}' appears to be open in another program.\n\n"
            "Please close the file and try again.",
        )
        logger.warning(f"Export failed because file is open: {output_path}")
    except (sqlite3.Error, Exception) as e:
        show_colorful_error(
            parent, "Export Error", f"An error occurred during export: {e}"
        )
        logger.error(f"An error occurred during export: {e}", exc_info=True)
