# -*- coding: utf-8 -*-
# File: c:\Users\aumji\source\repos\Finance\FinanceManager\GUIStock\dbutils\initial_tasks.py

import os
import sqlite3
from typing import Tuple

# Import using new package structure
from FinanceManager.GUIStock.config.globals import (
    get_db_connection, DB_PATH, logger
)


def create_database() -> Tuple[bool, str]:
    """
    Creates the database if it doesn't exist and initializes tables.
    This function sets up the entire database schema including tables for:
    - contracts: Stores contract information for trades
    - stocks: Stores stock details and current positions
    - transactions: Records individual trade transactions
    - corp_acts: Tracks corporate actions
    - exchange_orders: Maintains exchange order details

    Returns:
        Tuple[bool, str]: A tuple containing:
            - bool: True if database was created successfully, False if it already exists
            - str: Success/error message describing the outcome
    """
    if os.path.exists(DB_PATH):
        return False, "Database already exists."

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON;")

            # ------------------- Table: contracts -------------------
            cursor.execute("""
                CREATE TABLE contracts (
                    id_cont INTEGER PRIMARY KEY AUTOINCREMENT,
                    cont_no TEXT UNIQUE NOT NULL,
                    trd_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(trd_dt) = 10 AND
                        substr(trd_dt, 5, 1) = '-' AND
                        substr(trd_dt, 8, 1) = '-' AND
                        trd_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    settle_no INTEGER DEFAULT 0,
                    settle_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(settle_dt) = 10 AND
                        substr(settle_dt, 5, 1) = '-' AND
                        substr(settle_dt, 8, 1) = '-' AND
                        settle_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
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
                    tax_cont REAL GENERATED ALWAYS AS (gst_cont + stamp_cont + stt_cont + igst_cont) STORED,
                    chrg_cont REAL GENERATED ALWAYS AS (brok_cont + etc_cont + sebi_cont + sell_chrg_cont) STORED,
                    note_cont TEXT DEFAULT ''
                );
            """)

            # ------------------- Table: stocks -------------------
            cursor.execute("""
                CREATE TABLE stocks (
                    id_stk INTEGER PRIMARY KEY AUTOINCREMENT,
                    stk_code TEXT UNIQUE NOT NULL,
                    isin TEXT UNIQUE NOT NULL CHECK(length(isin) = 12 AND substr(isin, 1, 2) = 'IN'),
                    company_name TEXT UNIQUE NOT NULL,
                    short_name TEXT UNIQUE NOT NULL,
                    sector TEXT DEFAULT '',
                    face_value REAL DEFAULT 10.0 CHECK(face_value >= 0),
                    tick REAL DEFAULT 0.01,
                    is_active INTEGER DEFAULT 1 CHECK(is_active IN (0, 1)),
                    is_etf INTEGER DEFAULT 0 CHECK(is_etf IN (0, 1)),
                    curr_avg_price REAL DEFAULT 0.0 CHECK(curr_avg_price >= 0),
                    buy_qty INTEGER DEFAULT 0,
                    sell_qty INTEGER DEFAULT 0,
                    current_qty INTEGER GENERATED ALWAYS AS (buy_qty - sell_qty) STORED,
                    total_investment_amt REAL DEFAULT 0.0,
                    sell_amt REAL DEFAULT 0.0,
                    disinvestment_amt REAL DEFAULT 0.0,
                    rpnl_amt REAL DEFAULT 0,
                    curr_investment_amt REAL GENERATED ALWAYS AS (total_investment_amt - disinvestment_amt) STORED,
                    cmp_stk REAL DEFAULT 0.0,
                    urpnl_amt REAL DEFAULT 0,
                    urpnl_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(urpnl_dt) = 10 AND
                        substr(urpnl_dt, 5, 1) = '-' AND
                        substr(urpnl_dt, 8, 1) = '-' AND
                        urpnl_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    div_amt REAL DEFAULT 0,
                    no_of_div INTEGER DEFAULT 0,
                    note_stk TEXT DEFAULT ''
                );
            """)

            # ------------------- Table: transactions -------------------
            cursor.execute("""
                CREATE TABLE transactions (
                    id_trd INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_stk INTEGER NOT NULL,
                    cont_no TEXT NOT NULL,
                    trd_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(trd_dt) = 10 AND
                        substr(trd_dt, 5, 1) = '-' AND
                        substr(trd_dt, 8, 1) = '-' AND
                        trd_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    company_name TEXT NOT NULL,
                    trade_type_trd TEXT NOT NULL CHECK(trade_type_trd IN ('BUY', 'SELL')),
                    exchange TEXT DEFAULT 'NSE',
                    qty_trd INTEGER DEFAULT 0 CHECK(qty_trd >= 0),
                    wap_unit_trd REAL DEFAULT 0.0,
                    brok_unit_trd REAL DEFAULT 0.0,
                    price_lot_trd REAL DEFAULT NULL,
                    brok_lot_trd REAL DEFAULT 0.0,
                    etc_trd REAL DEFAULT 0.0,
                    sebi_trd REAL DEFAULT 0.0,
                    sell_chrg_trd REAL DEFAULT 0.0,
                    gst_trd REAL DEFAULT 0.0,
                    stamp_trd REAL DEFAULT 0.0,
                    stt_trd REAL DEFAULT 0.0,
                    igst_trd REAL DEFAULT 0.0,
                    net_amt_trd REAL DEFAULT 0.0,
                    tax_trd REAL GENERATED ALWAYS AS (gst_trd + stamp_trd + stt_trd + igst_trd) STORED,
                    chrg_trd REAL GENERATED ALWAYS AS (brok_lot_trd + etc_trd + sebi_trd + sell_chrg_trd) STORED,
                    error REAL GENERATED ALWAYS AS (
                        CASE
                            WHEN trade_type_trd = 'BUY' THEN net_amt_trd - price_lot_trd - tax_trd - chrg_trd
                            WHEN trade_type_trd = 'SELL' THEN net_amt_trd - price_lot_trd + tax_trd + chrg_trd
                            ELSE NULL
                        END
                    ) STORED,
                    sold_qty INTEGER DEFAULT 0,
                    note_trd TEXT DEFAULT '',
                    FOREIGN KEY (id_stk) REFERENCES stocks(id_stk) ON DELETE CASCADE,
                    FOREIGN KEY (cont_no) REFERENCES contracts(cont_no) ON DELETE NO ACTION,
                    FOREIGN KEY (company_name) REFERENCES stocks(company_name) ON DELETE NO ACTION
                );
            """)

            # ------------------- Indexes for transactions -------------------
            cursor.execute("CREATE INDEX idx_transactions_id_stk ON transactions(id_stk);")
            cursor.execute("CREATE INDEX idx_transactions_cont_no ON transactions(cont_no);")

            # ------------------- Table: corp_acts -------------------
            cursor.execute("""
                CREATE TABLE corp_acts (
                    id_act INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_stk INTEGER NOT NULL,
                    act_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(act_dt) = 10 AND
                        substr(act_dt, 5, 1) = '-' AND
                        substr(act_dt, 8, 1) = '-' AND
                        act_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    type_act TEXT NOT NULL,
                    details_act TEXT DEFAULT '',
                    div_percent_act REAL DEFAULT 0.0,
                    div_amount_act REAL DEFAULT 0.0,
                    ratio_old INTEGER DEFAULT 1,
                    ratio_new INTEGER DEFAULT 1,
                    note_act TEXT DEFAULT '',
                    FOREIGN KEY (id_stk) REFERENCES stocks(id_stk) ON DELETE CASCADE
                );
            """)

            # ------------------- Table: exchange_orders -------------------
            cursor.execute("""
                CREATE TABLE exchange_orders (
                    id_eo INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_trd INTEGER NOT NULL,
                    ord_no INTEGER DEFAULT 0,
                    ord_dt TEXT NOT NULL DEFAULT '1900-01-01' CHECK (
                        length(ord_dt) = 10 AND
                        substr(ord_dt, 5, 1) = '-' AND
                        substr(ord_dt, 8, 1) = '-' AND
                        ord_dt GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
                    ),
                    trd_no INTEGER DEFAULT 0,
                    qty_eo INTEGER DEFAULT 0,
                    rate_eo REAL DEFAULT 0.0,
                    brok_unit_eo REAL DEFAULT 0.0,
                    net_rate_eo REAL DEFAULT 0.0,
                    net_total_eo REAL DEFAULT 0.0,
                    note_eo TEXT DEFAULT '',
                    FOREIGN KEY (id_trd) REFERENCES transactions(id_trd) ON DELETE CASCADE
                );
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
                        SUM(CASE WHEN trade_type_trd = 'BUY' THEN price_lot_trd ELSE 0 END) AS buy_amt,
                        SUM(CASE WHEN trade_type_trd = 'SELL' THEN price_lot_trd ELSE 0 END) AS sell_amt,
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
            cursor.executescript('''
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
            AFTER UPDATE OF net_amt_trd, trade_type_trd, id_stk ON transactions
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
            AFTER UPDATE OF net_amt_trd, trade_type_trd, id_stk ON transactions
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
            ''')

            conn.commit()
            logger.info("Database created successfully")
            return True, "Database created successfully!"
    except sqlite3.Error as e:
        logger.error("Database creation failed: %s", e, exc_info=True)
        return False, f"Database creation failed: {str(e)}"
