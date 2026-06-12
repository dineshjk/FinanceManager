# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\database_setup_old.py

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


def run_schema_migrations():
    """
    Checks for and applies any missing schema updates to an existing database.
    This ensures older databases are automatically upgraded without data loss.
    """
    if not os.path.exists(STOCK_DB_PATH):
        return

    try:
        conn = sqlite3.connect(STOCK_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        # --- Migration 1: Add ticker to stocks ---
        cursor.execute("PRAGMA table_info(stocks)")
        columns = [col[1] for col in cursor.fetchall()]
        if "ticker" not in columns:
            logger.info(
                "Migrating schema: Adding 'ticker' column to 'stocks'."
            )
            cursor.execute(
                "ALTER TABLE stocks ADD COLUMN ticker TEXT DEFAULT '';"
            )

        # --- Migration 2: Drop Merger Trigger ---
        logger.info("Migrating schema: Dropping trg_merger_create_tx trigger.")
        cursor.execute("DROP TRIGGER IF EXISTS trg_merger_create_tx;")

        # --- Migration 3: Create Splits Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS splits (
                id_split INTEGER PRIMARY KEY AUTOINCREMENT,
                id_stk INTEGER NOT NULL,
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
                FOREIGN KEY (id_stk) REFERENCES stocks(id_stk) ON DELETE CASCADE
            );
        """)

        # --- Migration 4: Create Demerger Events Table (Parent) ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS demerger_events (
                id_demerger INTEGER PRIMARY KEY AUTOINCREMENT,
                id_stk_parent INTEGER NOT NULL,
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
                FOREIGN KEY (id_stk_parent) REFERENCES stocks(id_stk) ON DELETE CASCADE
            );
        """)

        # --- Migration 5: Create Demerger Allotments Table (Children) ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS demerger_allotments (
                id_allotment INTEGER PRIMARY KEY AUTOINCREMENT,
                id_demerger INTEGER NOT NULL,
                id_stk_child INTEGER NOT NULL,
                id_trd INTEGER DEFAULT NULL,
                ratio_parent INTEGER DEFAULT 1 CHECK(ratio_parent > 0),
                ratio_child INTEGER DEFAULT 1 CHECK(ratio_child > 0),
                coa_percent REAL NOT NULL CHECK(coa_percent >= 0 AND coa_percent <= 100),
                allotted_qty INTEGER DEFAULT 0,
                transferred_cost REAL DEFAULT 0.0,
                refund_amt REAL DEFAULT 0.0,
                FOREIGN KEY (id_demerger) REFERENCES demerger_events(id_demerger) ON DELETE CASCADE,
                FOREIGN KEY (id_stk_child) REFERENCES stocks(id_stk) ON DELETE CASCADE,
                FOREIGN KEY (id_trd) REFERENCES transactions(id_trd) ON DELETE SET NULL
            );
        """)

        conn.commit()
        logger.info("Migration successful.")
        conn.close()
    except sqlite3.Error as e:
        logger.error("Schema migration failed: %s", e, exc_info=True)


def create_database(_parent) -> Tuple[bool, str]:
    """
    Creates the database if it doesn't exist and initializes tables.
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
        run_schema_migrations()  # <--- ADD THIS LINE HERE
        return (
            True,
            "Database already exists. Schema migrations applied successfully!",
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
                        offer_type IN ('IPO', 'FPO', 'SME IPO', 'RIGHTS')
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
                    stt_trd INTEGER DEFAULT 1,
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
                    id_act INTEGER NULL,

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

                    -- Classification for reporting
                    div_type TEXT DEFAULT 'FINAL',

                    -- Immutable entitlement snapshot (prevents distortions after later splits/bonus)
                    entitled_qty  INTEGER NOT NULL CHECK (entitled_qty >= 0),
                    per_share_amt REAL    NOT NULL CHECK (per_share_amt >= 0),
                    gross_amt     REAL    GENERATED ALWAYS AS (entitled_qty * per_share_amt) STORED,

                    -- Tax and reconciliation
                    tds_amt REAL NOT NULL DEFAULT 0.0 CHECK (tds_amt >= 0),
                    net_amt REAL GENERATED ALWAYS AS (gross_amt - tds_amt) STORED,

                    -- Labels/notes
                    fy_label TEXT DEFAULT '',      -- e.g., 'FY2025', 'Q3 FY25'
                    note_div TEXT DEFAULT '',

                    FOREIGN KEY (id_stk) REFERENCES stocks(id_stk) ON DELETE CASCADE,
                    FOREIGN KEY (id_act) REFERENCES corp_acts(id_act) ON DELETE SET NULL
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
                    FOREIGN KEY (tx_id)
                        REFERENCES transactions(id_trd) ON DELETE SET NULL
                );
            """)

        # ------------------- Table: Merger -------------------
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS merger (
                    id_merger INTEGER PRIMARY KEY AUTOINCREMENT,
                    -- id of old stock that will be taken away
                    id_stk_existing INTEGER NOT NULL,
                    -- id of new stock that will be given
                    id_stk_new INTEGER NOT NULL,
                    id_trd INTEGER DEFAULT NULL,
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
                    --
                    invested_amt REAL DEFAULT 0.0 CHECK(invested_amt >= 0),
                    -- Refund amount for fractional shares
                    refund_amt REAL DEFAULT 0.0 CHECK(refund_amt >= 0),
                    cont_no TEXT DEFAULT NULL,
                    note_allot TEXT DEFAULT '',
                    FOREIGN KEY (id_stk_existing)
                        REFERENCES stocks(id_stk) ON DELETE CASCADE,
                    FOREIGN KEY (id_stk_new)
                        REFERENCES stocks(id_stk) ON DELETE CASCADE,
                    FOREIGN KEY (cont_no)
                        REFERENCES contracts(cont_no) ON DELETE NO ACTION,
                    FOREIGN KEY (id_trd)
                        REFERENCES transactions(id_trd) ON DELETE SET NULL
                );
            """)

        # ------------------- Table: splits -------------------
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS splits (
                    id_split INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_stk INTEGER NOT NULL,
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
                    FOREIGN KEY (id_stk) REFERENCES stocks(id_stk) ON DELETE CASCADE
                );
            """)

        # ------------------- Table: demerger_events -------------------
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS demerger_events (
                    id_demerger INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_stk_parent INTEGER NOT NULL,
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
                    FOREIGN KEY (id_stk_parent) REFERENCES stocks(id_stk) ON DELETE CASCADE
                );
            """)

        # ------------------- Table: demerger_allotments -------------------
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS demerger_allotments (
                    id_allotment INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_demerger INTEGER NOT NULL,
                    id_stk_child INTEGER NOT NULL,
                    id_trd INTEGER DEFAULT NULL,
                    ratio_parent INTEGER DEFAULT 1 CHECK(ratio_parent > 0),
                    ratio_child INTEGER DEFAULT 1 CHECK(ratio_child > 0),
                    coa_percent REAL NOT NULL CHECK(coa_percent >= 0 AND coa_percent <= 100),
                    allotted_qty INTEGER DEFAULT 0,
                    transferred_cost REAL DEFAULT 0.0,
                    refund_amt REAL DEFAULT 0.0,
                    FOREIGN KEY (id_demerger) REFERENCES demerger_events(id_demerger) ON DELETE CASCADE,
                    FOREIGN KEY (id_stk_child) REFERENCES stocks(id_stk) ON DELETE CASCADE,
                    FOREIGN KEY (id_trd) REFERENCES transactions(id_trd) ON DELETE SET NULL
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
            "CREATE INDEX IF NOT EXISTS idx_merger_id_stk ON "
            "merger(id_stk_new);"
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
                AFTER UPDATE OF qty_trd, trade_type_trd ON transactions
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
                AFTER UPDATE OF qty_trd, trade_type_trd ON transactions
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
