#!/usr/bin/env python3
"""
brain_atlas.py — renders the Brodmann map from its data file.

This module holds **no scientific curation**. Area definitions and sign links
come from the generated canonical atlas bundle. The editable surface-view label
coordinates come from `data/brodmann_map.json` and are presentation data only.

A view is a reference plate and the numerals placed on it, so there is no
geometry left to compute here: this loads the map and answers which areas a sign
localizes to, and why.
"""
import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_ROOT, "data", "atlas_bundle.json"), encoding="utf-8") as stream:
    MAP = json.load(stream)["brodmann"]
with open(os.path.join(_ROOT, "data", "brodmann_map.json"), encoding="utf-8") as stream:
    DISPLAY_MAP = json.load(stream)
for view_name, display_view in DISPLAY_MAP["views"].items():
    labels = {area["id"]: area["label"] for area in display_view["areas"]}
    for area in MAP["views"].get(view_name, {}).get("areas", []):
        if area["id"] in labels:
            area["label"] = labels[area["id"]]

AREAS = MAP["areas"]
VIEWS = MAP["views"]
VIEW_ORDER = tuple(name for name in ("lateral", "medial", "dorsal", "ventral") if name in VIEWS)
MAPPING = MAP["mapping"]
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


# --------------------------------------------------------------------------
# semiology -> areas
# --------------------------------------------------------------------------
def mapping_for_sign(sign):
    """
    Areas a sign localizes to, *and why the map gives it those areas*.

    `via="sign"` — the map records an entry for this sign id, and `rule` is the
    sign name that entry was written against (the same string the gate checks for
    drift). `via="none"` — no explicit per-sign area is recorded; `rule` carries
    the reason if one is declared under `mapping.unmapped`.

    Returning the provenance beside the ids is what lets the page state why a
    sign highlights where it does, rather than asserting it.
    """
    sid = str(sign.get("id"))
    entry = MAPPING["by_sign"].get(sid)
    if entry:
        names, via, rule = entry["areas"], "sign", entry.get("sign", "")
        map_links = [
            link for link in entry.get("map_links") or []
            if str(link.get("area_id") or "") in names
        ]
    else:
        rule = MAPPING["unmapped"].get(sid, "")
        names, via = [], "none"
        map_links = []
    out, seen = [], set()
    for a in names:
        if a in AREAS and a not in seen:
            out.append(a); seen.add(a)
    if not out:
        return {"areas": [], "via": "none", "rule": rule, "map_links": []}
    return {"areas": out, "via": via, "rule": rule, "map_links": map_links}


def areas_for_sign(sign):
    """Areas a sign localizes to (see `mapping_for_sign` for the provenance)."""
    return mapping_for_sign(sign)["areas"]


def views_with(aid):
    """The views that draw an area — so the page can say where to look for it."""
    return [v for v in VIEW_ORDER if any(a["id"] == aid for a in VIEWS[v]["areas"])]
