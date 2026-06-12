# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\trade_from_file.py

"""
trade_from_file.py
------------------
Bulk importer for legacy databases. Reads Stocks, Trades, IPOs, Rights,
and Corporate Actions, sorts them chronologically, and allows the user
to batch-import them into the current database via a checklist UI.
"""

import os
import sqlite3
import tkinter as tk
from tkinter import ttk
from typing import Union
from datetime import datetime

from Shared.globals import STOCK_DB_PATH, get_db_connection, logger, PROJECT_ROOT
from Shared.dialog_utils import show_colorful_info, show_colorful_error
from Shared.window_manager import push_window, pop_window, safe_close_modal
from Shared.modal_utils import disable_parent, enable_parent
from .trade_utils import (
    compute_avg_price,
    enforce_no_oversell_for_stock,
    process_allotment,
    rebuild_sell_allocations,
)
from Shared.gui_utils import apply_button_animations, universal_tree_sort
from .validation_utils import ValidationError, validate_trade_import_payload

SRC_LEGACY_DB = os.path.join(PROJECT_ROOT, "data", "mystocks_old.db")

# -------------------------------------------------------------------------
# DATABASE HELPERS
# -------------------------------------------------------------------------


def dict_factory(cursor, row):
    """Converts SQLite rows into Python dictionaries for easy column mapping."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def insert_dict(cursor, table: str, d: dict, exclude_keys: list):
    """Dynamically builds and executes an INSERT statement, ignoring generated columns."""
    keys = [k for k in d.keys() if k not in exclude_keys]
    vals = [d[k] for k in keys]
    qs = ",".join(["?"] * len(keys))
    cols = ",".join(keys)
    cursor.execute(f"INSERT INTO {table} ({cols}) VALUES ({qs})", vals)
    return cursor.lastrowid


def _table_columns(cursor: sqlite3.Cursor, table_name: str) -> set[str]:
    """Return available columns for a table on the active connection."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def _filtered_payload(payload: dict, columns: set[str]) -> dict:
    """Keep only fields that exist in the current table schema."""
    return {
        key: value
        for key, value in payload.items()
        if key in columns and value is not None
    }


def import_transaction(conn: sqlite3.Connection, tx: dict) -> bool:
    """Import one transaction payload into contracts, trades, and orders."""
    try:
        normalized = validate_trade_import_payload(tx)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")

        contract_columns = _table_columns(cursor, "contracts")
        transaction_columns = _table_columns(cursor, "transactions")
        order_columns = _table_columns(cursor, "exchange_orders")

        contract_payload = _filtered_payload(
            {
                "cont_no": normalized["cont_no"],
                "trd_dt": normalized["trd_dt"],
                "settle_no": normalized["settle_no"],
                "settle_dt": normalized["settle_dt"],
                "no_of_trades": normalized["no_of_trades"],
            },
            contract_columns,
        )
        if contract_payload:
            contract_cols = list(contract_payload.keys())
            contract_placeholders = ", ".join(["?"] * len(contract_cols))
            cursor.execute(
                "INSERT OR IGNORE INTO contracts "
                f"({', '.join(contract_cols)}) VALUES "
                f"({contract_placeholders})",
                tuple(contract_payload[col] for col in contract_cols),
            )

        transaction_payload = _filtered_payload(
            {
                "cont_no": normalized["cont_no"],
                "trd_dt": normalized["trd_dt"],
                "company_name": normalized["company_name"],
                "trade_type_trd": normalized["trade_type_trd"],
                "id_stk": normalized["id_stk"],
                "qty_trd": normalized["qty_trd"],
                "wap_unit_trd": normalized.get("wap_unit_trd", 0.0),
                "brok_unit_trd": normalized.get("brok_unit_trd", 0.0),
                "price_lot_trd": normalized.get(
                    "price_lot_trd", normalized.get("wap_unit_trd", 0.0)
                ),
                "net_amt_trd": normalized.get("net_amt_trd", 0.0),
                "sold_qty": normalized.get("sold_qty", 0),
            },
            transaction_columns,
        )

        cursor.execute(
            "SELECT id_trd FROM transactions "
            "WHERE cont_no = ? AND company_name = ? AND id_stk = ?",
            (
                normalized["cont_no"],
                normalized["company_name"],
                normalized["id_stk"],
            ),
        )
        existing = cursor.fetchone()
        if existing:
            id_trd = existing[0]
            update_cols = [
                col
                for col in transaction_payload
                if col not in {"cont_no", "company_name", "id_stk"}
            ]
            if update_cols:
                assignments = ", ".join(f"{col} = ?" for col in update_cols)
                cursor.execute(
                    f"UPDATE transactions SET {assignments} WHERE id_trd = ?",
                    tuple(transaction_payload[col] for col in update_cols)
                    + (id_trd,),
                )
        else:
            insert_cols = list(transaction_payload.keys())
            insert_placeholders = ", ".join(["?"] * len(insert_cols))
            cursor.execute(
                "INSERT INTO transactions "
                f"({', '.join(insert_cols)}) VALUES "
                f"({insert_placeholders})",
                tuple(transaction_payload[col] for col in insert_cols),
            )
            id_trd = cursor.lastrowid

        for order in normalized["exchange_orders"]:
            order_payload = _filtered_payload(
                {
                    "id_trd": id_trd,
                    "ord_no": order.get("ord_no"),
                    "ord_dt": order.get("ord_dt"),
                    "trd_no": order.get("trd_no"),
                    "qty_eo": order.get("qty_eo"),
                    "rate_eo": order.get("rate_eo"),
                    "brok_unit_eo": order.get("brok_unit_eo", 0.0),
                    "net_rate_eo": order.get("net_rate_eo", 0.0),
                    "net_total_eo": order.get("net_total_eo", 0.0),
                },
                order_columns,
            )

            cursor.execute(
                "UPDATE exchange_orders SET "
                "id_trd = ?, trd_no = ?, qty_eo = ?, rate_eo = ?, "
                "brok_unit_eo = ?, net_rate_eo = ?, net_total_eo = ? "
                "WHERE ord_no = ? AND ord_dt = ?",
                (
                    id_trd,
                    order.get("trd_no"),
                    order.get("qty_eo"),
                    order.get("rate_eo"),
                    order.get("brok_unit_eo", 0.0),
                    order.get("net_rate_eo", 0.0),
                    order.get("net_total_eo", 0.0),
                    order.get("ord_no"),
                    order.get("ord_dt"),
                ),
            )
            if cursor.rowcount == 0:
                order_cols = list(order_payload.keys())
                order_placeholders = ", ".join(["?"] * len(order_cols))
                cursor.execute(
                    "INSERT INTO exchange_orders "
                    f"({', '.join(order_cols)}) VALUES "
                    f"({order_placeholders})",
                    tuple(order_payload[col] for col in order_cols),
                )

        if normalized["trade_type_trd"] == "SELL":
            enforce_no_oversell_for_stock(cursor, normalized["id_stk"])

        conn.commit()
        return True

    except (ValidationError, sqlite3.Error, ValueError) as exc:
        logger.exception("Failed to import transaction: %s", exc)
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        return False


