# -*- coding: utf-8 -*-
# scripts/repair_transactions_from_eos.py
# Recompute transaction aggregates from exchange_orders and update transactions.
# Creates a timestamped backup before modifying the DB and prints a short summary.

import os
import shutil
import datetime
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB = os.path.join(ROOT, 'data', 'mystocks.db')
DB = os.path.abspath(DB)

if not os.path.exists(DB):
    print('Database not found at', DB)
    sys.exit(1)

bak = DB + '.repair.bak.' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
print('Creating backup:', bak)
shutil.copy2(DB, bak)

conn = sqlite3.connect(DB)
cur = conn.cursor()
updated_rows = 0
try:
    cur.execute('PRAGMA foreign_keys = ON')
    cur.execute('BEGIN')
    cur.execute("""
    UPDATE transactions
    SET
        qty_trd = COALESCE((SELECT SUM(qty_eo) FROM exchange_orders WHERE id_trd = transactions.id_trd), 0),
        wap_unit_trd = COALESCE((
            SELECT CASE WHEN SUM(qty_eo)=0 THEN 0 ELSE SUM(qty_eo*rate_eo)/SUM(qty_eo) END
            FROM exchange_orders WHERE id_trd = transactions.id_trd
        ), 0),
        brok_lot_trd = COALESCE((SELECT SUM(brok_unit_eo * qty_eo) FROM exchange_orders WHERE id_trd = transactions.id_trd), 0.0),
        brok_unit_trd = CASE
            WHEN COALESCE((SELECT SUM(qty_eo) FROM exchange_orders WHERE id_trd = transactions.id_trd),0) > 0
            THEN COALESCE((SELECT SUM(brok_unit_eo * qty_eo) FROM exchange_orders WHERE id_trd = transactions.id_trd),0.0) /
                 (SELECT SUM(qty_eo) FROM exchange_orders WHERE id_trd = transactions.id_trd)
            ELSE 0.0 END,
        price_lot_trd = COALESCE(price_lot_trd, (SELECT COALESCE(SUM(net_total_eo),0) FROM exchange_orders WHERE id_trd = transactions.id_trd)),
        net_amt_trd = COALESCE((SELECT SUM(net_total_eo) FROM exchange_orders WHERE id_trd = transactions.id_trd), net_amt_trd)
    ;
    """)
    # rowcount should be number of rows matched/updated by the UPDATE
    try:
        updated_rows = cur.rowcount
    except Exception:
        updated_rows = None
    conn.commit()
    print('Repair committed successfully.')
    if updated_rows is not None:
        print('Rows updated (approx):', updated_rows)
    else:
        print('Rows updated: (unknown)')
except Exception as ex:
    print('Repair failed:', ex)
    try:
        conn.rollback()
    except Exception:
        pass
finally:
    conn.close()
    print('Backup kept at', bak)

# Print a short post-check: how many transactions now have non-zero eo aggregates
try:
    conn2 = sqlite3.connect(DB)
    cur2 = conn2.cursor()
    cur2.execute('''
        SELECT COUNT(*) FROM (
            SELECT t.id_trd
            FROM transactions t
            LEFT JOIN (
              SELECT id_trd, SUM(qty_eo) AS sum_qty, SUM(net_total_eo) AS eo_net
              FROM exchange_orders GROUP BY id_trd
            ) eo ON eo.id_trd = t.id_trd
            WHERE (eo.sum_qty > 0 OR eo.eo_net > 0)
              AND (t.qty_trd IS NOT NULL AND t.qty_trd > 0)
        ) x
    ''')
    ok_count = cur2.fetchone()[0]
    cur2.execute('SELECT COUNT(*) FROM transactions')
    total = cur2.fetchone()[0]
    print(f'Transactions with eo aggregates present and qty_trd>0: {ok_count} / {total}')
    conn2.close()
except Exception:
    pass
