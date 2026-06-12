# -*- coding: utf-8 -*-
# scripts/importer_audit.py
r"""Small verification script producing a CSV audit of transactions vs
exchange_orders.

Usage: run from the project root. It writes audit.csv in the data/ directory.
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
