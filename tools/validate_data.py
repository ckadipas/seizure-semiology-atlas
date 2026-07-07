#!/usr/bin/env python3
"""
validate_data.py — integrity gate for the seizure-semiology dataset.

Runs with the Python standard library only (no pip install), so it works
unchanged in CI. Exits non-zero on any error so a bad correction can never
reach the build/deploy step.

Checks:
  1. data/semiology_data.json parses and is a list of objects.
  2. Every record matches schema/sign.schema.json:
       - required keys present, no unknown keys
       - enum fields (region, phase, latcode, evid) are valid
       - string fields non-empty where required
  3. `id` values are unique and positive.
  4. enrichment/enrichment.json parses; its evidence keys each resolve to at
     least one sign name (orphan keys are warnings, not errors);
     new_signs validate against the same schema.
  5. corpus/manifest.csv parses and has the expected header.
"""
import json, os, sys, csv

def _find_root(start):
    d = os.path.dirname(os.path.abspath(start))
    while True:
        if os.path.exists(os.path.join(d, ".atlas-root")): return d
        p = os.path.dirname(d)
        if p == d: return os.path.dirname(os.path.abspath(start))
        d = p

ROOT = _find_root(__file__)
errors, warnings = [], []
def err(m): errors.append(m)
def warn(m): warnings.append(m)

# ---- load schema ----
schema = json.load(open(os.path.join(ROOT, "schema", "sign.schema.json")))
props = schema["properties"]
required = set(schema["required"])
allowed = set(props.keys())
enums = {k: set(v["enum"]) for k, v in props.items() if "enum" in v}

def validate_record(rec, where, require_id=True):
    if not isinstance(rec, dict):
        err(f"{where}: record is not an object"); return
    keys = set(rec.keys())
    req = required if require_id else (required - {"id"})
    for miss in req - keys:
        err(f"{where}: missing required field '{miss}'")
    for extra in keys - allowed:
        err(f"{where}: unknown field '{extra}'")
    for f, allowedvals in enums.items():
        if f in rec and rec[f] not in allowedvals:
            err(f"{where}: field '{f}'='{rec[f]}' not in {sorted(allowedvals)}")
    if "id" in rec and not (isinstance(rec["id"], int) and rec["id"] >= 1):
        err(f"{where}: 'id' must be a positive integer, got {rec['id']!r}")
    for f in ("sign", "sub", "loc", "notes", "cite", "lat"):
        if f in rec and (not isinstance(rec[f], str) or len(rec[f].strip()) < 2):
            err(f"{where}: field '{f}' is empty or too short")

# ---- 1-3: dataset ----
data_path = os.path.join(ROOT, "data", "semiology_data.json")
try:
    data = json.load(open(data_path))
except Exception as e:
    print(f"FATAL: cannot parse {data_path}: {e}"); sys.exit(2)

if not isinstance(data, list):
    print("FATAL: dataset root must be a JSON array"); sys.exit(2)

seen_ids = {}
for i, rec in enumerate(data):
    where = f"sign[{i}] (id={rec.get('id','?')})"
    validate_record(rec, where)
    rid = rec.get("id")
    if rid in seen_ids:
        err(f"{where}: duplicate id (also used by sign[{seen_ids[rid]}])")
    seen_ids[rid] = i

sign_names = [r.get("sign", "").lower() for r in data]

# ---- 4: enrichment ----
enr_path = os.path.join(ROOT, "enrichment", "enrichment.json")
try:
    enr = json.load(open(enr_path))
except Exception as e:
    err(f"cannot parse {enr_path}: {e}"); enr = None

if enr is not None:
    for key in enr.get("evidence", {}):
        if not any(key in n for n in sign_names) and not any(
            key in ns.get("sign", "").lower() for ns in enr.get("new_signs", [])):
            warn(f"enrichment: evidence key '{key}' matches no sign name (orphan)")
    for j, ns in enumerate(enr.get("new_signs", [])):
        validate_record({k: v for k, v in ns.items() if k != "_ev"}, f"new_sign[{j}]", require_id=False)
    if not isinstance(enr.get("papers", []), list):
        err("enrichment: 'papers' must be a list")
    if not isinstance(enr.get("lateral", []), list):
        err("enrichment: 'lateral' must be a list")

# ---- 5: manifest ----
man_path = os.path.join(ROOT, "corpus", "manifest.csv")
if os.path.exists(man_path):
    with open(man_path, newline="") as f:
        rows = list(csv.reader(f))
    if not rows or rows[0][:3] != ["citation", "journal", "title"]:
        err("corpus/manifest.csv: unexpected header (want citation,journal,title,status,contribution)")
else:
    warn("corpus/manifest.csv not found")

# ---- report ----
n = len(data)
print(f"Validated {n} signs, {len(enr.get('evidence', {})) if enr else 0} evidence keys, "
      f"{len(enr.get('papers', [])) if enr else 0} papers.")
for w in warnings: print("  WARN:", w)
if errors:
    print(f"\nFAILED with {len(errors)} error(s):")
    for e in errors: print("  ERROR:", e)
    sys.exit(1)
print("OK — dataset is valid.")
