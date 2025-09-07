
"""
stocks.py
Main entry point for the stock portfolio management system.
This module provides a menu-driven interface to access all functionality:
- View and manage stocks
- Enter and modify transactions
- View reports and summaries
- Debug and maintenance functions
"""

import os
import sys
import sqlite3
import time
from datetime import datetime, timedelta




import glob
import shutil
from contextlib import nullcontext
import msvcrt
import time



sys.path.append(os.path.dirname(__file__))
DB_PATH = os.path.join(os.path.dirname(__file__), "StockData", "myfolio.db")






def create_database():
    """
    Create the SQLite database for stock portfolio tracking.
    Tables: contracts, stocks, transactions, corp_act, overall (view).
    Applies consistent naming, surrogate keys, foreign key constraints,
    and triggers for auto-updates.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Enable foreign key constraints
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
    print("Created table: contracts")
    time.sleep(0.2)

    # ------------------- Table: stocks -------------------
    cursor.execute("""
        CREATE TABLE stocks (
            id_stk INTEGER PRIMARY KEY AUTOINCREMENT,
            stk_code TEXT UNIQUE NOT NULL,
            isin TEXT UNIQUE NOT NULL CHECK(length(isin) = 12 AND substr(isin, 1, 2) = 'IN'),
            company_name TEXT UNIQUE NOT NULL,
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
    print("Created table: stocks")
    time.sleep(0.2)



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
            FOREIGN KEY (company_name) REFERENCES stocks(company_name) ON DELETE NO ACTION,
            FOREIGN KEY (cont_no) REFERENCES contracts(cont_no) ON DELETE NO ACTION
        );
    """)
    print("Created table: transactions")
    time.sleep(0.2)

    # ------------------- Indexes for transactions -------------------
    cursor.execute("CREATE INDEX idx_transactions_id_stk ON transactions(id_stk);")
    cursor.execute("CREATE INDEX idx_transactions_cont_no ON transactions(cont_no);")
    print("Created indexes on transactions table")
    time.sleep(0.2)


    # ------------------- Table: corp_act -------------------
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
    print("Created table: corp_acts")
    time.sleep(0.2)

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
    print("Created table: exchange_orders")
    time.sleep(0.2)

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
            -- Aggregate from transactions
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

            -- Aggregate from stocks
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
    print("Created view: view_gross_summary")
    time.sleep(0.2)

    conn.commit()
    conn.close()
    print("Database created and initialized successfully.")
    time.sleep(0.2)


    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
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
        ''')
        print("Triggers for buy_qty created successfully.")
        time.sleep(0.2)


        cursor.executescript('''
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
        ''')
        print("Triggers for sell_qty created successfully.")
        time.sleep(0.2)


        cursor.executescript('''
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
            -- Update OLD.id_stk (if trade_type_trd was BUY)
            UPDATE stocks
            SET total_investment_amt = (
                SELECT COALESCE(SUM(net_amt_trd), 0)
                FROM transactions
                WHERE id_stk = OLD.id_stk
                AND trade_type_trd = 'BUY'
            )
            WHERE id_stk = OLD.id_stk;

            -- Update NEW.id_stk (if trade_type_trd is now BUY)
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
        ''')
        print("Triggers for total_investment_amt created successfully.")
        time.sleep(0.2)

        # Create triggers to maintain investment_amt on INSERT, UPDATE, DELETE
        cursor.executescript('''
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
            -- Update OLD.id_stk (if trade_type_trd was SELL)
            UPDATE stocks
            SET sell_amt = (
                SELECT COALESCE(SUM(net_amt_trd), 0)
                FROM transactions
                WHERE id_stk = OLD.id_stk
                AND trade_type_trd = 'SELL'
            )
            WHERE id_stk = OLD.id_stk;

            -- Update NEW.id_stk (if trade_type_trd is now SELL)
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
        print("Triggers for sell_amt created successfully.")
        time.sleep(0.2)

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        conn.commit()
        conn.close()
        print("Triggers created successfully.")
        time.sleep(0.2)
    get_single_key("Database and triggers created successfully.\nPress any key to continue...")


def bulk_entry_company():
    """ This is one-time entry for some of the company data.
        One has to write a separate program to add company data that
        will take care of new companies
"""
    # (stk_code, company_name, isin, face_value, sector, is_active, is_etf, tick)
    company_data = [
        ("ABFRL", "Aditya Birla Fashion & Retail Ltd", "INE647O01011", 10.0, "Consumer Durables", 1,0, 0.01),
        ("ADILIF", "Aditya Birla Lifestyle Brands Limited", "INE14LE01019", 10.0, "Retail", 1,0, 0.01),
        ("ADANIPORTS", "Adani Ports and Special Economic Zone Limited", "INE742F01042", 2.0, "Port & Port services", 1, 0, 0.1),
        ("DMART", "Avenue Supermarts Limited DMART", "INE192R01011", 10.0, "Consumer Durables", 1, 0, 0.1),
        ("BAJFINANCE", "Bajaj Finance Limited", "INE296A01024", 2.0, "Non Banking Financial Company (NBFC)", 1, 0, 0.5),
        ("DEEPAKNTR", "Deepak Nitrite Limited", "INE288B01029", 2.0, "Chemicals", 1, 0, 0.1),
        ("DIXTEC", "Dixon Technologies (India) Limited", "INE935N01020", 2.0, "Consumer Durables", 1, 0, 1),
        ("ETERNAL(ZOMATO)", "Eternal Limited", "INE758T01015", 1.0, "E-Commerce/App based Aggregator", 1, 0, 0.01),
        ("GRWRHITECH", "Garware Hi-Tech Films Limited", "INE291A01017", 10.0, "Plastics", 1, 0, 0.1),
        ("HAL", "Hindustan Aeronautics Limited", "INE066F01012", 5.0, "Aerospace", 1, 0, 0.1),
        ("HDFC", "HDFC Bank Limited", "INE040A01034", 1.0, "Banking", 1, 0, 0.1),
        ("HYUNDAI", "Hyundai Motor India Limited", "INE0V6F01027", 10.0, "Automobile", 1, 0, 0.1),
        ("ICIBAN", "ICICI Bank Limited", "INE090A01021", 2.0, "Banking", 1, 0, 0.1),
        ("BSE500IETF", "ICICI Prudential BSE 500 ETF", "INF109KC1V59", 1.0, "Finance ETF", 1, 1, 0.01),
        ("GOLDIETF", "ICICI Prudential Gold ETF", "INF109KC1NT3", 1.0, "Gold ETF", 1, 1, 0.01),
        ("ISEC", "ICICI Securities Limited", "INE763G01038", 5.0, "Finance", 1, 0, 0.1),
        ("IOC", "Indian Oil Corporation Limited", "INE242A01010", 10.0, "Refineries/Oil-Gas", 1, 0, 0.01),
        ("IREDA", "Indian Renewable Energy Development Agency Ltd", "INE202E01016", 10.0, "Finance", 1, 0, 0.01),
        ("INFY", "Infosys Ltd", "INE009A01021", 5.0, "IT", 1, 0, 0.1),
        ("IRB", "IRB Infrastructure Developers Limited", "INE821I01022", 1.0, "Infrastructure", 1, 0, 0.01),
        ("ITC", "ITC Limited", "INE154A01025", 1.0, "FMCG", 1, 0, 0.05),
        ("JUSTDIAL", "Just Dial Limited", "INE599M01018", 10.0, "E-Commerce/App based Aggregator", 1, 0, 0.05),
        ("KOTAKBANK", "Kotak Mahindra Bank Ltd", "INE237A01028", 5.0, "Banking", 1, 0,0.1),
        ("KPIGREEN", "KPI Green Energy Limited", "INE542W01017", 5.0, "Power", 1, 0, 0.05),
        ("KSOLVES", "Ksolves India Limited", "INE0D6I01023", 5.0, "IT", 1, 0, 0.1),
        ("LT", "Larsen & Toubro Limited", "INE018A01030", 2.0, "Infrastructure", 1, 0, 0.1),
        ("NDTV", "New Delhi Television Limited", "INE155G01029", 4.0, "Media", 1, 0, 0.01),
        ("NIFTYBEES", "Nippon India ETF Nifty 50 Bees", "INF204KB14I2", 1.0, "ETF", 1, 1, 0.01),
        ("ONGC", "Oil And Natural Gas Corporation", "INE213A01029", 5.0, "Refineries/Oil-Gas", 1, 0, 0.01),
        ("TATAPOWER", "Tata Power Company Limited", "INE245A01021", 1.0, "Power/Generation/Distribution", 1, 0, 0.05),
        ("TATASTEEL", "Tata Steel Limited", "INE081A01020", 1.0, "Steel", 1, 0, 0.01),
        ("TECHM", "Tech Mahindra Limited", "INE669C01036", 5.0, "IT", 1, 0, 0.1),
        ("UNIONBANK", "Union Bank Of India", "INE692A01016", 10.0, "Banking", 1, 0, 0.01),
        ("WAAREE", "Waaree Energies Limited", "INE377N01017", 10.0, "Capital Goods", 1, 0, 0.1),
        ("WIPRO", "Wipro Ltd", "INE075A01022", 2.0, "IT", 1, 0,0.01),
    ]

    added_count = 0
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        for code, name, isin, fv, sector, active, isetf, tick in company_data:
            cur.execute("SELECT 1 FROM stocks WHERE stk_code = ? OR isin = ?", (code, isin))
            if cur.fetchone():
                print(f"⚠️ Skipping {name}: already exists.")
                continue

            cur.execute("""
                INSERT INTO stocks (stk_code, company_name, isin, face_value, sector, is_active, is_etf, tick)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, name, isin, fv, sector, active, isetf, tick))
            added_count += 1
            print(f"{added_count} stocks added so far... \n✅ Added {name}.")
            time.sleep(0.2)

        conn.commit()
        print(f"\n🎉 Successfully added {added_count} stocks to the database.")
        get_single_key("Press any key to continue...")
    except Exception as e:
        print("❌ Error inserting data:", e)
    finally:
        conn.close()

    print(f"\n🎉 All done. {added_count} new stocks added to the database.")
    return




def manage_report_backups(reports_dir, backup_dir, pattern):
    """
    Manages report backups by keeping only the three most recent backup files.

    Args:
        reports_dir: Directory containing the reports
        backup_dir: Directory to store backups
        pattern: File pattern to match for backups (e.g., "transactions_report_*.bak")
    """
    # Create backup directory if it doesn't exist
    os.makedirs(backup_dir, exist_ok=True)

    # Get all backup files and sort by creation time (newest first)
    backup_files = glob.glob(os.path.join(backup_dir, pattern))
    backup_files.sort(key=os.path.getctime, reverse=True)

    # Remove all but the three most recent backups
    for old_backup in backup_files[3:]:
        try:
            os.remove(old_backup)
        except OSError as e:
            print(f"Error removing old backup {old_backup}: {e}")




# Function to get valid date input (dd/mm/yyyy)
def get_valid_date(message = "Enter the date", default_value=None, dummy = None):
    while True:
        # Format the prompt to show both default value and format hint clearly
        if default_value:
            display_message = f"{message} (dd/mm/yyyy) [{default_value}]: "
        else:
            display_message = f"{message} (dd/mm/yyyy): "

        date_str = input(display_message).strip()

        # If empty input and default value exists, use default
        if not date_str and default_value:
            return default_value

        try:
            # If the input is already in YYYY-MM-DD format, validate and return as is
            if date_str.count('-') == 2:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                return date_str
            # Otherwise, expect dd/mm/yyyy format
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            return date_obj.strftime("%Y-%m-%d")  # Return date in YYYY-MM-DD format
        except ValueError:
            print("❌ Invalid date format. Please use dd/mm/yyyy.")

