from pathlib import Path
import sys

sys.path.insert(0, str(Path(".").resolve()))

from StockMan.trade_from_file import _fetch_source_transactions
from Shared.globals import STOCK_DB_PATH
import sqlite3, json

LEGACY = r"C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\data\mystocks_old.db"
rows = _fetch_source_transactions(LEGACY)
print("legacy rows:", len(rows))
if not rows:
    sys.exit(0)

# pick first and last legacy cont_no for inspection
conts = [r["cont_no"] for r in rows]
inspect_conts = conts[:3] + conts[-3:]
inspect_conts = list(dict.fromkeys(inspect_conts))

conn = sqlite3.connect(STOCK_DB_PATH)
cur = conn.cursor()
for cont in inspect_conts:
    print("\n--- CONT:", cont)
    cur.execute("SELECT * FROM transactions WHERE cont_no = ?", (cont,))
    cols = [c[0] for c in cur.description] if cur.description else []
    for r in cur.fetchall():
        print("TX:", dict(zip(cols, r)))
        tx_id = r[0] if cols and "id_trd" in cols else (r[0] if cols else None)
        if tx_id is None:
            continue
        cur.execute("SELECT * FROM exchange_orders WHERE id_trd = ?", (tx_id,))
        ecols = [c[0] for c in cur.description] if cur.description else []
        eos = [dict(zip(ecols, er)) for er in cur.fetchall()]
        print("EOs:", json.dumps(eos, indent=2, default=str))
conn.close()
print("\nDone")
