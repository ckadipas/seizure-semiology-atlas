#!/usr/bin/env python3
"""
brain_atlas.py — renders the Brodmann map from its data file.

This module holds **no scientific curation**. Area definitions and sign links
come from the generated canonical atlas bundle. The surface-view coordinates
are presentation data carried in that same redacted bundle.

A view is a reference plate and the numerals placed on it, so there is no
geometry left to compute here: this loads the map and answers which areas a sign
localizes to, and why.
"""
import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_ROOT, "data", "atlas_bundle.json"), encoding="utf-8") as stream:
    MAP = json.load(stream)["brodmann"]

AREAS = MAP["areas"]
VIEWS = MAP["views"]
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
    drift). `via="sub"` — the sign inherits the rule for its sub-region, and
    `rule` is that sub-region. `via="none"` — no areas; `rule` carries the reason
    if one is declared under `mapping.unmapped`.

    Returning the provenance beside the ids is what lets the page state why a
    sign highlights where it does, rather than asserting it.
    """
    sid = str(sign.get("id"))
    entry = MAPPING["by_sign"].get(sid)
    if entry:
        names, via, rule = entry["areas"], "sign", entry.get("sign", "")
    else:
        rule = sign.get("sub", "")
        names, via = MAPPING["by_sub"].get(rule, []), "sub"
    out, seen = [], set()
    for a in names:
        if a in AREAS and a not in seen:
            out.append(a); seen.add(a)
    if not out:
        return {"areas": [], "via": "none", "rule": MAPPING["unmapped"].get(sid, "")}
    return {"areas": out, "via": via, "rule": rule}


def areas_for_sign(sign):
    """Areas a sign localizes to (see `mapping_for_sign` for the provenance)."""
    return mapping_for_sign(sign)["areas"]


def views_with(aid):
    """The views that draw an area — so the page can say where to look for it."""
    return [v for v, spec in VIEWS.items() if any(a["id"] == aid for a in spec["areas"])]