# Function to get valid numerical input (positive float)
def get_valid_number(prompt,default_value=None, integer=False):
    while True:
        # Format the prompt to show both default value and format hint clearly
        if default_value is not None:
            if integer:
                display_message = f"{prompt} [{default_value}]: "
            else:
                display_message = f"{prompt} [{default_value:.4f}]: "
        else:
            display_message = f"{prompt}: "

        value = input(display_message).strip()

        # If empty input and default value exists, use default
        if not value and default_value == 0:
            return default_value
        elif not value and default_value:
            return default_value
        try:
            value = float(value) if not integer else int(value)
            return value
        except ValueError as e:
            print(f"❌ Invalid input. {e}. Please try again.")

def get_valid_string(prompt,default_value=None, dummy = None):
    while True:
        if default_value:
            display_message = f"{prompt} [{default_value}]: "
        else:
            display_message = f"{prompt}: "
        value = input(display_message).strip()
        if not value and default_value:
            return default_value
        return value



def clear_screen():
    """Clears the terminal screen (Windows or Unix)."""
    os.system("cls" if os.name == "nt" else "clear")

def get_single_key(message=None, valid_keys=None):
    """
    Input: message = None, valid_keys = ['Y', 'N'] (Example)
    Wait for a single valid keypress and return its name.
    If valid_keys is provided, repeat until one of them is pressed.
    Message is displayed before prompting.
    The prompt is cleared after key is pressed.
    """
    special_keys = {
        b'H': 'UP', b'P': 'DOWN', b'K': 'LEFT', b'M': 'RIGHT',
        b';': 'F1', b'<': 'F2', b'=': 'F3', b'>': 'F4',
        b'?': 'F5', b'@': 'F6', b'A': 'F7', b'B': 'F8',
        b'C': 'F9', b'D': 'F10', b'\x85': 'F11', b'\x86': 'F12'
    }

    def decode_key(key, is_extended):
        if is_extended:
            return special_keys.get(key, f'SPECIAL_{key.hex()}')
        if key == b'\r':
            return 'ENTER'
        if key == b'\x1b':
            return 'ESC'
        try:
            return key.decode().upper() if key.isalpha() else key.decode()
        except UnicodeDecodeError:
            return f'UNKNOWN_{key.hex()}'

    if message:
        print(message, end='', flush=True)

    while True:
        if msvcrt.kbhit():
            key = msvcrt.getch()
            is_extended = key in (b'\x00', b'\xe0')
            key = msvcrt.getch() if is_extended else key
            key_name = decode_key(key, is_extended)

            while msvcrt.kbhit():
                msvcrt.getch()

            if (valid_keys is None) or (key_name in valid_keys):
                print()
                return key_name

def beep(duration=1, beep_at=1):

    start_time = time.time()

    while True:
        elapsed = time.time() - start_time

        if int(elapsed) == beep_at:
            winsound.PlaySound("SystemQuestion", winsound.SND_ALIAS)  # ASCII Bell character; works on most terminals

        if elapsed >= duration:
            break

        time.sleep(0.1)  # small sleep to avoid busy waiting
    return True


def show_menu(menu_items, selected_index, begin_message="Menu", end_message="Select Option", highlight_hotkeys=True):
    """
    Displays a keyboard-navigable menu with optional hotkey highlighting and selection arrow.

    Parameters:
        menu_items (list): A list of (label, hotkey, func_name) tuples.
        selected_index (int): The index of the currently selected item.
        begin_message (str): Message to display before menu items.
        end_message (str): Message to display after menu items.
        highlight_hotkeys (bool): Whether to color the hotkey in each item.
    """
    clear_screen()
    print(begin_message, end='\n\n', flush=True)

    for index, (label, hotkey, _) in enumerate(menu_items):
        prefix = "➤ " if index == selected_index else "  "
        if highlight_hotkeys:
            colored_hotkey = f"\033[38;5;39m{hotkey}\033[0m"  # Bright blue hotkey
        else:
            colored_hotkey = hotkey
        menu_text = f"[{colored_hotkey}] {label}"
        if index == selected_index:
            # Yellow text on indigo background for selected item
            highlighted = f"\033[38;5;226;48;5;57m{prefix}{menu_text}\033[0m"
            print(highlighted)
        else:
            print(prefix + menu_text)

    print(f"\n{end_message}", end='', flush=True)


def operate_menu(menu_items, begin_message="Menu", end_message="Select Option"):
    """
    Operates a keyboard-driven menu using arrow keys, hotkeys, Enter, and Escape.
    Returns the function name associated with the selected menu item, or None to cancel.
    """
    selected_index = 0

    # Extract valid keys from menu items (arrow keys, Enter, ESC, and hotkeys)
    valid_keys = ['UP', 'DOWN', 'ENTER', 'ESC']
    valid_keys += [hotkey.upper() for _, hotkey, _ in menu_items]
    valid_keys += [hotkey.lower() for _, hotkey, _ in menu_items]

    while True:
        show_menu(menu_items, selected_index, begin_message, end_message)
        key = get_single_key(None, valid_keys)

        if key == 'UP':
            selected_index = (selected_index - 1) % len(menu_items)
        elif key == 'DOWN':
            selected_index = (selected_index + 1) % len(menu_items)
        elif key == 'ESC':
            clear_screen()
            return None
        elif key == 'ENTER':
            label, hotkey, func_name = menu_items[selected_index]
            clear_screen()
            return func_name
        else:
            for i, (_, hotkey, func_name) in enumerate(menu_items):
                if key.upper() == hotkey.upper():
                    clear_screen()
                    return func_name




def view_transaction_details(output_to_file=True):
    """
    Creates a detailed transaction report with all related information from all tables.

    Features:
    - One transaction per row for easy comparison
    - All related details from stocks and contracts tables
    - Automatic file naming with timestamp
    - Backup of previous reports (keeps 3 most recent)
    - Both screen and file output options
    """
    try:
        selected_ids = select_more_trans()
        if not selected_ids:
            print("No transactions selected.")
            return

        # Create reports directory in finprog/reports
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
        backup_dir = os.path.join(reports_dir, "backup")
        os.makedirs(reports_dir, exist_ok=True)
        os.makedirs(backup_dir, exist_ok=True)

        # Prepare output file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(reports_dir, "transactions_report.txt")

        # Backup existing report if any
        if os.path.exists(report_file):
            backup_file = os.path.join(backup_dir, f"transactions_report_{timestamp}.bak")
            shutil.copy2(report_file, backup_file)
            # Manage backups to keep only three most recent
            manage_report_backups(reports_dir, backup_dir, "transactions_report_*.bak")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Define column mappings (short_name: (full_name, alignment))
        # alignment: 'l' for left, 'r' for right, 'c' for center
        columns = {
            #'Sr.No': ('Sr. No', 'r'),
            'ID': ('Transaction ID', 'r'),
            'Date': ('Trade Date', 'c'),
            'Type': ('Trade Type', 'c'),
            'Stock': ('Stock Code', 'l'),
            'Company': ('Company Name', 'l'),
            'Qty': ('Quantity', 'r'),
            'PrcUnit': ('Price/Unit', 'r'),
            'TotBrk': ('Total Brok', 'r'),
            'SellChg': ('Sell Chrg', 'r'),
            'TotTax': ('Total Tax', 'r'),
            'TotChg': ('Total Chrg', 'r'),
            'NetAmt': ('Net Amount', 'r'),
            'Err': ('Error', 'r')
        }

        # Execute query and fetch data
        query = """
            SELECT
                CAST(t.id_trd AS INTEGER) as id_trd,
                t.trd_dt,
                t.trade_type_trd,
                s.stk_code,
                s.company_name,
                CAST(t.qty_trd AS INTEGER) as qty,
                t.wap_unit_trd,
                t.brok_lot_trd,
                t.sell_chrg_trd,
                t.tax_trd,
                t.chrg_trd,
                t.net_amt_trd,
                t.error
            FROM transactions t
            JOIN stocks s ON t.id_stk = s.id_stk
            JOIN contracts c ON t.cont_no = c.cont_no
            WHERE t.id_trd IN ({})
            ORDER BY t.trd_dt DESC, t.id_trd DESC
        """.format(','.join('?' * len(selected_ids)))
        cursor.execute(query, selected_ids)
        transactions = cursor.fetchall()
        #return

        def write_output(content, file=None):
            print(content)
            if file:
                file.write(content + "\n")

        with (open(report_file, 'w', encoding='utf-8') if output_to_file else nullcontext()) as f:
            # First calculate raw widths from data
            data_widths = {col: 0 for col in columns.keys()}
            for trans in transactions:
                for idx, (col, _) in enumerate(columns.items()):
                    val = trans[idx] if trans[idx] is not None else ''
                    if isinstance(val, (int, float)):
                        if col in ['Sr.No', 'ID']:
                            formatted = f"{int(val)}"
                        elif col == 'Qty':
                            formatted = f"{int(val):,}"
                        else:
                            formatted = f"{float(val):,.2f}"
                    else:
                        formatted = str(val).strip()
                    data_widths[col] = max(data_widths[col], len(formatted))

            # Take max of data width and header width, add 3 for padding
            col_widths = {
                col: max(data_widths[col], len(col)) + 3
                for col in columns.keys()
            }

            # Simple formatting function
            def format_value(val, width, align):
                if val is None:
                    val = ""
                elif isinstance(val, (int, float)):
                    if isinstance(val, int):
                        val = f"{val}"
                    else:
                        val = f"{val:.2f}"
                else:
                    val = str(val).strip()

                if align == 'r':
                    return f"{val:>{width}}"
                elif align == 'l':
                    return f"{val:<{width}}"
                else:
                    return f"{val:^{width}}"

            # Create minimal separator format
            format_str = "|".join(f"{{:{col_widths[col]}}}" for col in columns.keys())

            # Create header format string with center alignment for all headers
            header_format_str = "|".join(f"{{:^{col_widths[col]}}}" for col in columns.keys())

            # Write headers (centered)
            header_line = header_format_str.format(*(col for col in columns.keys()))
            write_output(header_line, f)
            write_output("-" * len(header_line), f)

            # Write data (with original alignment)
            for trans in transactions:
                formatted_values = []
                for idx, (col, (_, align)) in enumerate(columns.items()):
                    val = trans[idx]
                    if isinstance(val, (int, float)):
                        if col in ['Sr.No', 'ID']:
                            formatted = f"{int(val)}"
                        elif col == 'Qty':
                            formatted = f"{int(val):,}"
                        else:
                            formatted = f"{float(val):,.2f}"
                    else:
                        formatted = str(val if val is not None else "").strip()
                    formatted_values.append(format_value(formatted, col_widths[col], align))
                write_output(format_str.format(*formatted_values), f)

            write_output("-" * len(header_line), f)

            # Write summary for multiple transactions
            if len(transactions) > 1:
                write_output("\nSUMMARY", f)
                write_output("-" * 180, f)

                totals = {
                    'qty': sum(t[5] for t in transactions),
                    'price': sum(t[6] for t in transactions),
                    'charges': sum(t[10] for t in transactions),
                    'taxes': sum(t[9] for t in transactions),
                    'net': sum(t[11] for t in transactions)
                }

                summary = (
                    f"Total Transactions: {len(transactions)}\n"
                    f"Total Quantity: {totals['qty']:,}\n"
                    f"Total Price: ₹{totals['price']:,.2f}\n"
                    f"Total Charges: ₹{totals['charges']:,.2f}\n"
                    f"Total Taxes: ₹{totals['taxes']:,.2f}\n"
                    f"Total Net Amount: ₹{totals['net']:,.2f}"
                )
                write_output(summary, f)

            # Write column name mappings
            write_output("\nColumn Name Mappings:", f)
            write_output("-" * 50, f)
            for short_name, (full_name, _) in columns.items():
                write_output(f"{short_name:<10} : {full_name}", f)

            if output_to_file:
                print(f"\nReport has been saved to: {report_file}")
                print(f"Previous report backed up to: {backup_file}")

    except Exception as e:
        print(f"Error generating transaction report: {e}")

    finally:
        if 'conn' in locals():
            conn.close()
        get_single_key("\nPress any key to continue...")
        clear_screen()

