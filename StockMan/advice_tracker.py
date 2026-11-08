# -*- coding: utf-8 -*-
# StockMan/advice_tracker.py

"""
Advice Tracking & Execution Management for StockMan.

This module provides database CRUD operations, Pick of the Day AI report parsing,
and a rich Tkinter user interface to log, track, and mark historical AI advice
(e.g., 'Fully Followed', 'Partially Followed', or 'Not Followed') along with
execution dates.
"""

import glob
import os
import re
import sqlite3
import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk
from typing import Any, Dict, List, Optional

from Shared.globals import STOCK_DB_PATH, logger
from Shared.help_utils import show_standard_help
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import pop_window, push_window
from StockMan.config import UI_THEME
from StockMan.date_utils import is_valid_iso_date
from StockMan.stock_database_setup import ensure_advice_log_table


ALLOWED_STATUSES = ("Not Followed", "Partially Followed", "Fully Followed")


# =============================================================================
# Database CRUD Operations
# =============================================================================

def get_all_advices(
    db_path: str = STOCK_DB_PATH,
    status_filter: Optional[str] = None,
    search_query: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetches all advice log records from SQLite, ordered by advice_date DESC, id_advice DESC.
    Supports optional status filtering and search text filtering.
    """
    ensure_advice_log_table(db_path=db_path)
    if not os.path.exists(db_path):
        return []

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = """
            SELECT id_advice, advice_date, advice_text, status,
                   COALESCE(execution_date, '') AS execution_date,
                   COALESCE(notes, '') AS notes
            FROM advice_log
            WHERE 1=1
        """
        params: List[Any] = []

        if status_filter and status_filter in ALLOWED_STATUSES:
            query += " AND status = ?"
            params.append(status_filter)

        if search_query and search_query.strip():
            query += " AND (advice_text LIKE ? OR notes LIKE ? OR advice_date LIKE ?)"
            term = f"%{search_query.strip()}%"
            params.extend([term, term, term])

        query += " ORDER BY advice_date DESC, id_advice DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error fetching advices from '{db_path}': {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_advice_by_id(
    id_advice: int, db_path: str = STOCK_DB_PATH
) -> Optional[Dict[str, Any]]:
    """Fetches a single advice record by its primary key ID."""
    ensure_advice_log_table(db_path=db_path)
    if not os.path.exists(db_path):
        return None

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id_advice, advice_date, advice_text, status,
                   COALESCE(execution_date, '') AS execution_date,
                   COALESCE(notes, '') AS notes
            FROM advice_log
            WHERE id_advice = ?
            """,
            (id_advice,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error fetching advice ID {id_advice}: {e}")
        return None
    finally:
        if conn:
            conn.close()


def add_advice(
    advice_date: str,
    advice_text: str,
    status: str = "Not Followed",
    execution_date: Optional[str] = None,
    notes: str = "",
    db_path: str = STOCK_DB_PATH,
) -> int:
    """
    Inserts a new advice record into advice_log.
    Returns the new row ID.
    Raises ValueError on validation failure.
    """
    advice_date = (advice_date or "").strip()
    advice_text = (advice_text or "").strip()
    status = (status or "Not Followed").strip()
    execution_date = (execution_date or "").strip() or None
    notes = (notes or "").strip()

    if not is_valid_iso_date(advice_date):
        raise ValueError(f"Date of Advice must be in YYYY-MM-DD format (got: {advice_date!r})")
    if not advice_text:
        raise ValueError("The Advice Given cannot be empty.")
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Status must be one of {ALLOWED_STATUSES} (got: {status!r})")
    if execution_date and not is_valid_iso_date(execution_date):
        raise ValueError(f"Execution Date must be in YYYY-MM-DD format (got: {execution_date!r})")

    ensure_advice_log_table(db_path=db_path)
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO advice_log (advice_date, advice_text, status, execution_date, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (advice_date, advice_text, status, execution_date, notes),
        )
        conn.commit()
        new_id = cursor.lastrowid
        logger.info(f"Added advice log #{new_id}: '{advice_text}' ({status})")
        return new_id
    finally:
        if conn:
            conn.close()


def update_advice(
    id_advice: int,
    advice_date: str,
    advice_text: str,
    status: str,
    execution_date: Optional[str] = None,
    notes: str = "",
    db_path: str = STOCK_DB_PATH,
) -> bool:
    """
    Updates an existing advice record in advice_log.
    Returns True if row was updated.
    """
    advice_date = (advice_date or "").strip()
    advice_text = (advice_text or "").strip()
    status = (status or "Not Followed").strip()
    execution_date = (execution_date or "").strip() or None
    notes = (notes or "").strip()

    if not is_valid_iso_date(advice_date):
        raise ValueError(f"Date of Advice must be in YYYY-MM-DD format (got: {advice_date!r})")
    if not advice_text:
        raise ValueError("The Advice Given cannot be empty.")
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Status must be one of {ALLOWED_STATUSES} (got: {status!r})")
    if execution_date and not is_valid_iso_date(execution_date):
        raise ValueError(f"Execution Date must be in YYYY-MM-DD format (got: {execution_date!r})")

    ensure_advice_log_table(db_path=db_path)
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE advice_log
            SET advice_date = ?, advice_text = ?, status = ?, execution_date = ?, notes = ?
            WHERE id_advice = ?
            """,
            (advice_date, advice_text, status, execution_date, notes, id_advice),
        )
        conn.commit()
        updated = cursor.rowcount > 0
        logger.info(f"Updated advice log #{id_advice}: status={status}, execution_date={execution_date}")
        return updated
    finally:
        if conn:
            conn.close()


def update_advice_status(
    id_advice: int,
    status: str,
    execution_date: Optional[str] = None,
    db_path: str = STOCK_DB_PATH,
) -> bool:
    """Quick helper to update only the status and execution_date of an advice record."""
    status = (status or "Not Followed").strip()
    execution_date = (execution_date or "").strip() or None

    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Status must be one of {ALLOWED_STATUSES} (got: {status!r})")
    if execution_date and not is_valid_iso_date(execution_date):
        raise ValueError(f"Execution Date must be in YYYY-MM-DD format (got: {execution_date!r})")

    ensure_advice_log_table(db_path=db_path)
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE advice_log
            SET status = ?, execution_date = ?
            WHERE id_advice = ?
            """,
            (status, execution_date, id_advice),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        if conn:
            conn.close()


def delete_advice(id_advice: int, db_path: str = STOCK_DB_PATH) -> bool:
    """Deletes an advice record by ID."""
    ensure_advice_log_table(db_path=db_path)
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM advice_log WHERE id_advice = ?", (id_advice,))
        conn.commit()
        deleted = cursor.rowcount > 0
        logger.info(f"Deleted advice log #{id_advice}")
        return deleted
    finally:
        if conn:
            conn.close()


# =============================================================================
# Pick of the Day AI Report Parser & Automation
# =============================================================================

def _clean_markdown_text(val: str) -> str:
    """Strips markdown formatting, bold/italics, backticks, and escape backslashes."""
    if not val:
        return ""
    # Unescape characters commonly backslash-escaped in markdown (e.g. \~, \₹, \$, \*)
    cleaned = re.sub(r"\\([~*_\`₹\$])", r"\1", val)
    cleaned = re.sub(r"[*_~`]", "", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()


def parse_advice_from_pick_of_the_day(
    report_text: str, filename_hint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Parses a daily Pick of the Day intelligence markdown report to extract:
      - advice_date: ISO date (YYYY-MM-DD) from the report or fallback to today
      - advice_text: Concrete action recommendation (e.g. 'BUY 34 shares of HCLTECH at CMP (~₹1,430)... — Rebalancing Strategy: Funnel the ₹50,000 available cash into the IT sector (specifically HCLTECH)...')
      - winner: Extracted winner scrip/ticker
      - rebalancing_strategy: Extracted rebalancing advice/guidance
      - action: Specific buy/sell/allocation action
      - ticker: Stock symbol/ticker (e.g. 'HCLTECH')
      - notes: Explanatory notes (including Rebalancing Strategy)
    """
    if not report_text:
        return {
            "advice_date": date.today().isoformat(),
            "advice_text": "",
            "winner": "",
            "rebalancing_strategy": "",
            "action": "",
            "ticker": "",
            "notes": "",
        }

    # 1. Extract Date
    date_match = re.search(r"\*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2})", report_text, re.IGNORECASE)
    if not date_match:
        date_match = re.search(r"Date:\s*(\d{4}-\d{2}-\d{2})", report_text, re.IGNORECASE)
    if not date_match:
        # Check header e.g. "Report 2026-11-01"
        date_match = re.search(r"#.*?\b(\d{4}-\d{2}-\d{2})\b", report_text)
    if not date_match:
        # Check compact date in title e.g. "20261023"
        compact_m = re.search(r"#.*?\b(\d{4})(\d{2})(\d{2})\b", report_text)
        if compact_m:
            extracted_date = f"{compact_m.group(1)}-{compact_m.group(2)}-{compact_m.group(3)}"
        elif filename_hint:
            fn_iso = re.search(r"(\d{4})[-_](\d{2})[-_](\d{2})", filename_hint)
            if fn_iso:
                extracted_date = f"{fn_iso.group(1)}-{fn_iso.group(2)}-{fn_iso.group(3)}"
            else:
                fn_compact = re.search(r"(\d{4})(\d{2})(\d{2})", filename_hint)
                if fn_compact:
                    extracted_date = f"{fn_compact.group(1)}-{fn_compact.group(2)}-{fn_compact.group(3)}"
                else:
                    extracted_date = date.today().isoformat()
        else:
            extracted_date = date.today().isoformat()
    else:
        extracted_date = date_match.group(1)

    # 2. Extract Winner
    winner_match = re.search(r"\*\*Winner:\*\*\s*([^\n*]+)", report_text, re.IGNORECASE)
    if not winner_match:
        winner_match = re.search(r"Winner:\s*([^\n*]+)", report_text, re.IGNORECASE)
    winner_str = winner_match.group(1).strip() if winner_match else ""

    # 3. Extract Rebalancing Strategy
    rebal_match = re.search(
        r"(?:\*?Rebalancing Strategy:\*?|\bRebalancing Strategy:\s*)([^\n\r]+)",
        report_text,
        re.IGNORECASE,
    )
    rebalancing_strategy = _clean_markdown_text(rebal_match.group(1)) if rebal_match else ""

    # 4. Extract ADVICE_LOG_EXPORT table if present
    table_date = None
    table_ticker = None
    table_action = None
    table_qty = None
    table_target = None
    table_status = None
    export_table_m = re.search(
        r"###\s*ADVICE[\\_]+LOG[\\_]+EXPORT[^\n]*\n+([\s\S]*?)(?:\n##|\Z)",
        report_text,
        re.IGNORECASE,
    )
    if export_table_m:
        lines = [ln.strip() for ln in export_table_m.group(1).splitlines() if ln.strip().startswith("|")]
        if len(lines) >= 3:
            cols = [_clean_markdown_text(c) for c in lines[2].split("|")[1:-1]]
            if len(cols) >= 5:
                table_date = cols[0]
                table_ticker = cols[1]
                table_action = cols[2]
                table_qty = cols[3]
                table_target = cols[4]
                if len(cols) >= 6:
                    table_status = cols[5]
                if is_valid_iso_date(table_date):
                    extracted_date = table_date

    # 5. Extract Specific Action
    action_match = re.search(
        r"(?:-\s*Action:\s*|\bAction:\s*)([^\n\r]+)", report_text, re.IGNORECASE
    )
    action_str = _clean_markdown_text(action_match.group(1)) if action_match else ""

    # 6. Extract Ticker
    extracted_ticker = table_ticker or ""
    if not extracted_ticker and winner_str:
        ticker_m = re.search(r"\(([A-Z0-9_\.\-]+)\)", winner_str)
        if ticker_m:
            extracted_ticker = ticker_m.group(1).strip()
    if not extracted_ticker and action_str:
        ticker_m = re.search(r"\b([A-Z]{3,15})\b", action_str)
        if ticker_m and ticker_m.group(1) not in ("BUY", "ADD", "SELL", "TRIM", "CMP", "INR", "KEEP", "HOLD"):
            extracted_ticker = ticker_m.group(1).strip()
    if not extracted_ticker and rebalancing_strategy:
        ticker_m = re.search(r"\(([A-Z0-9_\.\-]+)\)", rebalancing_strategy)
        if ticker_m:
            extracted_ticker = ticker_m.group(1).strip()

    # 7. Compose advice_text
    if action_str and rebalancing_strategy:
        advice_text = f"{action_str} — Rebalancing Strategy: {rebalancing_strategy}"
    elif action_str:
        advice_text = action_str
    elif table_action and table_ticker and table_qty:
        advice_text = f"{table_action} {table_qty} shares of {table_ticker}"
        if table_target:
            advice_text += f" at {table_target}"
        if rebalancing_strategy:
            advice_text += f" — Rebalancing Strategy: {rebalancing_strategy}"
    elif rebalancing_strategy:
        advice_text = f"Rebalancing Strategy: {rebalancing_strategy}"
    elif winner_str:
        clean_winner = _clean_markdown_text(winner_str)
        advice_text = f"Buy Winner: {clean_winner}"
    else:
        # Check Rank 1 in table
        table_match = re.search(r"\|\s*1\s*\|\s*([^|]+)\|\s*[^|]+\|\s*([^|]+)\|", report_text)
        if table_match:
            ticker = _clean_markdown_text(table_match.group(1))
            act = _clean_markdown_text(table_match.group(2))
            advice_text = f"{act} {ticker}"
            if not extracted_ticker:
                extracted_ticker = ticker
        else:
            advice_text = "Daily Pick of the Day Recommendation"

    # 8. Compose notes
    notes_parts = []
    if rebalancing_strategy:
        notes_parts.append(f"Rebalancing Strategy: {rebalancing_strategy}")
    notes = " | ".join(notes_parts)

    return {
        "advice_date": extracted_date,
        "advice_text": advice_text,
        "winner": winner_str,
        "rebalancing_strategy": rebalancing_strategy,
        "action": action_str,
        "ticker": extracted_ticker,
        "notes": notes,
        "status": table_status or "Not Followed",
    }


def get_latest_pick_advice() -> Optional[Dict[str, Any]]:
    """
    Reads the latest local Pick of the Day report and parses its advice.
    Returns dict with keys ('advice_date', 'advice_text', 'winner', 'rebalancing_strategy', 'source_file') or None.
    """
    from StockMan.drive_sync import get_local_pick_of_the_day

    res = get_local_pick_of_the_day()
    if not res:
        return None
    content, filename, mtime = res
    parsed = parse_advice_from_pick_of_the_day(content)
    parsed["source_file"] = filename
    parsed["mtime"] = mtime
    return parsed


def auto_update_advice_from_pick_of_the_day(
    report_text_or_path: Optional[str] = None,
    db_path: str = STOCK_DB_PATH,
    excel_path: Optional[str] = None,
    trigger_drive_upload: bool = False,
    update_excel: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Automates parsing and syncing advice from Pick of the Day into:
      1. SQLite table 'advice_log' (deduplicating against existing entries).
      2. 'StockMan_Portfolio.xlsx' (sheet 'Advice_Log').
      3. Google Drive (if trigger_drive_upload is True).
    Returns result dictionary or None.
    """
    from StockMan.drive_sync import PORTFOLIO_EXCEL_PATH, get_local_pick_of_the_day, update_portfolio_excel

    target_excel = excel_path or PORTFOLIO_EXCEL_PATH
    content = None
    source_name = ""

    if report_text_or_path is None:
        local_res = get_local_pick_of_the_day()
        if not local_res:
            logger.info("auto_update_advice_from_pick_of_the_day: No local Pick of the Day report found.")
            return None
        content, source_name, _ = local_res
    elif isinstance(report_text_or_path, str) and os.path.isfile(report_text_or_path):
        source_name = os.path.basename(report_text_or_path)
        with open(report_text_or_path, "r", encoding="utf-8") as f_in:
            content = f_in.read()
    else:
        content = str(report_text_or_path)
        source_name = "Direct Content"

    parsed = parse_advice_from_pick_of_the_day(content, filename_hint=source_name)
    adv_date = parsed.get("advice_date")
    adv_text = parsed.get("advice_text")
    if not adv_date or not adv_text:
        return None

    # Determine notes
    base_notes = parsed.get("notes") or ""
    if source_name and source_name != "Direct Content":
        src_tag = f"Source: {source_name}"
        if src_tag not in base_notes:
            notes = f"{base_notes} | {src_tag}".strip(" |")
        else:
            notes = base_notes
    else:
        notes = base_notes

    ensure_advice_log_table(db_path=db_path)
    conn = None
    advice_id = None
    is_new = False
    is_updated = False

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Check existing entries for this date
        cur.execute(
            """
            SELECT id_advice, advice_date, advice_text, status, execution_date, notes
            FROM advice_log
            WHERE advice_date = ?
            ORDER BY id_advice ASC
            """,
            (adv_date,),
        )
        existing_rows = cur.fetchall()

        matched_row = None
        ticker = parsed.get("ticker", "").upper()
        reb_strat = parsed.get("rebalancing_strategy", "")

        for row in existing_rows:
            r_text = (row["advice_text"] or "").upper()
            if ticker and len(ticker) >= 3 and ticker in r_text:
                matched_row = row
                break
            if adv_text[:35].lower() in (row["advice_text"] or "").lower():
                matched_row = row
                break
            if (row["advice_text"] or "")[:35].lower() in adv_text.lower():
                matched_row = row
                break

        if matched_row:
            advice_id = matched_row["id_advice"]
            cur_adv_text = matched_row["advice_text"] or ""
            cur_notes = matched_row["notes"] or ""

            # Check if rebalancing strategy needs to be merged in
            should_update_text = (
                reb_strat
                and reb_strat not in cur_adv_text
                and "Rebalancing Strategy" not in cur_adv_text
            )
            should_update_notes = reb_strat and reb_strat not in cur_notes

            if should_update_text or should_update_notes:
                new_text = adv_text if should_update_text else cur_adv_text
                new_notes = notes if should_update_notes else cur_notes
                if should_update_notes and cur_notes and reb_strat not in cur_notes:
                    new_notes = f"{cur_notes} | Rebalancing Strategy: {reb_strat}"

                cur.execute(
                    """
                    UPDATE advice_log
                    SET advice_text = ?, notes = ?
                    WHERE id_advice = ?
                    """,
                    (new_text, new_notes, advice_id),
                )
                conn.commit()
                is_updated = True
                logger.info(f"Updated advice #{advice_id} with rebalancing strategy.")
        else:
            # Insert new advice
            cur.execute(
                """
                INSERT INTO advice_log (advice_date, advice_text, status, execution_date, notes)
                VALUES (?, ?, 'Not Followed', NULL, ?)
                """,
                (adv_date, adv_text, notes),
            )
            conn.commit()
            advice_id = cur.lastrowid
            is_new = True
            logger.info(f"Auto-logged advice #{advice_id} for {adv_date}: '{adv_text[:60]}...'")
    except Exception as e:
        logger.error(f"Error in auto_update_advice_from_pick_of_the_day: {e}", exc_info=True)
        return None
    finally:
        if conn:
            conn.close()

    # Regenerate StockMan_Portfolio.xlsx
    excel_result_path = target_excel
    if update_excel:
        try:
            excel_result_path = update_portfolio_excel(excel_path=target_excel, db_path=db_path)
        except Exception as ex_err:
            logger.error(f"Failed to regenerate '{target_excel}' during auto advice update: {ex_err}")

    # Optional Google Drive background upload
    if trigger_drive_upload:
        try:
            from StockMan.drive_sync import (
                GOOGLE_DRIVE_AVAILABLE,
                get_credentials_file,
                get_drive_service,
                upload_portfolio_to_drive,
            )
            if GOOGLE_DRIVE_AVAILABLE and get_credentials_file():
                import threading
                def _bg_up():
                    try:
                        svc = get_drive_service()
                        upload_portfolio_to_drive(svc, file_path=excel_result_path)
                    except Exception as u_err:
                        logger.warning(f"Background upload after auto advice update failed: {u_err}")
                threading.Thread(target=_bg_up, daemon=True).start()
        except Exception as e:
            logger.debug(f"Drive upload check failed: {e}")

    return {
        "advice_id": advice_id,
        "advice_date": adv_date,
        "advice_text": adv_text,
        "is_new": is_new,
        "is_updated": is_updated,
        "excel_path": excel_result_path,
        "source_file": source_name,
    }


def sync_all_pending_pick_of_the_day_advices(
    search_dirs: Optional[List[str]] = None,
    db_path: str = STOCK_DB_PATH,
    excel_path: Optional[str] = None,
    trigger_drive_upload: bool = False,
) -> List[Dict[str, Any]]:
    """
    Scans all Pick_of_the_day_*.md files on disk,
    checks if each report's advice is already in SQLite advice_log,
    auto-imports missing advice, and refreshes StockMan_Portfolio.xlsx.
    """
    from StockMan.drive_sync import DATA_DIR, PORTFOLIO_EXCEL_PATH, PROJECT_ROOT, update_portfolio_excel

    target_excel = excel_path or PORTFOLIO_EXCEL_PATH
    if search_dirs is None:
        search_dirs = [DATA_DIR]
        if os.path.abspath(DATA_DIR) != os.path.abspath(PROJECT_ROOT):
            search_dirs.append(PROJECT_ROOT)

    files_to_process = []
    seen_basenames = set()

    for s_dir in search_dirs:
        if not os.path.isdir(s_dir):
            continue
        for pat in ("Pick_of_the_day_*.md", "Pick_of_the_day_*.txt"):
            for f_path in glob.glob(os.path.join(s_dir, pat)):
                bname = os.path.basename(f_path)
                # Ignore alias/mirror and documentation templates
                if "latest" in bname.lower() or "doc" in bname.lower():
                    continue
                if bname in seen_basenames:
                    continue
                seen_basenames.add(bname)
                files_to_process.append(f_path)

    # Sort files chronologically by date in filename or mtime
    def _file_sort_key(p):
        fname = os.path.basename(p)
        dt_m = re.search(r"(\d{4})[-_]?(\d{2})[-_]?(\d{2})", fname)
        if dt_m:
            return f"{dt_m.group(1)}-{dt_m.group(2)}-{dt_m.group(3)}"
        return datetime.fromtimestamp(os.path.getmtime(p)).date().isoformat()

    files_to_process.sort(key=_file_sort_key)

    results = []
    any_change = False

    for fp in files_to_process:
        try:
            res = auto_update_advice_from_pick_of_the_day(
                report_text_or_path=fp,
                db_path=db_path,
                excel_path=target_excel,
                trigger_drive_upload=False,
                update_excel=False,
            )
            if res:
                results.append(res)
                if res.get("is_new") or res.get("is_updated"):
                    any_change = True
        except Exception as err:
            logger.warning(f"Error processing '{fp}' in sync_all_pending_pick_of_the_day_advices: {err}")

    # Ensure Excel is refreshed once if changes were made
    if any_change:
        try:
            update_portfolio_excel(excel_path=target_excel, db_path=db_path)
            logger.info(f"sync_all_pending_pick_of_the_day_advices: Refreshed '{target_excel}'.")
        except Exception as ex:
            logger.error(f"Failed to refresh Excel after batch advice sync: {ex}")

        if trigger_drive_upload:
            try:
                from StockMan.drive_sync import (
                    GOOGLE_DRIVE_AVAILABLE,
                    get_credentials_file,
                    get_drive_service,
                    upload_portfolio_to_drive,
                )
                if GOOGLE_DRIVE_AVAILABLE and get_credentials_file():
                    import threading
                    def _bg_up():
                        try:
                            svc = get_drive_service()
                            upload_portfolio_to_drive(svc, file_path=target_excel)
                        except Exception as u_err:
                            logger.warning(f"Background upload after batch advice sync failed: {u_err}")
                    threading.Thread(target=_bg_up, daemon=True).start()
            except Exception as e:
                logger.debug(f"Drive upload check failed: {e}")

    return results


# =============================================================================
# Advice Tracking UI (Tkinter Modal)
# =============================================================================

def show_advice_tracker(
    parent: Optional[tk.Tk | tk.Toplevel] = None,
    initial_advice: Optional[Dict[str, str]] = None,
) -> None:
    """
    Displays the Advice Tracking & Execution Management modal window.
    Allows logging daily AI advice, reviewing historical logs, updating execution status
    ('Fully Followed', 'Partially Followed', 'Not Followed'), setting execution dates,
    and syncing/exporting to StockMan_Portfolio.xlsx & Google Drive.
    """
    modal_id = disable_parent(parent) if parent else None

    win = tk.Toplevel(parent)
    win.title("📋 AI Advice Tracking & Execution Log")
    win.geometry("1160x740")
    win.minsize(980, 580)
    win.configure(bg=UI_THEME.get("dark_slate", "#1e293b"))

    if parent:
        win.transient(parent)
        win.grab_set()
        win.focus_set()
        push_window(win, parent)

    def close_modal():
        if parent:
            pop_window()
        win.destroy()
        if modal_id is not None and parent:
            enable_parent(modal_id)

    win.protocol("WM_DELETE_WINDOW", close_modal)
    win.bind("<Escape>", lambda e: close_modal())

    # State variables
    current_selected_id = tk.StringVar(value="")
    advice_date_var = tk.StringVar(value=date.today().isoformat())
    advice_text_var = tk.StringVar(value="")
    status_var = tk.StringVar(value="Not Followed")
    exec_date_var = tk.StringVar(value="")
    notes_var = tk.StringVar(value="")
    filter_status_var = tk.StringVar(value="All")
    search_var = tk.StringVar(value="")

    # Apply initial advice if passed from Pick of the Day
    if initial_advice:
        if initial_advice.get("advice_date"):
            advice_date_var.set(initial_advice["advice_date"])
        if initial_advice.get("advice_text"):
            advice_text_var.set(initial_advice["advice_text"])

    # -------------------------------------------------------------------------
    # Top Header & Stats Card
    # -------------------------------------------------------------------------
    header_frame = tk.Frame(win, bg=UI_THEME.get("dark_slate", "#1e293b"), padx=16, pady=10)
    header_frame.pack(fill="x")

    title_box = tk.Frame(header_frame, bg=UI_THEME.get("dark_slate", "#1e293b"))
    title_box.pack(side="left")

    tk.Label(
        title_box,
        text="📋 AI Advice Tracking & Execution Log",
        font=("Helvetica", 16, "bold"),
        bg=UI_THEME.get("dark_slate", "#1e293b"),
        fg=UI_THEME.get("gold", "#FFD700"),
    ).pack(anchor="w")

    tk.Label(
        title_box,
        text="Track AI 'Pick of the Day' actions & log execution status for closed-loop feedback",
        font=("Helvetica", 10),
        bg=UI_THEME.get("dark_slate", "#1e293b"),
        fg="#94a3b8",
    ).pack(anchor="w")

    # KPI stats summary on top right
    stats_box = tk.Frame(header_frame, bg=UI_THEME.get("charcoal", "#334155"), padx=12, pady=6)
    stats_box.pack(side="right")

    lbl_total = tk.Label(stats_box, text="Total: 0", font=("Helvetica", 10, "bold"), bg=UI_THEME.get("charcoal", "#334155"), fg="#f8fafc")
    lbl_total.pack(side="left", padx=8)

    lbl_fully = tk.Label(stats_box, text="Fully: 0", font=("Helvetica", 10, "bold"), bg=UI_THEME.get("charcoal", "#334155"), fg="#34d399")
    lbl_fully.pack(side="left", padx=8)

    lbl_partially = tk.Label(stats_box, text="Partially: 0", font=("Helvetica", 10, "bold"), bg=UI_THEME.get("charcoal", "#334155"), fg="#fbbf24")
    lbl_partially.pack(side="left", padx=8)

    lbl_not = tk.Label(stats_box, text="Not Followed: 0", font=("Helvetica", 10, "bold"), bg=UI_THEME.get("charcoal", "#334155"), fg="#f87171")
    lbl_not.pack(side="left", padx=8)

    # -------------------------------------------------------------------------
    # Input / Edit Form Frame
    # -------------------------------------------------------------------------
    form_frame = tk.LabelFrame(
        win,
        text=" Log / Edit Advice Entry ",
        font=("Helvetica", 11, "bold"),
        bg=UI_THEME.get("dark_slate", "#1e293b"),
        fg=UI_THEME.get("gold", "#FFD700"),
        padx=14,
        pady=10,
    )
    form_frame.pack(fill="x", padx=16, pady=(0, 10))

    # Row 1: Advice Date, Advice Given (wide), Status
    r1 = tk.Frame(form_frame, bg=UI_THEME.get("dark_slate", "#1e293b"))
    r1.pack(fill="x", pady=2)

    tk.Label(r1, text="Date of Advice:", font=("Helvetica", 10, "bold"), bg=UI_THEME.get("dark_slate", "#1e293b"), fg="#f8fafc", width=14, anchor="w").pack(side="left")
    ent_date = tk.Entry(r1, textvariable=advice_date_var, width=12, font=("Helvetica", 10), bg="black", fg="yellow", insertbackground="white")
    ent_date.pack(side="left", padx=(0, 15))

    tk.Label(r1, text="The Advice Given:", font=("Helvetica", 10, "bold"), bg=UI_THEME.get("dark_slate", "#1e293b"), fg="#f8fafc", width=16, anchor="w").pack(side="left")
    ent_advice = tk.Entry(r1, textvariable=advice_text_var, font=("Helvetica", 10), bg="black", fg="yellow", insertbackground="white")
    ent_advice.pack(side="left", fill="x", expand=True, padx=(0, 15))

    tk.Label(r1, text="Status:", font=("Helvetica", 10, "bold"), bg=UI_THEME.get("dark_slate", "#1e293b"), fg="#f8fafc", width=8, anchor="w").pack(side="left")
    status_combo = ttk.Combobox(r1, textvariable=status_var, values=list(ALLOWED_STATUSES), state="readonly", width=18, font=("Helvetica", 10))
    status_combo.pack(side="left")

    # Auto-adjust execution date when status changes
    def on_status_selected(event=None):
        st = status_var.get()
        if st in ("Fully Followed", "Partially Followed"):
            if not exec_date_var.get().strip():
                exec_date_var.set(date.today().isoformat())
        elif st == "Not Followed":
            exec_date_var.set("")

    status_combo.bind("<<ComboboxSelected>>", on_status_selected)

    # Row 2: Execution Date + Today Btn, Notes, and Action Buttons
    r2 = tk.Frame(form_frame, bg=UI_THEME.get("dark_slate", "#1e293b"))
    r2.pack(fill="x", pady=(6, 2))

    tk.Label(r2, text="Execution Date:", font=("Helvetica", 10, "bold"), bg=UI_THEME.get("dark_slate", "#1e293b"), fg="#f8fafc", width=14, anchor="w").pack(side="left")
    ent_exec_date = tk.Entry(r2, textvariable=exec_date_var, width=12, font=("Helvetica", 10), bg="black", fg="yellow", insertbackground="white")
    ent_exec_date.pack(side="left")

    def set_exec_today():
        exec_date_var.set(date.today().isoformat())
        if status_var.get() == "Not Followed":
            status_var.set("Fully Followed")

    btn_today = tk.Button(r2, text="📅 Today", command=set_exec_today, font=("Helvetica", 9, "bold"), bg="#0284c7", fg="white", cursor="hand2", padx=6, pady=0)
    btn_today.pack(side="left", padx=(4, 15))

    tk.Label(r2, text="Notes:", font=("Helvetica", 10, "bold"), bg=UI_THEME.get("dark_slate", "#1e293b"), fg="#f8fafc", width=8, anchor="w").pack(side="left")
    ent_notes = tk.Entry(r2, textvariable=notes_var, font=("Helvetica", 10), bg="black", fg="yellow", insertbackground="white")
    ent_notes.pack(side="left", fill="x", expand=True, padx=(0, 15))

    # Form Buttons (Save New, Update, Auto-fill, Clear)
    btn_box = tk.Frame(r2, bg=UI_THEME.get("dark_slate", "#1e293b"))
    btn_box.pack(side="right")

    def clear_form():
        current_selected_id.set("")
        advice_date_var.set(date.today().isoformat())
        advice_text_var.set("")
        status_var.set("Not Followed")
        exec_date_var.set("")
        notes_var.set("")
        tree.selection_remove(tree.selection())

    def auto_fill_from_pick():
        parsed = get_latest_pick_advice()
        if not parsed:
            messagebox.showinfo(
                "Pick of the Day",
                "No local Pick of the Day report found in data/ folder.\n"
                "Please sync from Drive or run the scanner first.",
                parent=win,
            )
            return

        advice_date_var.set(parsed["advice_date"])
        advice_text_var.set(parsed["advice_text"])
        notes_var.set(f"Source: {parsed.get('source_file', 'Pick of the Day')}")
        messagebox.showinfo(
            "Auto-filled",
            f"Pre-filled from latest Pick of the Day:\n\n"
            f"Date: {parsed['advice_date']}\n"
            f"Advice: {parsed['advice_text']}",
            parent=win,
        )

    def save_new_advice():
        adv_dt = advice_date_var.get().strip()
        adv_txt = advice_text_var.get().strip()
        st = status_var.get().strip()
        ex_dt = exec_date_var.get().strip() or None
        nts = notes_var.get().strip()

        try:
            new_id = add_advice(adv_dt, adv_txt, st, ex_dt, nts)
            messagebox.showinfo("Success", f"Logged new advice #{new_id} successfully!", parent=win)
            clear_form()
            refresh_table()
            try:
                from StockMan.drive_sync import update_portfolio_excel
                update_portfolio_excel()
            except Exception as e_ex:
                logger.warning(f"Could not auto-update Excel after adding advice: {e_ex}")
        except ValueError as err:
            messagebox.showerror("Validation Error", str(err), parent=win)
        except Exception as ex:
            messagebox.showerror("Database Error", f"Failed to add advice: {ex}", parent=win)

    def save_updated_advice():
        cur_id = current_selected_id.get().strip()
        if not cur_id:
            messagebox.showwarning("Select Entry", "Please select an advice entry from the table to update.", parent=win)
            return

        adv_dt = advice_date_var.get().strip()
        adv_txt = advice_text_var.get().strip()
        st = status_var.get().strip()
        ex_dt = exec_date_var.get().strip() or None
        nts = notes_var.get().strip()

        try:
            ok = update_advice(int(cur_id), adv_dt, adv_txt, st, ex_dt, nts)
            if ok:
                messagebox.showinfo("Success", f"Updated advice #{cur_id} successfully!", parent=win)
                refresh_table()
                try:
                    from StockMan.drive_sync import update_portfolio_excel
                    update_portfolio_excel()
                except Exception as e_ex:
                    logger.warning(f"Could not auto-update Excel after updating advice: {e_ex}")
            else:
                messagebox.showwarning("Not Found", f"Advice #{cur_id} was not found.", parent=win)
        except ValueError as err:
            messagebox.showerror("Validation Error", str(err), parent=win)
        except Exception as ex:
            messagebox.showerror("Database Error", f"Failed to update advice: {ex}", parent=win)

    btn_add = tk.Button(
        btn_box,
        text="➕ Add New",
        command=save_new_advice,
        font=("Helvetica", 9, "bold"),
        bg="#10b981",  # emerald green
        fg="white",
        cursor="hand2",
        padx=8,
        pady=2,
    )
    btn_add.pack(side="left", padx=2)

    btn_update = tk.Button(
        btn_box,
        text="💾 Update Selected",
        command=save_updated_advice,
        font=("Helvetica", 9, "bold"),
        bg="#3b82f6",  # blue
        fg="white",
        cursor="hand2",
        padx=8,
        pady=2,
    )
    btn_update.pack(side="left", padx=2)

    btn_autofill = tk.Button(
        btn_box,
        text="⚡ Auto-Pick",
        command=auto_fill_from_pick,
        font=("Helvetica", 9, "bold"),
        bg="#e11d48",  # ruby rose
        fg="white",
        cursor="hand2",
        padx=8,
        pady=2,
    )
    btn_autofill.pack(side="left", padx=2)

    btn_clear = tk.Button(
        btn_box,
        text="🧹 Clear",
        command=clear_form,
        font=("Helvetica", 9, "bold"),
        bg="#64748b",  # slate
        fg="white",
        cursor="hand2",
        padx=6,
        pady=2,
    )
    btn_clear.pack(side="left", padx=2)

    # -------------------------------------------------------------------------
    # Filter & Search Bar
    # -------------------------------------------------------------------------
    filter_bar = tk.Frame(win, bg=UI_THEME.get("dark_slate", "#1e293b"), padx=16, pady=4)
    filter_bar.pack(fill="x")

    tk.Label(filter_bar, text="Filter by Status:", font=("Helvetica", 10, "bold"), bg=UI_THEME.get("dark_slate", "#1e293b"), fg="#f8fafc").pack(side="left", padx=(0, 6))

    combo_filter = ttk.Combobox(
        filter_bar,
        textvariable=filter_status_var,
        values=["All"] + list(ALLOWED_STATUSES),
        state="readonly",
        width=16,
        font=("Helvetica", 10),
    )
    combo_filter.pack(side="left", padx=(0, 20))
    combo_filter.bind("<<ComboboxSelected>>", lambda e: refresh_table())

    tk.Label(filter_bar, text="Search:", font=("Helvetica", 10, "bold"), bg=UI_THEME.get("dark_slate", "#1e293b"), fg="#f8fafc").pack(side="left", padx=(0, 6))

    ent_search = tk.Entry(filter_bar, textvariable=search_var, width=22, font=("Helvetica", 10), bg="black", fg="yellow", insertbackground="white")
    ent_search.pack(side="left", padx=(0, 8))
    ent_search.bind("<KeyRelease>", lambda e: refresh_table())

    btn_reset_filter = tk.Button(
        filter_bar,
        text="Reset Filters",
        command=lambda: [filter_status_var.set("All"), search_var.set(""), refresh_table()],
        font=("Helvetica", 9),
        bg="#475569",
        fg="white",
        cursor="hand2",
        padx=6,
        pady=0,
    )
    btn_reset_filter.pack(side="left")

    # -------------------------------------------------------------------------
    # Central Table: Treeview of Historical Advices
    # -------------------------------------------------------------------------
    table_frame = tk.Frame(win, bg=UI_THEME.get("dark_slate", "#1e293b"), padx=16, pady=0)
    table_frame.pack(fill="both", expand=True)

    columns = ("id", "advice_date", "advice_text", "status", "execution_date", "notes")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

    tree.heading("id", text="ID")
    tree.heading("advice_date", text="Date of Advice")
    tree.heading("advice_text", text="The Advice Given")
    tree.heading("status", text="Execution Status")
    tree.heading("execution_date", text="Execution Date")
    tree.heading("notes", text="Notes")

    tree.column("id", width=50, anchor="center", stretch=False)
    tree.column("advice_date", width=120, anchor="center", stretch=False)
    tree.column("advice_text", width=380, anchor="w", stretch=True)
    tree.column("status", width=150, anchor="center", stretch=False)
    tree.column("execution_date", width=120, anchor="center", stretch=False)
    tree.column("notes", width=220, anchor="w", stretch=True)

    # Style tags for row colors
    tree.tag_configure("fully_followed", background="#064e3b", foreground="#6ee7b7")     # emerald
    tree.tag_configure("partially_followed", background="#78350f", foreground="#fde68a") # amber
    tree.tag_configure("not_followed", background="#450a0a", foreground="#fca5a5")       # rose

    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    vsb.pack(side="right", fill="y")
    tree.configure(yscrollcommand=vsb.set)

    hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
    hsb.pack(side="bottom", fill="x")
    tree.configure(xscrollcommand=hsb.set)

    tree.pack(fill="both", expand=True)

    def on_tree_select(event=None):
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0], "values")
        if vals:
            current_selected_id.set(vals[0])
            advice_date_var.set(vals[1])
            advice_text_var.set(vals[2])
            status_var.set(vals[3])
            exec_date_var.set(vals[4] if vals[4] != "—" else "")
            notes_var.set(vals[5] if vals[5] != "—" else "")

    tree.bind("<<TreeviewSelect>>", on_tree_select)

    # -------------------------------------------------------------------------
    # One-Click Quick Status Buttons for Selected Row
    # -------------------------------------------------------------------------
    quick_bar = tk.Frame(win, bg=UI_THEME.get("dark_slate", "#1e293b"), padx=16, pady=8)
    quick_bar.pack(fill="x")

    tk.Label(
        quick_bar,
        text="Quick Status Actions:",
        font=("Helvetica", 10, "bold"),
        bg=UI_THEME.get("dark_slate", "#1e293b"),
        fg="#cbd5e1",
    ).pack(side="left", padx=(0, 8))

    def quick_mark_status(new_status: str):
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Select Row", "Please click on an advice entry in the table first.", parent=win)
            return
        row_id = int(tree.item(sel[0], "values")[0])

        if new_status in ("Fully Followed", "Partially Followed"):
            # If execution date is not set, use today's date
            ex_date = exec_date_var.get().strip() or date.today().isoformat()
        else:
            ex_date = None

        try:
            update_advice_status(row_id, new_status, ex_date)
            refresh_table()
            try:
                from StockMan.drive_sync import update_portfolio_excel
                update_portfolio_excel()
            except Exception as e_ex:
                logger.warning(f"Could not auto-update Excel after status change: {e_ex}")
            # Reselect row
            for item in tree.get_children():
                if tree.item(item, "values")[0] == str(row_id):
                    tree.selection_set(item)
                    break
        except Exception as err:
            messagebox.showerror("Error", f"Failed to mark status: {err}", parent=win)

    btn_mark_fully = tk.Button(
        quick_bar,
        text="✅ Mark Fully Followed",
        command=lambda: quick_mark_status("Fully Followed"),
        font=("Helvetica", 9, "bold"),
        bg="#059669",
        fg="white",
        cursor="hand2",
        padx=8,
        pady=2,
    )
    btn_mark_fully.pack(side="left", padx=4)

    btn_mark_part = tk.Button(
        quick_bar,
        text="⚠️ Mark Partially Followed",
        command=lambda: quick_mark_status("Partially Followed"),
        font=("Helvetica", 9, "bold"),
        bg="#d97706",
        fg="white",
        cursor="hand2",
        padx=8,
        pady=2,
    )
    btn_mark_part.pack(side="left", padx=4)

    btn_mark_not = tk.Button(
        quick_bar,
        text="❌ Mark Not Followed",
        command=lambda: quick_mark_status("Not Followed"),
        font=("Helvetica", 9, "bold"),
        bg="#dc2626",
        fg="white",
        cursor="hand2",
        padx=8,
        pady=2,
    )
    btn_mark_not.pack(side="left", padx=4)

    def delete_selected():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Select Row", "Please select an advice entry to delete.", parent=win)
            return
        row_id = int(tree.item(sel[0], "values")[0])
        adv_desc = tree.item(sel[0], "values")[2]

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete advice log #{row_id}?\n\n'{adv_desc}'",
            parent=win,
        )
        if confirm:
            try:
                delete_advice(row_id)
                clear_form()
                refresh_table()
                try:
                    from StockMan.drive_sync import update_portfolio_excel
                    update_portfolio_excel()
                except Exception as e_ex:
                    logger.warning(f"Could not auto-update Excel after deleting advice: {e_ex}")
            except Exception as err:
                messagebox.showerror("Error", f"Failed to delete advice: {err}", parent=win)

    btn_delete = tk.Button(
        quick_bar,
        text="🗑️ Delete Advice",
        command=delete_selected,
        font=("Helvetica", 9, "bold"),
        bg="#991b1b",
        fg="white",
        cursor="hand2",
        padx=8,
        pady=2,
    )
    btn_delete.pack(side="left", padx=(12, 4))

    # -------------------------------------------------------------------------
    # Footer Action Buttons (Export to Excel/Drive, Help, Close)
    # -------------------------------------------------------------------------
    footer_bar = tk.Frame(win, bg=UI_THEME.get("dark_slate", "#1e293b"), padx=16, pady=12)
    footer_bar.pack(fill="x")

    def export_and_sync_drive():
        try:
            from StockMan.drive_sync import export_and_upload_portfolio, PORTFOLIO_EXCEL_PATH

            res = export_and_upload_portfolio()
            if res.get("uploaded"):
                drive_info = res.get("drive_result", {})
                status_txt = drive_info.get("status", "uploaded")
                file_id = drive_info.get("id", "")
                msg = (
                    f"✅ Export & Drive Sync Successful!\n\n"
                    f"• Local Excel File: {PORTFOLIO_EXCEL_PATH}\n"
                    f"• Sheet 'Advice_Log' and 'Portfolio' refreshed.\n"
                    f"• Google Drive: {status_txt.capitalize()} (ID: {file_id})\n\n"
                    f"Your AI agent can now read the updated Advice_Log directly!"
                )
                messagebox.showinfo("Drive Sync Successful", msg, parent=win)
            else:
                msg = (
                    f"Local Excel Export Successful!\n\n"
                    f"• Saved to: {PORTFOLIO_EXCEL_PATH}\n"
                    f"• Sheets: 'Portfolio' & 'Advice_Log' updated.\n\n"
                    f"Notice: {res.get('error', 'Drive upload skipped.')}"
                )
                messagebox.showinfo("Excel Export Complete", msg, parent=win)
        except Exception as ex:
            messagebox.showerror("Export Failed", f"Failed to export & sync:\n{ex}", parent=win)

    btn_export = tk.Button(
        footer_bar,
        text="📤 Export & Sync to Excel / Drive",
        command=export_and_sync_drive,
        font=("Helvetica", 11, "bold"),
        bg="#0284c7",  # bright cyan/blue
        fg="white",
        cursor="hand2",
        padx=12,
        pady=4,
    )
    btn_export.pack(side="left")

    def show_help_dialog(e=None):
        guide = [
            "Welcome to the AI Advice Tracking & Execution Manager.",
            "",
            "This module tracks daily AI recommendations (Pick of the Day, Buy/Sell signals)",
            "and logs your actual execution decisions for closed-loop AI learning.",
            "",
            "• Date of Advice: The date when the recommendation was provided (YYYY-MM-DD).",
            "• The Advice Given: Concrete action text (e.g. 'Buy 30 HDFCBANK', 'Trim 50% TATASTEEL').",
            "• Execution Status:",
            "    - 'Fully Followed': Trade was executed exactly as recommended.",
            "    - 'Partially Followed': Sized down, scaled in, or partially executed.",
            "    - 'Not Followed': Decided to skip, or target criteria not met.",
            "• Execution Date: Date the trade was executed in your brokerage (YYYY-MM-DD).",
            "• Automated Trade Management Sync: Whenever you enter a Buy/Sell trade in Trade Management,",
            "  the system automatically scans this Advice Log for matching recommendations,",
            "  marks them as 'Fully Followed' or 'Partially Followed' with the trade date,",
            "  and regenerates StockMan_Portfolio.xlsx with both sheets instantly synced.",
            "• Excel & Drive Export: Automatically updates the dedicated 'Advice_Log' sheet in",
            "  StockMan_Portfolio.xlsx and uploads it to Google Drive for your AI model to read.",
        ]
        faq = [
            (
                "Q: How does the AI read this data?",
                "A: The export appends all historical advice to a dedicated 'Advice_Log' worksheet "
                "in StockMan_Portfolio.xlsx on Google Drive. The AI parses this sheet before formulating new advice."
            ),
            (
                "Q: Do I need to manually mark advice when I execute a trade in Trade Management?",
                "A: No! Trade Management automatically checks your Advice Log when you save any trade. "
                "If it finds a matching unfulfilled advice (e.g. buying 30 HDFC when 'Buy 30 HDFCBANK' is logged), "
                "it automatically marks it as 'Fully Followed' with the trade date and syncs the Excel file."
            ),
            (
                "Q: Can I auto-import from today's Pick of the Day?",
                "A: Yes! Click the '⚡ Auto-Pick' button in the form to parse the latest Pick of the Day report."
            ),
            (
                "Q: How do I change status with one click?",
                "A: Click any row in the table, then click '✅ Mark Fully Followed', '⚠️ Mark Partially Followed', "
                "or '❌ Mark Not Followed' in the quick actions bar."
            ),
        ]
        show_standard_help(win, "Advice Tracking Help", guide, faq)

    win.bind("<F1>", show_help_dialog)

    btn_help = tk.Button(
        footer_bar,
        text="❓ Help (F1)",
        command=show_help_dialog,
        font=("Helvetica", 10, "bold"),
        bg="#475569",
        fg="white",
        cursor="hand2",
        padx=10,
        pady=4,
    )
    btn_help.pack(side="right", padx=(8, 0))

    btn_close = tk.Button(
        footer_bar,
        text="❌ Close (Esc)",
        command=close_modal,
        font=("Helvetica", 10, "bold"),
        bg="#64748b",
        fg="white",
        cursor="hand2",
        padx=12,
        pady=4,
    )
    btn_close.pack(side="right")

    # -------------------------------------------------------------------------
    # Table Refresh & Stat Calculation
    # -------------------------------------------------------------------------
    def refresh_table():
        # Clear tree
        for item in tree.get_children():
            tree.delete(item)

        st_filter = filter_status_var.get()
        if st_filter == "All":
            st_filter = None

        search_txt = search_var.get().strip() or None

        records = get_all_advices(status_filter=st_filter, search_query=search_txt)

        # Update KPI counters (from full list)
        all_records = get_all_advices()
        total_count = len(all_records)
        fully_count = sum(1 for r in all_records if r["status"] == "Fully Followed")
        part_count = sum(1 for r in all_records if r["status"] == "Partially Followed")
        not_count = sum(1 for r in all_records if r["status"] == "Not Followed")

        lbl_total.config(text=f"Total: {total_count}")
        lbl_fully.config(text=f"Fully Followed: {fully_count}")
        lbl_partially.config(text=f"Partially: {part_count}")
        lbl_not.config(text=f"Not Followed: {not_count}")

        # Insert rows into Treeview
        for r in records:
            tag = "not_followed"
            if r["status"] == "Fully Followed":
                tag = "fully_followed"
            elif r["status"] == "Partially Followed":
                tag = "partially_followed"

            tree.insert(
                "",
                "end",
                values=(
                    r["id_advice"],
                    r["advice_date"],
                    r["advice_text"],
                    r["status"],
                    r["execution_date"] or "—",
                    r["notes"] or "—",
                ),
                tags=(tag,),
            )

    # Auto-sync any pending Pick of the Day reports on disk into advice_log & Excel
    try:
        sync_all_pending_pick_of_the_day_advices()
    except Exception as e_sync:
        logger.debug(f"Advice Tracker initial sync notice: {e_sync}")

    # Initial data load
    refresh_table()


# =============================================================================
# Automated Trade Management Integration & Advice Auto-Matching
# =============================================================================

def find_matching_advice_for_trade(
    conn: sqlite3.Connection,
    trade_info: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Scans the 'advice_log' table for any unfulfilled AI advice ('Not Followed' or
    'Partially Followed') that matches the given trade.

    Matching criteria:
      1. Stock: Matches ticker symbol (e.g. 'HDFC', 'HDFCBANK'), short name, or company words.
      2. Action: Trade direction ('BUY' vs 'SELL') matches the recommendation intent.
      3. Quantity: If a target quantity is detected in the advice text (e.g. 'Buy 30 HDFCBANK'),
         an equal or greater trade quantity marks it 'Fully Followed'; smaller marks 'Partially Followed'.
         If no target quantity is specified, any executed trade marks it 'Fully Followed'.

    Returns matched dict or None.
    """
    id_stk = trade_info.get("id_stk")
    stk_code = str(trade_info.get("stk_code") or "").strip().upper()
    comp_name = str(trade_info.get("company_name") or "").strip().upper()
    trade_type = str(trade_info.get("trade_type_trd") or "").strip().upper()
    try:
        qty_trd = float(trade_info.get("qty_trd") or 0)
    except (ValueError, TypeError):
        qty_trd = 0.0
    trd_dt = str(trade_info.get("trd_dt") or date.today().isoformat()).strip()

    stock_aliases = set()
    if stk_code:
        stock_aliases.add(stk_code)
        stock_aliases.add(stk_code.replace(".NS", "").replace(".BO", ""))

    if id_stk:
        cur = conn.cursor()
        cur.execute(
            "SELECT stk_code, short_name, company_name, ticker FROM stocks WHERE id_stk = ?",
            (id_stk,),
        )
        row = cur.fetchone()
        if row:
            if row[0]:
                stock_aliases.add(str(row[0]).upper())
            if row[1]:
                stock_aliases.add(str(row[1]).upper())
            if row[2]:
                stock_aliases.add(str(row[2]).upper())
            if row[3]:
                stock_aliases.add(str(row[3]).upper().replace(".NS", "").replace(".BO", ""))

    # Common synonym normalization
    for alias in list(stock_aliases):
        if alias in ("HDFC", "HDFCBANK", "HDFC BANK"):
            stock_aliases.update(["HDFC", "HDFCBANK", "HDFC BANK"])
        elif alias in ("ICICI", "ICIBAN", "ICICIBANK"):
            stock_aliases.update(["ICICI", "ICIBAN", "ICICIBANK", "ICICI BANK"])
        elif alias == "INFY":
            stock_aliases.add("INFOSYS")
        elif alias == "TCS":
            stock_aliases.add("TATA CONSULTANCY")

    cur = conn.cursor()
    cur.execute(
        """
        SELECT id_advice, advice_date, advice_text, status, execution_date, notes
        FROM advice_log
        WHERE status IN ('Not Followed', 'Partially Followed')
        ORDER BY advice_date DESC, id_advice DESC
        """
    )
    candidates = cur.fetchall()

    for cand in candidates:
        adv_id, adv_dt, adv_text, cur_status, ex_dt, nts = cand
        adv_upper = adv_text.upper()

        # 1. Stock match check
        matched_stock = any(alias in adv_upper for alias in stock_aliases if len(alias) >= 3)
        if not matched_stock and comp_name:
            words = [
                w for w in comp_name.split()
                if len(w) >= 4 and w not in ("LIMITED", "LTD", "CORP", "CORPORATION", "INDIA")
            ]
            matched_stock = any(w in adv_upper for w in words)

        if not matched_stock:
            continue

        # 2. Action match check
        matched_action = False
        if trade_type == "BUY":
            matched_action = any(
                k in adv_upper
                for k in ("BUY", "ADD", "ACCUMULATE", "WINNER", "PURCHASE", "PICK", "FUNNEL", "ALLOCATE", "REBALANCE", "INVEST")
            )
        elif trade_type == "SELL":
            matched_action = any(k in adv_upper for k in ("SELL", "TRIM", "BOOK", "EXIT", "REDUCE"))

        if not matched_action:
            continue

        # 3. Target quantity extraction
        target_qty = None
        qty_match = re.search(r"\b(?:buy|add|trim|sell|qty|shares)\s*[:=]?\s*(\d+)\b", adv_text, re.IGNORECASE)
        if not qty_match:
            qty_match = re.search(r"\b(\d+)\s*(?:shares|qty|stocks)\b", adv_text, re.IGNORECASE)
        if not qty_match:
            qty_match = re.search(r"\b(?:buy|add|trim|sell)\s+(\d+)\b", adv_text, re.IGNORECASE)

        if qty_match:
            try:
                target_qty = float(qty_match.group(1))
            except ValueError:
                target_qty = None

        if target_qty is not None and target_qty > 0:
            new_status = "Fully Followed" if qty_trd >= target_qty else "Partially Followed"
        else:
            new_status = "Fully Followed"

        return {
            "id_advice": adv_id,
            "advice_date": adv_dt,
            "advice_text": adv_text,
            "current_status": cur_status,
            "new_status": new_status,
            "target_qty": target_qty,
            "trade_qty": qty_trd,
            "execution_date": trd_dt or date.today().isoformat(),
        }

    return None


def auto_sync_trade_with_advice(
    trade_info: Dict[str, Any],
    db_path: str = STOCK_DB_PATH,
    trigger_drive_upload: bool = True,
    excel_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Triggered automatically whenever a trade is logged or updated in Trade Management:
      1. Scans SQLite 'advice_log' for any matching unfulfilled AI advice.
      2. If matching advice is found:
         - Automatically marks status as 'Fully Followed' (or 'Partially Followed').
         - Sets execution_date to trade date (trd_dt).
         - Records auto-matching note in SQLite.
      3. Automatically calls update_portfolio_excel() to regenerate StockMan_Portfolio.xlsx
         (updating both 'Portfolio' holdings and 'Advice_Log' sheets).
      4. Optionally uploads to Google Drive in a background daemon thread.
    Returns summary dict.
    """
    ensure_advice_log_table(db_path=db_path)
    result: Dict[str, Any] = {
        "matched": False,
        "advice_id": None,
        "advice_text": None,
        "new_status": None,
        "execution_date": None,
        "excel_path": None,
        "drive_triggered": False,
    }

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        matched = find_matching_advice_for_trade(conn, trade_info)
        if matched:
            cur = conn.cursor()
            trd_type = trade_info.get("trade_type_trd", "Trade")
            qty_val = trade_info.get("qty_trd", 0)
            exec_dt = matched["execution_date"]
            note_addition = f"Auto-matched with {trd_type} {qty_val} on {exec_dt}"

            cur.execute(
                """
                UPDATE advice_log
                SET status = ?,
                    execution_date = ?,
                    notes = CASE
                        WHEN notes IS NULL OR notes = '' THEN ?
                        ELSE notes || ' | ' || ?
                    END
                WHERE id_advice = ?
                """,
                (
                    matched["new_status"],
                    exec_dt,
                    note_addition,
                    note_addition,
                    matched["id_advice"],
                ),
            )
            conn.commit()

            result["matched"] = True
            result["advice_id"] = matched["id_advice"]
            result["advice_text"] = matched["advice_text"]
            result["new_status"] = matched["new_status"]
            result["execution_date"] = exec_dt
            logger.info(
                f"Auto-matched trade with advice #{matched['id_advice']}: "
                f"'{matched['advice_text']}' -> {matched['new_status']} (Exec: {exec_dt})"
            )
    except Exception as e:
        logger.error(f"Error matching trade to advice in '{db_path}': {e}")
    finally:
        if conn:
            conn.close()

    # Automatically regenerate StockMan_Portfolio.xlsx and adjust cash
    try:
        from StockMan.drive_sync import (
            GOOGLE_DRIVE_AVAILABLE,
            get_credentials_file,
            get_drive_service,
            update_portfolio_excel,
            upload_portfolio_to_drive,
            adjust_cash_for_trades,
        )

        net_amt = trade_info.get("net_amt_trd")
        if net_amt is not None and float(net_amt) > 0 and trade_info.get("trade_type_trd"):
            new_cash, appetite, out_excel = adjust_cash_for_trades(
                [trade_info],
                excel_path=excel_path,
                db_path=db_path,
                trigger_drive_upload=trigger_drive_upload,
            )
            result["excel_path"] = out_excel
            result["new_cash"] = new_cash
            result["drive_triggered"] = trigger_drive_upload and GOOGLE_DRIVE_AVAILABLE
            logger.info(
                f"Automatically updated '{out_excel}' and adjusted cash (New cash: ₹{new_cash:,.2f}) following trade entry."
            )
        else:
            out_excel = update_portfolio_excel(excel_path=excel_path, db_path=db_path)
            result["excel_path"] = out_excel
            logger.info(f"Automatically updated '{out_excel}' following trade entry.")

            # Background Google Drive upload
            if trigger_drive_upload and GOOGLE_DRIVE_AVAILABLE:
                def _bg_upload():
                    try:
                        cred_file = get_credentials_file()
                        if cred_file:
                            svc = get_drive_service()
                            upload_portfolio_to_drive(svc, file_path=out_excel)
                            logger.info("Background Google Drive upload completed following trade sync.")
                    except Exception as up_err:
                        logger.warning(f"Background Google Drive upload notice: {up_err}")

                import threading
                threading.Thread(target=_bg_upload, daemon=True).start()
                result["drive_triggered"] = True
    except Exception as ex:
        logger.error(f"Failed to auto-update portfolio Excel: {ex}")

    return result


def auto_sync_trades_batch_with_advice(
    trades_list: List[Dict[str, Any]],
    db_path: str = STOCK_DB_PATH,
    trigger_drive_upload: bool = True,
    excel_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Processes a batch of trades (e.g. from Zerodha contract note),
    updates matching advice in advice_log for each trade,
    and refreshes StockMan_Portfolio.xlsx once.
    """
    ensure_advice_log_table(db_path=db_path)
    results = []

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        for trade_info in trades_list:
            matched = find_matching_advice_for_trade(conn, trade_info)
            if matched:
                trd_type = trade_info.get("trade_type_trd", "Trade")
                qty_val = trade_info.get("qty_trd", 0)
                exec_dt = matched["execution_date"]
                note_addition = f"Auto-matched with {trd_type} {qty_val} on {exec_dt}"

                cur.execute(
                    """
                    UPDATE advice_log
                    SET status = ?,
                        execution_date = ?,
                        notes = CASE
                            WHEN notes IS NULL OR notes = '' THEN ?
                            ELSE notes || ' | ' || ?
                        END
                    WHERE id_advice = ?
                    """,
                    (
                        matched["new_status"],
                        exec_dt,
                        note_addition,
                        note_addition,
                        matched["id_advice"],
                    ),
                )
                results.append({
                    "matched": True,
                    "advice_id": matched["id_advice"],
                    "advice_text": matched["advice_text"],
                    "new_status": matched["new_status"],
                    "execution_date": exec_dt,
                })
            else:
                results.append({"matched": False})

        conn.commit()
    except Exception as e:
        logger.error(f"Error in batch trade advice sync: {e}")
    finally:
        if conn:
            conn.close()

    # Regenerate Excel once for the entire batch and adjust cash
    try:
        from StockMan.drive_sync import (
            GOOGLE_DRIVE_AVAILABLE,
            get_credentials_file,
            get_drive_service,
            update_portfolio_excel,
            upload_portfolio_to_drive,
            adjust_cash_for_trades,
        )

        has_amounts = any(
            t.get("net_amt_trd") is not None and float(t.get("net_amt_trd") or 0.0) > 0
            for t in trades_list
        )
        if has_amounts:
            new_cash, appetite, out_excel = adjust_cash_for_trades(
                trades_list,
                excel_path=excel_path,
                db_path=db_path,
                trigger_drive_upload=trigger_drive_upload,
            )
            logger.info(
                f"Automatically updated '{out_excel}' and adjusted cash (New cash: ₹{new_cash:,.2f}) following batch trade entry."
            )
        else:
            out_excel = update_portfolio_excel(excel_path=excel_path, db_path=db_path)
            logger.info(f"Automatically updated '{out_excel}' following batch trade entry.")

            if trigger_drive_upload and GOOGLE_DRIVE_AVAILABLE:
                def _bg_upload():
                    try:
                        cred_file = get_credentials_file()
                        if cred_file:
                            svc = get_drive_service()
                            upload_portfolio_to_drive(svc, file_path=out_excel)
                            logger.info("Background Google Drive upload completed following batch trade sync.")
                    except Exception as up_err:
                        logger.warning(f"Background Google Drive upload notice: {up_err}")

                import threading
                threading.Thread(target=_bg_upload, daemon=True).start()
    except Exception as ex:
        logger.error(f"Failed to auto-update portfolio Excel after batch trades: {ex}")

    return results
