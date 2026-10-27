# -*- coding: utf-8 -*-
# StockMan/transfer_data.py

"""
Module for calculating and exporting discrepant holding data for shares
transferred to Zerodha from ICICI Securities.

Performs FIFO (First-In, First-Out) matching for each scrip using transactions
originating from ICICI Securities (including corporate actions like bonuses,
splits, mergers, demerger allotments, and rights/IPO allotments), while
excluding shares purchased directly through Zerodha (contract numbers starting
with 'CNT-26/27').

Outputs the remaining open buy lots and their summary average buy price to
an Excel spreadsheet located at data/transfer_stocks.xlsx.
"""

import os
import shutil
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    openpyxl = None

from Shared.dialog_utils import show_colorful_error, show_colorful_info
from Shared.globals import (
    PROJECT_ROOT,
    STOCK_DB_PATH,
    logger,
)

DEFAULT_EXPORT_PATH = os.path.join(
    PROJECT_ROOT, "data", "transfer_stocks.xlsx"
)

# Friendly aliases to support case-insensitive and alternative column lookups
_COLUMN_ALIASES: Dict[str, str] = {
    "company_name": "Scrip Name",
    "company name": "Scrip Name",
    "scrip": "Scrip Name",
    "scrip_name": "Scrip Name",
    "stock": "Scrip Name",
    "ticker": "Symbol",
    "code": "Symbol",
    "stock_code": "Symbol",
    "buy_date": "Buy Date",
    "date": "Buy Date",
    "buy_qty": "Buy Qty",
    "qty": "Buy Qty",
    "quantity": "Buy Qty",
    "buy_price": "Buy Price",
    "price": "Buy Price",
    "avg_price": "Buy Price",
    "average_buy_price": "Buy Price",
}


if pd is not None:

    class FlexibleDataFrame(pd.DataFrame):
        """A pandas DataFrame allowing case-insensitive & alias column access."""

        @property
        def _constructor(self):
            return FlexibleDataFrame

        def __getitem__(self, key: Any) -> Any:
            if isinstance(key, str) and key not in self.columns:
                k = key.lower().strip()
                if k in _COLUMN_ALIASES and _COLUMN_ALIASES[k] in self.columns:
                    return super().__getitem__(_COLUMN_ALIASES[k])
                key_clean = k.replace("_", " ")
                if (
                    key_clean in _COLUMN_ALIASES
                    and _COLUMN_ALIASES[key_clean] in self.columns
                ):
                    return super().__getitem__(_COLUMN_ALIASES[key_clean])
                for col in self.columns:
                    if col.lower().replace("_", " ").strip() == key_clean:
                        return super().__getitem__(col)
            return super().__getitem__(key)

else:
    FlexibleDataFrame = None  # type: ignore[assignment,misc]


