# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\database_setup.py

"""Database schema and initialization helpers for StockMan.

This module defines the SQLite schema (tables, views and triggers)
used by the StockMan application and exposes the
``create_database`` helper which initializes the database file at
``STOCK_DB_PATH``. Tests may override ``STOCK_DB_PATH`` before calling
``create_database`` to use ephemeral or in-memory databases.
"""

import os
import sqlite3
from typing import Tuple

# Import using relative package structure
from Shared.globals import STOCK_DB_PATH, logger


def _table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def _column_exists(
    cursor: sqlite3.Cursor, table_name: str, column_name: str
) -> bool:
    if not _table_exists(cursor, table_name):
        return False
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cursor.fetchall())


def _repair_linkages(cursor: sqlite3.Cursor) -> dict[str, int]:
    repairs: dict[str, int] = {}

    def run_repair(name: str, sql: str) -> None:
        cursor.execute(sql)
        repairs[name] = max(cursor.rowcount, 0)

    if _column_exists(cursor, "offer_allotments", "tx_id"):
        run_repair(
            "offer_allotments.tx_id",
            """
            UPDATE offer_allotments
            SET tx_id = (
                SELECT t.id_trd
                FROM transactions t
                WHERE t.cont_no = offer_allotments.cont_no
                  AND t.id_stk = offer_allotments.id_stk
                  AND t.trade_type_trd = 'BUY'
                ORDER BY t.id_trd
                LIMIT 1
            )
            WHERE cont_no IS NOT NULL
              AND tx_id IS NULL
            """,
        )

    if _column_exists(cursor, "offer_allotments", "id_comp_bt"):
        run_repair(
            "offer_allotments.id_comp_bt",
            """
            UPDATE offer_allotments
            SET id_comp_bt = (
                SELECT cb.id_comp_bt
                FROM computed_bank cb
                WHERE cb.cont_no = offer_allotments.cont_no
                ORDER BY cb.id_comp_bt
                LIMIT 1
            )
            WHERE cont_no IS NOT NULL
              AND id_comp_bt IS NULL
            """,
        )

    if _column_exists(cursor, "dividends", "id_comp_bt"):
        run_repair(
            "dividends.id_comp_bt",
            """
            UPDATE dividends
            SET id_comp_bt = (
                SELECT cb.id_comp_bt
                FROM computed_bank cb
                WHERE cb.cont_no = 'DIV_' || dividends.id_div
                ORDER BY cb.id_comp_bt
                LIMIT 1
            )
            WHERE id_comp_bt IS NULL
            """,
        )

    if _column_exists(cursor, "splits", "id_trd"):
        run_repair(
            "splits.id_trd",
            """
            UPDATE splits
            SET id_trd = (
                SELECT t.id_trd
                FROM transactions t
                WHERE t.cont_no = 'SPLIT_' || splits.id_split
                  AND t.id_stk = splits.id_stk
                  AND t.trade_type_trd = 'BUY'
                ORDER BY t.id_trd
                LIMIT 1
            )
            WHERE id_trd IS NULL
            """,
        )

    if _column_exists(cursor, "bonus_issues", "id_trd"):
        run_repair(
            "bonus_issues.id_trd",
            """
            UPDATE bonus_issues
            SET id_trd = COALESCE(
                (
                    SELECT t.id_trd
                    FROM transactions t
                    WHERE t.cont_no = 'BONUS_' || bonus_issues.id_bonus
                      AND t.id_stk = bonus_issues.id_stk
                      AND t.trade_type_trd = 'BUY'
                    ORDER BY t.id_trd
                    LIMIT 1
                ),
                (
                    SELECT t.id_trd
                    FROM transactions t
                    WHERE t.cont_no = 'BONUS_' || bonus_issues.id_act
                      AND t.id_stk = bonus_issues.id_stk
                      AND t.trade_type_trd = 'BUY'
                    ORDER BY t.id_trd
                    LIMIT 1
                                ),
                                (
                                        SELECT t.id_trd
                                        FROM transactions t
                                        JOIN corp_acts c
                                            ON c.id_act = bonus_issues.id_act
                                        WHERE t.id_stk = bonus_issues.id_stk
                                            AND t.trade_type_trd = 'BUY'
                                            AND t.qty_trd =
                                                    bonus_issues.bonus_qty
                                            AND t.cont_no LIKE 'BONUS_%'
                                            AND t.note_trd =
                                                    'Bonus Shares Allocation (' ||
                                                    c.details_act || ')'
                                        ORDER BY t.id_trd
                                        LIMIT 1
                )
            )
                        WHERE id_trd IS NULL
                            AND EXISTS (
                                    SELECT 1
                                    FROM transactions t
                                    WHERE (
                                            t.cont_no =
                                                    'BONUS_' || bonus_issues.id_bonus
                                            OR t.cont_no =
                                                    'BONUS_' || bonus_issues.id_act
                                    )
                                        AND t.id_stk = bonus_issues.id_stk
                                        AND t.trade_type_trd = 'BUY'
                                    UNION
                                    SELECT 1
                                    FROM transactions t
                                    JOIN corp_acts c
                                        ON c.id_act = bonus_issues.id_act
                                    WHERE t.id_stk = bonus_issues.id_stk
                                        AND t.trade_type_trd = 'BUY'
                                        AND t.qty_trd = bonus_issues.bonus_qty
                                        AND t.cont_no LIKE 'BONUS_%'
                                        AND t.note_trd =
                                                'Bonus Shares Allocation (' ||
                                                c.details_act || ')'
                            )
            """,
        )

    if _column_exists(cursor, "merger", "id_extinguish_trd"):
        run_repair(
            "merger.id_extinguish_trd",
            """
            UPDATE merger
            SET id_extinguish_trd = (
                SELECT t.id_trd
                FROM transactions t
                WHERE t.cont_no = merger.cont_no
                  AND t.id_stk = merger.id_stk_existing
                  AND t.trade_type_trd = 'SELL'
                ORDER BY t.id_trd
                LIMIT 1
            )
            WHERE cont_no IS NOT NULL
              AND id_extinguish_trd IS NULL
            """,
        )

    if _column_exists(cursor, "merger", "id_allotment_trd"):
        run_repair(
            "merger.id_allotment_trd",
            """
            UPDATE merger
            SET id_allotment_trd = (
                SELECT t.id_trd
                FROM transactions t
                WHERE t.cont_no = merger.cont_no
                  AND t.id_stk = merger.id_stk_new
                  AND t.trade_type_trd = 'BUY'
                ORDER BY t.id_trd
                LIMIT 1
            )
            WHERE cont_no IS NOT NULL
              AND id_allotment_trd IS NULL
            """,
        )

    if _column_exists(cursor, "merger", "id_trd"):
        run_repair(
            "merger.id_trd",
            """
            UPDATE merger
            SET id_trd = COALESCE(
                id_allotment_trd,
                (
                    SELECT t.id_trd
                    FROM transactions t
                    WHERE t.cont_no = merger.cont_no
                      AND t.id_stk = merger.id_stk_new
                      AND t.trade_type_trd = 'BUY'
                    ORDER BY t.id_trd
                    LIMIT 1
                )
            )
            WHERE cont_no IS NOT NULL
              AND id_trd IS NULL
            """,
        )

    if _column_exists(cursor, "merger", "id_comp_bt"):
        run_repair(
            "merger.id_comp_bt",
            """
            UPDATE merger
            SET id_comp_bt = (
                SELECT cb.id_comp_bt
                FROM computed_bank cb
                WHERE cb.cont_no = merger.cont_no
                ORDER BY cb.id_comp_bt
                LIMIT 1
            )
            WHERE cont_no IS NOT NULL
              AND id_comp_bt IS NULL
            """,
        )

    if _column_exists(cursor, "demerger_events", "parent_adjustment_trd_id"):
        run_repair(
            "demerger_events.parent_adjustment_trd_id",
            """
            UPDATE demerger_events
            SET parent_adjustment_trd_id = (
                SELECT t.id_trd
                FROM transactions t
                WHERE t.cont_no = 'DEM_DED_' || demerger_events.id_demerger
                  AND t.id_stk = demerger_events.id_stk_parent
                ORDER BY t.id_trd
                LIMIT 1
            )
            WHERE parent_adjustment_trd_id IS NULL
            """,
        )

    if _column_exists(cursor, "demerger_allotments", "id_trd"):
        run_repair(
            "demerger_allotments.id_trd",
            """
            UPDATE demerger_allotments
            SET id_trd = (
                SELECT t.id_trd
                FROM transactions t
                WHERE t.cont_no = (
                    'DEM_ALT_' || demerger_allotments.id_demerger || '_' ||
                    (
                        SELECT COUNT(*) - 1
                        FROM demerger_allotments da2
                        WHERE da2.id_demerger = demerger_allotments.id_demerger
                          AND da2.id_allotment <= demerger_allotments.id_allotment
                    )
                )
                  AND t.id_stk = demerger_allotments.id_stk_child
                  AND t.trade_type_trd = 'BUY'
                ORDER BY t.id_trd
                LIMIT 1
            )
            WHERE id_trd IS NULL
            """,
        )

    if _column_exists(cursor, "demerger_allotments", "id_comp_bt"):
        run_repair(
            "demerger_allotments.id_comp_bt",
            """
            UPDATE demerger_allotments
            SET id_comp_bt = (
                SELECT cb.id_comp_bt
                FROM computed_bank cb
                WHERE cb.cont_no = (
                    'DEM_ALT_' || demerger_allotments.id_demerger || '_' ||
                    (
                        SELECT COUNT(*) - 1
                        FROM demerger_allotments da2
                        WHERE da2.id_demerger = demerger_allotments.id_demerger
                          AND da2.id_allotment <= demerger_allotments.id_allotment
                    )
                )
                ORDER BY cb.id_comp_bt
                LIMIT 1
            )
            WHERE refund_amt > 0
              AND id_comp_bt IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM computed_bank cb
                  WHERE cb.cont_no = (
                      'DEM_ALT_' || demerger_allotments.id_demerger || '_' ||
                      (
                          SELECT COUNT(*) - 1
                          FROM demerger_allotments da2
                                                    WHERE
                                                            da2.id_demerger =
                                                            demerger_allotments.id_demerger
                                                        AND da2.id_allotment <=
                                                            demerger_allotments.id_allotment
                      )
                  )
              )
            """,
        )

    return repairs