# def manage_report_backups(reports_dir, backup_dir, pattern):
#     """
#     Manages report backups by keeping only the three most recent backup files.

#     Args:
#         reports_dir: Directory containing the reports
#         backup_dir: Directory to store backups
#         pattern: File pattern to match for backups (e.g., "transactions_report_*.bak")
#     """
#     # Create backup directory if it doesn't exist
#     os.makedirs(backup_dir, exist_ok=True)

#     # Get all backup files and sort by creation time (newest first)
#     backup_files = glob.glob(os.path.join(backup_dir, pattern))
#     backup_files.sort(key=os.path.getctime, reverse=True)

#     # Remove all but the three most recent backups
#     for old_backup in backup_files[3:]:
#         try:
#             os.remove(old_backup)
#         except OSError as e:
#             print(f"Error removing old backup {old_backup}: {e}")



def print_table_data(table_name, columns=None, where_clause=None, output_to_file=True):
    """
    Print data from a specified table in a formatted manner.

    Args:
        table_name (str): Name of the table to query.
        columns (dict): Dictionary of column_name: Heading Title.
        where_clause (str): Optional WHERE clause for filtering results.
        output_to_file (bool): Whether to write output to a file.
    """

    if columns is None or not isinstance(columns, dict):
        raise ValueError("You must pass a dictionary for columns (e.g., {'col': 'Heading'})")

    # Setup directories
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
    backup_dir = os.path.join(reports_dir, "backup")
    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(reports_dir, f"{table_name}_report.txt")
    backup_file = None

    # Backup previous report
    if output_to_file and os.path.exists(report_file):
        backup_file = os.path.join(backup_dir, f"{table_name}_report_{timestamp}.bak")
        shutil.copy2(report_file, backup_file)
        manage_report_backups(reports_dir, backup_dir, f"{table_name}_report_*.bak")

    # Fetch data
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    column_names = list(columns.keys())
    sql_query = f"SELECT {', '.join(column_names)} FROM {table_name}"
    if where_clause:
        sql_query += f" WHERE {where_clause}"

    cursor.execute(sql_query)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print(f"No data found in table '{table_name}'.")
        return

    # Compute column widths
    col_lengths = {}

    for i, col in enumerate(column_names):
        max_len = len(columns[col])  # Start with header title length
        for row in rows:
            value = row[i]
            if isinstance(value, float):
                formatted = f"{value:,.2f}"
            elif isinstance(value, int):
                formatted = f"{value}"
            else:
                formatted = str(value)
            max_len = max(max_len, len(formatted))
        col_lengths[col] = max_len + 2  # Add padding

    # ✅ This must be outside the for-loop
    col_lengths = {"sr_no": 6, **col_lengths}
    total_length = sum(col_lengths.values()) + 3 * (len(col_lengths) - 1)

    lines = []

    # Header block
    report_title = f"Report for table: {table_name}"
    time_line = f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    lines.append(report_title.center(total_length))
    lines.append(time_line.center(total_length))
    lines.append("=" * total_length)

    # Column headers
    sample_row = rows[0]  # Use first row for type detection

    header_row = f"{'Sr. No.':>{col_lengths['sr_no']}}"
    for col in column_names:
        sample_value = sample_row[column_names.index(col)]
        align_right = isinstance(sample_value, (int, float))
        fmt = f"{{:{col_lengths[col]}}}" if not align_right else f"{{:>{col_lengths[col]}}}"
        header_row += " | " + fmt.format(columns[col])
    lines.append(header_row)
    lines.append("-" * total_length)

    # Data rows
    for idx, row in enumerate(rows, 1):
        row_str = f"{idx:>{col_lengths['sr_no']}}"
        for i, col in enumerate(column_names):
            value = row[i]
            if isinstance(value, float):
                formatted = f"{value:,.2f}"
            elif isinstance(value, int):
                formatted = f"{value}"
            else:
                formatted = str(value)

            align_right = isinstance(value, (int, float))
            fmt = f"{{:<{col_lengths[col]}}}" if not align_right else f"{{:>{col_lengths[col]}}}"
            row_str += " | " + fmt.format(formatted)
        lines.append(row_str)

    # Bottom border
    lines.append("-" * total_length)

    # Write to file and/or screen
    with (open(report_file, 'w', encoding='utf-8') if output_to_file else nullcontext()) as f:
        for line in lines:
            print(line)
            if output_to_file:
                f.write(line + "\n")

    if output_to_file:
        print(f"\nReport has been saved to: {report_file}")
        if backup_file:
            print(f"Previous report backed up to: {backup_file}")

        # Optional: Open the file in default editor (e.g., Notepad on Windows)
        try:
            os.startfile(report_file)  # Windows only
        except AttributeError:
            # Non-Windows fallback (optional)
            pass
    get_single_key("\nPress any key to continue...")






def select_stock_id():
    """
    Displays existing stocks in pages of 5 items and allows selection of one stock.
    Input: one serial number.
    Returns: List of selected stock IDs or None if no selection made

    Navigation:
    - Press Enter to see next page
    - Enter serial number to select one stock
    - Returns None when reaching end of list without selection
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get total count of stocks
        cursor.execute("SELECT COUNT(*) FROM stocks")
        total_records = cursor.fetchone()[0]

        if total_records == 0:
            print("No stocks found in the database.")
            return None

        offset = 0
        page_size = 5

        while offset < total_records:
            clear_screen()

            # Fetch 5 records with stock code
            cursor.execute("""
                SELECT
                    s.id_stk,
                    s.stk_code,
                    s.company_name,
                    s.isin
                FROM stocks s
                ORDER BY s.stk_code ASC
                LIMIT ? OFFSET ?
            """, (page_size, offset))

            records = cursor.fetchall()
            sr_no_map = {}  # Map serial numbers to stock IDs
            length = {}
            length['sr_no'] = 6
            length['id_stk'] = 4
            length['stk_code'] = max(len(r[1]) for r in records)+2
            length['company_name'] = max(len(r[2]) for r in records)+2
            length['isin'] = max(len(r[3]) for r in records)+2
            total_length = sum(length.values()) + 6
            print("\nStock List:")
            print("=" * total_length)
            print(f"{'    Sr.':^{length['sr_no']}}{'Id':^{length['id_stk']}}   {'Stock':^{length['stk_code']}} {'Company':^{length['company_name']}} {'ISIN':<{length['isin']}}")
            print("-" * total_length)


            for idx, (id_stk, stk_code, company, isin) in enumerate(records, 1):
                sr_no = offset + idx
                sr_no_map[sr_no] = id_stk
                print(f"{sr_no:>{length['sr_no']}} {id_stk:>{length['id_stk']}}   {stk_code:<{length['stk_code']}} {company:<{length['company_name']}} {isin:>{length['isin']}}")

            print("-" * total_length)
            remaining = total_records - (offset + len(records))
            if remaining > 0:
                print(f"\n{remaining} more stocks available.")
                prompt = "Enter serial number to select, or press Enter for more: "
            else:
                print("\nEnd of stocks list.")
                prompt = "Enter serial number to select, or press Enter to exit: "

            choice = input(prompt).strip()

            if not choice:  # Enter key pressed
                if remaining > 0:
                    offset += page_size
                    continue
                else:
                    return None

            try:
                # Parse input and remove any whitespace
                selected_number = int(choice.strip())


                if selected_number in sr_no_map:
                    return sr_no_map[selected_number]
                else:
                    print(f"Invalid serial number: {selected_number}")
                    print("Press any key to continue...")
                    get_single_key()
                    continue


            except ValueError:
                print("Invalid input. Please enter numbers separated by commas.")
                print("Press any key to continue...")
                get_single_key()

        return None  # Return None if no selection was made

    except Exception as e:
        print(f"Error listing transactions: {e}")
        get_single_key("Press any key to continue...")
        return None

    finally:
        if 'conn' in locals():
            conn.close()





def select_stock_id():
    """
    Displays existing stocks in pages of 5 items and allows selection of one stock.
    Input: one serial number.
    Returns: List of selected stock IDs or None if no selection made

    Navigation:
    - Press Enter to see next page
    - Enter serial number to select one stock
    - Returns None when reaching end of list without selection
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get total count of stocks
        cursor.execute("SELECT COUNT(*) FROM stocks")
        total_records = cursor.fetchone()[0]

        if total_records == 0:
            print("No stocks found in the database.")
            return None

        offset = 0
        page_size = 5

        while offset < total_records:
            clear_screen()

            # Fetch 5 records with stock code
            cursor.execute("""
                SELECT
                    s.id_stk,
                    s.stk_code,
                    s.company_name,
                    s.isin
                FROM stocks s
                ORDER BY s.stk_code ASC
                LIMIT ? OFFSET ?
            """, (page_size, offset))

            records = cursor.fetchall()
            sr_no_map = {}  # Map serial numbers to stock IDs
            length = {}
            length['sr_no'] = 6
            length['id_stk'] = 4
            length['stk_code'] = max(len(r[1]) for r in records)+2
            length['company_name'] = max(len(r[2]) for r in records)+2
            length['isin'] = max(len(r[3]) for r in records)+2
            total_length = sum(length.values()) + 6
            print("\nStock List:")
            print("=" * total_length)
            print(f"{'    Sr.':^{length['sr_no']}}{'Id':^{length['id_stk']}}   {'Stock':^{length['stk_code']}} {'Company':^{length['company_name']}} {'ISIN':<{length['isin']}}")
            print("-" * total_length)


            for idx, (id_stk, stk_code, company, isin) in enumerate(records, 1):
                sr_no = offset + idx
                sr_no_map[sr_no] = id_stk
                print(f"{sr_no:>{length['sr_no']}} {id_stk:>{length['id_stk']}}   {stk_code:<{length['stk_code']}} {company:<{length['company_name']}} {isin:>{length['isin']}}")

            print("-" * total_length)
            remaining = total_records - (offset + len(records))
            if remaining > 0:
                print(f"\n{remaining} more stocks available.")
                prompt = "Enter serial number to select, or press Enter for more: "
            else:
                print("\nEnd of stocks list.")
                prompt = "Enter serial number to select, or press Enter to exit: "

            choice = input(prompt).strip()

            if not choice:  # Enter key pressed
                if remaining > 0:
                    offset += page_size
                    continue
                else:
                    return None

            try:
                # Parse input and remove any whitespace
                selected_number = int(choice.strip())


                if selected_number in sr_no_map:
                    return sr_no_map[selected_number]
                else:
                    print(f"Invalid serial number: {selected_number}")
                    print("Press any key to continue...")
                    get_single_key()
                    continue


            except ValueError:
                print("Invalid input. Please enter numbers separated by commas.")
                print("Press any key to continue...")
                get_single_key()

        return None  # Return None if no selection was made

    except Exception as e:
        print(f"Error listing transactions: {e}")
        get_single_key("Press any key to continue...")
        return None

    finally:
        if 'conn' in locals():
            conn.close()