def calculate_transfer_data(
    db_path: Optional[str] = None,
) -> pd.DataFrame:
    """
    Query database for ICICI Securities transactions and apply FIFO matching
    to determine remaining buy lots and average purchase prices for each scrip.

    Shares bought through Zerodha (contract numbers starting with 'CNT-26/27')
    are excluded. Corporate actions (bonuses, splits, demerger allotments,
    merger allotments, and rights/IPO allotments) are retained.

    Returns:
        FlexibleDataFrame containing remaining lots and scrip summary rows.
    """
    if pd is None:
        raise ImportError(
            "The 'pandas' library is required to calculate transfer data."
        )

    resolved_db_path = db_path or STOCK_DB_PATH
    if not os.path.exists(resolved_db_path):
        raise FileNotFoundError(
            f"Database file not found at: {resolved_db_path}"
        )

    # Use a direct sqlite3 connection if custom path provided, else context mgr
    conn = sqlite3.connect(resolved_db_path)
    try:
        cursor = conn.cursor()

        # Query all distinct scrips that have non-Zerodha transactions
        cursor.execute(
            """
            SELECT DISTINCT t.id_stk, t.company_name, s.stk_code
            FROM transactions t
            LEFT JOIN stocks s ON t.id_stk = s.id_stk
            WHERE (t.cont_no IS NULL OR t.cont_no NOT LIKE 'CNT-26/27%')
            ORDER BY t.company_name ASC;
            """
        )
        scrips = cursor.fetchall()

        all_rows: List[Dict[str, Any]] = []

        for id_stk, comp_name, stk_code in scrips:
            cursor.execute(
                """
                SELECT id_trd, cont_no, trd_dt, trade_type_trd, qty_trd, net_amt_trd
                FROM transactions
                WHERE id_stk = ?
                  AND (cont_no IS NULL OR cont_no NOT LIKE 'CNT-26/27%')
                ORDER BY trd_dt ASC, id_trd ASC;
                """,
                (id_stk,),
            )
            trades = cursor.fetchall()

            buy_lots: List[Dict[str, Any]] = []

            for trd in trades:
                t_id, cont_no, trd_dt, t_type, qty, net_amt = trd

                if t_type == "BUY":
                    if qty and qty > 0:
                        unit_price = (net_amt / qty) if qty else 0.0
                        buy_lots.append(
                            {
                                "id_trd": t_id,
                                "cont_no": cont_no,
                                "date": trd_dt,
                                "orig_qty": qty,
                                "rem_qty": qty,
                                "unit_price": unit_price,
                                "net_amt": net_amt,
                            }
                        )

                elif t_type == "SELL":
                    sell_qty = qty
                    if not sell_qty or sell_qty <= 0:
                        continue

                    rem_sell = sell_qty
                    for lot in buy_lots:
                        if lot["rem_qty"] > 0:
                            deduct = min(lot["rem_qty"], rem_sell)
                            lot["rem_qty"] -= deduct
                            rem_sell -= deduct
                            if rem_sell == 0:
                                break

                    if rem_sell > 0:
                        logger.warning(
                            "FIFO warning for stock id=%s (%s): %s unsold shares remaining unmatched",
                            id_stk,
                            comp_name,
                            rem_sell,
                        )

            # Filter down to currently held (remaining) buy lots
            open_lots = [lot for lot in buy_lots if lot["rem_qty"] > 0]
            if not open_lots:
                continue

            tot_qty = sum(lot["rem_qty"] for lot in open_lots)
            tot_cost = sum(
                lot["rem_qty"] * lot["unit_price"] for lot in open_lots
            )
            avg_price = (tot_cost / tot_qty) if tot_qty > 0 else 0.0

            symbol = stk_code or ""

            # Row for each open buy lot
            for lot in open_lots:
                all_rows.append(
                    {
                        "Scrip Name": comp_name,
                        "Symbol": symbol,
                        "Buy Date": lot["date"],
                        "Buy Qty": int(lot["rem_qty"]),
                        "Buy Price": round(float(lot["unit_price"]), 4),
                        "_is_summary": False,
                    }
                )

            # Summary row for the scrip
            all_rows.append(
                {
                    "Scrip Name": comp_name,
                    "Symbol": symbol,
                    "Buy Date": "Average",
                    "Buy Qty": int(tot_qty),
                    "Buy Price": round(float(avg_price), 4),
                    "_is_summary": True,
                }
            )

        return FlexibleDataFrame(all_rows)
    finally:
        conn.close()


