#!/usr/bin/env python3
"""
brodmann_plate.py — prepare a reference brain plate for the Brodmann map.

Three jobs that share the same segmentation, so they share the same code:

    clean  <shot.jpg> <x0> <y0> <x1> <y1> <out.png>
        Crop one panel, remove the viewer's crosshairs, cut the page background
        (and its graticule) away to alpha, and upscale. Produces the base image
        that goes in generator/assets/.

    trace  <plate.jpg> [x0 x1 y0 y1]
        Walk the silhouette boundary and print a simplified point list in the
        figure's coordinate box, for an outline in data/brodmann_map.json.

    regions <view> [view ...]        (or "all")
        Read each area's numeral position out of data/brodmann_map.json, grow it
        across the plate until it meets a drawn boundary or a change of tint, and
        write the resulting outline back as that area's `points`. The plate does
        not draw one patch per Brodmann area — a single drawn region often spans
        several — so where a patch holds more than one numeral it is subdivided
        between them, each keeping the drawn edge as its outer border.

Authoring aid: not part of the build, and needs Pillow + numpy. Reference images
are never committed — only what is derived from them.
"""
import json
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---- shared segmentation -------------------------------------------------
def tissue_mask(a8, sat=22, dark=170, close=9):
    """Coloured tissue or dark ink, excluding the pale grey graticule."""
    mx, mn = a8.max(2), a8.min(2)
    m = ((mx - mn) > sat) | (mx < dark)
    p = Image.fromarray((m * 255).astype(np.uint8))
    return np.asarray(p.filter(ImageFilter.MaxFilter(close))
                       .filter(ImageFilter.MinFilter(close))) > 127


