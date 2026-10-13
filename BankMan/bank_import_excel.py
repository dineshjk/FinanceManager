import sqlite3
import pandas as pd
from tkinter import filedialog
from tkinter import messagebox
from datetime import datetime
import os
import math


def setup_staging_table(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bank_transactions_staging (
        staging_id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER,
        serial_no INTEGER,
        value_date TEXT,
        trans_date TEXT,
        cheque_no TEXT,
        bank_desc TEXT,
        withdrawal_amount REAL DEFAULT 0.0,
        deposit_amount REAL DEFAULT 0.0,
        balance_after REAL,
        user_desc TEXT,
        is_processed INTEGER DEFAULT 0
    )
    """)
    try:
        cur.execute("ALTER TABLE bank_transactions_staging ADD COLUMN account_id INTEGER")
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()
    conn.close()


def import_from_excel(
    db_path,
    account_id=1,
    default_path=r"C:\Data\Personal\Finance_and_Investment\Banks\ICICI Bank\Statements\Manual Passbook.xlsm",
):
    file_path = filedialog.askopenfilename(
        title="Select Excel File",
        initialdir=os.path.dirname(default_path),
        initialfile=os.path.basename(default_path),
        filetypes=[("Excel Files", "*.xlsx *.xlsm *.xls")],
    )
    if not file_path:
        return None

    setup_staging_table(db_path)

    try:
        xl = pd.ExcelFile(file_path, engine="openpyxl")
        target_sheet = (
            "TranNotes" if "TranNotes" in xl.sheet_names else xl.sheet_names[0]
        )
        df = pd.read_excel(file_path, sheet_name=target_sheet, engine="openpyxl")
    except Exception as e:
        messagebox.showerror("Error", f"Could not read excel sheet: {e}")
        return None

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Clear previously unprocessed staging rows so we start fresh
    cur.execute("DELETE FROM bank_transactions_staging WHERE is_processed = 0")
    conn.commit()

    new_rows = 0
    skipped = 0

    for idx, row in df.iterrows():
        # Format date from datetime to string YYYY-MM-DD
        def format_date(v):
            if pd.isna(v):
                return None
            if isinstance(v, str):
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"):
                    try:
                        return datetime.strptime(v.split()[0], fmt).strftime("%Y-%m-%d")
                    except ValueError:
                        pass
                return v
            try:
                return v.strftime("%Y-%m-%d")
            except:
                return str(v)

        def get_val(key, exclude=None):
            for c in df.columns:
                c_clean = str(c).lower().replace("\n", "").strip()
                if key.lower() in c_clean:
                    if exclude and exclude.lower() in c_clean:
                        continue
                    return row[c]
            return None

        gen_serial = get_val("general serial")
        try:
            gen_serial = int(gen_serial)
        except:
            gen_serial = None

        val_date = format_date(get_val("value date"))
        trans_date = format_date(get_val("transaction date"))
        cheq_no = get_val("cheque number")
        bank_rem = get_val("transaction remarks")
        with_amt = get_val("withdrawal amount")
        dep_amt = get_val("deposit amount")
        bal = get_val("balance (inr )")
        if pd.isna(bal):
            bal = get_val("balance")
        user_rem = get_val("user_remark") or get_val("remark", exclude="transaction")

        if pd.isna(val_date) and pd.isna(trans_date):
            continue

        with_amt = float(with_amt) if not pd.isna(with_amt) else 0.0
        dep_amt = float(dep_amt) if not pd.isna(dep_amt) else 0.0
        bal = float(bal) if not pd.isna(bal) else 0.0
        bank_rem = str(bank_rem) if not pd.isna(bank_rem) else ""
        user_rem = str(user_rem) if not pd.isna(user_rem) else ""
        cheq_no = str(cheq_no) if not pd.isna(cheq_no) and str(cheq_no) != "nan" else ""

        # Check duplicate
        cur.execute(
            """
            SELECT 1 FROM bank_transactions
            WHERE account_id = ?
            AND trans_date = ?
            AND round(withdrawal_amount, 2) = round(?, 2)
            AND round(deposit_amount, 2) = round(?, 2)
            AND round(balance_after, 2) = round(?, 2)
        """,
            (account_id, trans_date, with_amt, dep_amt, bal),
        )
        if cur.fetchone():
            skipped += 1
            continue

        cur.execute(
            """
            INSERT INTO bank_transactions_staging
            (account_id, serial_no, value_date, trans_date, cheque_no, bank_desc, withdrawal_amount, deposit_amount, balance_after, user_desc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                account_id,
                gen_serial,
                val_date,
                trans_date,
                cheq_no,
                bank_rem,
                with_amt,
                dep_amt,
                bal,
                user_rem,
            ),
        )
        new_rows += 1

    conn.commit()
    conn.close()

    messagebox.showinfo(
        "Import Complete",
        f"Imported {new_rows} new rows to staging.\nSkipped {skipped} duplicates.",
    )
    return new_rows


def fetch_next_staging(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    row = None
    try:
        while True:
            cur.execute("""
                SELECT staging_id, account_id, serial_no, value_date, trans_date, cheque_no, bank_desc, withdrawal_amount, deposit_amount, balance_after, user_desc
                FROM bank_transactions_staging
                WHERE is_processed = 0
                ORDER BY staging_id ASC LIMIT 1
            """)
            row = cur.fetchone()

            if not row:
                break

            staging_id = row[0]
            account_id = row[1]
            trans_date = row[4]
            with_amt = row[7]
            dep_amt = row[8]
            bal = row[9]

            # Check duplicate in main table using the dynamic account_id (fallback to 1 for legacy rows)
            cur.execute(
                """
                SELECT 1 FROM bank_transactions
                WHERE account_id = ?
                AND trans_date = ?
                AND round(withdrawal_amount, 2) = round(?, 2)
                AND round(deposit_amount, 2) = round(?, 2)
                AND round(balance_after, 2) = round(?, 2)
                """,
                (account_id or 1, trans_date, with_amt, dep_amt, bal),
            )

            if cur.fetchone():
                # Manually entered! Flag as processed and fetch next.
                cur.execute("UPDATE bank_transactions_staging SET is_processed = 1 WHERE staging_id = ?", (staging_id,))
                conn.commit()
                continue
            else:
                # Fresh, un-entered row found!
                break

    except sqlite3.OperationalError as e:
        if "no such table" not in str(e):
            raise
    finally:
        conn.close()
    if not row:
        messagebox.showinfo("Empty", "No more pending imports in the staging table.")
        return None

    # Return as dict
    return {
        "staging_id": row[0],
        "account_id": row[1],
        "serial_no": row[2],
        "value_date": row[3],
        "trans_date": row[4],
        "cheque_no": row[5],
        "bank_desc": row[6],
        "withdrawal_amount": row[7],
        "deposit_amount": row[8],
        "balance_after": row[9],
        "user_desc": row[10],
    }


def mark_staging_processed(db_path, staging_id):
    if not staging_id:
        return
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE bank_transactions_staging SET is_processed = 1 WHERE staging_id = ?",
        (staging_id,),
    )
    conn.commit()
    conn.close()