def _verify_linkages(cursor: sqlite3.Cursor) -> dict[str, int]:
    unresolved: dict[str, int] = {}

    def record_check(name: str, sql: str) -> None:
        cursor.execute(sql)
        row = cursor.fetchone()
        unresolved[name] = row[0] if row else 0

    if _column_exists(cursor, "offer_allotments", "tx_id"):
        record_check(
            "offer_allotments.tx_id",
            """
            SELECT COUNT(*)
            FROM offer_allotments
            WHERE cont_no IS NOT NULL
              AND tx_id IS NULL
            """,
        )

    if _column_exists(cursor, "offer_allotments", "id_comp_bt"):
        record_check(
            "offer_allotments.id_comp_bt",
            """
            SELECT COUNT(*)
            FROM offer_allotments
            WHERE cont_no IS NOT NULL
              AND id_comp_bt IS NULL
            """,
        )

    if _column_exists(cursor, "dividends", "id_comp_bt"):
        record_check(
            "dividends.id_comp_bt",
            """
            SELECT COUNT(*)
            FROM dividends
            WHERE net_amt > 0
              AND id_comp_bt IS NULL
            """,
        )

    if _column_exists(cursor, "splits", "id_trd"):
        record_check(
            "splits.id_trd",
            """
            SELECT COUNT(*)
            FROM splits
            WHERE id_trd IS NULL
            """,
        )

    if _column_exists(cursor, "bonus_issues", "id_trd"):
        record_check(
            "bonus_issues.id_trd",
            """
            SELECT COUNT(*)
            FROM bonus_issues
            WHERE id_trd IS NULL
            """,
        )

    if _column_exists(cursor, "merger", "id_extinguish_trd"):
        record_check(
            "merger.id_extinguish_trd",
            """
            SELECT COUNT(*)
            FROM merger
            WHERE cont_no IS NOT NULL
              AND id_extinguish_trd IS NULL
            """,
        )

    if _column_exists(cursor, "merger", "id_allotment_trd"):
        record_check(
            "merger.id_allotment_trd",
            """
            SELECT COUNT(*)
            FROM merger
            WHERE cont_no IS NOT NULL
              AND id_allotment_trd IS NULL
            """,
        )

    if _column_exists(cursor, "merger", "id_trd"):
        record_check(
            "merger.id_trd",
            """
            SELECT COUNT(*)
            FROM merger
            WHERE cont_no IS NOT NULL
              AND id_trd IS NULL
            """,
        )

    if _column_exists(cursor, "merger", "id_comp_bt"):
        record_check(
            "merger.id_comp_bt",
            """
            SELECT COUNT(*)
            FROM merger
            WHERE refund_amt > 0
              AND id_comp_bt IS NULL
            """,
        )

    if _column_exists(cursor, "demerger_events", "parent_adjustment_trd_id"):
        record_check(
            "demerger_events.parent_adjustment_trd_id",
            """
            SELECT COUNT(*)
            FROM demerger_events d
            WHERE d.parent_adjustment_trd_id IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM transactions t
                  WHERE t.cont_no = 'DEM_DED_' || d.id_demerger
                    AND t.id_stk = d.id_stk_parent
              )
            """,
        )

    if _column_exists(cursor, "demerger_allotments", "id_trd"):
        record_check(
            "demerger_allotments.id_trd",
            """
            SELECT COUNT(*)
            FROM demerger_allotments
            WHERE id_trd IS NULL
              AND (allotted_qty > 0 OR transferred_cost > refund_amt)
            """,
        )

    if _column_exists(cursor, "demerger_allotments", "id_comp_bt"):
        record_check(
            "demerger_allotments.id_comp_bt",
            """
            SELECT COUNT(*)
            FROM demerger_allotments
            WHERE refund_amt > 0
              AND id_comp_bt IS NULL
            """,
        )

    return unresolved


