from pathlib import Path
import json

# Try StockMan/data first, then project/data
data_dir1 = Path(__file__).resolve().parents[1] / "data"
data_dir2 = Path(__file__).resolve().parents[2] / "data"
p = data_dir1 / "import_audit_20251018-190051.json"
if not p.exists():
    p = data_dir2 / "import_audit_20251018-190051.json"
if not p.exists():
    print("Audit file not found:", p)
    raise SystemExit(1)

j = json.loads(p.read_text(encoding="utf-8"))
print("Generated at:", j.get("generated_at"))
print("Legacy path:", j.get("legacy_path"))
print("Backup path:", j.get("backup_path"))
print("Live path:", j.get("live_path"))
entries = j.get("entries", [])
print("Entries:", len(entries))
print("\nFirst 5 entries summary:")
for e in entries[:5]:
    cont_no = e.get("cont_no")
    legacy_id = e.get("legacy_src_id")
    new_eos_count = len(e.get("exchange_orders_new", []))
    print("-", cont_no, "legacy_id=", legacy_id, "new_eos=", new_eos_count)
