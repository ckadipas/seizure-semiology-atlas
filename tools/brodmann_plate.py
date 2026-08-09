#!/usr/bin/env python3
"""
brodmann_plate.py — prepare a reference brain plate for the Brodmann map.

One job:

    clean  <shot.jpg> <x0> <y0> <x1> <y1> <out.png>
        Crop one panel, remove the viewer's crosshairs, cut the page background
        (and its graticule) away to alpha, and upscale. Produces the base image
        that goes in generator/assets/.

    The map draws nothing over the plate — a view is the plate and its numerals,
    and the numerals are positioned in the page's own editor at #edit-labels — so
    there is no outline to trace or segment here.

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


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] != "clean":
        print(__doc__); sys.exit(2)
    cmd_clean(sys.argv[2], [int(v) for v in sys.argv[3:7]], sys.argv[7])