def largest_component(m, step=5):
    h, w = m.shape
    seen = np.zeros_like(m, bool); best = []
    for sy in range(0, h, step):
        for sx in range(0, w, step):
            if not m[sy, sx] or seen[sy, sx]:
                continue
            q = deque([(sy, sx)]); seen[sy, sx] = True; c = []
            while q:
                y, x = q.popleft(); c.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and m[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True; q.append((ny, nx))
            if len(c) > len(best):
                best = c
    out = np.zeros_like(m, bool)
    for y, x in best:
        out[y, x] = True
    return out


def fill_holes(m):
    h, w = m.shape
    bg = ~m; seen = np.zeros_like(m, bool); q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if bg[y, x] and not seen[y, x]: seen[y, x] = True; q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if bg[y, x] and not seen[y, x]: seen[y, x] = True; q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and bg[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True; q.append((ny, nx))
    return m | (bg & ~seen)


def silhouette(a8, **kw):
    return fill_holes(largest_component(tissue_mask(a8, **kw)))


# ---- clean ---------------------------------------------------------------
def de_line(a):
    """Crosshairs are full-length straight lines: rebuild them by interpolation."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    bl = (b - np.maximum(r, g)) > 8
    for axis in (0, 1):
        frac = bl.mean(axis=axis)
        bad = set(np.where(frac > 0.45)[0].tolist())
        for i in sorted(bad):
            lo = i - 1
            while lo >= 0 and lo in bad: lo -= 1
            hi = i + 1
            while hi < len(frac) and hi in bad: hi += 1
            if lo < 0 or hi >= len(frac):
                continue
            t = (i - lo) / (hi - lo)
            if axis == 0: a[:, i] = a[:, lo] * (1 - t) + a[:, hi] * t
            else:         a[i, :] = a[lo, :] * (1 - t) + a[hi, :] * t
    return a


def cmd_clean(src, box, dst, scale=2):
    a = np.asarray(Image.open(src).convert("RGB").crop(box)).astype(float)
    a8 = np.clip(de_line(a), 0, 255).astype(np.uint8)
    al = silhouette(a8)
    alim = Image.fromarray((al * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.4))
    out = Image.fromarray(np.dstack([a8, np.asarray(alim)]), "RGBA")
    ys, xs = np.where(al)
    out = out.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    out = out.resize((out.width * scale, out.height * scale), Image.LANCZOS)
    out.save(dst)
    print(dst, out.size)


# ---- trace ---------------------------------------------------------------
def boundary(m, step=2):
    h, w = m.shape
    ys, xs = np.where(m)
    sy = ys.min(); sx = xs[ys == sy].min()
    nb = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    cur = (sy, sx); b = 7; out = [cur]
    for _ in range(200000):
        for i in range(8):
            d = nb[(b + 1 + i) % 8]; ny, nx = cur[0] + d[0], cur[1] + d[1]
            if 0 <= ny < h and 0 <= nx < w and m[ny, nx]:
                b = (b + 1 + i + 4) % 8; cur = (ny, nx); out.append(cur); break
        else:
            break
        if cur == (sy, sx) and len(out) > 10:
            break
    return np.array([(x, y) for y, x in out[::step]], float)


def rdp(pts, eps=3.0):
    keep = np.zeros(len(pts), bool); keep[0] = keep[-1] = True
    st = [(0, len(pts) - 1)]
    while st:
        i, j = st.pop()
        if j <= i + 1:
            continue
        a, bb = pts[i], pts[j]; ab = bb - a; L = np.hypot(*ab); seg = pts[i + 1:j] - a
        d = (np.abs(ab[0] * seg[:, 1] - ab[1] * seg[:, 0]) / L) if L > 1e-9 \
            else np.hypot(seg[:, 0], seg[:, 1])
        k = int(np.argmax(d))
        if d[k] > eps:
            keep[i + 1 + k] = True; st += [(i, i + 1 + k), (i + 1 + k, j)]
    return pts[keep]


def cmd_trace(src, box):
    a8 = np.asarray(Image.open(src).convert("RGB"))
    p = rdp(boundary(silhouette(a8, sat=45, dark=120, close=5)))
    x0, x1, y0, y1 = box
    ax0, ay0, ax1, ay1 = p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max()
    p = np.stack([(p[:, 0] - ax0) / (ax1 - ax0) * (x1 - x0) + x0,
                  (p[:, 1] - ay0) / (ay1 - ay0) * (y1 - y0) + y0], 1)
    print("[")
    for i in range(0, len(p), 6):
        print("  " + ", ".join(f"[{q[0]:.0f}, {q[1]:.0f}]" for q in p[i:i + 6]) + ",")
    print("]")


# ---- regions -------------------------------------------------------------
def undraw_lines(a, thr=-7, reach=7, rounds=2):
    """
    The plate carries a measuring graticule and a pair of crosshairs. They are
    perfectly straight and span the whole plate, so they are the one thing in the
    picture that can be found by its geometry alone: rebuild each affected row or
    column from its neighbours. The published image keeps them — this is only so
    they cannot cut a region in two during segmentation.
    """
    for _ in range(rounds):
        for axis in (1, 0):
            n = a.shape[1] if axis == 1 else a.shape[0]
            prof = a.mean(axis=0) if axis == 1 else a.mean(axis=1)
            dev = np.zeros(n)
            for i in range(reach, n - reach):
                dev[i] = (prof[i] - (prof[i - reach] + prof[i + reach]) / 2).mean()
            bad = set(np.where(dev < thr)[0].tolist())
            for i in list(bad):            # a translucent line fades at its edges
                bad.update(p for p in (i - 2, i - 1, i + 1, i + 2) if 0 <= p < n)
            for i in sorted(bad):
                lo = i - 1
                while lo >= 0 and lo in bad: lo -= 1
                hi = i + 1
                while hi < n and hi in bad: hi += 1
                if lo < 0 or hi >= n:
                    continue
                t = (i - lo) / (hi - lo)
                if axis == 1: a[:, i] = a[:, lo] * (1 - t) + a[:, hi] * t
                else:         a[i, :] = a[lo, :] * (1 - t) + a[hi, :] * t
        a = np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
                       .filter(ImageFilter.MedianFilter(3))).astype(float)
    return a


def plate_layers(path, dil=7, ink=22):
    """The plate as the segmenter sees it: tissue, drawn boundaries, flat tint."""
    a = np.asarray(Image.open(path).convert("RGB")).astype(float)
    a = np.clip(undraw_lines(a), 0, 255).astype(np.uint8)
    a = np.asarray(Image.fromarray(a).filter(ImageFilter.MedianFilter(5)))
    brain = fill_holes(largest_component(a.min(2).astype(int) < 244, step=7))
    g = np.asarray(Image.fromarray(a).convert("L")).astype(int)
    loc = np.asarray(Image.fromarray(g.astype(np.uint8))
                     .filter(ImageFilter.MedianFilter(11))).astype(int)
    # a boundary is ink that is dark against its own surroundings; the finer
    # sulcal shading in the drawing is lighter and stays out of the mask
    line = ((loc - g) > ink) & brain
    if dil > 1:
        line = np.asarray(Image.fromarray((line * 255).astype(np.uint8))
                          .filter(ImageFilter.MaxFilter(dil))) > 127
    tint = np.asarray(Image.fromarray(a).filter(ImageFilter.MedianFilter(7)))
    return a, brain, line, tint


def grow(seeds, brain, line, tint, tol=44, step=13):
    """
    Every numeral claims outward at the same rate. A claim crosses into a pixel
    only if it is not a drawn boundary and either still matches the numeral's own
    tint or differs from where it came from by no more than a shading gradient —
    so a change of colour stops it just as a drawn line does. Whatever no claim
    reaches (the boundaries themselves, and any patch holding no numeral) then
    goes to its nearest claimant, leaving the surface exactly tiled.
    """
    h, w = brain.shape
    t = tint.astype(np.int16)
    cols = np.stack([t[y, x] for y, x in seeds]).astype(np.int16)
    lab = np.full((h, w), -1, np.int16)
    q = deque()
    for i, (y, x) in enumerate(seeds):
        lab[y, x] = i; q.append((y, x))
    free = brain & ~line
    while q:
        y, x = q.popleft(); i = lab[y, x]; c = cols[i]
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and lab[ny, nx] < 0 and free[ny, nx]:
                d = t[ny, nx] - c; e = t[ny, nx] - t[y, x]
                if (d * d).sum() <= tol * tol or (e * e).sum() <= step * step:
                    lab[ny, nx] = i; q.append((ny, nx))
    reached = int((lab >= 0).sum())
    q = deque(zip(*np.where(lab >= 0)))
    while q:
        y, x = q.popleft(); i = lab[y, x]
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and lab[ny, nx] < 0 and brain[ny, nx]:
                lab[ny, nx] = i; q.append((ny, nx))
    return lab, reached


def _boxsum(m, r):
    c = np.cumsum(np.cumsum(np.pad(m.astype(np.int32), ((1, 0), (1, 0))), 0), 1)
    h, w = m.shape
    y0 = np.clip(np.arange(h) - r, 0, h); y1 = np.clip(np.arange(h) + r + 1, 0, h)
    x0 = np.clip(np.arange(w) - r, 0, w); x1 = np.clip(np.arange(w) + r + 1, 0, w)
    return (c[np.ix_(y1, x1)] - c[np.ix_(y0, x1)] - c[np.ix_(y1, x0)] + c[np.ix_(y0, x0)])


def smooth_labels(lab, brain, k=9, rounds=2):
    """Majority vote over a window: drops the seams left where a line was rebuilt."""
    n = int(lab.max()) + 1
    for _ in range(rounds):
        best = np.full(lab.shape, -1, np.int32); score = np.zeros(lab.shape, np.int32)
        for i in range(n):
            s = _boxsum(lab == i, k // 2)
            take = s > score
            best[take] = i; score[take] = s[take]
        lab = np.where(brain & (best >= 0), best, lab).astype(np.int16)
    return lab


def cmd_regions(views, tol=44, eps=3.2):
    path = os.path.join(ROOT, "data", "brodmann_map.json")
    doc = json.load(open(path))
    for view in views:
        v = doc["views"][view]; box = v["image"]
        plate = os.path.join(ROOT, "generator", "assets", box["file"])
        a, brain, line, tint = plate_layers(plate)
        h, w = brain.shape
        if v.get("mirror"):
            # the renderer draws one hemisphere and mirrors it about the midline,
            # so only the side the numerals sit on is segmented
            cut = int(round((v["mid"] - box["x"]) / box["w"] * w))
            brain = brain & (np.arange(w)[None, :] < cut)
        ids, seeds = [], []
        for ar in v["areas"]:
            lab_xy = ar.get("label")
            if not lab_xy:
                print(f"  {view} {ar['id']}: no numeral position — left as it was"); continue
            x = int(round((lab_xy[0] - box["x"]) / box["w"] * w))
            y = int(round((lab_xy[1] - box["y"]) / box["h"] * h))
            if not (0 <= y < h and 0 <= x < w) or not brain[y, x]:
                # seed inside the cortex, not on its rim, or the area has no room to grow
                inner = np.asarray(Image.fromarray((brain * 255).astype(np.uint8))
                                   .filter(ImageFilter.MinFilter(31))) > 127
                ys, xs = np.where(inner if inner.any() else brain)
                k = int(np.argmin((ys - y) ** 2 + (xs - x) ** 2))
                print(f"  {view} {ar['id']}: numeral sits off the plate's brain at ({x},{y}) — "
                      f"seeded at the nearest cortex ({xs[k]},{ys[k]}); move the numeral")
                y, x = int(ys[k]), int(xs[k])
            elif line[y, x]:
                yy, xx = np.mgrid[max(0, y - 30):y + 31, max(0, x - 30):x + 31]
                m = (brain & ~line)[max(0, y - 30):y + 31, max(0, x - 30):x + 31]
                if m.any():
                    d = np.where(m, (yy - y) ** 2 + (xx - x) ** 2, 10 ** 9)
                    i = np.unravel_index(np.argmin(d), d.shape)
                    y, x = int(yy[i]), int(xx[i])
            ids.append(ar["id"]); seeds.append((y, x))
        lab, reached = grow(seeds, brain, line, tint, tol=tol)
        raw = lab.copy()
        lab = smooth_labels(lab, brain)
        # a small area can be voted away wholesale by its larger neighbours
        for i in range(len(ids)):
            if not (lab == i).any():
                lab[raw == i] = i
                print(f"  {view} {ids[i]}: too small to survive smoothing — kept its raw outline")
        print(f"{view}: {len(ids)} areas over {brain.sum()} px; "
              f"{100 * reached / max(1, brain.sum()):.0f}% claimed at the drawn edges, rest by nearest")
        by_id = {ar["id"]: ar for ar in v["areas"]}
        for i, aid in enumerate(ids):
            m = largest_component(lab == i, step=3)
            if not m.any():
                print(f"  {view} {aid}: empty after segmentation — left as it was"); continue
            p = rdp(boundary(fill_holes(m)), eps=eps)
            pts = [[round(px / w * box["w"] + box["x"], 1),
                    round(py / h * box["h"] + box["y"], 1)] for px, py in p]
            ar = by_id[aid]
            ar.pop("band", None); ar.pop("small", None)
            ar["points"] = pts
        v["areas"] = [by_id[ar["id"]] for ar in v["areas"]]
    with open(path, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("wrote", os.path.relpath(path, ROOT))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(2)
    cmd = sys.argv[1]
    if cmd == "clean":
        cmd_clean(sys.argv[2], [int(v) for v in sys.argv[3:7]], sys.argv[7])
    elif cmd == "trace":
        box = [float(v) for v in sys.argv[3:7]] if len(sys.argv) > 6 else [98, 880, 48, 548]
        cmd_trace(sys.argv[2], box)
    elif cmd == "regions":
        names = sys.argv[2:]
        if names == ["all"]:
            names = list(json.load(open(os.path.join(ROOT, "data", "brodmann_map.json")))["views"])
        cmd_regions(names)
    else:
        print(__doc__); sys.exit(2)
