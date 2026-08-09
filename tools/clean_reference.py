#!/usr/bin/env python3
"""
clean_reference.py — turn a screenshot of a reference brain atlas plate into a
clean, transparent, high-resolution base image.

    python3 tools/clean_reference.py shot.jpg 30 60 1180 760 out.png

Steps: crop the panel; remove the viewer's crosshairs (full-length straight lines
are detected by the fraction of blue-ish pixels along a row/column and rebuilt by
interpolating from the nearest clean neighbours); segment the brain (coloured
tissue or dark ink, excluding the pale grey graticule); keep the largest
component and fill interior holes; use that as an alpha channel so the page
background and its grid disappear entirely; then upscale 2x with Lanczos.

Authoring aid, not part of the build. Requires Pillow + numpy. Reference images
are never committed - only what is derived from them.
"""
import sys
import numpy as np
from PIL import Image, ImageFilter
from collections import deque


def de_line(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    bl = (b - np.maximum(r, g)) > 8
    for axis in (0, 1):
        frac = bl.mean(axis=axis)
        bad = set(np.where(frac > 0.45)[0].tolist())
        for i in sorted(bad):
            lo = i - 1
            while lo >= 0 and lo in bad:
                lo -= 1
            hi = i + 1
            while hi < len(frac) and hi in bad:
                hi += 1
            if lo < 0 or hi >= len(frac):
                continue
            t = (i - lo) / (hi - lo)
            if axis == 0:
                a[:, i] = a[:, lo] * (1 - t) + a[:, hi] * t
            else:
                a[i, :] = a[lo, :] * (1 - t) + a[hi, :] * t
    return a


def alpha_of(a8):
    mx, mn = a8.max(2), a8.min(2)
    m = ((mx - mn) > 22) | (mx < 170)          # tissue or ink; grey graticule excluded
    p = Image.fromarray((m * 255).astype(np.uint8))
    m = np.asarray(p.filter(ImageFilter.MaxFilter(9))
                    .filter(ImageFilter.MinFilter(9))) > 127
    h, w = m.shape
    seen = np.zeros_like(m, bool); best = []
    for sy in range(0, h, 5):
        for sx in range(0, w, 5):
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


if __name__ == "__main__":
    src, box, dst = sys.argv[1], [int(v) for v in sys.argv[2:6]], sys.argv[6]
    a = np.asarray(Image.open(src).convert("RGB").crop(box)).astype(float)
    a8 = np.clip(de_line(a), 0, 255).astype(np.uint8)
    al = alpha_of(a8)
    alim = Image.fromarray((al * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.4))
    out = Image.fromarray(np.dstack([a8, np.asarray(alim)]), "RGBA")
    ys, xs = np.where(al)
    out = out.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    out = out.resize((out.width * 2, out.height * 2), Image.LANCZOS)
    out.save(dst)
    print(dst, out.size)
