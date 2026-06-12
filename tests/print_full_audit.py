from pathlib import Path
import json
import glob

project_data = Path(__file__).resolve().parents[2] / "data"
pattern = str(project_data / "import_audit_*.json")
files = sorted(glob.glob(pattern))
if not files:
    print("No audit files found in", project_data)
    raise SystemExit(1)

latest = Path(files[-1])
print("Using audit file:", latest)

j = json.loads(latest.read_text(encoding="utf-8"))
entries = j.get("entries", [])
print("Total entries:", len(entries))
print("\nFull entries:")
for e in entries:
    print("---")
    print("cont_no:", e.get("cont_no"))
    print("company:", e.get("company_name"))
    print("legacy_src_id:", e.get("legacy_src_id"))
    print("contract_in_backup:", e.get("contract_in_backup"))
    print("contract_in_live:", e.get("contract_in_live"))
    t_backup = len(e.get("transactions_in_backup", []))
    t_live = len(e.get("transactions_in_live", []))
    print("transactions_in_backup_count:", t_backup)
    print("transactions_in_live_count:", t_live)
    print("new_exchange_orders_count:", len(e.get("exchange_orders_new", [])))
