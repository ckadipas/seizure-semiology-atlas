#!/usr/bin/env python3
"""
brodmann_plate.py — prepare a reference brain plate for the Brodmann map.

Two jobs that share the same segmentation, so they share the same code:

    clean  <shot.jpg> <x0> <y0> <x1> <y1> <out.png>
        Crop one panel, remove the viewer's crosshairs, cut the page background
        (and its graticule) away to alpha, and upscale. Produces the base image
        that goes in generator/assets/.

    trace  <plate.jpg> [x0 x1 y0 y1]
        Walk the silhouette boundary and print a simplified point list in the
        figure's coordinate box, for an outline in data/brodmann_map.json.

Authoring aid: not part of the build, and needs Pillow + numpy. Reference images
are never committed — only what is derived from them.
"""
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageFilter


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


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(2)
    cmd = sys.argv[1]
    if cmd == "clean":
        cmd_clean(sys.argv[2], [int(v) for v in sys.argv[3:7]], sys.argv[7])
    elif cmd == "trace":
        box = [float(v) for v in sys.argv[3:7]] if len(sys.argv) > 6 else [98, 880, 48, 548]
        cmd_trace(sys.argv[2], box)
    else:
        print(__doc__); sys.exit(2)