def sync_stocks(old_conn, new_conn):
    """Silently copies any missing companies from the old DB to the new DB."""
    old_conn.row_factory = dict_factory
    old_cur = old_conn.cursor()
    new_cur = new_conn.cursor()

    old_cur.execute("SELECT * FROM stocks ORDER BY company_name ASC")
    for row in old_cur.fetchall():
        new_cur.execute(
            "SELECT id_stk FROM stocks WHERE company_name=?",
            (row["company_name"],),
        )
        if not new_cur.fetchone():
            insert_dict(
                new_cur,
                "stocks",
                row,
                ["id_stk", "current_qty", "curr_investment_amt"],
            )
    new_conn.commit()


def fetch_chronological_events(old_conn):
    """Fetches Trades, Offers, and Corp Acts from the old DB and sorts them by date."""
    events = []
    old_conn.row_factory = sqlite3.Row
    cur = old_conn.cursor()

    # 1. Fetch Manual Trades (Excluding IPO/Merger auto-generated trades)
    cur.execute("""
        SELECT id_trd, trd_dt, company_name, trade_type_trd, qty_trd, wap_unit_trd, net_amt_trd, cont_no
        FROM transactions
        WHERE cont_no NOT LIKE 'PO_%' AND cont_no NOT LIKE 'Merged%'
    """)
    for row in cur.fetchall():
        events.append(
            {
                "type": "TRADE",
                "date": row["trd_dt"],
                "company": row["company_name"],
                "action": row["trade_type_trd"],
                "qty": row["qty_trd"],
                "rate": row["wap_unit_trd"],
                "net": row["net_amt_trd"],
                "status": "Executed",
                "old_id": row["id_trd"],
                "cont_no": row["cont_no"],
            }
        )

    # 2. Fetch Primary Offers (IPOs / Rights)
    cur.execute("""
        SELECT o.id_allot, COALESCE(o.allotment_dt, p.close_dt, p.open_dt, p.ann_dt, '1900-01-01') as ev_dt,
               s.company_name, p.offer_type, o.applied_qty, p.issue_price, o.allotted_amt, o.status, p.id_offer
        FROM offer_allotments o
        JOIN primary_offers p ON o.id_offer = p.id_offer
        JOIN stocks s ON o.id_stk = s.id_stk
    """)
    for row in cur.fetchall():
        events.append(
            {
                "type": "OFFER",
                "date": row["ev_dt"],
                "company": row["company_name"],
                "action": row["offer_type"],
                "qty": row["applied_qty"],
                "rate": row["issue_price"],
                "net": row["allotted_amt"],
                "status": row["status"],
                "old_id": row["id_allot"],
                "old_id_offer": row["id_offer"],
            }
        )

    # 3. Fetch Corporate Actions (Bonuses / Splits)
    cur.execute("""
        SELECT c.id_act, c.act_dt, s.company_name, c.type_act, c.details_act
        FROM corp_acts c
        JOIN stocks s ON c.id_stk = s.id_stk
    """)
    for row in cur.fetchall():
        events.append(
            {
                "type": "CORP_ACT",
                "date": row["act_dt"],
                "company": row["company_name"],
                "action": row["type_act"],
                "qty": 0,
                "rate": 0.0,
                "net": 0.0,
                "status": row["details_act"],
                "old_id": row["id_act"],
            }
        )

    # Sort everything strictly by date
    events.sort(key=lambda x: x["date"])
    return events


