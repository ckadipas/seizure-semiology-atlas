#!/usr/bin/env python3
"""
trace_outline.py — derive a brain silhouette from a reference figure.

Segments the plate (coloured tissue vs white page), removes grid lines and
annotation with a morphological opening, keeps the largest component, fills
interior holes, walks the boundary (Moore neighbourhood), simplifies it
(Ramer-Douglas-Peucker) and rescales it into the figure's coordinate box.

    python3 tools/trace_outline.py reference/brodmann_lateral.jpg 98 880 48 548

Prints a Python point list for generator/brain_atlas.py. Requires Pillow+numpy;
it is a one-off authoring aid, not part of the build.

The reference image itself is never committed — only the derived outline, which
is geometry (an anatomical fact), not the source artwork.
"""
import sys
import numpy as np
from PIL import Image, ImageFilter
from collections import deque


def silhouette(path, sat=45, dark=120, open_k=5):
    im = np.asarray(Image.open(path).convert("RGB")).astype(int)
    m = ((im.max(2) - im.min(2)) > sat) | (im.max(2) < dark)
    p = Image.fromarray((m * 255).astype(np.uint8))
    m = np.asarray(p.filter(ImageFilter.MinFilter(open_k))
                    .filter(ImageFilter.MaxFilter(open_k))) > 127
    h, w = m.shape
    seen = np.zeros_like(m, bool); best = []
    for sy in range(0, h, 3):
        for sx in range(0, w, 3):
            if not m[sy, sx] or seen[sy, sx]:
                continue
            q = deque([(sy, sx)]); seen[sy, sx] = True; comp = []
            while q:
                y, x = q.popleft(); comp.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and m[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True; q.append((ny, nx))
            if len(comp) > len(best):
                best = comp
    mm = np.zeros_like(m, bool)
    for y, x in best:
        mm[y, x] = True
    bg = ~mm; s2 = np.zeros_like(mm, bool); q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if bg[y, x] and not s2[y, x]: s2[y, x] = True; q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if bg[y, x] and not s2[y, x]: s2[y, x] = True; q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and bg[ny, nx] and not s2[ny, nx]:
                s2[ny, nx] = True; q.append((ny, nx))
    return mm | (bg & ~s2)


def boundary(mm, step=2):
    h, w = mm.shape
    ys, xs = np.where(mm)
    sy = ys.min(); sx = xs[ys == sy].min()
    nb = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    cur = (sy, sx); b = 7; out = [cur]
    for _ in range(200000):
        for i in range(8):
            d = nb[(b + 1 + i) % 8]; ny, nx = cur[0] + d[0], cur[1] + d[1]
            if 0 <= ny < h and 0 <= nx < w and mm[ny, nx]:
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


def fit(p, x0, x1, y0, y1):
    ax0, ay0, ax1, ay1 = p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max()
    return np.stack([(p[:, 0] - ax0) / (ax1 - ax0) * (x1 - x0) + x0,
                     (p[:, 1] - ay0) / (ay1 - ay0) * (y1 - y0) + y0], 1)


if __name__ == "__main__":
    src = sys.argv[1]
    box = [float(v) for v in sys.argv[2:6]] if len(sys.argv) > 5 else [98, 880, 48, 548]
    pts = fit(rdp(boundary(silhouette(src))), *box)
    print("[")
    for i in range(0, len(pts), 6):
        print("    " + ", ".join(f"({p[0]:.0f}, {p[1]:.0f})" for p in pts[i:i + 6]) + ",")
    print("]")
