#!/usr/bin/env python3
"""
check_brain_map.py — keep the Brodmann map in sync with the master ledger.

The interactive Brodmann figure carries its own layer of curation: which cortical
areas each sign localizes to (generator/brain_atlas.py). That layer is keyed by
sign id and by sub-region string, so it can drift silently out of sync with the
dataset — an intake that adds a sign, renames a sub-region or renumbers an id
would quietly leave signs off the map with nothing failing.

This gate closes that hole. It runs with the standard library only and exits
non-zero on any error, so a drifted map can never reach the build or deploy step.

Checks:
  1. Every sign the page renders (data/semiology_data.json + enrichment new_signs)
     resolves to at least one Brodmann tile, except ids declared in UNMAPPED below
     with a stated reason.
  2. Every per-sign override in SIGN_TILES points at a sign that still exists —
     catches a deleted or renumbered record silently re-targeting another sign.
  3. Every sub-region rule in SUB_TILES matches a sub-region in use — catches an
     orphan rule left behind by a rename.
  4. Every sub-region in the dataset has a rule — catches a new sub-region
     arriving from intake with no mapping, which would drop its signs off the map.
  5. Every tile referenced by any rule exists in TILE_INFO.
  6. Every tile in TILE_INFO is either drawn in at least one view or declared
     buried — catches an area defined but unreachable.
  7. Every LABEL_POS entry refers to a tile actually drawn in that view.
"""
import json
import os
import sys

def _find_root(start):
    d = os.path.dirname(os.path.abspath(start))
    while True:
        if os.path.exists(os.path.join(d, ".atlas-root")):
            return d
        p = os.path.dirname(d)
        if p == d:
            return os.path.dirname(os.path.abspath(start))
        d = p

ROOT = _find_root(__file__)
sys.path.insert(0, os.path.join(ROOT, "generator"))
import brain_atlas as BA  # noqa: E402

# Signs with no cortical-surface localization, declared rather than silently absent.
UNMAPPED = {
    110: "peri-ictal urinary urge — the record states no lobar localization",
}

errors, notes = [], []
def err(m): errors.append(m)


# ---- the sign set the page actually renders -------------------------------
signs = json.load(open(os.path.join(ROOT, "data", "semiology_data.json")))
enr = json.load(open(os.path.join(ROOT, "enrichment", "enrichment.json")))
new_signs = enr.get("new_signs", [])
nid = max(s["id"] for s in signs) + 1
for ns in new_signs:
    ns.setdefault("id", nid); nid += 1
all_signs = signs + new_signs
by_id = {s["id"]: s for s in all_signs}
subs_in_use = {s["sub"] for s in all_signs}

# ---- tiles drawn in each view ---------------------------------------------
def _strip(t):
    return t[:-1] if t.endswith("b") else t

drawn = {
    "lateral": {t for t, _, _ in BA.LATERAL_TILES},
    "medial":  {t for t, _, _ in BA.MEDIAL_TILES},
    "dorsal":  {_strip(t) for t, *_ in BA.DORSAL_BANDS} | {t for t, *_ in BA.DORSAL_EDGE},
    "ventral": {_strip(t) for t, *_ in BA.VENTRAL_BANDS},
}
drawn_any = set().union(*drawn.values())

# ---- 1. every rendered sign reaches the map -------------------------------
for s in all_signs:
    tiles = BA.tiles_for_sign(s)
    if tiles:
        if s["id"] in UNMAPPED:
            err(f"sign {s['id']} ({s['sign'][:44]!r}) is declared UNMAPPED but does map to {tiles}")
    elif s["id"] not in UNMAPPED:
        err(f"sign {s['id']} ({s['sign'][:44]!r}) maps to no Brodmann area, and is not "
            f"declared in UNMAPPED — it would vanish from the map")

for sid in UNMAPPED:
    if sid not in by_id:
        err(f"UNMAPPED declares sign {sid}, which no longer exists")

# ---- 2. per-sign overrides still point at real signs ----------------------
for sid in BA.SIGN_TILES:
    if sid not in by_id:
        err(f"SIGN_TILES has an override for sign id {sid}, which no longer exists — "
            f"a renumbered dataset would silently re-target this at another sign")

# ---- 3 & 4. sub-region rules and dataset sub-regions agree ----------------
for sub in BA.SUB_TILES:
    if sub not in subs_in_use:
        err(f"SUB_TILES rule for a sub-region no longer in the dataset: {sub!r}")
for sub in sorted(subs_in_use):
    if sub not in BA.SUB_TILES:
        err(f"sub-region has no Brodmann rule, so its signs would fall off the map: {sub!r}")

# ---- 5. every referenced tile exists --------------------------------------
referenced = set()
for v in BA.SUB_TILES.values():
    referenced |= set(v)
for v in BA.SIGN_TILES.values():
    referenced |= set(v)
for t in sorted(referenced):
    if t not in BA.TILE_INFO:
        err(f"mapping references tile {t!r}, which is not defined in TILE_INFO")

# ---- 6. every defined tile is reachable -----------------------------------
for t, info in BA.TILE_INFO.items():
    if t not in drawn_any and not info.get("buried"):
        err(f"tile {t!r} ({info['name'][:40]}) is defined but drawn in no view, and is "
            f"not marked buried — it is unreachable")

# ---- 7. label overrides refer to tiles present in that view ---------------
for view, pos in getattr(BA, "LABEL_POS", {}).items():
    if view not in drawn:
        err(f"LABEL_POS has a view {view!r} that the figure does not draw")
        continue
    for t in pos:
        if t not in drawn[view]:
            err(f"LABEL_POS[{view!r}] positions tile {t!r}, which is not drawn in that view")

# ---- report ---------------------------------------------------------------
mapped = sum(1 for s in all_signs if BA.tiles_for_sign(s))
notes.append(f"{mapped}/{len(all_signs)} signs mapped onto {len(drawn_any)} drawn areas "
             f"across {len(drawn)} views; {len(UNMAPPED)} declared unmapped")

for n in notes:
    print(f"  {n}")
if errors:
    print(f"\nBrodmann map is out of sync with the ledger — {len(errors)} error(s):", file=sys.stderr)
    for e in errors:
        print(f"  ERROR: {e}", file=sys.stderr)
    sys.exit(1)
print("OK — Brodmann map is in sync with the dataset.")