def select_trade_id():
    """Select a trade from the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT t.id_trd, s.company_name, t.cont_no, t.trd_dt, t.qty_trd, t.trade_type_trd
            FROM transactions t
            JOIN stocks s ON t.id_stk = s.id_stk
            ORDER BY t.trd_dt DESC, s.company_name
        """)
        trades = cursor.fetchall()

        if not trades:
            print("No trades found in the database.")
            return None

        print("\nAvailable Trades:")
        print("ID   | Company Name | Contract No | Trade Date | Quantity | Type")
        print("-" * 80)
        for trade in trades:
            print(f"{trade[0]:<5}| {trade[1]:<12}| {trade[2]:<11}| {trade[3]:<10}| {trade[4]:<8}| {trade[5]}")

        while True:
            try:
                trade_id = input("\nEnter Trade ID (or 0 to cancel): ")
                if not trade_id.strip():
                    continue

                trade_id = int(trade_id)
                if trade_id == 0:
                    return None

                cursor.execute("SELECT id_trd FROM transactions WHERE id_trd = ?", (trade_id,))
                if cursor.fetchone():
                    return trade_id
                else:
                    print("Invalid Trade ID. Please try again.")
            except ValueError:
                print("Please enter a valid number.")

    except Exception as e:
        print(f"Error selecting trade: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()


def compute_fields():
    """
    Computes and displays various financial fields for a given stock.

    Features:
    - Calculates total charges and taxes
    - Determines tax percentage based on charges and taxes
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(" SELECT * FROM view_gross_summary" )
        overall = cursor.fetchone()
        cursor.execute(" SELECT SUM(stt_cont) FROM contracts")
        gross_stt = cursor.fetchone()[0]
        if overall:
            total_invest = overall[0]
            total_sold = overall[1]
            current_invest = overall[2]
            brokerage_total = overall[3]
            total_tax = overall[4]
            total_charges = overall[5]
            print(f"Total Invested     : {total_invest:,.2f}")
            print(f"Total Sold         : {total_sold:,.2f}")
            print(f"Current Invested   : {current_invest:,.2f}")
            print(f"Brokerage Total    : {brokerage_total:,.2f}")
            print(f"Total Tax          : {total_tax:,.2f}")
            print(f"Total Charges      : {total_charges:,.2f}")
            tax_pc = 100 * total_tax / total_charges
            print(f"Tax Percentage     : {tax_pc:.2f}%")
            print(f"Total STT paid     : {gross_stt:,.2f}")
            stt_pc = 100 * gross_stt/total_charges
            print(f"STT Percentage     : {stt_pc:.2f}%")
            get_single_key("Press any key to continue...")

    except Exception as e:
        print(f"Error in compute_fields: {e}")
        get_single_key("Press any key to continue...")

    finally:
        if 'conn' in locals():
            conn.close()


def pc(company):
    """Print company header"""
    clear_screen()
    print("-" * 60)
    print(f"Company: {company}")
    print("-" * 60)
    return

def select_trade_id():
    """
    Displays existing trades in pages of 5 items and allows selection of one stock.
    Input: one serial number.
    Returns: List of selected stock IDs or None if no selection made

    Navigation:
    - Press Enter to see next page
    - Enter serial number to select one stock
    - Returns None when reaching end of list without selection
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get total count of stocks
        cursor.execute("SELECT COUNT(*) FROM transactions")
        total_records = cursor.fetchone()[0]

        if total_records == 0:
            print("No trade found in the database.")
            return None

        offset = 0
        page_size = 5

        while offset < total_records:
            clear_screen()

            # Fetch 5 records with stock code
            cursor.execute("""
                SELECT
                    t.id_trd,
                    t.id_stk,
                    t. cont_no,
                    t.trd_dt,
                    t.trade_type_trd,
                    t.qty_trd,
                    t.net_amt_trd,
                    s.company_name
                FROM transactions t
                JOIN stocks s ON t.id_stk = s.id_stk
                ORDER BY s.company_name ASC, t.trd_dt ASC
                LIMIT ? OFFSET ?
            """, (page_size, offset))

            records = cursor.fetchall()

            sr_no_map = {}  # Map serial numbers to stock IDs
            length = {}
            length['sr_no'] = 6
            length['company_name'] = max(25, max(len(r[7]) for r in records)+2)
            length['trd_dt'] = max(len(r[3]) for r in records)+2
            length['trade_type_trd'] = max(len(r[4]) for r in records)+2
            length['qty_trd'] = max(len(str(r[5])) for r in records)+4
            length['net_amt_trd'] = max(len((f"{r[6]:.4f}")) for r in records)+2
            total_length = sum(length.values()) + 6
            print("\nTrade List:")
            print("=" * total_length)
            print(f"{'    Sr.':^{length['sr_no']}}{'Company':^{length['company_name']}}   {'Date':^{length['trd_dt']}} {'B/S':^{length['trade_type_trd']}} {'Qty':<{length['qty_trd']}} {'Amount':<{length['net_amt_trd']}}")
            print("-" * total_length)
            for idx, (id_trd, _, _, trd_dt, trade_type_trd, qty_trd, net_amt_trd, company_name) in enumerate(records, 1):
                sr_no = offset + idx
                sr_no_map[sr_no] = id_trd
                print(f"{sr_no:>{length['sr_no']}} {company_name:<{length['company_name']}}   {trd_dt:<{length['trd_dt']}} {trade_type_trd:^{length['trade_type_trd']}} {qty_trd:<{length['qty_trd']}} {net_amt_trd:>{length['net_amt_trd']}.4f}")
            print("-" * total_length)
            remaining = total_records - (offset + len(records))
            if remaining > 0:
                print(f"\n{remaining} more stocks available.")
                prompt = "Enter serial number to select, or press Enter for more: "
            else:
                print("\nEnd of stocks list.")
                prompt = "Enter serial number to select, or press Enter to exit: "

            choice = input(prompt).strip()

            if not choice:  # Enter key pressed
                if remaining > 0:
                    offset += page_size
                    continue
                else:
                    return None

            try:
                # Parse input and remove any whitespace
                selected_number = int(choice.strip())
                if selected_number in sr_no_map:
                    return sr_no_map[selected_number]
                else:
                    print(f"Invalid serial number: {selected_number}")
                    print("Press any key to continue...")
                    get_single_key()
                    continue

            except ValueError:
                print("Invalid input. Please enter numbers separated by commas.")
                print("Press any key to continue...")
                get_single_key()

        return None  # Return None if no selection was made

    except Exception as e:
        print(f"Error listing transactions: {e}")
        get_single_key("Press any key to continue...")
        return None

    finally:
        if 'conn' in locals():
            conn.close()

def manage_all():
    """
    Allot sold_qty FIFO, (Using migrated_manage_sell)
    Compute: (migrated_manage_sell -> compute_avg_price)
        Current Quantity
        Current Average Price
        Disinvestment Amount
        Realized Profit Loss
    Args:
        None
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # For loop, collect stock_ids.
        cursor.execute("SELECT id_stk FROM stocks ORDER BY id_stk ASC")
        stock_ids = cursor.fetchall()
        # For each stock ID, process the sell trades.
        for stock_id_tuple in stock_ids:
            stock_id = stock_id_tuple[0]
            print(f"\nProcessing stock ID: {stock_id}")
            time.sleep(0.5)

            # Get all sell trades for the stock total their qty_trd.
            cursor.execute("""
                SELECT id_trd, qty_trd
                FROM transactions t
                JOIN stocks s ON t.id_stk = s.id_stk
                WHERE t.id_stk = ? AND trade_type_trd = 'SELL'
            """, (stock_id,))
            sell_trades = cursor.fetchall()
            if not sell_trades:
                total_sold_qty = 0
                print(f"No sell trades found for stock ID {stock_id}.")
            else:
                total_sold_qty = sum(qty_trd  for _, qty_trd in sell_trades)

            # Initialize sold qty of BUY trades to be zero.
            cursor.execute("""
                UPDATE transactions
                SET sold_qty = 0
                WHERE id_stk = ? AND trade_type_trd = 'BUY'
            """, (stock_id,))
            conn.commit()
            # For stock ID distribute sold qty.
            manage_sell(stock_id, total_sold_qty)
            print(f"Stock id {stock_id} processed successfully.")
            time.sleep(0.2)
        print("\nAll sold qty allotted FIFO successfully.")
        print("Average price also computed.")
        conn.commit()


    except Exception as e:
        print(f"Error managing stocks: {e}")

    finally:
        if 'conn' in locals():
            conn.close()
        get_single_key("\nPress any key to continue...")
        return




# def print_table_data(table_name, columns=None, where_clause=None, output_file=None):
#     """
#     Print data from a specified table in a formatted manner.

#     Args:
#         table_name (str): Name of the table to query.
#         columns (dict): Dictionary of column_name: Heading Title.
#         where_clause (str): Optional WHERE clause for filtering results.
#         output_file (str): Optional filename to also write output. Example: "file_name.txt"
#     """


#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()

#     if columns is None or not isinstance(columns, dict):
#         raise ValueError("You must pass a dictionary for columns (e.g., {'col': 'Heading'})")

#     column_names = list(columns.keys())
#     #column_titles = list(columns.values())

#     sql_query = f"SELECT {', '.join(column_names)} FROM {table_name}"
#     if where_clause:
#         sql_query += f" WHERE {where_clause}"

#     cursor.execute(sql_query)
#     rows = cursor.fetchall()

#     if not rows:
#         print(f"No data found in table '{table_name}'.")
#         conn.close()
#         return

#     # Compute column widths
#     col_lengths = {}
#     for i, col in enumerate(column_names):
#         max_data_len = max(len(str(row[i])) for row in rows)
#         col_lengths[col] = max(max_data_len, len(columns[col])) + 2  # Padding

#     # Add Sr. No. column
#     col_lengths = {"sr_no": 6, **col_lengths}  # Fixed width for Sr. No.
#     total_length = sum(col_lengths.values()) + 3 * (len(col_lengths) - 1)

#     lines = []

#     # Top border
#     lines.append("=" * total_length)

#     # Header row
#     header_row = f"{'Sr. No.':>{col_lengths['sr_no']}}"
#     for col in column_names:
#         header_row += " | " + f"{columns[col]:<{col_lengths[col]}}"
#     lines.append(header_row)

#     # Underline
#     lines.append("-" * total_length)

#     # Data rows
#     for idx, row in enumerate(rows, 1):
#         row_str = f"{idx:>{col_lengths['sr_no']}}"
#         for i, col in enumerate(column_names):
#             row_str += " | " + f"{str(row[i]):<{col_lengths[col]}}"
#         lines.append(row_str)

#     # Bottom border
#     lines.append("-" * total_length)

#     # Output to screen and file if specified
#     for line in lines:
#         print(line)
#         if output_file:
#             os.makedirs("reports", exist_ok=True)
#             with open(f"reports/{output_file}", "a", encoding="utf-8") as f:
#                 f.write(line + "\n")

#     get_single_key("\nPress any key to continue...")
#     conn.close()

def manage_sell(stock_id, current_sold_qty):
    """
    Manage selling transactions for a specific stock.
    Allotment of sold_qty is done on FIFO basis.

    Args:
        stock_id: ID of the stock to manage
        current_sold_qty: Current quantity sold
        Adds the sold_qty starting from earliest possible
        buy trade on fifo basis
        returns the remaining quantity to be sold
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id_trd, trd_dt, qty_trd, net_amt_trd,sold_qty,
            s.company_name
            FROM transactions t
            JOIN stocks s ON t.id_stk = s.id_stk
            WHERE t.id_stk = ? AND trade_type_trd = 'BUY'
            ORDER BY trd_dt ASC
        """, (stock_id,))
        buy_trades = cursor.fetchall()
        if not buy_trades:
            print(f"No buy trades found for stock ID {stock_id}.")
            return

        share_available = sum((buy_trades[i][2] - buy_trades[i][4]) for i in range(len(buy_trades)))
        #print(f"Total shares available for stock ID {stock_id}: {share_available}")

        # If sell is > available shares, produce error
        if current_sold_qty > share_available:
            print(f"Error: Cannot sell {current_sold_qty} shares. Only {share_available} shares available.")
            get_single_key("Press any key to continue...")
            return
        for trade in (enumerate(buy_trades)):
            # Check if we can sell from this trade
            if current_sold_qty <= (trade[1][2] - trade[1][4]):
                cursor.execute("""
                    UPDATE transactions
                    SET sold_qty = sold_qty + ?
                    WHERE id_trd = ?
                """, (current_sold_qty, trade[1][0]))
                print(f"Sold {current_sold_qty} shares from trade ID {trade[1][0]}")
                time.sleep(0.2)
                current_sold_qty = 0  # All shares sold
            else:
                current_sold_qty -= (trade[1][2] - trade[1][4])  # Subtract already sold shares
                cursor.execute("""
                    UPDATE transactions
                    SET sold_qty = qty_trd
                    WHERE id_trd = ?
                """, (trade[1][0],))
                print(f"Sold {(trade[1][2] - trade[1][4])} shares from trade ID {trade[1][0]}")
                time.sleep(0.2)
                #print(f"Sell {trade[1][2] - trade[1][4]} shares from trade ID {trade[1][0]} dated {trade[1][1]} for {trade[1][5]}")

            if current_sold_qty == 0:
                conn.commit()
                print("All sold quantity updated.")
                time.sleep(0.2)
                break
        #Print the transactions
        list_trades(stock_id, ask = False)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
            print("conn closed.")
    compute_avg_price(stock_id)
    get_single_key("\nPress any key to continue...")
    return