def process_single_event(event, old_conn, new_conn):
    """Processes a single chronological event, bridging old tables to new tables."""
    old_conn.row_factory = dict_factory
    old_cur = old_conn.cursor()
    new_cur = new_conn.cursor()

    def backfill_bonus_trade_link(cont_no: str, new_trd_id: int) -> None:
        if not cont_no.startswith("BONUS_"):
            return
        bonus_key = cont_no.removeprefix("BONUS_")
        if not bonus_key.isdigit():
            return

        old_bonus_id = int(bonus_key)
        old_cur.execute(
            "SELECT * FROM corp_acts WHERE id_act=? AND type_act='BONUS'",
            (old_bonus_id,),
        )
        old_act_row = old_cur.fetchone()

        if not old_act_row:
            old_cur.execute(
                "SELECT * FROM bonus_issues WHERE id_bonus=?", (old_bonus_id,)
            )
            old_bonus_row = old_cur.fetchone()
            if not old_bonus_row:
                return
            old_cur.execute(
                "SELECT * FROM corp_acts WHERE id_act=? AND type_act='BONUS'",
                (old_bonus_row["id_act"],),
            )
            old_act_row = old_cur.fetchone()

        if not old_act_row:
            return

        new_cur.execute(
            """
            SELECT id_act
            FROM corp_acts
            WHERE id_stk=? AND act_dt=? AND type_act='BONUS' AND details_act=?
            ORDER BY id_act
            LIMIT 1
            """,
            (new_id_stk, old_act_row["act_dt"], old_act_row["details_act"]),
        )
        new_act_row = new_cur.fetchone()
        if not new_act_row:
            return

        new_cur.execute(
            """
            UPDATE bonus_issues
            SET id_trd=?
            WHERE id_act=? AND id_trd IS NULL
            """,
            (new_trd_id, new_act_row[0]),
        )

    def remap_stock_id(old_stock_id):
        if old_stock_id in (None, ""):
            return None
        old_cur.execute(
            "SELECT company_name FROM stocks WHERE id_stk=?", (old_stock_id,)
        )
        old_stock_row = old_cur.fetchone()
        if not old_stock_row:
            return None
        company_name = old_stock_row["company_name"]
        new_cur.execute(
            "SELECT id_stk FROM stocks WHERE company_name=?", (company_name,)
        )
        new_stock_row = new_cur.fetchone()
        return new_stock_row[0] if new_stock_row else None

    # Get the new ID for the stock
    new_cur.execute(
        "SELECT id_stk FROM stocks WHERE company_name = ?", (event["company"],)
    )
    stock_res = new_cur.fetchone()
    if not stock_res:
        return None  # Safety catch if stock wasn't synced
    new_id_stk = stock_res[0]

    if event["type"] == "TRADE":
        cont_no = event["cont_no"]

        # 0. Duplicate Check: Use trd_dt instead of cont_no (NULL values fail SQL equality checks)
        new_cur.execute(
            "SELECT 1 FROM transactions WHERE id_stk=? AND trd_dt=? AND trade_type_trd=? AND qty_trd=?",
            (new_id_stk, event["date"], event["action"], event["qty"]),
        )
        if new_cur.fetchone():
            return None  # Skip existing record

        # 1. Contract
        new_cur.execute(
            "SELECT COUNT(*) FROM contracts WHERE cont_no=?", (cont_no,)
        )
        if new_cur.fetchone()[0] == 0:
            old_cur.execute(
                "SELECT * FROM contracts WHERE cont_no=?", (cont_no,)
            )
            c_row = old_cur.fetchone()
            if c_row:
                insert_dict(
                    new_cur,
                    "contracts",
                    c_row,
                    ["id_cont", "tax_cont", "chrg_cont", "difference_cont"],
                )

        # 2. Transaction
        old_cur.execute(
            "SELECT * FROM transactions WHERE id_trd=?", (event["old_id"],)
        )
        t_row = old_cur.fetchone()
        t_row["id_stk"] = new_id_stk
        t_row["sold_qty"] = (
            0  # <--- CRITICAL FIX: Reset to 0 so FIFO allocation works natively!
        )

        new_trd_id = insert_dict(
            new_cur,
            "transactions",
            t_row,
            ["id_trd", "tax_trd", "chrg_trd", "error", "difference_trd"],
        )

        # 3. Exchange Orders
        old_cur.execute(
            "SELECT * FROM exchange_orders WHERE id_trd=?", (event["old_id"],)
        )
        for eo_row in old_cur.fetchall():
            eo_row["id_trd"] = new_trd_id
            insert_dict(new_cur, "exchange_orders", eo_row, ["id_eo"])

        # 4. Computed Bank
        old_cur.execute(
            "SELECT * FROM computed_bank WHERE cont_no=?", (cont_no,)
        )
        for cb_row in old_cur.fetchall():
            new_cur.execute(
                "SELECT COUNT(*) FROM computed_bank WHERE cont_no=? AND comp_bt_amt=? AND comp_bt_type=?",
                (cont_no, cb_row["comp_bt_amt"], cb_row["comp_bt_type"]),
            )
            if new_cur.fetchone()[0] == 0:
                insert_dict(
                    new_cur,
                    "computed_bank",
                    cb_row,
                    ["id_comp_bt", "difference_bt"],
                )

        backfill_bonus_trade_link(cont_no, new_trd_id)
        if t_row["trade_type_trd"] == "SELL":
            enforce_no_oversell_for_stock(new_cur, new_id_stk)
        new_conn.commit()

        # Wrapped in a try/except just in case your compute_avg_price signature is slightly different
        try:
            compute_avg_price(new_id_stk, t_row["trade_type_trd"], poke=False)
        except TypeError:
            compute_avg_price(new_id_stk, poke=False)

        return new_id_stk

    elif event["type"] == "OFFER":
        # 0. Duplicate Check: Removed date check because event["date"] might be allotment_dt, not ann_dt
        new_cur.execute(
            """SELECT 1 FROM offer_allotments o
               JOIN primary_offers p ON o.id_offer = p.id_offer
               WHERE o.id_stk=? AND o.applied_qty=? AND p.offer_type=?""",
            (new_id_stk, event["qty"], event["action"]),
        )
        if new_cur.fetchone():
            return None  # Skip existing record

        # 1. Primary Offer
        old_cur.execute(
            "SELECT * FROM primary_offers WHERE id_offer=?",
            (event["old_id_offer"],),
        )
        p_row = old_cur.fetchone()
        p_row["id_stk"] = new_id_stk

        new_cur.execute(
            "SELECT id_offer FROM primary_offers WHERE id_stk=? AND offer_type=? AND ann_dt=?",
            (new_id_stk, p_row["offer_type"], p_row["ann_dt"]),
        )
        existing_offer = new_cur.fetchone()
        if existing_offer:
            new_id_offer = existing_offer[0]
        else:
            new_id_offer = insert_dict(
                new_cur, "primary_offers", p_row, ["id_offer"]
            )

        # 2. Offer Allotment
        old_cur.execute(
            "SELECT * FROM offer_allotments WHERE id_allot=?",
            (event["old_id"],),
        )
        o_row = old_cur.fetchone()
        o_row["id_stk"] = new_id_stk
        o_row["id_offer"] = new_id_offer
        o_row["tx_id"] = None
        o_row["id_comp_bt"] = None
        o_row["cont_no"] = None

        # ADD THIS: Capture the new row ID
        new_id_allot = insert_dict(
            new_cur, "offer_allotments", o_row, ["id_allot"]
        )

        # ADD THIS: Let the utility function create the transaction via the active cursor
        process_allotment(new_id_allot, cursor=new_cur)

        new_conn.commit()

        try:
            compute_avg_price(new_id_stk, "BUY", poke=False)
        except TypeError:
            compute_avg_price(new_id_stk, poke=False)

    elif event["type"] == "CORP_ACT":
        # 0. Duplicate Check
        new_cur.execute(
            "SELECT 1 FROM corp_acts WHERE id_stk=? AND act_dt=? AND type_act=?",
            (new_id_stk, event["date"], event["action"]),
        )
        if new_cur.fetchone():
            return None  # Skip existing record

        old_cur.execute(
            "SELECT * FROM corp_acts WHERE id_act=?", (event["old_id"],)
        )
        c_row = old_cur.fetchone()
        if not c_row:
            return None

        # 1. Insert Master Ledger Record
        c_row["id_stk"] = new_id_stk
        new_id_act = insert_dict(new_cur, "corp_acts", c_row, ["id_act"])
        old_id_act = event["old_id"]
        act_type = event["action"]

        # Helper to fetch legacy child rows safely (handles old DBs missing the table or columns)
        def get_legacy_child(table, stk_col="id_stk", dt_col="record_dt"):
            old_cur.execute(f"PRAGMA table_info({table})")
            cols = [c["name"] for c in old_cur.fetchall()]
            if not cols:
                return None
            if "id_act" in cols:
                old_cur.execute(
                    f"SELECT * FROM {table} WHERE id_act=?", (old_id_act,)
                )
            else:
                old_cur.execute(
                    f"SELECT * FROM {table} WHERE {stk_col}=? AND {dt_col}=?",
                    (c_row["id_stk"], event["date"]),
                )
            return old_cur.fetchone()

        # Helper to grab newly generated Transaction and Bank IDs
        def get_links(cont_no):
            id_trd, tx_id = None, None
            new_cur.execute(
                "SELECT id_trd FROM transactions WHERE cont_no=?", (cont_no,)
            )
            t = new_cur.fetchone()
            if t:
                id_trd = t[0]
            new_cur.execute(
                "SELECT id_comp_bt FROM computed_bank WHERE cont_no=?",
                (cont_no,),
            )
            b = new_cur.fetchone()
            if b:
                tx_id = b[0]
            return id_trd, tx_id

        # 2. Migrate Child Tables & Bind Foreign Keys
        if act_type == "DIVIDEND":
            d_row = get_legacy_child("dividends", "id_stk", "record_dt")
            if d_row:
                d_row["id_act"] = new_id_act
                d_row["id_stk"] = new_id_stk
                old_id_div = d_row.get("id_div", old_id_act)
                old_div_bank_id = d_row.get("id_comp_bt")
                new_comp_bt_id = None
                if old_div_bank_id:
                    old_cur.execute(
                        "SELECT * FROM computed_bank WHERE id_comp_bt=?",
                        (old_div_bank_id,),
                    )
                    cb_row = old_cur.fetchone()
                    if cb_row:
                        new_cur.execute(
                            """
                            SELECT id_comp_bt FROM computed_bank
                            WHERE cont_no=? AND comp_bt_dt=?
                              AND comp_bt_type=? AND comp_bt_amt=?
                            """,
                            (
                                cb_row["cont_no"],
                                cb_row["comp_bt_dt"],
                                cb_row["comp_bt_type"],
                                cb_row["comp_bt_amt"],
                            ),
                        )
                        existing_cb = new_cur.fetchone()
                        if existing_cb:
                            new_comp_bt_id = existing_cb[0]
                        else:
                            new_comp_bt_id = insert_dict(
                                new_cur,
                                "computed_bank",
                                cb_row,
                                ["id_comp_bt", "difference_bt"],
                            )
                if not new_comp_bt_id:
                    _, new_comp_bt_id = get_links(f"DIV_{old_id_div}")
                d_row["id_comp_bt"] = new_comp_bt_id
                insert_dict(
                    new_cur,
                    "dividends",
                    d_row,
                    ["id_div", "gross_amt", "net_amt"],
                )
        elif act_type == "SPLIT":
            s_row = get_legacy_child("splits", "id_stk", "record_dt")
            if s_row:
                s_row["id_act"] = new_id_act
                s_row["id_stk"] = new_id_stk
                old_id_split = s_row.get("id_split", old_id_act)
                id_trd, _ = get_links(f"SPLIT_{old_id_split}")
                s_row["id_trd"] = id_trd
                insert_dict(new_cur, "splits", s_row, ["id_split"])

        elif act_type == "BONUS":
            b_row = get_legacy_child("bonus_issues", "id_stk", "record_dt")
            if b_row:
                b_row["id_act"] = new_id_act
                b_row["id_stk"] = new_id_stk
                old_id_bonus = b_row.get("id_bonus", old_id_act)
                id_trd, _ = get_links(f"BONUS_{old_id_bonus}")
                if not id_trd:
                    id_trd, _ = get_links(f"BONUS_{old_id_act}")
                b_row["id_trd"] = id_trd
                insert_dict(new_cur, "bonus_issues", b_row, ["id_bonus"])

        elif act_type == "MERGER":
            m_row = get_legacy_child("merger", "id_stk_target", "allotment_dt")
            if m_row:
                m_row["id_act"] = new_id_act
                m_row["id_stk_existing"] = new_id_stk
                remapped_new_stk = remap_stock_id(m_row.get("id_stk_new"))
                if remapped_new_stk is not None:
                    m_row["id_stk_new"] = remapped_new_stk
                if "id_stk_target" in m_row:
                    del m_row["id_stk_target"]
                old_id_merger = m_row.get("id_merger", old_id_act)
                merge_cont_no = m_row.get("cont_no")
                extinguish_trd_id = None
                allotment_trd_id = None
                tx_id = None
                if merge_cont_no:
                    new_cur.execute(
                        """
                        SELECT id_trd FROM transactions
                        WHERE cont_no=? AND id_stk=? AND trade_type_trd='SELL'
                        ORDER BY id_trd LIMIT 1
                        """,
                        (merge_cont_no, new_id_stk),
                    )
                    row = new_cur.fetchone()
                    if row:
                        extinguish_trd_id = row[0]
                    new_cur.execute(
                        """
                        SELECT id_trd FROM transactions
                        WHERE cont_no=? AND id_stk=? AND trade_type_trd='BUY'
                        ORDER BY id_trd LIMIT 1
                        """,
                        (merge_cont_no, m_row.get("id_stk_new")),
                    )
                    row = new_cur.fetchone()
                    if row:
                        allotment_trd_id = row[0]
                    _, tx_id = get_links(merge_cont_no)
                if not extinguish_trd_id:
                    extinguish_trd_id, fallback_tx_id = get_links(
                        f"MRG_EXT_{old_id_merger}"
                    )
                    if not tx_id:
                        tx_id = fallback_tx_id
                if not allotment_trd_id:
                    allotment_trd_id, fallback_tx_id = get_links(
                        f"MRG_ALT_{old_id_merger}"
                    )
                    if not tx_id:
                        tx_id = fallback_tx_id
                m_row["id_trd"] = allotment_trd_id
                m_row["id_extinguish_trd"] = extinguish_trd_id
                m_row["id_allotment_trd"] = allotment_trd_id
                m_row["id_comp_bt"] = tx_id
                insert_dict(new_cur, "merger", m_row, ["id_merger"])

        elif act_type == "DEMERGER":
            de_row = get_legacy_child(
                "demerger_events", "id_stk_parent", "ex_dt"
            )
            if de_row:
                de_row["id_act"] = new_id_act
                de_row["id_stk_parent"] = new_id_stk
                old_id_dem = de_row.get("id_demerger", old_id_act)
                parent_adjustment_trd_id, _ = get_links(
                    f"DEM_DED_{old_id_dem}"
                )
                de_row["parent_adjustment_trd_id"] = parent_adjustment_trd_id
                new_id_dem = insert_dict(
                    new_cur, "demerger_events", de_row, ["id_demerger"]
                )

                # Handle children allotments safely
                old_cur.execute("PRAGMA table_info(demerger_allotments)")
                if old_cur.fetchall():
                    old_cur.execute(
                        "SELECT * FROM demerger_allotments WHERE id_demerger=?",
                        (old_id_dem,),
                    )
                    for i, da_row in enumerate(old_cur.fetchall()):
                        da_row["id_demerger"] = new_id_dem
                        remapped_child_id = remap_stock_id(
                            da_row.get("id_stk_child")
                        )
                        if remapped_child_id is not None:
                            da_row["id_stk_child"] = remapped_child_id
                        id_trd, tx_id = get_links(f"DEM_ALT_{old_id_dem}_{i}")
                        da_row["id_trd"] = id_trd
                        da_row["id_comp_bt"] = tx_id
                        insert_dict(
                            new_cur,
                            "demerger_allotments",
                            da_row,
                            ["id_allotment"],
                        )

        new_conn.commit()