def repair_existing_links(db_path: str | None = None) -> dict[str, int]:
    """Backfill deterministic foreign-key-style links in an existing DB."""
    target_path = db_path or STOCK_DB_PATH
    if not os.path.exists(target_path):
        return {}

    conn = None
    try:
        conn = sqlite3.connect(target_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        repairs = _repair_linkages(cursor)
        conn.commit()

        repaired = {
            name: count for name, count in repairs.items() if count > 0
        }
        if repaired:
            logger.info(
                "Link repair updates applied: %s",
                ", ".join(
                    f"{name}={count}" for name, count in repaired.items()
                ),
            )
        else:
            logger.info("No link repair updates were needed.")
        return repairs
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error("Link repair failed: %s", e, exc_info=True)
        raise
    finally:
        if conn:
            conn.close()


def verify_existing_links(db_path: str | None = None) -> dict[str, int]:
    """Verify whether deterministic link fields remain unresolved."""
    target_path = db_path or STOCK_DB_PATH
    if not os.path.exists(target_path):
        return {}

    conn = None
    try:
        conn = sqlite3.connect(target_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        unresolved = _verify_linkages(cursor)
        remaining = {
            name: count for name, count in unresolved.items() if count > 0
        }
        if remaining:
            logger.warning(
                "Link verification found unresolved rows: %s",
                ", ".join(
                    f"{name}={count}" for name, count in remaining.items()
                ),
            )
        else:
            logger.info("Link verification passed with no unresolved rows.")
        return unresolved
    except sqlite3.Error as e:
        logger.error("Link verification failed: %s", e, exc_info=True)
        raise
    finally:
        if conn:
            conn.close()


def _format_maintenance_summary(result: dict) -> str:
    migrations = result.get("migrations", [])
    repaired = result.get("repaired", {})
    unresolved = result.get("unresolved", {})

    repaired_total = sum(count for count in repaired.values() if count > 0)
    unresolved_total = sum(count for count in unresolved.values() if count > 0)

    summary_lines = [
        f"Migrations applied: {len(migrations)}",
        f"Links repaired: {repaired_total}",
        f"Unresolved links: {unresolved_total}",
    ]

    top_repairs = [
        f"{name}={count}" for name, count in repaired.items() if count > 0
    ][:5]
    top_unresolved = [
        f"{name}={count}" for name, count in unresolved.items() if count > 0
    ][:5]

    if top_repairs:
        summary_lines.append("Repaired: " + ", ".join(top_repairs))
    if top_unresolved:
        summary_lines.append("Unresolved: " + ", ".join(top_unresolved))

    return "\n".join(summary_lines)


def run_schema_migrations():
    """
    Checks for and applies any missing schema updates to an existing database,
    then repairs deterministic links that older rows may be missing.
    """
    if not os.path.exists(STOCK_DB_PATH):
        return
    conn = None
    try:
        conn = sqlite3.connect(STOCK_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        migrations_applied = []

        if not _column_exists(cursor, "offer_allotments", "id_comp_bt"):
            cursor.execute(
                "ALTER TABLE offer_allotments "
                "ADD COLUMN id_comp_bt INTEGER DEFAULT NULL "
                "REFERENCES computed_bank(id_comp_bt) ON DELETE SET NULL"
            )
            migrations_applied.append("offer_allotments.id_comp_bt")

        if not _column_exists(cursor, "merger", "id_extinguish_trd"):
            cursor.execute(
                "ALTER TABLE merger "
                "ADD COLUMN id_extinguish_trd INTEGER DEFAULT NULL "
                "REFERENCES transactions(id_trd) ON DELETE SET NULL"
            )
            migrations_applied.append("merger.id_extinguish_trd")

        if not _column_exists(cursor, "merger", "id_allotment_trd"):
            cursor.execute(
                "ALTER TABLE merger "
                "ADD COLUMN id_allotment_trd INTEGER DEFAULT NULL "
                "REFERENCES transactions(id_trd) ON DELETE SET NULL"
            )
            migrations_applied.append("merger.id_allotment_trd")

        if not _column_exists(
            cursor, "demerger_events", "parent_adjustment_trd_id"
        ):
            cursor.execute(
                "ALTER TABLE demerger_events "
                "ADD COLUMN parent_adjustment_trd_id INTEGER DEFAULT NULL "
                "REFERENCES transactions(id_trd) ON DELETE SET NULL"
            )
            migrations_applied.append(
                "demerger_events.parent_adjustment_trd_id"
            )

        if not _table_exists(cursor, "watchlist"):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id_watch INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_stk INTEGER NOT NULL UNIQUE,
                    target_buy_price REAL DEFAULT 0.0,
                    target_sell_price REAL DEFAULT 0.0,
                    notes TEXT DEFAULT '',
                    FOREIGN KEY (id_stk) REFERENCES stocks(id_stk) ON DELETE CASCADE
                );
                """)
            migrations_applied.append("watchlist_table_created")

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_offer_allot_id_comp_bt "
            "ON offer_allotments(id_comp_bt);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_merger_id_extinguish_trd "
            "ON merger(id_extinguish_trd);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_merger_id_allotment_trd "
            "ON merger(id_allotment_trd);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_demerger_parent_adjustment_trd "
            "ON demerger_events(parent_adjustment_trd_id);"
        )

        repaired_links = _repair_linkages(cursor)
        unresolved_links = _verify_linkages(cursor)

        conn.commit()

        if migrations_applied:
            logger.info(
                "Schema migrations applied: %s",
                ", ".join(migrations_applied),
            )
        else:
            logger.info("No schema migrations were needed.")

        repaired = {
            name: count for name, count in repaired_links.items() if count > 0
        }
        if repaired:
            logger.info(
                "Link repair updates applied during migration: %s",
                ", ".join(
                    f"{name}={count}" for name, count in repaired.items()
                ),
            )
        else:
            logger.info("No link repair updates were needed during migration.")
        remaining = {
            name: count
            for name, count in unresolved_links.items()
            if count > 0
        }
        if remaining:
            logger.warning(
                "Link verification found unresolved rows during migration: %s",
                ", ".join(
                    f"{name}={count}" for name, count in remaining.items()
                ),
            )
        else:
            logger.info(
                "Link verification passed during migration with no "
                "unresolved rows."
            )
        return {
            "migrations": migrations_applied,
            "repaired": repaired_links,
            "unresolved": unresolved_links,
        }
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error("Schema migration failed: %s", e, exc_info=True)
        raise
    finally:
        if conn:
            conn.close()


def create_stockman_database(_parent) -> Tuple[bool, str]:
    """
    Creates the database if it doesn't exist and initializes tables.
    If the database already exists, it applies schema migrations and
    repairs deterministic missing links.

    This function sets up the entire database schema including tables for:
    - contracts: Stores contract information for trades
    - stocks: Stores stock details and current positions
    - transactions: Records individual trade transactions
    - corp_acts: Tracks corporate actions (bonus, splits, dividends)
    - primary_offers: Tracks IPOs, FPOs, and Rights Issues
    - offer_allotments: Tracks the application and allotment of primary offers
    - exchange_orders: Maintains exchange order details

    Returns:
        Tuple[bool, str]: A tuple containing:
            - bool: True if database was created successfully,
                   False if it already exists
            - str: Success/error message describing the outcome
    """
    if os.path.exists(STOCK_DB_PATH):
        result = run_schema_migrations()
        unresolved = {
            name: count
            for name, count in result.get("unresolved", {}).items()
            if count > 0
        }
        summary = _format_maintenance_summary(result)
        if unresolved:
            return (
                True,
                "Database already exists. Schema migrations and link "
                "repairs applied, but verification found unresolved links. "
                "Please check the log for details.\n\n" + summary,
            )
        return (
            True,
            "Database already exists. Schema migrations, link repairs, "
            "and verification completed successfully!\n\n" + summary,
        )

    try:
        # Use the STOCK_DB_PATH from this module so tests can override
        # database_setup.STOCK_DB_PATH prior to calling create_database.
        conn = sqlite3.connect(STOCK_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        # ------------------- Table: contracts -------------------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS contracts (
            id_cont INTEGER PRIMARY KEY AUTOINCREMENT,
            cont_no TEXT UNIQUE NOT NULL,
            trd_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                length(trd_dt) = 10 AND
                substr(trd_dt, 5, 1) = '-' AND
                substr(trd_dt, 8, 1) = '-' AND
                trd_dt GLOB
                '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
            ),
            settle_no INTEGER DEFAULT 0,
            settle_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                length(settle_dt) = 10 AND
                substr(settle_dt, 5, 1) = '-' AND
                substr(settle_dt, 8, 1) = '-' AND
                settle_dt GLOB
                '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
            ),
            -- number of trades in this contract
            no_of_trades INTEGER DEFAULT 1,
            brok_cont REAL DEFAULT 0.0,
            etc_cont REAL DEFAULT 0.0,
            sebi_cont REAL DEFAULT 0.0,
            gst_cont REAL DEFAULT 0.0,
            stamp_cont REAL DEFAULT 0.0,
            stt_cont REAL DEFAULT 0.0,
            igst_cont REAL DEFAULT 0.0,
            sell_chrg_cont REAL DEFAULT 0.0,
            net_amt_cont REAL DEFAULT 0.0,
            -- Applicable (Theoretical) Values
            etc_cont_applicable REAL DEFAULT 0.0,
            gst_cont_applicable REAL DEFAULT 0.0,
            stt_cont_applicable REAL DEFAULT 0.0,
            net_amt_cont_applicable REAL DEFAULT 0.0,
            tax_cont REAL GENERATED ALWAYS AS (
                gst_cont + stamp_cont + stt_cont + igst_cont
            ) STORED,
            chrg_cont REAL GENERATED ALWAYS AS (
                brok_cont + etc_cont + sebi_cont + sell_chrg_cont
            ) STORED,
            difference_cont REAL GENERATED ALWAYS AS (
                net_amt_cont - net_amt_cont_applicable
            ) STORED,
            note_cont TEXT DEFAULT ''
        );
        """)

        # ------------------- Table: stocks -------------------
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS stocks (
                    id_stk INTEGER PRIMARY KEY AUTOINCREMENT,
                    stk_code TEXT UNIQUE NOT NULL,
                    isin TEXT UNIQUE NOT NULL CHECK(
                        length(isin) = 12 AND substr(isin, 1, 2) = 'IN'
                    ),
                    company_name TEXT UNIQUE NOT NULL,
                    short_name TEXT UNIQUE NOT NULL,
                    ticker TEXT DEFAULT '', -- <--- NEW COLUMN ADDED HERE
                    sector TEXT DEFAULT '',
                    face_value REAL DEFAULT 10.0 CHECK(face_value >= 0),
                    tick REAL DEFAULT 0.01,
                    is_active INTEGER DEFAULT 1 CHECK(is_active IN (0, 1)),
                    is_etf INTEGER DEFAULT 0 CHECK(is_etf IN (0, 1)),
                    curr_avg_price REAL DEFAULT 0.0 CHECK(curr_avg_price >= 0),
                    buy_qty INTEGER DEFAULT 0,
                    sell_qty INTEGER DEFAULT 0,
                    current_qty INTEGER GENERATED ALWAYS AS (
                        buy_qty - sell_qty
                    ) STORED,
                    total_investment_amt REAL DEFAULT 0.0,
                    -- total sell amount from sells
                    sell_amt REAL DEFAULT 0.0,
                    -- total buy amount of sold qty
                    disinvestment_amt REAL DEFAULT 0.0,
                    -- total realized P&L from sells
                    rpnl_amt REAL DEFAULT 0,
                    curr_investment_amt REAL GENERATED ALWAYS AS (
                        total_investment_amt - disinvestment_amt
                    ) STORED,
                    div_amt REAL DEFAULT 0,
                    no_of_div INTEGER DEFAULT 0,
                    note_stk TEXT DEFAULT ''
                );
            """)

        # ------------------- Table: primary_offers -------------------
        # Unified table replacing 'ipos' and 'rights_issues'
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS primary_offers (
                    id_offer INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_stk INTEGER NOT NULL,
                    offer_type TEXT NOT NULL CHECK(
                        offer_type IN ('IPO', 'FPO', 'SME IPO', 'RIGHTS', 'OFS')
                    ),
                    offer_name TEXT DEFAULT '',
                    ann_dt TEXT DEFAULT '1900-01-01',
                    record_dt TEXT DEFAULT '1900-01-01',
                    open_dt TEXT DEFAULT '1900-01-01',
                    close_dt TEXT DEFAULT '1900-01-01',
                    allotment_dt TEXT DEFAULT '1900-01-01',
                    listing_dt TEXT DEFAULT '1900-01-01',
                    issue_price REAL DEFAULT 0.0,
                    ratio TEXT DEFAULT '',
                    FOREIGN KEY (id_stk)
                        REFERENCES stocks(id_stk) ON DELETE CASCADE
                );
            """)

        # ------------------- Table: transactions -------------------
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id_trd INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_stk INTEGER NOT NULL,
                    cont_no TEXT NOT NULL,
                    trd_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(trd_dt) = 10 AND
                        substr(trd_dt, 5, 1) = '-' AND
                        substr(trd_dt, 8, 1) = '-' AND
                        trd_dt GLOB
                        '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    company_name TEXT NOT NULL,
                    trade_type_trd TEXT NOT NULL CHECK(
                        trade_type_trd IN ('BUY', 'SELL')
                    ),
                    exchange TEXT DEFAULT 'NSE',
                    qty_trd INTEGER DEFAULT 0 CHECK(qty_trd >= 0),
                    -- weighted average price per unit
                    wap_unit_trd REAL DEFAULT 0.0,
                    -- brokerage per unit
                    brok_unit_trd REAL DEFAULT 0.0,
                    price_lot_trd REAL DEFAULT NULL, -- price per lot
                    -- total brokerage for the lot
                    brok_lot_trd REAL DEFAULT 0.0,
                    etc_trd REAL DEFAULT 0.0,
                    sebi_trd REAL DEFAULT 0.0,
                    sell_chrg_trd REAL DEFAULT 0.0,
                    gst_trd REAL DEFAULT 0.0,
                    stamp_trd REAL DEFAULT 0.0,
                    stt_trd INTEGER DEFAULT 0,
                    igst_trd REAL DEFAULT 0.0,
                    net_amt_trd REAL DEFAULT 0.0,
                    -- Applicable (Theoretical) Values
                    etc_trd_applicable REAL DEFAULT 0.0,
                    gst_trd_applicable REAL DEFAULT 0.0,
                    stt_trd_applicable REAL DEFAULT 0.0,
                    net_amt_trd_applicable REAL DEFAULT 0.0,
                    tax_trd REAL GENERATED ALWAYS AS (
                        gst_trd + stamp_trd + stt_trd + igst_trd
                    ) STORED,
                    chrg_trd REAL GENERATED ALWAYS AS (
                        brok_lot_trd + etc_trd + sebi_trd + sell_chrg_trd
                    ) STORED,
                    error REAL GENERATED ALWAYS AS (
                        CASE
                            WHEN trade_type_trd = 'BUY' THEN
                                net_amt_trd - price_lot_trd -
                                tax_trd - chrg_trd
                            WHEN trade_type_trd = 'SELL' THEN
                                net_amt_trd - price_lot_trd +
                                tax_trd + chrg_trd
                            ELSE NULL
                        END
                    ) STORED,
                    difference_trd REAL GENERATED ALWAYS AS (
                        net_amt_trd - net_amt_trd_applicable
                    ) STORED,
                    -- on FIFO basis
                    sold_qty INTEGER DEFAULT 0,
                    note_trd TEXT DEFAULT '',
                    FOREIGN KEY (id_stk)
                        REFERENCES stocks(id_stk) ON DELETE CASCADE,
                    FOREIGN KEY (cont_no)
                        REFERENCES contracts(cont_no) ON DELETE NO ACTION,
                    FOREIGN KEY (company_name)
                        REFERENCES stocks(company_name) ON DELETE NO ACTION
                );
            """)

        # ------------------- Table: exchange_orders -------------------
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS exchange_orders (
                    id_eo INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_trd INTEGER NOT NULL,
                    exchange_eo TEXT DEFAULT 'NSE',
                    ord_no INTEGER DEFAULT 0,
                    ord_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(ord_dt) = 10 AND
                        substr(ord_dt, 5, 1) = '-' AND
                        substr(ord_dt, 8, 1) = '-' AND
                        ord_dt GLOB
                        '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    trd_no INTEGER DEFAULT 0,
                    qty_eo INTEGER DEFAULT 0,
                    rate_eo REAL DEFAULT 0.0,
                    brok_unit_eo REAL DEFAULT 0.0,
                    net_rate_eo REAL DEFAULT 0.0,
                    net_total_eo REAL DEFAULT 0.0,
                    note_eo TEXT DEFAULT '',
                    FOREIGN KEY (id_trd)
                        REFERENCES transactions(id_trd) ON DELETE CASCADE
                );
            """)

        # ------------------- Table: sell_records -------------------
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS sell_records (
                    id_sell INTEGER PRIMARY KEY AUTOINCREMENT,
                    -- id_trd of sell transaction
                    sell_id_trd INTEGER NOT NULL,
                    -- id_trd of matched buy transaction
                    buy_id_trd INTEGER NOT NULL,
                    -- stock being sold
                    id_stk INTEGER NOT NULL,
                    -- quantity sold from this buy lot
                    sell_qty INTEGER NOT NULL CHECK(sell_qty > 0),
                    -- buy date
                    buy_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(buy_dt) = 10 AND
                        substr(buy_dt, 5, 1) = '-' AND
                        substr(buy_dt, 8, 1) = '-' AND
                        buy_dt GLOB
                        '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    -- total buy value for sell_qty
                    buy_value REAL NOT NULL,
                    -- sell date
                    sell_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(sell_dt) = 10 AND
                        substr(sell_dt, 5, 1) = '-' AND
                        substr(sell_dt, 8, 1) = '-' AND
                        sell_dt GLOB
                        '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    -- total sell value for sell_qty
                    sell_value REAL NOT NULL,
                    pnl_amt REAL GENERATED ALWAYS AS (
                        sell_value - buy_value
                    ) STORED,
                    holding_days INTEGER GENERATED ALWAYS AS (
                        julianday(sell_dt) - julianday(buy_dt)
                    ) STORED,
                    annual_return_percent REAL GENERATED ALWAYS AS (
                        CASE
                            WHEN (julianday(sell_dt) - julianday(buy_dt)) > 0
                            THEN (
                                ((sell_value - buy_value) * 365.0 /
                                 buy_value) /
                                (julianday(sell_dt) - julianday(buy_dt)) *
                                100
                            )
                            ELSE NULL
                        END
                    ) STORED,
                    FOREIGN KEY (sell_id_trd)
                        REFERENCES transactions(id_trd) ON DELETE CASCADE,
                    FOREIGN KEY (buy_id_trd)
                        REFERENCES transactions(id_trd) ON DELETE CASCADE,
                    FOREIGN KEY (id_stk)
                        REFERENCES stocks(id_stk) ON DELETE CASCADE
                );
            """)

        # ------------------- Table: computed_bank_trans -------------------

        cursor.execute("""
                CREATE TABLE IF NOT EXISTS computed_bank (
                    id_comp_bt INTEGER PRIMARY KEY AUTOINCREMENT,
                    cont_no TEXT DEFAULT '',
                    -- computed bank transaction date
                    comp_bt_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(comp_bt_dt) = 10 AND
                        substr(comp_bt_dt, 5, 1) = '-' AND
                        substr(comp_bt_dt, 8, 1) = '-' AND
                        comp_bt_dt GLOB
                        '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    comp_bt_type TEXT NOT NULL CHECK(
                        comp_bt_type IN ('CREDIT', 'DEBIT')
                    ),
                    -- comp_bt actual amount
                    comp_bt_amt REAL NOT NULL,
                    -- comp_bt applicable (theoretical) amount
                    comp_bt_amt_applicable REAL DEFAULT 0.0,
                    -- comp_bt description
                    comp_bt_desc TEXT DEFAULT '',
                    difference_bt REAL GENERATED ALWAYS AS (
                        comp_bt_amt - comp_bt_amt_applicable
                    ) STORED
                );
            """)

        # ------------------- Table: actual_bank_trans -------------------

        cursor.execute("""
                CREATE TABLE IF NOT EXISTS actual_bank (
                    id_actu_bt INTEGER PRIMARY KEY AUTOINCREMENT,
                    -- actual bank transaction date
                    actu_bt_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(actu_bt_dt) = 10 AND
                        substr(actu_bt_dt, 5, 1) = '-' AND
                        substr(actu_bt_dt, 8, 1) = '-' AND
                        actu_bt_dt GLOB
                        '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    actu_bt_type TEXT NOT NULL CHECK(
                        actu_bt_type IN ('CREDIT', 'DEBIT')
                    ),
                    -- actu_bt amount
                    actu_bt_amt REAL NOT NULL,
                    -- actu_bt description
                    actu_bt_desc TEXT DEFAULT ''
                );
            """)

        # ------------------- Table: corp_acts -------------------
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS corp_acts (
                    id_act INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_stk INTEGER NOT NULL,
                    act_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(act_dt) = 10 AND
                        substr(act_dt, 5, 1) = '-' AND
                        substr(act_dt, 8, 1) = '-' AND
                        act_dt GLOB
                        '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    -- activity type, e.g. DIVIDEND, BONUS, SPLIT, etc.
                    type_act TEXT NOT NULL,
                    -- details like '10% Dividend' or '1:2 Bonus'
                    details_act TEXT DEFAULT '',
                    -- for dividends
                    div_percent_act REAL DEFAULT 0.0,
                    div_amount_act REAL DEFAULT 0.0,
                    -- ratio for entitlement adjustments
                    ratio_old INTEGER DEFAULT 1,
                    ratio_new INTEGER DEFAULT 1,
                    note_act TEXT DEFAULT '',
                    FOREIGN KEY (id_stk)
                        REFERENCES stocks(id_stk) ON DELETE CASCADE
                );
            """)

        # ------------------- Table: dividends -------------------
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS dividends (
                    id_div INTEGER PRIMARY KEY AUTOINCREMENT,
                    -- Link to stock master; cascade deletes keep data consistent per stock
                    id_stk INTEGER NOT NULL,
                    -- Optional link to a corporate action announcement, if tracked
                    id_act INTEGER DEFAULT NULL,
                    id_comp_bt INTEGER DEFAULT NULL,
                    -- EX-DATE: trade ON/AFTER this date ⇒ buyer will NOT receive the dividend
                    ex_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(ex_dt)=10 AND substr(ex_dt,5,1)='-' AND substr(ex_dt,8,1)='-' AND
                        ex_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    -- RECORD DATE: company snapshot for entitlement
                    -- (legal register)
                    record_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(record_dt)=10 AND substr(record_dt,5,1)='-' AND substr(record_dt,8,1)='-' AND
                        record_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),

                    -- CREDIT DATE: when money actually lands in bank
                    credit_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(credit_dt)=10 AND substr(credit_dt,5,1)='-' AND substr(credit_dt,8,1)='-' AND
                        credit_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    div_type TEXT DEFAULT 'FINAL',
                    div_percent REAL NOT NULL DEFAULT 0.0,
                    -- Immutable entitlement snapshot (prevents distortions after later splits/bonus)
                    entitled_qty INTEGER NOT NULL CHECK (entitled_qty >= 0),
                    per_share_amt REAL NOT NULL DEFAULT 0.0 CHECK (per_share_amt >= 0),
                    gross_amt REAL GENERATED ALWAYS AS (entitled_qty * per_share_amt) STORED,
                    -- Tax and reconciliation
                    tds_amt REAL NOT NULL DEFAULT 0.0 CHECK (tds_amt >= 0),
                    net_amt REAL GENERATED ALWAYS AS (gross_amt - tds_amt) STORED,
                    -- Labels/notes
                    fy_label TEXT DEFAULT '',      -- e.g., 'FY2025', 'Q3 FY25'
                    note_div TEXT DEFAULT '',
                    FOREIGN KEY (id_stk) REFERENCES stocks(id_stk) ON DELETE CASCADE,
                    FOREIGN KEY (id_act) REFERENCES corp_acts(id_act) ON DELETE SET NULL,
                    FOREIGN KEY (id_comp_bt) REFERENCES computed_bank(id_comp_bt) ON DELETE SET NULL
                );
            """)

        # ------------------- Table: offer_allotments -------------------
        # Updated to link to primary_offers and removed acct_holder
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS offer_allotments (
                    id_allot INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_stk INTEGER NOT NULL,
                    id_offer INTEGER NOT NULL,
                    tx_id INTEGER DEFAULT NULL,
                    id_comp_bt INTEGER DEFAULT NULL,
                    exchange TEXT DEFAULT 'NSE',
                    record_qty INTEGER DEFAULT 0,
                    entitlement_qty INTEGER DEFAULT 0,
                    applied_qty INTEGER DEFAULT 0,
                    allotted_qty INTEGER DEFAULT 0,
                    allotment_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(allotment_dt) = 10 AND
                        substr(allotment_dt, 5, 1) = '-' AND
                        substr(allotment_dt, 8, 1) = '-' AND
                        allotment_dt GLOB
                        '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    renounced_qty INTEGER DEFAULT 0,
                    allotted_amt REAL DEFAULT 0.0,
                    status TEXT DEFAULT '',
                    cont_no TEXT DEFAULT NULL,
                    note_allot TEXT DEFAULT '',
                    FOREIGN KEY (id_stk)
                        REFERENCES stocks(id_stk) ON DELETE CASCADE,
                    FOREIGN KEY (id_offer)
                        REFERENCES primary_offers(id_offer) ON DELETE CASCADE,
                    FOREIGN KEY (cont_no)
                        REFERENCES contracts(cont_no) ON DELETE NO ACTION,
                    FOREIGN KEY (id_comp_bt)
                        REFERENCES computed_bank(id_comp_bt) ON DELETE SET NULL,
                    FOREIGN KEY (tx_id)
                        REFERENCES transactions(id_trd) ON DELETE SET NULL
                );
            """)

        # ------------------- Table: merger -------------------
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS merger (
                    id_merger INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_act INTEGER,
                    -- id of old stock that will be taken away
                    id_stk_existing INTEGER NOT NULL,
                    -- id of new stock that will be given
                    id_stk_new INTEGER NOT NULL,
                    id_trd INTEGER DEFAULT NULL,
                    id_extinguish_trd INTEGER DEFAULT NULL,
                    id_allotment_trd INTEGER DEFAULT NULL,
                    id_comp_bt INTEGER DEFAULT NULL,
                    name TEXT DEFAULT '',
                    -- These many shares of old company will vanish
                    ratio_old INTEGER DEFAULT 1 CHECK(ratio_old > 0),
                    -- These many shares of new company will be given
                    ratio_new INTEGER DEFAULT 1 CHECK(ratio_new > 0),
                    -- These many shares of old company are held
                    held_qty INTEGER DEFAULT 0,
                    newly_allotted_qty INTEGER DEFAULT 0,
                    allotment_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(allotment_dt) = 10 AND
                        substr(allotment_dt, 5, 1) = '-' AND
                        substr(allotment_dt, 8, 1) = '-' AND
                        allotment_dt GLOB
                        '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    invested_amt REAL DEFAULT 0.0 CHECK(invested_amt >= 0),
                    -- Refund amount for fractional shares
                    refund_amt REAL DEFAULT 0.0 CHECK(refund_amt >= 0),
                    cont_no TEXT DEFAULT NULL,
                    note_allot TEXT DEFAULT '',
                    FOREIGN KEY (id_act) REFERENCES corp_acts(id_act) ON DELETE CASCADE,
                    FOREIGN KEY (id_stk_existing) REFERENCES stocks(id_stk) ON DELETE CASCADE,
                    FOREIGN KEY (id_stk_new) REFERENCES stocks(id_stk) ON DELETE CASCADE,
                    FOREIGN KEY (cont_no) REFERENCES contracts(cont_no) ON DELETE NO ACTION,
                    FOREIGN KEY (id_trd) REFERENCES transactions(id_trd) ON DELETE SET NULL,
                    FOREIGN KEY (id_extinguish_trd) REFERENCES transactions(id_trd) ON DELETE SET NULL,
                    FOREIGN KEY (id_allotment_trd) REFERENCES transactions(id_trd) ON DELETE SET NULL,
                    FOREIGN KEY (id_comp_bt) REFERENCES computed_bank(id_comp_bt) ON DELETE SET NULL
                );
            """)

        # ------------------- Table: splits -------------------
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS splits (
                    id_split INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_act INTEGER,
                    id_stk INTEGER NOT NULL,
                    id_trd INTEGER DEFAULT NULL,
                    ex_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(ex_dt) = 10 AND
                        substr(ex_dt, 5, 1) = '-' AND
                        substr(ex_dt, 8, 1) = '-' AND
                        ex_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    record_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(record_dt) = 10 AND
                        substr(record_dt, 5, 1) = '-' AND
                        substr(record_dt, 8, 1) = '-' AND
                        record_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    old_fv REAL NOT NULL CHECK(old_fv > 0),
                    new_fv REAL NOT NULL CHECK(new_fv > 0),
                    old_qty INTEGER NOT NULL CHECK(old_qty >= 0),
                    new_allotted_qty INTEGER NOT NULL CHECK(new_allotted_qty >= 0),
                    note_split TEXT DEFAULT '',
                    FOREIGN KEY (id_act) REFERENCES corp_acts(id_act) ON DELETE CASCADE,
                    FOREIGN KEY (id_stk) REFERENCES stocks(id_stk) ON DELETE CASCADE,
                    FOREIGN KEY (id_trd) REFERENCES transactions(id_trd) ON DELETE SET NULL
                );
            """)

        # ------------------- Table: bonus_issues -------------------
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS bonus_issues (
                    id_bonus INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_act INTEGER,
                    id_stk INTEGER NOT NULL,
                    id_trd INTEGER DEFAULT NULL,
                    ex_dt TEXT NOT NULL DEFAULT '1900-01-01',
                    record_dt TEXT NOT NULL DEFAULT '1900-01-01',
                    ratio_old INTEGER NOT NULL CHECK(ratio_old > 0),
                    ratio_new INTEGER NOT NULL CHECK(ratio_new > 0),
                    held_qty INTEGER NOT NULL CHECK(held_qty >= 0),
                    bonus_qty INTEGER NOT NULL CHECK(bonus_qty >= 0),
                    note_bonus TEXT DEFAULT '',
                    FOREIGN KEY (id_act) REFERENCES corp_acts(id_act) ON DELETE CASCADE,
                    FOREIGN KEY (id_stk) REFERENCES stocks(id_stk) ON DELETE CASCADE,
                    FOREIGN KEY (id_trd) REFERENCES transactions(id_trd) ON DELETE SET NULL
                );
            """)

        # ------------------- Table: demerger_events -------------------
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS demerger_events (
                    id_demerger INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_act INTEGER,
                    id_stk_parent INTEGER NOT NULL,
                    parent_adjustment_trd_id INTEGER DEFAULT NULL,
                    ex_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(ex_dt) = 10 AND
                        substr(ex_dt, 5, 1) = '-' AND
                        substr(ex_dt, 8, 1) = '-' AND
                        ex_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    record_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(record_dt) = 10 AND
                        substr(record_dt, 5, 1) = '-' AND
                        substr(record_dt, 8, 1) = '-' AND
                        record_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    total_held_qty INTEGER DEFAULT 0,
                    total_invested_amt REAL DEFAULT 0.0,
                    note_demerger TEXT DEFAULT '',
                    FOREIGN KEY (id_act) REFERENCES corp_acts(id_act) ON DELETE CASCADE,
                    FOREIGN KEY (parent_adjustment_trd_id) REFERENCES transactions(id_trd) ON DELETE SET NULL,
                    FOREIGN KEY (id_stk_parent) REFERENCES stocks(id_stk) ON DELETE CASCADE
                );
            """)

        # ------------------- Table: demerger_allotments (Children) -------------------
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS demerger_allotments (
                    id_allotment INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_demerger INTEGER NOT NULL,
                    id_stk_child INTEGER NOT NULL,
                    id_trd INTEGER DEFAULT NULL,
                    id_comp_bt INTEGER DEFAULT NULL,
                    ratio_parent INTEGER DEFAULT 1 CHECK(ratio_parent > 0),
                    ratio_child INTEGER DEFAULT 1 CHECK(ratio_child > 0),
                    coa_percent REAL NOT NULL CHECK(coa_percent >= 0 AND coa_percent <= 100),
                    allotted_qty INTEGER DEFAULT 0,
                    transferred_cost REAL DEFAULT 0.0,
                    refund_amt REAL DEFAULT 0.0,
                    FOREIGN KEY (id_demerger) REFERENCES demerger_events(id_demerger) ON DELETE CASCADE,
                    FOREIGN KEY (id_stk_child) REFERENCES stocks(id_stk) ON DELETE CASCADE,
                    FOREIGN KEY (id_trd) REFERENCES transactions(id_trd) ON DELETE SET NULL,
                    FOREIGN KEY (id_comp_bt) REFERENCES computed_bank(id_comp_bt) ON DELETE SET NULL
                );
            """)

        # ------------------- Table: watchlist -------------------
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id_watch INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_stk INTEGER NOT NULL UNIQUE,
                    target_buy_price REAL DEFAULT 0.0,
                    target_sell_price REAL DEFAULT 0.0,
                    notes TEXT DEFAULT '',
                    FOREIGN KEY (id_stk) REFERENCES stocks(id_stk) ON DELETE CASCADE
                );
            """)

        # ------------------- Indexes  ---
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_id_stk ON "
            "transactions(id_stk);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_cont_no ON "
            "transactions(cont_no);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_offer_allot_id_stk ON "
            "offer_allotments(id_stk);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_offer_allot_id_offer ON "
            "offer_allotments(id_offer);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_offer_allot_id_comp_bt ON "
            "offer_allotments(id_comp_bt);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_merger_id_stk_existing ON "
            "merger(id_stk_existing);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_merger_id_stk_new ON "
            "merger(id_stk_new);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_merger_id_extinguish_trd ON "
            "merger(id_extinguish_trd);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_merger_id_allotment_trd ON "
            "merger(id_allotment_trd);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_demerger_parent_adjustment_trd ON "
            "demerger_events(parent_adjustment_trd_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_dividends_id_stk ON dividends(id_stk);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_dividends_ex_dt ON dividends(ex_dt);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_dividends_record_dt ON dividends(record_dt);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_dividends_credit_dt ON dividends(credit_dt);"
        )

        # ------------------- View: buy_lots -------------------
        cursor.execute("""
                CREATE VIEW IF NOT EXISTS buy_lots AS
                SELECT
                    id_trd,
                    id_stk,
                    trd_dt,
                    qty_trd,
                    sold_qty,
                    qty_trd - sold_qty AS qty_open
                FROM transactions
                WHERE trade_type_trd = 'BUY';
            """)

        # ------------------- View: gross -------------------
        cursor.execute("""
                CREATE VIEW IF NOT EXISTS view_gross_summary AS
                SELECT
                    SUM(buy_amt) AS buy_amt_gross,
                    SUM(sell_amt) AS sell_amt_gross,
                    SUM(brok_amt) AS brok_gross,
                    SUM(tax_amt) AS taxes_gross,
                    SUM(chrg_amt) AS chrg_gross,
                    SUM(total_investment_amt) AS investment_gross,
                    SUM(curr_investment_amt) AS invest_curr_gross,
                    SUM(rpnl_amt) AS real_pl_gross,
                    SUM(disinvestment_amt) AS disinvestment_gross
                FROM (
                    SELECT
                        SUM(CASE WHEN trade_type_trd = 'BUY'
                            THEN price_lot_trd ELSE 0 END) AS buy_amt,
                        SUM(CASE WHEN trade_type_trd = 'SELL'
                            THEN price_lot_trd ELSE 0 END) AS sell_amt,
                        SUM(brok_lot_trd) AS brok_amt,
                        SUM(tax_trd) AS tax_amt,
                        SUM(chrg_trd) AS chrg_amt,
                        0 AS total_investment_amt,
                        0 AS curr_investment_amt,
                        0 AS rpnl_amt,
                        0 AS disinvestment_amt
                    FROM transactions

                    UNION ALL

                    SELECT
                        0 AS buy_amt,
                        0 AS sell_amt,
                        0 AS brok_amt,
                        0 AS tax_amt,
                        0 AS chrg_amt,
                        SUM(total_investment_amt),
                        SUM(curr_investment_amt),
                        SUM(rpnl_amt),
                        SUM(disinvestment_amt)
                    FROM stocks
                );
            """)

        # ------------------- Triggers -------------------
        cursor.executescript("""
                CREATE TRIGGER IF NOT EXISTS update_stock_buy_qty_insert
                AFTER INSERT ON transactions
                WHEN NEW.trade_type_trd = 'BUY'
                BEGIN
                    UPDATE stocks
                    SET buy_qty = (
                        SELECT COALESCE(SUM(qty_trd), 0)
                        FROM transactions
                        WHERE transactions.id_stk = NEW.id_stk
                        AND transactions.trade_type_trd = 'BUY'
                    )
                    WHERE id_stk = NEW.id_stk;
                END;

                CREATE TRIGGER IF NOT EXISTS update_stock_buy_qty_update
                AFTER UPDATE OF qty_trd, trade_type_trd, id_stk ON transactions
                BEGIN
                    UPDATE stocks
                    SET buy_qty = (
                        SELECT COALESCE(SUM(qty_trd), 0)
                        FROM transactions
                        WHERE transactions.id_stk = OLD.id_stk
                        AND transactions.trade_type_trd = 'BUY'
                    )
                    WHERE id_stk = OLD.id_stk;

                    UPDATE stocks
                    SET buy_qty = (
                        SELECT COALESCE(SUM(qty_trd), 0)
                        FROM transactions
                        WHERE transactions.id_stk = NEW.id_stk
                        AND transactions.trade_type_trd = 'BUY'
                    )
                    WHERE id_stk = NEW.id_stk;
                END;

                CREATE TRIGGER IF NOT EXISTS update_stock_buy_qty_delete
                AFTER DELETE ON transactions
                WHEN OLD.trade_type_trd = 'BUY'
                BEGIN
                    UPDATE stocks
                    SET buy_qty = (
                        SELECT COALESCE(SUM(qty_trd), 0)
                        FROM transactions
                        WHERE transactions.id_stk = OLD.id_stk
                        AND transactions.trade_type_trd = 'BUY'
                    )
                    WHERE id_stk = OLD.id_stk;
                END;

                CREATE TRIGGER IF NOT EXISTS update_stock_sell_qty_insert
                AFTER INSERT ON transactions
                WHEN NEW.trade_type_trd = 'SELL'
                BEGIN
                    UPDATE stocks
                    SET sell_qty = (
                        SELECT COALESCE(SUM(qty_trd), 0)
                        FROM transactions
                        WHERE transactions.id_stk = NEW.id_stk
                        AND transactions.trade_type_trd = 'SELL'
                    )
                    WHERE id_stk = NEW.id_stk;
                END;

                CREATE TRIGGER IF NOT EXISTS update_stock_sell_qty_update
                AFTER UPDATE OF qty_trd, trade_type_trd, id_stk ON transactions
                BEGIN
                    UPDATE stocks
                    SET sell_qty = (
                        SELECT COALESCE(SUM(qty_trd), 0)
                        FROM transactions
                        WHERE transactions.id_stk = OLD.id_stk
                        AND transactions.trade_type_trd = 'SELL'
                    )
                    WHERE id_stk = OLD.id_stk;

                    UPDATE stocks
                    SET sell_qty = (
                        SELECT COALESCE(SUM(qty_trd), 0)
                        FROM transactions
                        WHERE transactions.id_stk = NEW.id_stk
                        AND transactions.trade_type_trd = 'SELL'
                    )
                    WHERE id_stk = NEW.id_stk;
                END;

                CREATE TRIGGER IF NOT EXISTS update_stock_sell_qty_delete
                AFTER DELETE ON transactions
                WHEN OLD.trade_type_trd = 'SELL'
                BEGIN
                    UPDATE stocks
                    SET sell_qty = (
                        SELECT COALESCE(SUM(qty_trd), 0)
                        FROM transactions
                        WHERE transactions.id_stk = OLD.id_stk
                        AND transactions.trade_type_trd = 'SELL'
                    )
                    WHERE id_stk = OLD.id_stk;
                END;

                CREATE TRIGGER IF NOT EXISTS update_investment_amt_insert
                AFTER INSERT ON transactions
                WHEN NEW.trade_type_trd = 'BUY'
                BEGIN
                    UPDATE stocks
                    SET total_investment_amt = (
                        SELECT COALESCE(SUM(net_amt_trd), 0)
                        FROM transactions
                        WHERE id_stk = NEW.id_stk
                        AND trade_type_trd = 'BUY'
                    )
                    WHERE id_stk = NEW.id_stk;
                END;

                CREATE TRIGGER IF NOT EXISTS update_investment_amt_update
                AFTER UPDATE OF net_amt_trd, trade_type_trd, id_stk ON
                transactions
                BEGIN
                    UPDATE stocks
                    SET total_investment_amt = (
                        SELECT COALESCE(SUM(net_amt_trd), 0)
                        FROM transactions
                        WHERE id_stk = OLD.id_stk
                        AND trade_type_trd = 'BUY'
                    )
                    WHERE id_stk = OLD.id_stk;

                    UPDATE stocks
                    SET total_investment_amt = (
                        SELECT COALESCE(SUM(net_amt_trd), 0)
                        FROM transactions
                        WHERE id_stk = NEW.id_stk
                        AND trade_type_trd = 'BUY'
                    )
                    WHERE id_stk = NEW.id_stk;
                END;

                CREATE TRIGGER IF NOT EXISTS update_investment_amt_delete
                AFTER DELETE ON transactions
                WHEN OLD.trade_type_trd = 'BUY'
                BEGIN
                    UPDATE stocks
                    SET total_investment_amt = (
                        SELECT COALESCE(SUM(net_amt_trd), 0)
                        FROM transactions
                        WHERE id_stk = OLD.id_stk
                        AND trade_type_trd = 'BUY'
                    )
                    WHERE id_stk = OLD.id_stk;
                END;

                CREATE TRIGGER IF NOT EXISTS update_sell_amt_insert
                AFTER INSERT ON transactions
                WHEN NEW.trade_type_trd = 'SELL'
                BEGIN
                    UPDATE stocks
                    SET sell_amt = (
                        SELECT COALESCE(SUM(net_amt_trd), 0)
                        FROM transactions
                        WHERE id_stk = NEW.id_stk
                        AND trade_type_trd = 'SELL'
                    )
                    WHERE id_stk = NEW.id_stk;
                END;

                CREATE TRIGGER IF NOT EXISTS update_sell_amt_update
                AFTER UPDATE OF net_amt_trd, trade_type_trd, id_stk ON
                transactions
                BEGIN
                    UPDATE stocks
                    SET sell_amt = (
                        SELECT COALESCE(SUM(net_amt_trd), 0)
                        FROM transactions
                        WHERE id_stk = OLD.id_stk
                        AND trade_type_trd = 'SELL'
                    )
                    WHERE id_stk = OLD.id_stk;

                    UPDATE stocks
                    SET sell_amt = (
                        SELECT COALESCE(SUM(net_amt_trd), 0)
                        FROM transactions
                        WHERE id_stk = NEW.id_stk
                        AND trade_type_trd = 'SELL'
                    )
                    WHERE id_stk = NEW.id_stk;
                END;

                CREATE TRIGGER IF NOT EXISTS update_sell_amt_delete
                AFTER DELETE ON transactions
                WHEN OLD.trade_type_trd = 'SELL'
                BEGIN
                    UPDATE stocks
                    SET sell_amt = (
                        SELECT COALESCE(SUM(net_amt_trd), 0)
                        FROM transactions
                        WHERE id_stk = OLD.id_stk
                        AND trade_type_trd = 'SELL'
                    )
                    WHERE id_stk = OLD.id_stk;
                END;



                -- Sanity triggers: ensure ex_dt is not after record_dt (cannot encode business days here)
                CREATE TRIGGER IF NOT EXISTS trg_dividends_ex_le_record
                BEFORE INSERT ON dividends
                FOR EACH ROW
                WHEN julianday(NEW.ex_dt) > julianday(NEW.record_dt)
                BEGIN
                    SELECT RAISE(ABORT, 'ex_dt cannot be after record_dt');
                END;

                CREATE TRIGGER IF NOT EXISTS trg_dividends_ex_le_record_upd
                BEFORE UPDATE OF ex_dt, record_dt ON dividends
                FOR EACH ROW
                WHEN julianday(NEW.ex_dt) > julianday(NEW.record_dt)
                BEGIN
                    SELECT RAISE(ABORT, 'ex_dt cannot be after record_dt (update)');
                END;

                """)

        conn.commit()
        logger.info("Database created successfully")
        return True, "Database created successfully!"
    except sqlite3.Error as e:
        logger.error("Database creation failed: %s", e, exc_info=True)
        return False, f"Database creation failed: {str(e)}"


# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\database_setup.py ends here