def compute_avg_price(stock_id):
    """
    Compute the average price of a stock based on its trades.
    Compute Current Average Price,
            Disinvestment Amount,
            Realized Profit Loss Amount

    Args:
        stock_id: ID of the stock to compute average price for
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get all buy trades for the stock
        cursor.execute("""
            SELECT net_amt_trd, qty_trd, sold_qty FROM transactions
            WHERE id_stk = ? AND trade_type_trd = 'BUY'
        """, (stock_id,))
        trades = cursor.fetchall()

        if not trades:
            print(f"No buy trades found for stock ID {stock_id}.")
            return

        withdrawn_amt = sum((net_amt_trd/qty_trd) * sold_qty for net_amt_trd, qty_trd, sold_qty in trades)
        print(f"Total amount recovered from sold shares: {withdrawn_amt:.4f}")

        total_current_invest = sum((net_amt_trd/qty_trd) * (qty_trd - sold_qty) for net_amt_trd, qty_trd, sold_qty in trades)
        total_current_qty = sum((qty_trd - sold_qty) for _, qty_trd, sold_qty in trades)

        if total_current_qty == 0:
            print("No quantity available to compute average price.")
            avg_price = 0.0
        else:
            avg_price = total_current_invest / total_current_qty
            print(f"Average price for stock ID {stock_id}: {avg_price:.4f}")

        cursor.execute("SELECT sum(net_amt_trd) FROM transactions WHERE id_stk = ? AND trade_type_trd = 'SELL'", (stock_id,))
        amts = cursor.fetchone()
        sell_amt = amts[0] if amts and amts[0] is not None else 0.0
        if sell_amt < withdrawn_amt:
            oh_no = f"There seems to be a loss {sell_amt[0]} is less than disinvestment amount {withdrawn_amt}."
            get_single_key(oh_no)


        cursor.execute("""
            UPDATE stocks
            SET curr_avg_price = ?, disinvestment_amt = ?,
            rpnl_amt = sell_amt - ?
            WHERE id_stk = ?
        """, (avg_price, withdrawn_amt, withdrawn_amt, stock_id))
        conn.commit()

    except Exception as e:
        print(f"Error computing average price: {e}")

    finally:
        if 'conn' in locals():
            conn.close()
    print("Average, disinvestment and rpnl inserted/updated. \nPress any key to continue...")
    time.sleep(0.2)
    return


def add_company():
    """
    Interactive function to add a new company to the stocks database.

    Validates and processes:
    - Stock code (unique, uppercase)
    - Company name (unique)
    - ISIN (unique, format check)
    - Sector and face value

    Returns: New stock ID if successful, None if cancelled or error
    """
    print("\nAdding a new company to the database.")
    print("-" * 60)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get company details with validation
        while True:
            stk_code = input("Stock Code (e.g., TATASTEEL): ").strip().upper()
            if not stk_code:
                print("Operation cancelled.")
                return None

            # Check if stock code already exists
            cursor.execute("SELECT 1 FROM stocks WHERE stk_code = ?", (stk_code,))
            if cursor.fetchone():
                print(f"Stock code {stk_code} already exists. Please use a different code.")
                continue
            break

        while True:
            company_name = input("Company Name: ").strip()
            if not company_name:
                print("Operation cancelled.")
                return None

            # Check if company name already exists
            cursor.execute("SELECT 1 FROM stocks WHERE company_name = ?", (company_name,))
            if cursor.fetchone():
                print(f"Company name {company_name} already exists. Please check and try again.")
                continue
            break

        while True:
            isin = input("ISIN (must start with 'IN' and be 12 characters): ").strip().upper()
            if not isin:
                print("Operation cancelled.")
                return None

            # Validate ISIN format
            if len(isin) != 12 or not isin.startswith('IN'):
                print("Invalid ISIN format. Must be 12 characters and start with 'IN'.")
                continue

            # Check if ISIN already exists
            cursor.execute("SELECT 1 FROM stocks WHERE isin = ?", (isin,))
            if cursor.fetchone():
                print(f"ISIN {isin} already exists. Please check and try again.")
                continue
            break

        sector = input("Sector (optional): ").strip()

        while True:
            try:
                face_value = float(input("Face Value [10.0]: ").strip() or "10.0")
                if face_value < 0:
                    print("Face value cannot be negative.")
                    continue
                break
            except ValueError:
                print("Please enter a valid number for face value.")
        tick = get_valid_number("Tick size ", 0.01)
        is_etf = get_single_key("Is it an ETF? (Y/N): ", ["Y", "N"])
        is_etf = 1 if is_etf.lower() == 'y' else 0
        # Default values
        is_active = 1
        curr_avg_price = 0.0
        buy_qty = 0
        sell_qty = 0
        total_investment_amt = 0.0
        sell_amt = 0.0
        disinvestment_amt = 0.0
        rpnl_amt = 0.0
        urpnl_amt = 0.0
        note_stk = ''

        # Insert the new company
        cursor.execute("""
            INSERT INTO stocks (
                stk_code, company_name, isin, sector, face_value,
                tick, is_active, is_etf, curr_avg_price, buy_qty,
                sell_qty, total_investment_amt,
                sell_amt, disinvestment_amt, rpnl_amt,
                urpnl_amt, note_stk
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            stk_code, company_name, isin, sector, face_value,
            tick, is_active, is_etf, curr_avg_price, buy_qty,
            sell_qty, total_investment_amt,
            sell_amt, disinvestment_amt, rpnl_amt,
            urpnl_amt, note_stk
        ))

        # Get the id of the newly inserted company
        new_id = cursor.lastrowid

        conn.commit()
        print(f"\n✅ Successfully added {company_name} to the database.")
        return new_id

    except Exception as e:
        print(f"Error adding company: {e}")
        if 'conn' in locals():
            conn.rollback()
        return None

    finally:
        if 'conn' in locals():
            conn.close()
        get_single_key("\nPress any key to continue...")



def delete_transactions():
    """
    Delete one or more transactions with proper handling of related contracts.

    Features:
    - Displays comprehensive transaction details for selection
    - Allows multiple transaction selection
    - Automatically handles contract deletion if it becomes empty
    - Confirms before deletion
    - Updates contract totals if other transactions remain
    """
    try:
        # First use select_trans to get the transactions to delete
        selected_id = select_trade_id()
        if not selected_id:
            print("No transactions selected for deletion.")
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get detailed information about selected transactions
        query = """
            SELECT
                s.id_stk,
                t.id_trd,
                t.cont_no,
                s.stk_code,
                s.company_name,
                t.trd_dt,
                t.trade_type_trd,
                t.qty_trd,
                t.price_lot_trd,
                t.net_amt_trd,
                (SELECT COUNT(*) FROM transactions WHERE cont_no = t.cont_no) as trans_count
            FROM transactions t
            JOIN stocks s ON t.id_stk = s.id_stk
            WHERE t.id_trd = ?
            ORDER BY t.trd_dt DESC, t.id_trd DESC
        """

        cursor.execute(query, (selected_id,))
        transactions = cursor.fetchone()

        # Display transactions to be deleted
        print("\nTransaction selected for deletion:")
        print("=" * 100)
        print(f"{'ID':^2} {'Contract':^30} {'Stock':^15} {'Date':^12} "
              f"{'Type':^6} {'Qty':^8} {'Net Amount':^15} {'Count':^2}")
        print("-" * 100)
        (id_stk,id_trd, cont_no, stk_code, company, trd_dt,
             trd_type, qty, price, net_amt, trans_count) = transactions

        print(f"{id_trd:>2} {cont_no:<30} {stk_code:^15} {trd_dt:<12} "
            f"{trd_type:<6} {qty:>8} {net_amt:>15,.2f}, {trans_count:>2}")
        print("-" * 100)

        # Show which contracts will be affected
        print("\nContract Impact Analysis:")
        if trans_count == 1:
            print(f"Contract {cont_no}: Will be deleted (all transactions being deleted)")
        else:
            print(f"Contract {cont_no}: Will be updated ({trans_count - 1} transactions will remain)")


        # Confirm deletion
        print("\nWarning: This operation cannot be undone!")
        confirm = get_single_key("Are you sure you want to delete these transactions? (Y/N): ", ['Y', 'N'])

        if confirm == 'Y':
            try:
                if trd_type == 'SELL':
                    success = delete_sell(id_stk, qty)
                    if not success:
                        print("Error deleting sell transactions. Please check the logs.")
                    return

                # Start transaction
                cursor.execute("BEGIN TRANSACTION")

                # Delete selected transactions
                delete_query = f"DELETE FROM transactions WHERE id_trd = ?"
                cursor.execute(delete_query, (selected_id,))

                # Check if any transactions remain for this contract
                cursor.execute("SELECT COUNT(*) FROM transactions WHERE cont_no = ?", (cont_no,))
                remaining_count = cursor.fetchone()[0]

                if remaining_count == 0:
                    # Delete contract if no transactions remain
                    cursor.execute("DELETE FROM contracts WHERE cont_no = ?", (cont_no,))
                    print(f"\nContract {cont_no} deleted as no transactions remain.")
                else:
                    # Update contract totals if transactions remain
                    update_or_insert_contract(cursor, cont_no, trd_dt)
                    print(f"\nContract {cont_no} updated with remaining transactions.")

                # Commit changes
                conn.commit()
                print(f"\nSuccessfully deleted one transaction(s).")

            except Exception as e:
                conn.rollback()
                print(f"Error during deletion: {e}")
                return
        else:
            print("\nDeletion cancelled.")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if 'conn' in locals():
            conn.close()
        get_single_key("\nPress any key to continue...")
        clear_screen()



