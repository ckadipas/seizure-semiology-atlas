#!/usr/bin/env python3
"""
brain_atlas.py — renders the Brodmann map from its data file.

This module holds **no curation**. Which areas exist, where they are drawn, where
their numerals sit and which areas a sign localizes to all live in
`data/brodmann_map.json` — edited by hand like `data/semiology_data.json`,
validated by `tools/validate_data.py`, rendered here. That keeps the map's
knowledge reviewable as data and under the same gate as the rest of the atlas,
instead of buried in generator code.

What lives here is only geometry maths: smoothing a point list into a path,
growing a polygon so neighbours overlap, and turning a band spec into a polygon.
"""
import json
import os
from math import hypot

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


def _signed_area(pts):
    a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]; x1, y1 = pts[(i + 1) % len(pts)]
        a += x0 * y1 - x1 * y0
    return a / 2.0


def inflate(pts, d=7.0):
    """
    Grow a polygon ~d px along each vertex normal. Every area is inflated, so
    neighbours overlap rather than abut: with the painter's-order draw the later
    area's edge becomes the visible seam and hairline gaps cannot appear.
    """
    n = len(pts)
    if n < 3:
        return pts
    sgn = 1.0 if _signed_area(pts) > 0 else -1.0
    out = []
    for i in range(n):
        px, py = pts[(i - 1) % n]
        cx, cy = pts[i]
        nx, ny = pts[(i + 1) % n]
        e1x, e1y, e2x, e2y = cx - px, cy - py, nx - cx, ny - cy
        l1 = hypot(e1x, e1y) or 1.0
        l2 = hypot(e2x, e2y) or 1.0
        n1 = (e1y / l1 * sgn, -e1x / l1 * sgn)
        n2 = (e2y / l2 * sgn, -e2x / l2 * sgn)
        bx, by = n1[0] + n2[0], n1[1] + n2[1]
        bl = hypot(bx, by)
        if bl < 1e-6:
            bx, by, bl = n2[0], n2[1], 1.0
        out.append((round(cx + bx / bl * d, 1), round(cy + by / bl * d, 1)))
    return out


def margin_x(margin, y):
    """Lateral margin x at a given y, interpolated down the outline."""
    for i in range(len(margin) - 1):
        (x0, y0), (x1, y1) = margin[i], margin[i + 1]
        if y0 <= y <= y1:
            t = 0.0 if y1 == y0 else (y - y0) / (y1 - y0)
            return x0 + (x1 - x0) * t
    return margin[-1][0] if y > margin[-1][1] else margin[0][0]


def band(margin, y0, y1, f0, f1, mid, steps=7, over=26):
    """Transverse band of a hemisphere, between fractional distances f0..f1."""
    pts = []
    ys = [y0 + (y1 - y0) * i / steps for i in range(steps + 1)]
    for y in ys:
        x = mid - f1 * (mid - margin_x(margin, y))
        pts.append((x - (over if f1 >= 0.999 else 0), y))
    for y in reversed(ys):
        pts.append((mid - f0 * (mid - margin_x(margin, y)), y))
    return pts


def area_polygon(view, area):
    """The polygon for one area in one view, however that view defines it."""
    if "points" in area:
        return [tuple(p) for p in area["points"]]
    y0, y1, f0, f1 = area["band"]
    return band([tuple(p) for p in view["margin"]], y0, y1, f0, f1, view["mid"])


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
