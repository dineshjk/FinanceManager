# -*- coding: utf-8 -*-
# File: c:\Users\aumji\source\repos\Finance\FinanceManager\GUIStock\dbutils\company_utils.py


import sqlite3
import time
import tkinter as tk
from tkinter import messagebox
from typing import Tuple, List
from GUIStock.config.globals import logger, get_db_connection
import threading



# --- GUI Bulk Entry Company ---
def bulk_entry_company(parent: tk.Tk) -> None:
    """GUI version: Bulk insert company data into the stocks table with progress UI."""
    # Tuple stock_code, company_name, short_name, isin, face_value, sector, is_active, is_etf, tick
    company_data = [
        ("ABFRL", "Aditya Birla Fashion & Retail Ltd", "Adi Birla Fashion", "INE647O01011", 10.0, "Consumer Durables", 1,0, 0.01),
        ("ADILIF", "Aditya Birla Lifestyle Brands Limited", "Adi Birla Lifestyle", "INE14LE01019", 10.0, "Retail", 1,0, 0.01),
        ("ADANIPORTS", "Adani Ports and Special Economic Zone Limited", "Adani Ports", "INE742F01042", 2.0, "Port & Port services", 1, 0, 0.1),
        ("DMART", "Avenue Supermarts Limited DMART", "Dmart", "INE192R01011", 10.0, "Consumer Durables", 1, 0, 0.1),
        ("BAJFINANCE", "Bajaj Finance Limited", "Bajaj Fin", "INE296A01024", 2.0, "Non Banking Financial Company (NBFC)", 1, 0, 0.5),
        ("BANKBARODA", "Bank of Baroda", "BoB", "INE028A01039", 2.0, "Banking", 1, 0, 0.01),
        ("BHEL", "Bharat Heavy Electricals Limited", "BHEL", "INE257A01026", 2.0, "Heavy Electrical Equipment", 1, 0, 0.01),
        ("COALINDIA", "Coal India Limited", "Coal India", "INE522F01014", 10.0, "Coal", 1, 0, 0.05),
        ("DEEPAKNTR", "Deepak Nitrite Limited", "Deepak Nitrite", "INE288B01029", 2.0, "Chemicals", 1, 0, 0.1),
        ("DIXTEC", "Dixon Technologies (India) Limited", "Dixon Tech", "INE935N01020", 2.0, "Consumer Durables", 1, 0, 1),
        ("ETERNAL(ZOMATO)", "Eternal Limited", "Zomato", "INE758T01015", 1.0, "E-Commerce/App based Aggregator", 1, 0, 0.01),
        ("GRWRHITECH", "Garware Hi-Tech Films Limited", "Garware Hi-Tech Films", "INE291A01017", 10.0, "Plastics", 1, 0, 0.1),
        ("HCLTECH", "HCL Technologies Limited", "HCL Tech", "INE860A01027", 2.0, "Software and Consultancy", 1, 0, 0.1),
        ("HAL", "Hindustan Aeronautics Limited", "HAL", "INE066F01012", 5.0, "Aerospace", 1, 0, 0.1),
        ("HDFC", "HDFC Bank Limited", "HDFC Bank", "INE040A01034", 1.0, "Banking", 1, 0, 0.1),
        ("HYUNDAI", "Hyundai Motor India Limited", "Hyundai Motor India", "INE0V6F01027", 10.0, "Automobile", 1, 0, 0.1),
        ("ICIBAN", "ICICI Bank Limited", "ICICI Bank", "INE090A01021", 2.0, "Banking", 1, 0, 0.1),
        ("BSE500IETF", "ICICI Prudential BSE 500 ETF", "IPru BSE 500 ETF", "INF109KC1V59", 1.0, "Finance ETF", 1, 1, 0.01),
        ("GOLDIETF", "ICICI Prudential Gold ETF", "IPru Gold ETF", "INF109KC1NT3", 1.0, "Gold ETF", 1, 1, 0.01),
        ("ISEC", "ICICI Securities Limited", "ISecure", "INE763G01038", 5.0, "Finance", 1, 0, 0.1),
        ("IOC", "Indian Oil Corporation Limited", "IOC", "INE242A01010", 10.0, "Refineries/Oil-Gas", 1, 0, 0.01),
        ("IREDA", "Indian Renewable Energy Development Agency Ltd", "IREDA", "INE202E01016", 10.0, "Finance", 1, 0, 0.01),
        ("INFY", "Infosys Ltd", "Infosys", "INE009A01021", 5.0, "IT", 1, 0, 0.1),
        ("IRB", "IRB Infrastructure Developers Limited", "IRB", "INE821I01022", 1.0, "Infrastructure", 1, 0, 0.01),
        ("ITC", "ITC Limited", "ITC", "INE154A01025", 1.0, "FMCG", 1, 0, 0.05),
        ("JUSTDIAL", "Just Dial Limited", "Just Dial", "INE599M01018", 10.0, "E-Commerce/App based Aggregator", 1, 0, 0.05),
        ("KOTAKBANK", "Kotak Mahindra Bank Ltd", "Kotak Mahindra Bank", "INE237A01028", 5.0, "Banking", 1, 0,0.1),
        ("KPIGREEN", "KPI Green Energy Limited", "KPI Green Energy", "INE542W01017", 5.0, "Power", 1, 0, 0.05),
        ("KPEL", "K.P. Energy Limited", "K.P. Energy", "INE127T01021", 5.0, "Power", 1, 0, 0.05),
        ("KSOLVES", "Ksolves India Limited", "Ksolves India", "INE0D6I01023", 5.0, "IT", 1, 0, 0.1),
        ("LT", "Larsen & Toubro Limited", "L & T", "INE018A01030", 2.0, "Infrastructure", 1, 0, 0.1),
        ("NDTV", "New Delhi Television Limited", "NDTV", "INE155G01029", 4.0, "Media", 1, 0, 0.01),
        ("NIFTYBEES", "Nippon ETF Nifty 50 Bees", "Nippon ETF Nif50 Bees", "INF204KB14I2", 1.0, "ETF", 1, 1, 0.01),
        ("ONGC", "Oil And Natural Gas Corporation", "ONGC", "INE213A01029", 5.0, "Refineries/Oil-Gas", 1, 0, 0.01),
        ("TATAPOWER", "Tata Power Company Limited", "Tata Power", "INE245A01021", 1.0, "Power/Generation/Distribution", 1, 0, 0.05),
        ("TATASTEEL", "Tata Steel Limited", "Tata Steel", "INE081A01020", 1.0, "Steel", 1, 0, 0.01),
        ("TECHM", "Tech Mahindra Limited", "Tech Mahindra", "INE669C01036", 5.0, "IT", 1, 0, 0.1),
        ("UNIONBANK", "Union Bank Of India", "Union Bank", "INE692A01016", 10.0, "Banking", 1, 0, 0.01),
        ("WAAREE", "Waaree Energies Limited", "Waaree Energies", "INE377N01017", 10.0, "Capital Goods", 1, 0, 0.1),
        ("WIPRO", "Wipro Ltd", "Wipro", "INE075A01022", 2.0, "IT", 1, 0,0.01),
    ]

    win = tk.Toplevel(parent)
    win.title("Bulk Entry Company")
    win.geometry("500x200")
    win.resizable(False, False)
    win.transient(parent)
    win.grab_set()

    status_label = tk.Label(win, text="Starting bulk entry...", font=("Helvetica", 12))
    status_label.pack(pady=20)
    progress = tk.DoubleVar(value=0)
    progress_bar = tk.Scale(win, variable=progress, from_=0, to=len(company_data), orient="horizontal", length=400, showvalue=0, state="disabled")
    progress_bar.pack(pady=10)

    def do_bulk_entry():

        added_count = 0
        skipped_count = 0
        logger.info("Starting bulk entry of companies. Total: %d", len(company_data))
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                for idx, (code, name, short, isin, fv, sector, active, isetf, tick) in enumerate(company_data, 1):
                    logger.debug("Processing company #%d: %s (%s)", idx, name, code)
                    cur.execute("SELECT 1 FROM stocks WHERE stk_code = ? OR isin = ?", (code, isin))
                    if cur.fetchone():
                        skipped_count += 1
                        msg = f"⚠️ Skipping {name}: already exists."
                        logger.info("Skipped company: %s (%s), already exists.", name, code)
                    else:
                        cur.execute("""
                            INSERT INTO stocks (stk_code, company_name, short_name, isin, face_value, sector, is_active, is_etf, tick)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (code, name, short, isin, fv, sector, active, isetf, tick))
                        added_count += 1
                        msg = f"✅ Added {name}."
                        logger.info("Added company: %s (%s)", name, code)
                    win.after(0, status_label.config, {"text": f"{msg}\n{added_count} added, {skipped_count} skipped."})
                    win.after(0, progress.set, idx)
                    time.sleep(0.05)
                conn.commit()
                logger.info("Bulk entry complete. Added: %d, Skipped: %d", added_count, skipped_count)
        except Exception as e:
            logger.error("Error during bulk entry: %s", e, exc_info=True)
            win.after(0, status_label.config, {"text": f"❌ Error: {e}"})
        finally:
            win.after(500, lambda: (win.grab_release(), win.destroy()))
            parent.after(600, lambda: messagebox.showinfo("Bulk Entry Complete", f"Added: {added_count}\nSkipped: {skipped_count}", parent=parent))

    threading.Thread(target=do_bulk_entry, daemon=True).start()




def add_company_db(
    stk_code: str,
    isin: str,
    company_name: str,
    short_name: str = '',
    sector: str = '',
    face_value: float = 10.0,
    tick: float = 0.01,
    is_active: int = 1,
    is_etf: int = 0
) -> Tuple[bool, str]:
    """
    Adds a company to the stocks table.
    Returns (True, 'Success message') or (False, 'Error message').
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO stocks (
                    stk_code, isin, company_name, short_name, sector, face_value, tick, is_active, is_etf
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stk_code, isin, company_name, short_name, sector, face_value, tick, is_active, is_etf
                )
            )
            conn.commit()
        logger.info("Added company: %s (%s)", company_name, stk_code)
        return True, f"Company '{company_name}' added successfully."
    except sqlite3.IntegrityError as e:
        logger.warning("Integrity error adding company: %s (%s): %s", company_name, stk_code, e)
        return False, f"Integrity error: {e}"
    except Exception as e:
        logger.error("Error adding company: %s (%s): %s", company_name, stk_code, e, exc_info=True)
        return False, f"Error: {e}"