def delete_sell(stock_id, current_sold_qty):
    """
    Delete sell transactions for a specific stock.

    Args:
        stock_id: ID of the stock to delete
        current_sold_qty: Current quantity sold
        Deletes the sold_qty starting from earliest possible
        buy trade on fifo basis
        returns the remaining quantity to be sold
    """
    success = False
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id_trd, trd_dt, qty_trd, net_amt_trd, sold_qty,
            s.company_name
            FROM transactions t
            JOIN stocks s ON t.id_stk = s.id_stk
            WHERE t.id_stk = ? AND trade_type_trd = 'BUY'
            ORDER BY trd_dt DESC
        """, (stock_id,))
        all_trades = cursor.fetchall()
        if not all_trades:
            print(f"No trade found for stock ID {stock_id}.")
            return success

        share_sold_figure = sum((all_trades[i][4]) for i in range(len(all_trades)))
        #print(f"Total shares available for stock ID {stock_id}: {share_available}")

        # If sell is > available shares, produce error
        if current_sold_qty > share_sold_figure:
            print(f"Sold quantity not updated. Currently only {share_sold_figure} exist(s).")
            get_single_key("Press any key to continue...")
            return success

        for trade in (enumerate(all_trades)):
            # Check if we can delete from this trade
            if current_sold_qty <= (trade[1][4]):
                cursor.execute("""
                    UPDATE transactions
                    SET sold_qty = sold_qty - ?
                    WHERE id_trd = ?
                """, (current_sold_qty, trade[1][0]))
                current_sold_qty = 0  # All shares deleted
                #trade[1][4] -= current_sold_qty  # Update the sold quantity in the trade

            else:
                current_sold_qty -= (trade[1][4])
                cursor.execute("""
                    UPDATE transactions
                    SET sold_qty = 0
                    WHERE id_trd = ?
                """, (trade[1][0],))
                #trade[1][4] = 0  # Set sold quantity to 0 for this trade
                #print(f"Deleted {trade[1][4]} shares from trade ID {trade[1][0]} dated {trade[1][1]} for {trade[1][5]}")
            if current_sold_qty == 0:
                print("All shares deleted.")
                success = True
                conn.commit()
                break
    except Exception as e:
        print(f"Error: {e}")
        return success
    finally:
        if 'conn' in locals():
            conn.close()
            print("conn closed.")
    return success


def select_more_trans():
    """
    Displays transactions in pages of 10 items and allows multiple selections.
    Input: Comma-separated serial numbers (e.g., "1,3,5" or "1, 3, 5")
    Returns: List of selected transaction IDs or None if no selection made

    Navigation:
    - Press Enter to see next page
    - Enter serial numbers with commas to select multiple transactions
    - Returns None when reaching end of list without selection
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get total count of transactions
        cursor.execute("SELECT COUNT(*) FROM transactions")
        total_records = cursor.fetchone()[0]

        if total_records == 0:
            print("No transactions found in the database.")
            return None

        offset = 0
        page_size = 10

        while offset < total_records:
            clear_screen()

            # Fetch 10 records with stock code
            cursor.execute("""
                SELECT
                    t.id_trd,
                    s.stk_code,
                    t.trd_dt,
                    t.trade_type_trd,
                    t.qty_trd,
                    t.net_amt_trd
                FROM transactions t
                JOIN stocks s ON t.id_stk = s.id_stk
                ORDER BY t.trd_dt ASC, t.id_trd ASC
                LIMIT ? OFFSET ?
            """, (page_size, offset))

            records = cursor.fetchall()
            sr_no_map = {} # Map serial numbers to transaction IDs
            length = {}
            length['sr_no'] = 6
            length['id_trd'] = 4
            length['stk_code'] = max(len(r[1]) for r in records)+2
            length['trd_dt'] = max(len(r[2]) for r in records)+2
            length['trade_type_trd'] = max(len(r[3]) for r in records)+2
            length['qty_trd'] = max(len(str(r[4])) for r in records)+2
            length['net_amt_trd'] = max(len(str(r[5])) for r in records)+2
            total_length = sum(length.values()) + 10
            print("\nTransaction List:")
            print("=" * total_length)
            print(f"{' Sr.':^{length['sr_no']}}{'Id':>{length['id_trd']}} {'Stock':^{length['stk_code']}} {'Date':^{length['trd_dt']}} {'Type':^{length['trade_type_trd']}} {'Qty':^{length['qty_trd']}} {'Net Amt':^{length['net_amt_trd']}}")
            print("-" * total_length)


            for idx, (id_trd, stk_code, trd_dt, trade_type_trd, qty_trd, net_amt) in enumerate(records, 1):
                sr_no = offset + idx
                sr_no_map[sr_no] = id_trd
                print(f"{sr_no:>{length['sr_no']}} {id_trd:>{length['id_trd']}} {stk_code:<{length['stk_code']}} {trd_dt:>{length['trd_dt']}} {trade_type_trd:<{length['trade_type_trd']}} {qty_trd:>{length['qty_trd']}} {net_amt:>{length['net_amt_trd']}.2f}")

            print("-" * total_length)
            remaining = total_records - (offset + len(records))
            if remaining > 0:
                print(f"\n{remaining} more transactions available.")
                prompt = "Enter serial numbers (comma-separated), '*' for all, or press Enter for more: "
                #prompt = "Enter serial numbers (comma-separated) to select, or press Enter for more: "
            else:
                print("\nEnd of transactions list.")
                prompt = "Enter serial numbers (comma-separated) to select, or press Enter to exit: "

            choice = input(prompt).strip()

            if not choice: # Enter key pressed
                if remaining > 0:
                    offset += page_size
                    continue
                else:
                    return None
            if choice in {'*', 'all'}:
                cursor.execute("SELECT id_trd FROM transactions ORDER BY trd_dt ASC, id_trd ASC")
                all_ids = [row[0] for row in cursor.fetchall()]
                return all_ids

            try:
                # Parse comma-separated input and remove any whitespace
                selected_numbers = [int(num.strip()) for num in choice.split(',')]

                # Validate all numbers before returning
                selected_ids = []
                invalid_numbers = []

                for sr_no in selected_numbers:
                    if sr_no in sr_no_map:
                        selected_ids.append(sr_no_map[sr_no])
                    else:
                        invalid_numbers.append(sr_no)

                if invalid_numbers:
                    print(f"Invalid serial number(s): {', '.join(map(str, invalid_numbers))}")
                    print("Press any key to continue...")
                    get_single_key()
                    continue

                if selected_ids:
                    return selected_ids # Return list of selected transaction IDs

            except ValueError:
                print("Invalid input. Please enter numbers separated by commas.")
                print("Press any key to continue...")
                get_single_key()

        return None # Return None if no selection was made

    except Exception as e:
        print(f"Error listing transactions: {e}")
        get_single_key("Press any key to continue...")
        return None

    finally:
        if 'conn' in locals():
            conn.close()

def update_or_insert_contract(cursor, cont_no, trd_dt):
    """
    Updates the 'contracts' table with aggregated values
    from 'transactions' if the cont_no already exists,
    otherwise inserts a new record.
    """
    # Select one record from contracts table to check if it exists
    cursor.execute("SELECT 1 FROM contracts WHERE cont_no = ?", (cont_no,))
    cont_row = cursor.fetchone()

    if cont_row:
        cursor.execute("""
            UPDATE contracts
            SET
                trd_dt = ?,
                brok_cont = (SELECT SUM(brok_lot_trd) FROM transactions WHERE cont_no = ?),
                etc_cont = (SELECT SUM(etc_trd) FROM transactions WHERE cont_no = ?),
                sebi_cont = (SELECT SUM(sebi_trd) FROM transactions WHERE cont_no = ?),
                gst_cont = (SELECT SUM(gst_trd) FROM transactions WHERE cont_no = ?),
                stamp_cont = (SELECT SUM(stamp_trd) FROM transactions WHERE cont_no = ?),
                stt_cont = (SELECT SUM(stt_trd) FROM transactions WHERE cont_no = ?),
                igst_cont = (SELECT SUM(igst_trd) FROM transactions WHERE cont_no = ?),
                net_amt_cont = (SELECT SUM(net_amt_trd) FROM transactions WHERE cont_no = ?),
                sell_chrg_cont = (SELECT SUM(sell_chrg_trd) FROM transactions WHERE cont_no = ?),
                no_of_trades = (SELECT COUNT(*) FROM transactions WHERE cont_no = ?)
            WHERE cont_no = ?
        """, (trd_dt, cont_no, cont_no, cont_no, cont_no, cont_no, cont_no, cont_no, cont_no, cont_no, cont_no, cont_no))
    else:
        cursor.execute("""
            INSERT INTO contracts (
                cont_no, trd_dt, brok_cont, etc_cont,
                sebi_cont, gst_cont, stamp_cont,
                stt_cont, igst_cont, net_amt_cont,
                sell_chrg_cont, no_of_trades)
            SELECT
                ?, ?,
                SUM(brok_lot_trd), SUM(etc_trd),
                SUM(sebi_trd), SUM(gst_trd),
                SUM(stamp_trd), SUM(stt_trd),
                SUM(igst_trd), SUM(net_amt_trd),
                SUM(sell_chrg_trd), COUNT(*)
            FROM transactions
            WHERE cont_no = ?
        """, (cont_no, trd_dt, cont_no))
    print("Contract {cont_no} updated or inserted successfully.")
    time.sleep(0.2)