# -------------------------------------------------------------------------
# UI AND BATCH PROCESSING
# -------------------------------------------------------------------------


def trade_entry_from_file(
    parent: Union[tk.Toplevel, tk.Tk], src_db_path: str = SRC_LEGACY_DB
) -> None:
    """Displays the mass importer checklist UI."""

    # FORCE the absolute path, completely ignoring whatever the menu tries to pass in.
    src_db_path = SRC_LEGACY_DB
    if not os.path.exists(src_db_path):
        show_colorful_error(
            parent,
            "File Not Found",
            f"Could not find legacy database at:\n{src_db_path}",
        )
        return

    # --- DIAGNOSTIC 1: Check the OLD database ---
    try:
        old_conn = sqlite3.connect(src_db_path)
        old_cur = old_conn.cursor()
        old_cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        old_tables = [row[0] for row in old_cur.fetchall()]

        if "stocks" not in old_tables:
            tables_str = (
                ", ".join(old_tables)
                if old_tables
                else "None (The file is completely empty!)"
            )
            show_colorful_error(
                parent,
                "Old DB Error",
                f"The legacy database at:\n{src_db_path}\n\nDoes NOT have a 'stocks' table.\n\nTables it actually contains:\n{tables_str}",
            )
            old_conn.close()
            return
    except sqlite3.Error as e:
        show_colorful_error(
            parent,
            "Connection Error",
            f"Failed connecting to legacy database: {e}",
        )
        return

    # --- DIAGNOSTIC 2: Check the NEW database ---
    try:
        with get_db_connection() as new_conn:
            new_cur = new_conn.cursor()
            new_cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            new_tables = [row[0] for row in new_cur.fetchall()]

            if "stocks" not in new_tables:
                tables_str = (
                    ", ".join(new_tables)
                    if new_tables
                    else "None (The file is completely empty!)"
                )
                show_colorful_error(
                    parent,
                    "New DB Error",
                    f"The CURRENT database does NOT have a 'stocks' table.\n\nTables it actually contains:\n{tables_str}",
                )
                old_conn.close()
                return

            # If both databases passed the test, run the sync!
            sync_stocks(old_conn, new_conn)
            all_events = fetch_chronological_events(old_conn)

    except sqlite3.Error as e:
        show_colorful_error(
            parent,
            "Sync Error",
            f"Failed to sync stocks or fetch events:\n{e}",
        )
        old_conn.close()
        return

    if not all_events:
        show_colorful_info(parent, "Done", "No legacy events found to import.")
        old_conn.close()
        return

    modal_id = disable_parent(parent)
    win = tk.Toplevel(parent)
    win.title("Bulk Importer - Chronological Sequence")
    win.geometry("1100x650")
    win.configure(bg="#f8fafc")
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    push_window(win, parent)

    # --- Styling: Increase Font Size ---
    style = ttk.Style()
    style.configure("Treeview", font=("Helvetica", 11), rowheight=28)
    style.configure("Treeview.Heading", font=("Helvetica", 11, "bold"))

    # --- Treeview Checklist ---
    tree_frame = ttk.Frame(win, padding=10)
    tree_frame.pack(fill="both", expand=True)

    cols = (
        "Select",
        "Date",
        "Cont_No",
        "Type",
        "Action",
        "Company",
        "Qty",
        "Rate",
        "Net Amount",
        "Status",
    )
    tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=15)

    for col in cols:
        tree.heading(
            col,
            text=col,
            command=lambda _col=col: universal_tree_sort(tree, _col, False),
        )

    tree.column("Select", width=60, anchor="center")
    tree.column("Date", width=100, anchor="center")
    tree.column("Cont_No", width=120, anchor="w")
    tree.column("Type", width=80, anchor="w")
    tree.column("Action", width=80, anchor="center")
    tree.column("Company", width=220, anchor="w")
    tree.column("Qty", width=80, anchor="e")
    tree.column("Rate", width=100, anchor="e")
    tree.column("Net Amount", width=90, anchor="e")
    tree.column("Status", width=150, anchor="w")

    # Populate Data
    for i, ev in enumerate(all_events):

        # Convert YYYY-MM-DD from the DB into DD-MM-YYYY for the UI
        disp_date = ev["date"]
        try:
            if disp_date and len(disp_date) >= 10:
                disp_date = datetime.strptime(
                    disp_date[:10], "%Y-%m-%d"
                ).strftime("%d-%m-%Y")
        except ValueError:
            pass

        values = (
            "[ ]",
            disp_date,
            ev.get("cont_no", ""),
            ev["type"],
            ev["action"],
            ev["company"],
            ev["qty"],
            f"{ev['rate']:.2f}",
            f"{ev['net']:.2f}",
            "      " + ev["status"],
        )
        # Store the actual event dictionary in the item tags so we can retrieve it during import
        tree.insert("", "end", iid=str(i), values=values)

    # Initial focus on the first row
    if tree.get_children():
        first_item = tree.get_children()[0]
        tree.focus(first_item)
        tree.selection_set(first_item)

    scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    # --- Interactivity ---
    def toggle_row(event):
        region = tree.identify_region(event.x, event.y)
        if region == "cell":
            col = tree.identify_column(event.x)
            if col == "#1":  # The Select Column
                iid = tree.identify_row(event.y)
                vals = list(tree.item(iid, "values"))
                vals[0] = "[X]" if vals[0] == "[ ]" else "[ ]"
                tree.item(iid, values=vals)

    def toggle_space(event):
        focused_item = tree.focus()
        if focused_item:
            vals = list(tree.item(focused_item, "values"))
            vals[0] = "[X]" if vals[0] == "[ ]" else "[ ]"
            tree.item(focused_item, values=vals)
        return "break"  # Prevent default scrolling behavior of spacebar

    tree.bind("<Button-1>", toggle_row)
    tree.bind("<space>", toggle_space)

    # --- Bottom Buttons ---
    btn_frame = tk.Frame(win, bg="#f8fafc")
    # Using side="bottom" forces the frame to stay anchored to the bottom edge
    btn_frame.pack(side="bottom", fill="x", padx=10, pady=10)

    is_all_selected = [False]

    def on_toggle_all():
        new_val = "[X]" if not is_all_selected[0] else "[ ]"
        for child in tree.get_children():
            vals = list(tree.item(child, "values"))
            vals[0] = new_val
            tree.item(child, values=vals)

        is_all_selected[0] = not is_all_selected[0]
        toggle_all_btn.config(
            text="Deselect All" if is_all_selected[0] else "Select All"
        )

    def cleanup(_event=None):
        try:
            old_conn.close()
        except Exception:
            pass
        enable_parent(modal_id)
        safe_close_modal(win, parent)

    def process_imports():
        # Gather all selected rows
        selected_indices = []
        for child in tree.get_children():
            if tree.item(child, "values")[0] == "[X]":
                selected_indices.append(int(child))

        if not selected_indices:
            show_colorful_error(
                win,
                "No Selection",
                "Please select at least one row to import.",
            )
            return

        # Force Chronological Order
        selected_indices.sort()

        import_btn.config(state="disabled")
        toggle_all_btn.config(state="disabled")
        cancel_btn.config(state="disabled")

        progress_var = tk.DoubleVar()
        progress = ttk.Progressbar(
            btn_frame, variable=progress_var, maximum=len(selected_indices)
        )
        progress.pack(side="left", fill="x", expand=True, padx=20)

        status_lbl = tk.Label(
            btn_frame,
            text="Starting import...",
            bg="#f8fafc",
            fg="blue",
            font=("Helvetica", 10, "bold"),
        )
        status_lbl.pack(side="left", padx=10)

        # Track counters using lists so they can be modified inside the nested function
        added_count = [0]
        skipped_count = [0]
        imported_stock_ids: set[int] = set()

        # Background Batch Loop
        def import_next(idx_ptr=0):
            if idx_ptr >= len(selected_indices):
                if imported_stock_ids:
                    fifo_result = rebuild_sell_allocations(
                        sorted(imported_stock_ids)
                    )
                    if fifo_result["failed"]:
                        first_err = fifo_result["failed"][0]
                        show_colorful_error(
                            win,
                            "Sell Allocation Warning",
                            f"Central FIFO rebuild had failures.\n"
                            f"First error for {first_err['company_name']}: "
                            f"{first_err['error']}",
                        )
                status_lbl.config(text="Import Complete!", fg="green")
                show_colorful_info(
                    win,
                    "Import Complete",
                    f"{added_count[0]} records added.\n{skipped_count[0]} existing records skipped.",
                )
                cleanup()
                return

            try:
                event_index = selected_indices[idx_ptr]
                event_data = all_events[event_index]

                status_lbl.config(
                    text=f"Importing {event_data['company']} ({event_data['date']})..."
                )

                with get_db_connection() as new_conn:
                    # Record how many rows have been modified on this connection before we start
                    start_changes = new_conn.total_changes

                    imported_stk = process_single_event(
                        event_data, old_conn, new_conn
                    )
                    if imported_stk is not None:
                        imported_stock_ids.add(imported_stk)

                    # If total_changes went up, it was added. If it didn't, it was skipped.
                    if new_conn.total_changes > start_changes:
                        added_count[0] += 1
                    else:
                        skipped_count[0] += 1

                # Mark as done visually
                vals = list(tree.item(str(event_index), "values"))
                vals[0] = "[DONE]"
                tree.item(str(event_index), values=vals)

                progress_var.set(idx_ptr + 1)
                # Call next batch after 20ms to keep UI perfectly responsive
                win.after(20, import_next, idx_ptr + 1)

            except Exception as e:
                logger.error(
                    "Import failed at index %s: %s", idx_ptr, e, exc_info=True
                )
                show_colorful_error(
                    win,
                    "Import Error",
                    f"Failed on {event_data['company']}: {e}",
                )
                import_btn.config(state="normal")
                cancel_btn.config(state="normal")

        # Kick off the loop
        win.after(100, import_next, 0)

    toggle_all_btn = tk.Button(
        btn_frame,
        text="Select All",
        width=15,
        font=("Helvetica", 12, "bold"),
        bg="#e2e8f0",
        command=on_toggle_all,
        padx=10,
        pady=8,
    )
    toggle_all_btn.pack(side="left", padx=5, pady=10)

    cancel_btn = tk.Button(
        btn_frame,
        text="Cancel",
        width=12,
        font=("Helvetica", 12, "bold"),
        bg="#ef4444",
        fg="white",
        command=cleanup,
        padx=10,
        pady=8,
    )
    cancel_btn.pack(side="right", padx=5, pady=10)

    import_btn = tk.Button(
        btn_frame,
        text="Import Selected",
        width=18,
        font=("Helvetica", 12, "bold"),
        bg="#22c55e",
        fg="white",
        command=process_imports,
        padx=10,
        pady=8,
    )
    import_btn.pack(side="right", padx=5, pady=10)

    apply_button_animations(toggle_all_btn, "#e2e8f0", "#cbd5e1")
    apply_button_animations(cancel_btn, "#ef4444", "#dc2626")
    apply_button_animations(import_btn, "#22c55e", "#16a34a")

    win.bind("<Escape>", cleanup)
    win.protocol("WM_DELETE_WINDOW", cleanup)


# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\trade_from_file.py ends here
