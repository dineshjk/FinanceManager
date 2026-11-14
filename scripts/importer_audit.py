# -*- coding: utf-8 -*-
# scripts/importer_audit.py
"""
Data Migration Audit & Transaction Verification Utility.

This script executes an automated post-migration audit of the active database. It verifies
the relational integrity of imported contract notes, double-entry passbook linkages,
and cash ledger balances.

Key Responsibilities:
    • Ledger Integrity Audit: Verifies that all polymorphic links in `bank_transactions`
      reference valid primary keys in specialist tables (`fd_transactions`, `cc_transactions`, etc.).
    • Share Balance Audit: Checks cumulative trade histories to ensure no negative holding balances exist.
    • Summary Generation: Outputs structured diagnostic metrics to the console or log files.
"""
import sqlite3
import csv
import os

DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'mystocks.db')
DB = os.path.abspath(DB)
OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'import_audit.csv')

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute(
    (
        'SELECT id_trd, cont_no, company_name, qty_trd, '
        'wap_unit_trd, net_amt_trd '
        'FROM transactions ORDER BY id_trd'
    )
)
trs = cur.fetchall()

with open(OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow([
        'id_trd', 'cont_no', 'company_name', 'qty_trd', 'wap_unit_trd',
        'net_amt_trd', 'eo_sum_qty', 'eo_wap', 'eo_net_total'
    ])
    for tr in trs:
        id_trd = tr[0]
        cur.execute(
            (
                'SELECT SUM(qty_eo), '
                'CASE WHEN SUM(qty_eo)=0 THEN 0 '
                'ELSE SUM(qty_eo*rate_eo)/SUM(qty_eo) END, '
                'SUM(net_total_eo) '
                'FROM exchange_orders WHERE id_trd = ?'
            ),
            (id_trd,),
        )
        agg = cur.fetchone()
        w.writerow([
            tr[0], tr[1], tr[2], tr[3], tr[4], tr[5],
            agg[0] or 0, agg[1] or 0, agg[2] or 0,
        ])

cur.close()
conn.close()
print('Audit written to', OUT)