def enter_trade():
    """This function adds data to the transaction table
        and also calls other functions for computing the
        secondary fields.
    """
    ISINT = ISCHOICE = ISCONT = ISTRD = ISORD = ISSTOCK = True
    NOINT = NOCHOICE = NOCONT = NOTRD = NOORD = NOSTOCK = False
    ETCN = 0.00003313 # Tested numbers 0.0000331, 0.0000332, 0.00003315
    ETCB = 0.000030 # Tested numbers 0.0000307
    BROK = 0.0022  # Brokerage rate
    GST = 0.18  # GST rate
    SEBI = 0.000001  # SEBI charges rate
    STT = 0.001
    # Initialize queries
    data = {}

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Dictionary for First entry
        first_entry = {"cont_no": ("Text", "Contract Number", "get_valid_string", None, NOINT, NOCHOICE, ISCONT, ISTRD, NOORD),
                     "trd_dt": ("Date", "Trade Date", "get_valid_date", None, NOINT, NOCHOICE, ISCONT, ISTRD, NOORD),
                     "settle_no": ("Integer", "Settlement Number", "get_valid_number", 0, ISINT, NOCHOICE, ISCONT, NOTRD, NOORD),
                     "settle_dt": ("Date", "Settlement Date", "get_valid_date", None, NOINT, NOCHOICE, ISCONT, NOTRD, NOORD),
                     "no_of_trades": ("Integer", "Number of Trades", "get_valid_number", 1, ISINT, NOCHOICE, ISCONT, NOTRD, NOORD),
                     }
        # Dictionary for order entry column_name to (type, label, validation_function, default_value, integer, choices, is_cont, is_trd, is_ord)
        order_entry = {"ord_no": ("Integer", "Order Number", "get_valid_number", 0, ISINT, NOCHOICE, NOCONT, NOTRD, ISORD),
                     "ord_dt": ("Date", "Order Date", "get_valid_date", lambda data: data["trd_dt"], NOINT, NOCHOICE, NOCONT, NOTRD, ISORD),
                     "trd_no": ("Integer", "Trade Number", "get_valid_number", 0, ISINT, NOCHOICE, NOCONT, NOTRD, ISORD),
                     "qty_eo": ("Integer", "Quantity Exchange Order", "get_valid_number", lambda data: data["qty_trd"] - data["check_qty"] , ISINT, NOCHOICE, NOCONT, NOTRD, ISORD),
                     "rate_eo": ("Float", "Price per Unit Exchange Order", "get_valid_number", 0.0, NOINT, NOCHOICE, NOCONT, NOTRD, ISORD),
                     "brok_unit_eo": ("Float", "Brokerage per Unit Exchange Order", "get_valid_number", lambda data: data["rate_eo"] * BROK, NOINT, NOCHOICE, NOCONT, NOTRD, ISORD),
                     "net_rate_eo": ("Float", "Net Rate Exchange Order", "get_valid_number", lambda data: data["rate_eo"] + data["brok_unit_eo"] if data["trade_type_trd"] == "BUY" else data["rate_eo"] - data["brok_unit_eo"],
                           NOINT, NOCHOICE, NOCONT, NOTRD, ISORD),
                     "net_total_eo": ("Float", "Net Total Exchange Order", "get_valid_number", lambda data: data["net_rate_eo"] * data["qty_eo"], NOINT, NOCHOICE, NOCONT, NOTRD, ISORD),
                     }

        # Dictionary column_name to (type, label, validation_function, default_value, integer, choices, is_cont, is_trd, is_ord)
        all_entry = {"trade_type_trd": ("Choice", f"Trade Type ([B]UY/[S]ELL): ", "get_single_key",
                                        None, NOINT, ['B', 'S',], NOCONT, ISTRD, NOORD),
                     "qty_trd": ("Integer", "Quantity Traded", "get_valid_number", 1, ISINT,
                                 NOCHOICE, NOCONT, ISTRD, NOORD),
                     "exchange": ("Choice", f"Enter exchange ([N]SE/[B]SE/[M]CX/[O]ther): ",
                                  "get_single_key", None, NOINT, ['N', 'B', 'M', 'O'], NOCONT,
                                  ISTRD, NOORD),
                     "wap_unit_trd": ("Float", "Weighted Average Price", "get_valid_number",
                                      lambda data: data["total_order_price"] / data["qty_trd"],
                                      NOINT, NOCHOICE, NOCONT, ISTRD, NOORD),
                     "brok_unit_trd": ("Float", "Brokerage per Unit Trade", "get_valid_number",
                                       lambda data: data["wap_unit_trd"] * BROK, NOINT,
                                       NOCHOICE, NOCONT, ISTRD, NOORD),
                     "price_lot_trd": ("Float", "Price per Lot Trade", "get_valid_number",
                                       lambda data: data["wap_unit_trd"] * data["qty_trd"],
                                       NOINT, NOCHOICE, NOCONT, ISTRD, NOORD),
                     "brok_lot_trd": ("Float", "Brokerage per Lot Trade", "get_valid_number",
                                      lambda data: data["brok_unit_trd"] * data["qty_trd"],
                                      NOINT, NOCHOICE, NOCONT, ISTRD, NOORD),
                     "etc_trd": ("Float", "ETC Charges Trade", "get_valid_number",
                                 lambda data: (data["price_lot_trd"] + data["brok_lot_trd"]) * (ETCN if data["exchange"] == "NSE" else ETCB),
                                 NOINT, NOCHOICE, NOCONT, ISTRD, NOORD),
                     "sebi_trd": ("Float", "SEBI Charges Trade", "get_valid_number",
                                  lambda data: (data["price_lot_trd"]) * SEBI, NOINT, NOCHOICE, NOCONT, ISTRD, NOORD),
                     "sell_chrg_trd": ("Float", "Sell Charges Trade", "get_valid_number",
                                       0.0, NOINT, NOCHOICE, NOCONT, ISTRD, NOORD),
                     "gst_trd": ("Float", "GST Charges Trade", "get_valid_number",
                                 lambda data: (data["brok_lot_trd"] + data["etc_trd"] + data["sebi_trd"]) * GST,
                                 NOINT, NOCHOICE, NOCONT, ISTRD, NOORD),
                     "stamp_trd": ("Float", "Stamp Charges Trade", "get_valid_number",
                                   0.0, NOINT, NOCHOICE, NOCONT, ISTRD, NOORD),
                     "stt_trd": ("Float", "STT Charges Trade", "get_valid_number",
                                 lambda data: (data["price_lot_trd"]) * STT, NOINT, NOCHOICE, NOCONT, ISTRD, NOORD),
                     "igst_trd": ("Float", "IGST Charges Trade", "get_valid_number",
                                  0.0, NOINT, NOCHOICE, NOCONT, ISTRD, NOORD),
                     "net_amt_trd": ("Float", "Net Amount Trade", "get_valid_number",
                                     lambda data: (data["price_lot_trd"] + data["brok_lot_trd"]
                                         + data["etc_trd"] + data["sebi_trd"]
                                         + data["gst_trd"] + data["stamp_trd"]
                                         + data["stt_trd"] + data["igst_trd"] )
                                     if data["trade_type_trd"] == "BUY"
                                     else (data["price_lot_trd"]
                                           - (data["brok_lot_trd"] + data["etc_trd"]
                                              + data["sebi_trd"] + data["gst_trd"] + data["stamp_trd"]
                                              + data["stt_trd"] + data["igst_trd"]
                                              + data["sell_chrg_trd"])
                                           ), NOINT, NOCHOICE, NOCONT, ISTRD, NOORD),
                     }
        # Fields to be computed and added to the database
        # column_name to (table, default_value, label)
        all_computed = {"brok_cont" : (ISCONT, lambda data: data["brok_cont"], "Brokerage Contract"),
                        "etc_cont": (ISCONT, lambda data: data["etc_cont"], "ETC Charges Contract"),
                        "sebi_cont": (ISCONT, lambda data: data["sebi_cont"], "SEBI Charges Contract"),
                        "gst_cont": (ISCONT, lambda data: data["gst_cont"], "GST Charges Contract"),
                        "stamp_cont": (ISCONT, lambda data: data["stamp_cont"], "Stamp Charges Contract"),
                        "stt_cont": (ISCONT, lambda data: data["stt_cont"], "STT Charges Contract"),
                        "igst_cont": (ISCONT, lambda data: data["igst_cont"], "IGST Charges Contract"),
                        "sell_chrg_cont": (ISCONT, lambda data: data["sell_chrg_cont"], "Sell Charges Contract"),
                        "net_amt_cont": (ISCONT, lambda data: data["net_amt_cont"], "Net Amount Contract"),
                        }

        #Initialize the data dictionary
        data = {
            "company_name": "",
            "isin": "",
            "brok_cont": 0.0,
            "etc_cont": 0.0,
            "sebi_cont": 0.0,
            "gst_cont": 0.0,
            "stamp_cont": 0.0,
            "stt_cont": 0.0,
            "igst_cont": 0.0,
            "sell_chrg_cont": 0.0,
            "net_amt_cont": 0.0,
            "check_qty" : 0,  # This will be updated later
        }

        contract_cols, contract_vals = [], []
        transaction_cols, transaction_vals = [], []
        order_cols, order_vals = [], []

        # Get the first entry data
        for key, (col_type, label, validation_func, default_value, is_integer, choices, cont, trd, ord) in first_entry.items():
            # If we're getting settle_dt and have trd_dt, calculate next day as default
            if key == "settle_dt" and "trd_dt" in data:
                default_value = (datetime.strptime(data["trd_dt"], "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            data[key] = value = globals()[validation_func](label, default_value, is_integer)
            # Presently avoiding but to check if cont_no exists.
            # In that case populate other fields from the database.
            # After that exit the loop.
            if isinstance(value, (int, float)):
                value_sql = str(value)            # No quotes
            else:
                value_sql = f"'{str(value)}'"     # Quotes for strings/dates
            contract_cols.append(key)
            contract_vals.append(value_sql)
        # Postpone the contract insertion.

        #Select one company at a time and enter data
        for company_no in range(data["no_of_trades"]):
            #data["total_order_amt"] = 0.0
            data["total_order_price"] = 0.0
            # Get only one stock_id at a time.
            stock_id = select_stock_id()
            data["id_stk"] = stock_id
            if stock_id is None:
                print("No stock selected. Data Entry aborted.")
                print("If your company is not listed, please add it first.")
                return
            # Check if trade already exists
            if list_trades(stock_id) == 'Y':
                print("Trade already exists in the database.")
                if company_no + 1 < data["no_of_trades"]:
                    print("Resuming the next trade.")
                    continue
                return

            #Get company name and isin
            cursor.execute("SELECT company_name, isin FROM stocks WHERE id_stk = ?", (stock_id,))
            co = cursor.fetchone()
            if co:
                data["company_name"], data["isin"]  = co
            else:
                data["company_name"], data["isin"]  = "Unknown Company", "Unknown ISIN"
            transaction_cols.append("id_stk")
            value_sql = str(stock_id)
            transaction_vals.append(value_sql)
            transaction_cols.append("company_name")
            value_sql = f"'{str(data['company_name'])}'"
            transaction_vals.append(value_sql)
            transaction_cols.append("cont_no")
            value_sql = f"'{str(data['cont_no'])}'"
            transaction_vals.append(value_sql)
            transaction_cols.append("trd_dt")
            value_sql = f"'{str(data['trd_dt'])}'"
            transaction_vals.append(value_sql)

            # Now get all_entry one transaction for the company
            for key, (col_type, label, validation_func, default_value, is_integer, choices, cont, trd, ord) in all_entry.items():
                # Skip if the trade_type_trd is BUY and the key == "sell_chrg_trd"
                if key == "sell_chrg_trd" and data["trade_type_trd"] == "BUY":
                    data[key] = 0.0
                    continue
                # Check if default_value is callable, if so, call it with data
                actual_default = default_value(data) if callable(default_value) else default_value
                default_value = actual_default
                if col_type == "Choice":
                    value = get_single_key(label, choices)
                    if key == "exchange":
                        # Convert choice to full name
                        if value == 'N':
                            value = 'NSE'
                        elif value == 'B':
                            value = 'BSE'
                        elif value == 'M':
                            value = 'MCX'
                        elif value == 'O':
                            value = 'Other'
                        data[key] = value
                        value_sql = f"'{str(value)}'"
                        transaction_cols.append(key)
                        transaction_vals.append(value_sql)
                        continue # Must go for next iteration of for loop. Othewise it will update transaction again.
                    if key == "trade_type_trd":
                        if value == 'B':
                            value = 'BUY'
                        elif value == 'S':
                            value = 'SELL'
                        data[key] = value
                        value_sql = f"'{str(value)}'"
                        transaction_cols.append(key)
                        transaction_vals.append(value_sql)
                        insert_transaction = f"INSERT INTO transactions ({', '.join(transaction_cols)}) VALUES ({', '.join(transaction_vals)});"
                        cursor.execute(insert_transaction) # Important to insert.
                        transaction_cols, transaction_vals = [], []
                        get_single_key(f"Partial Data of Transactions inserted.\nPress a key to continue...")
                        # Now get the id_trd for the order table
                        data["id_trd"] = cursor.lastrowid
                        continue #Go for next iteration of for loop.
                else:           # Not Choice
                    data[key] = value = globals()[validation_func](label, default_value, is_integer)
                    if key == "igst_trd" and data[key] != 0.0:
                        print("IGST is usually zero. Are you sure of this value?")
                        igstans = get_single_key("Enter 'Y' to continue with your value of IGST, or any other key to enter a value: ", ['Y', 'N'])
                        if igstans != 'Y':
                            data[key] = 0.0
                            continue
                    if isinstance(value, (int, float)):
                        value_sql = str(value)            # No quotes
                    else:
                        value_sql = f"'{str(value)}'"     # Quotes for strings/dates
                if cont:
                    contract_cols.append(key)
                    contract_vals.append(value_sql)
                if trd:
                    transaction_cols.append(key)
                    transaction_vals.append(value_sql)
                if ord:
                    order_cols.append(key)
                    order_vals.append(value_sql)
                #Insert into transactions if the key == qty_trd
                if key == "qty_trd":
                    data["check_qty"] = 0
                    while data["check_qty"] < data["qty_trd"]:
                        order_cols.append("id_trd")
                        value_sql = str(data["id_trd"])
                        order_vals.append(value_sql)
                        # Get the quantity for this order
                        for key, (col_type, label, validation_func, default_value, is_integer, choices, cont, trd, ord) in order_entry.items():
                            actual_default = default_value(data) if callable(default_value) else default_value
                            default_value = actual_default
                            data[key] = value = globals()[validation_func](label, default_value, is_integer)
                            if isinstance(value, (int, float)):
                                value_sql = str(value)            # No quotes
                            else:
                                value_sql = f"'{str(value)}'"     # Quotes for strings/dates
                            #add to query
                            order_cols.append(key)
                            order_vals.append(value_sql)
                            if key == "trd_no":
                                print(f"\nISIN: {data["isin"]}")
                                print(f"Company: {data["company_name"]}")
                            if key == "qty_eo":
                                data["check_qty"] += value
                                if data["check_qty"] > data["qty_trd"]:
                                    print(f"⚠️ Warning: Total quantity of Exchange Orders ({data["check_qty"]}) exceeds Quantity Traded ({data['qty_trd']}).")
                                    get_single_key("Press any key to continue...")
                                    return
                        #for loop of orders over, one order is ready to be inserted.
                        #data["total_order_amt"] += data["net_total_eo"]
                        data["total_order_price"] += (data["qty_eo"] * data["rate_eo"])
                        insert_order = f"INSERT INTO exchange_orders ({', '.join(order_cols)}) VALUES ({', '.join(order_vals)});"
                        cursor.execute(insert_order)
                        order_cols, order_vals = [], []
                        get_single_key(f"Data of one EO inserted. Press a key to continue...")
                # if qty_trd ends in the above line.
            # for loop for data entry of one trade over.
            # Still in the same stock

            set_clause = ", ".join(f"{col} = ?" for col in transaction_cols)
            update_sql = f"UPDATE transactions SET {set_clause} WHERE id_trd = ?"
            update_params = transaction_vals + [data["id_trd"]]
            cursor.execute(update_sql, update_params) # Important to insert.
            transaction_cols, transaction_vals = [], []
            # If the contract is incomplete, first commit the changes and continue.
            conn.commit()

        update_or_insert_contract(cursor, data["cont_no"], data["trd_dt"])
        conn.commit()
        print("All data entered in to database")
        if data['trade_type_trd'] == 'SELL':
            print(f"\nManaging sell transaction for {data["company_name"]}...")
            manage_sell(stock_id, data['qty_trd'])
        else:
            compute_avg_price(stock_id)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
        get_single_key("\nPress any key to continue...")
        clear_screen()
    return


def edit_trade():
    """This function is used to edit a trade.
    It will ask for the trade id and then allow the user to edit the trade.
    """
    trade_id = select_trade_id()
    print(f"You selected trade id: {trade_id}")
    print("This function is not implemented yet.")
    get_single_key("Press any key to continue...")
    clear_screen()

    return




def list_trades(stock_id, ask = True):
    """
    List all trades for a given stock ID.

    Args:
        stock_id: The ID of the stock to list trades for
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get company name for the stock ID
    cursor.execute("SELECT company_name FROM stocks WHERE id_stk = ?", (stock_id,))
    co = cursor.fetchone()
    company = co[0] if co else "Unknown Company"

    # Get all trades for the company
    cursor.execute("SELECT id_trd, trd_dt, trade_type_trd, qty_trd, net_amt_trd FROM transactions WHERE id_stk = ?", (stock_id,))
    trades = cursor.fetchall()
    if not trades:
        print(f"No trades found for {company}.")
        return False

    # Display new version
    length = {}
    length['sr_no'] = 6
    length['trd_dt'] = max(len(r[1]) for r in trades)+2
    length['trade_type_trd'] = max(len(r[2]) for r in trades)+2
    length['qty_trd'] = max(len(str(r[3])) for r in trades)+4
    length['net_amt_trd'] = max(len((f"{r[4]:.4f}")) for r in trades)+2
    total_length = sum(length.values()) + 6
    print("\nTrade List:")
    print("=" * total_length)
    print(f"{'    Sr.':^{length['sr_no']}} {'Date':^{length['trd_dt']}} {'B/S':^{length['trade_type_trd']}} {'Qty':<{length['qty_trd']}} {'Amount':<{length['net_amt_trd']}}")
    print("-" * total_length)
    for sr_no, (_, trd_dt, trade_type_trd, qty_trd, net_amt_trd) in enumerate(trades, 1):
        print(f"{sr_no:>{length['sr_no']}} {trd_dt:<{length['trd_dt']}} {trade_type_trd:^{length['trade_type_trd']}} {qty_trd:<{length['qty_trd']}} {net_amt_trd:>{length['net_amt_trd']}.4f}")
    print("-" * total_length)
    #get_single_key("\nNew type of printing.")

    # Close connection
    conn.close()
    if ask:
        return get_single_key("\n Does your trade exist in the database? (Y/N): ", ['Y', 'N'])
    else:
        get_single_key("\nPress any key to continue...")
    return



def select_trade(stock_id):
    """
    List all trades for a given stock ID.

    Args:
        stock_id: The ID of the stock to list trades for
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get company name for the stock ID
    cursor.execute("SELECT company_name FROM stocks WHERE id_stk = ?", (stock_id,))
    co = cursor.fetchone()
    company = co[0] if co else "Unknown Company"

    # Get all trades for the company
    cursor.execute("SELECT id_trd, trd_dt, trade_type_trd, qty_trd, net_amt_trd FROM transactions WHERE id_stk = ?", (stock_id,))
    trades = cursor.fetchall()
    if not trades:
        print(f"No trades found for {company}.")
        return False

    # Display new version
    length = {}
    length['sr_no'] = 6
    length['trd_dt'] = max(len(r[1]) for r in trades)+2
    length['trade_type_trd'] = max(len(r[2]) for r in trades)+2
    length['qty_trd'] = max(len(str(r[3])) for r in trades)+4
    length['net_amt_trd'] = max(len((f"{r[4]:.4f}")) for r in trades)+2
    total_length = sum(length.values()) + 6
    print("\nTrade List:")
    print("=" * total_length)
    print(f"{'    Sr.':^{length['sr_no']}} {'Date':^{length['trd_dt']}} {'B/S':^{length['trade_type_trd']}} {'Qty':<{length['qty_trd']}} {'Amount':<{length['net_amt_trd']}}")
    print("-" * total_length)
    trd = {}

    for sr_no, (id_trd, trd_dt, trade_type_trd, _, qty_trd, net_amt_trd,*_) in enumerate(trades, 1):
        print(f"{sr_no:>{length['sr_no']}} {trd_dt:<{length['trd_dt']}} {trade_type_trd:^{length['trade_type_trd']}} {qty_trd:<{length['qty_trd']}} {net_amt_trd:>{length['net_amt_trd']}.4f}")
        trd[sr_no] = id_trd
    print("-" * total_length)
    # Close connection
    conn.close()
    num = get_valid_number("Enter Sr. No. to edit", integer=True)
    return trd[num] if num in trd else None


def main_menu():
    """
    Display and handle the main menu options.
    Returns the function name to be executed or None to exit.
    """
    menu_items = [
        ("Create Database", "C", "create_database"),
        ("Data Entry", "D", "data_entry_menu"),
        ("Maintanence", "M", "maintanence_menu"),
        ("Reports", "R", "report_menu"),
        ("Exit", "X", "exit")
    ]
    return operate_menu(menu_items, "Stock Portfolio Management", "Select an option")

def data_entry_menu():
    """
    Display and handle the one-time menu options.
    Returns the function name to be executed or None to exit.
    """
    menu_items = [
        ("Bulk Entry Company", "B", "bulk_entry_company"),
        ("Enter Trade", "E", "enter_trade"),
        ("Enter Trade New", "N", "enter_trade_new"),
        ("Add New Company", "A", "add_company"),
        ("Delete Trades", "D", "delete_transactions"),("Previous Menu", "X", "exit")
    ]
    while True:
        choice = operate_menu(menu_items, "One-Time Menu", "Select an option")
        if choice == "exit":
            print("Returning to Main Menu...")
            break
        elif choice:
            # Execute the selected function
            try:
                globals()[choice]()
            except Exception as e:
                print(f"Error executing {choice}: {e}")
                get_single_key("Press any key to continue...")


def maintanence_menu():
    """
    Display and handle the one-time menu options.
    Returns the function name to be executed or None to exit.
    """
    menu_items = [
        ("Manage All Trades", "M", "manage_all"),
        ("Edit a Trade", "E", "edit_trade"),
        ("Compute Fields", "C", "compute_fields"),
        ("Previous Menu", "X", "exit")
    ]
    while True:
        choice = operate_menu(menu_items, "One-Time Menu", "Select an option")
        if choice == "exit":
            print("Exiting program...")
            break
        elif choice:
            # Execute the selected function
            try:
                globals()[choice]()
            except Exception as e:
                print(f"Error executing {choice}: {e}")
                get_single_key("Press any key to continue...")





def report_menu():
    """
    Display and handle the migration menu options.
    Returns the function name to be executed or None to exit.
    """
    menu_items = [
        ("View Contracts", "C", "view_contracts"),
        ("Print Tables", "T", "temporary_branch"),
        ("View Database Structure", "D", "view_db_structure_new"),
        ("View Transactions", "V", "view_transaction_details"),
        ("List Triggers", "L", "list_triggers"),
        ("Previous Menu", "X", "exit")
    ]
    while True:
        choice = operate_menu(menu_items, "One-Time Menu", "Select an option")
        if choice == "exit":
            print("Exiting program...")
            break
        elif choice:
            # Execute the selected function
            try:
                globals()[choice]()
            except Exception as e:
                print(f"Error executing {choice}: {e}")
                get_single_key("Press any key to continue...")


def temporary_branch():
    """
    Temporary branch for testing purposes.
    Allows the user to choose a table and print selected columns.
    """

    menu_items = [
        ("Stocks", "S", "stocks"),
        ("Transactions", "T", "transactions"),
        ("Contracts", "C", "contracts"),
        ("Corporate Actions", "A", "corp_acts"),
        ("Exchange Orders", "E", "exchange_orders"),
        ("Previous Menu", "X", "exit")
    ]

    while True:
        choice = operate_menu(menu_items, "Tables", "Select Table")
        if choice == "exit":
            print("Exiting to previous menu...")
            break
        elif choice:
            # Load column specs for the selected table
            try:
                col_specs = get_column_specs(choice)
                pass_dict = {}
                for key, value in col_specs.items():
                    ans = get_single_key(f"Want to print {key}? (Y/N): ", valid_keys=['Y', 'N'])
                    if ans == 'Y':
                        pass_dict[key] = value[1]  # Heading from column specs

                if not pass_dict:
                    print("No columns selected. Returning to menu...")
                    continue

                print_table_data(
                    table_name=choice,
                    columns=pass_dict,
                    where_clause=None,
                    output_to_file=True
                )

            except Exception as e:
                print(f"Error while printing table '{choice}': {e}")

            finally:
                get_single_key("Press any key to return to the menu...")


def main():
    """
    Main program loop. Handles menu selection and function execution.
    """

    while True:
        clear_screen()
        choice = main_menu()

        if choice == "exit":
            print("Exiting program...")
            break
        elif choice:
            # Execute the selected function
            try:
                globals()[choice]()
            except Exception as e:
                print(f"Error executing {choice}: {e}")
                get_single_key("Press any key to continue...")

if __name__ == "__main__":
    main()


