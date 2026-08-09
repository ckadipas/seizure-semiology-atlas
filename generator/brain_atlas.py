#!/usr/bin/env python3
"""
brain_atlas.py — renders the Brodmann map from its data file.

This module holds **no curation**. Which areas exist, where they are drawn, where
their numerals sit and which areas a sign localizes to all live in
`data/brodmann_map.json` — edited by hand like `data/semiology_data.json`,
validated by `tools/validate_data.py`, rendered here. That keeps the map's
knowledge reviewable as data and under the same gate as the rest of the atlas,
instead of buried in generator code.

What lives here is only geometry maths: smoothing a traced point list into a
path, and reading an area's outline out of its record.
"""
import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP = json.load(open(os.path.join(_ROOT, "data", "brodmann_map.json")))

AREAS = MAP["areas"]
VIEWS = MAP["views"]
MAPPING = MAP["mapping"]
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------
def smooth_path(pts, closed=True, s=0.17):
    """Catmull-Rom through the points, emitted as cubic beziers."""
    n = len(pts)
    if n < 3:
        return "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    d = [f"M {pts[0][0]:.1f},{pts[0][1]:.1f}"]
    last = n if closed else n - 1
    for i in range(last):
        p0 = pts[(i - 1) % n] if closed else pts[max(i - 1, 0)]
        p1, p2 = pts[i % n], pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if closed else pts[min(i + 2, n - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) * s, p1[1] + (p2[1] - p0[1]) * s)
        c2 = (p2[0] - (p3[0] - p1[0]) * s, p2[1] - (p3[1] - p1[1]) * s)
        d.append(f"C {c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    if closed:
        d.append("Z")
    return " ".join(d)


def area_polygon(area):
    """
    An area's outline, traced off the reference plate by tools/brodmann_plate.py:
    it follows the boundary the plate itself draws, so the shading on screen sits
    on the anatomy rather than over it.
    """
    return [tuple(p) for p in area["points"]]


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