def export_transfer_data_to_excel(
    df: pd.DataFrame,
    output_path: Optional[str] = None,
) -> str:
    """
    Export the compiled transfer data DataFrame to an Excel file with
    professional styling using openpyxl.

    Args:
        df: The pandas DataFrame generated by calculate_transfer_data.
        output_path: Target Excel file path. Defaults to data/transfer_stocks.xlsx.

    Returns:
        The absolute path to the saved Excel file.
    """
    if pd is None or openpyxl is None:
        raise ImportError(
            "Both 'pandas' and 'openpyxl' libraries are required for Excel export."
        )

    target_path = os.path.abspath(output_path or DEFAULT_EXPORT_PATH)
    target_dir = os.path.dirname(target_path)
    os.makedirs(target_dir, exist_ok=True)

    # Optional backup of prior file
    if os.path.exists(target_path):
        try:
            backup_dir = os.path.join(target_dir, "Backup")
            os.makedirs(backup_dir, exist_ok=True)
            ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(
                backup_dir, f"transfer_stocks_{ts}.xlsx.bak"
            )
            shutil.copy2(target_path, backup_path)
        except Exception as e:
            logger.debug("Failed to create backup of transfer_stocks: %s", e)

    # Preserve internal flag for styling before exporting
    is_summary_flags: List[bool] = []
    if "_is_summary" in df.columns:
        is_summary_flags = list(df["_is_summary"])
        export_df = df.drop(columns=["_is_summary"])
    else:
        is_summary_flags = [
            str(d).strip().lower() in ("average", "summary")
            for d in df["Buy Date"]
        ]
        export_df = df.copy()

    try:
        with pd.ExcelWriter(target_path, engine="openpyxl") as writer:
            sheet_name = "Transfer Stocks"
            export_df.to_excel(writer, sheet_name=sheet_name, index=False)
            ws = writer.sheets[sheet_name]

            # Style definitions
            header_font = Font(
                name="Calibri", size=11, bold=True, color="FFFFFF"
            )
            header_fill = PatternFill(
                start_color="1E3A8A", end_color="1E3A8A", fill_type="solid"
            )
            header_align = Alignment(
                horizontal="center", vertical="center", wrap_text=True
            )

            summary_font = Font(
                name="Calibri", size=11, bold=True, color="0F172A"
            )
            summary_fill = PatternFill(
                start_color="E2E8F0", end_color="E2E8F0", fill_type="solid"
            )

            regular_font = Font(name="Calibri", size=11)

            thin_border = Border(
                left=Side(style="thin", color="CBD5E1"),
                right=Side(style="thin", color="CBD5E1"),
                top=Side(style="thin", color="CBD5E1"),
                bottom=Side(style="thin", color="CBD5E1"),
            )

            # Format header row
            for col_idx in range(1, len(export_df.columns) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_align
                cell.border = thin_border

            # Format data rows
            for r_idx, is_summary in enumerate(is_summary_flags, start=2):
                current_font = summary_font if is_summary else regular_font
                current_fill = summary_fill if is_summary else None

                for col_idx, col_name in enumerate(export_df.columns, start=1):
                    cell = ws.cell(row=r_idx, column=col_idx)
                    cell.font = current_font
                    if current_fill:
                        cell.fill = current_fill
                    cell.border = thin_border

                    # Alignments and number formats
                    if col_name in ("Scrip Name", "Symbol"):
                        cell.alignment = Alignment(
                            horizontal="left", vertical="center"
                        )
                    elif col_name == "Buy Date":
                        cell.alignment = Alignment(
                            horizontal="center", vertical="center"
                        )
                    elif col_name == "Buy Qty":
                        cell.alignment = Alignment(
                            horizontal="right", vertical="center"
                        )
                        cell.number_format = "#,##0"
                    elif col_name == "Buy Price":
                        cell.alignment = Alignment(
                            horizontal="right", vertical="center"
                        )
                        cell.number_format = "#,##0.0000"

            # Freeze panes on header row
            ws.freeze_panes = "A2"

            # Auto-adjust column widths
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    val_str = str(cell.value or "")
                    max_len = max(max_len, len(val_str))
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    except PermissionError as pe:
        raise PermissionError(
            f"Unable to write to '{target_path}'. The file is open in another "
            "program (e.g. Microsoft Excel). Please close it and retry."
        ) from pe

    return target_path


def generate_and_export_transfer_data(
    db_path: Optional[str] = None,
    output_path: Optional[str] = None,
) -> Tuple[pd.DataFrame, str, Dict[str, Any]]:
    """
    Orchestrate the calculation and export of transfer holding data.

    Returns:
        Tuple of (DataFrame, target_path, stats_dict).
    """
    df = calculate_transfer_data(db_path=db_path)
    target_path = export_transfer_data_to_excel(df, output_path=output_path)

    summary_rows = [
        str(d).strip().lower() in ("average", "summary")
        for d in df["Buy Date"]
    ]
    num_scrips = sum(summary_rows)
    num_lots = len(df) - num_scrips
    total_qty = sum(
        df.loc[
            [not s for s in summary_rows],
            "Buy Qty",
        ]
    )

    stats = {
        "num_scrips": int(num_scrips),
        "num_lots": int(num_lots),
        "total_qty": int(total_qty),
    }

    return df, target_path, stats


def export_transfer_data_gui(parent: Any = None) -> None:
    """
    Tkinter action handler for the 'Transfer Data' button.
    Calculates discrepant holding data and exports to Excel, presenting
    colorful user dialogs for success or errors.
    """
    if pd is None or openpyxl is None:
        show_colorful_error(
            parent,
            "Missing Dependencies",
            "The 'pandas' and 'openpyxl' libraries are required for Transfer Data export.\n\n"
            "Please install them via: pip install pandas openpyxl",
        )
        return

    try:
        _, target_path, stats = generate_and_export_transfer_data()
        msg = (
            "Discrepant holding data for transferred shares has been successfully "
            f"calculated and exported to Excel!\n\n"
            f"📁 File Path:\n{target_path}\n\n"
            "📊 Portfolio Summary:\n"
            f"  • Total Scrips: {stats['num_scrips']}\n"
            f"  • Active Buy Lots: {stats['num_lots']}\n"
            f"  • Total Transferred Shares: {stats['total_qty']:,}\n\n"
            "All lots and weighted average buy prices follow strict FIFO matching."
        )
        show_colorful_info(parent, "Transfer Data Exported", msg)
    except Exception as e:
        logger.exception("Failed to export transfer data: %s", e)
        show_colorful_error(
            parent,
            "Export Failed",
            f"An error occurred while generating transfer data:\n\n{e}",
        )