def add_company(parent: 'tk.Tk') -> None:
    """GUI form for adding a company to the stocks table."""

    ac = tk.Toplevel(parent)
    ac.title("Add Company")
    ac.geometry("400x600")
    ac.resizable(False, False)
    ac.transient(parent)
    ac.grab_set()
    ac.focus_set()
    try:
        parent.attributes('-disabled', True)
    except Exception:
        pass

    fields = [
        ("Stock Code", "stk_code"),
        ("ISIN", "isin"),
        ("Company Name", "company_name"),
        ("Short Name", "short_name"),
        ("Sector", "sector"),
        ("Face Value", "face_value"),
        ("Tick", "tick"),
        ("Is Active (1/0)", "is_active"),
        ("Is ETF (1/0)", "is_etf"),
    ]
    entries = {}
    for idx, (label, key) in enumerate(fields):
        tk.Label(ac, text=label, anchor="w").grid(row=idx, column=0, sticky="w", padx=10, pady=3)
        ent = tk.Entry(ac, width=30)
        ent.grid(row=idx, column=1, padx=10, pady=3)
        entries[key] = ent
        if key == "stk_code":
            ent.focus_set()
    # Set defaults
    entries["face_value"].insert(0, "10.0")
    entries["tick"].insert(0, "0.01")
    entries["is_active"].insert(0, "1")
    entries["is_etf"].insert(0, "0")
    # cont_no_entry.focus_set()

    def on_submit():
        data = {}
        for _, key in fields:
            val = entries[key].get().strip()
            data[key] = val
        # Type conversions
        try:
            data["face_value"] = float(data["face_value"])
            data["tick"] = float(data["tick"])
            data["is_active"] = int(data["is_active"])
            data["is_etf"] = int(data["is_etf"])
        except Exception as e:
            messagebox.showerror("Input Error", f"Invalid input: {e}", parent=ac)
            return
        # Call backend DB function
        success, message = add_company_db(
            data["stk_code"], data["isin"], data["company_name"], data["short_name"], data["sector"],
            data["face_value"], data["tick"], data["is_active"], data["is_etf"]
        )
        if success:
            messagebox.showinfo("Success", message, parent=ac)
            ac.destroy()
        else:
            messagebox.showerror("Error", message, parent=ac)

    btn_frame = tk.Frame(ac)
    btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)
    submit_btn = tk.Button(btn_frame, text="Submit", command=on_submit)
    submit_btn.pack(side="left", padx=10)
    cancel_btn = tk.Button(btn_frame, text="Cancel", command=ac.destroy)
    cancel_btn.pack(side="left", padx=10)
    # Bind Enter to submit and Escape to cancel
    ac.bind('<Return>', lambda event: on_submit())
    ac.bind('<Escape>', lambda event: ac.destroy())
    ac.wait_window(ac)
    # Re-enable parent window after modal closes
    try:
        parent.attributes('-disabled', False)
    except Exception:
        pass