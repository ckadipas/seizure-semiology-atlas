#!/usr/bin/env python3
"""
brain_atlas.py — geometry and semiology mapping for the interactive Brodmann figure.

Four schematic surface views of one hemisphere (lateral, medial, dorsal, ventral)
are drawn as tiled Brodmann areas, following the conventions of the classic
Brodmann plates: every area carries its number, boundaries *between* lobes are
solid and boundaries *within* a lobe are dashed.

Each tile is a hand-placed polygon, inflated so neighbours overlap (hairline gaps
between areas are impossible) and trimmed by an SVG clipPath, so the brain edge is
always exactly the silhouette curve.

Nothing here is copyrighted figure content: the outlines are schematic drawings
authored for this atlas, and the area/sign mapping is derived from the dataset's
own localization fields.
"""
from math import hypot

# --------------------------------------------------------------------------
# Brodmann tiles. `lobe` drives the solid-vs-dashed boundary convention.
# --------------------------------------------------------------------------
def _T(label, bas, lobe, name, buried=False):
    return dict(label=label, bas=bas, lobe=lobe, name=name, buried=buried)

TILE_INFO = {
    # ---- frontal ----
    "4":  _T("4",  [4],  "Frontal", "Primary motor cortex (precentral gyrus)"),
    "6":  _T("6",  [6],  "Frontal", "Premotor cortex & supplementary motor area (SMA)"),
    "8":  _T("8",  [8],  "Frontal", "Frontal eye field"),
    "9":  _T("9",  [9],  "Frontal", "Dorsolateral prefrontal cortex"),
    "10": _T("10", [10], "Frontal", "Frontopolar cortex"),
    "11": _T("11", [11], "Frontal", "Orbitofrontal cortex"),
    "44": _T("44", [44], "Frontal", "Pars opercularis (Broca's area)"),
    "45": _T("45", [45], "Frontal", "Pars triangularis (Broca's area)"),
    "46": _T("46", [46], "Frontal", "Dorsolateral prefrontal cortex (middle frontal gyrus)"),
    "47": _T("47", [47], "Frontal", "Pars orbitalis / lateral orbitofrontal cortex"),
    # ---- parietal ----
    "3":  _T("3",  [3],  "Parietal", "Primary somatosensory cortex (area 3)"),
    "1":  _T("1",  [1],  "Parietal", "Primary somatosensory cortex (area 1)"),
    "2":  _T("2",  [2],  "Parietal", "Primary somatosensory cortex (area 2)"),
    "5":  _T("5",  [5],  "Parietal", "Superior parietal lobule (somatosensory association)"),
    "7":  _T("7",  [7],  "Parietal", "Superior parietal lobule / precuneus"),
    "39": _T("39", [39], "Parietal", "Angular gyrus (temporo-parietal junction)"),
    "40": _T("40", [40], "Parietal", "Supramarginal gyrus"),
    "43": _T("43", [43], "Parietal", "Subcentral area / parietal operculum (S2, gustatory)"),
    # ---- temporal ----
    "20": _T("20", [20], "Temporal", "Inferior temporal gyrus"),
    "21": _T("21", [21], "Temporal", "Middle temporal gyrus"),
    "22": _T("22", [22], "Temporal", "Superior temporal gyrus (Wernicke's area posteriorly)"),
    "37": _T("37", [37], "Temporal", "Fusiform / occipitotemporal gyrus"),
    "38": _T("38", [38], "Temporal", "Temporal pole"),
    "41": _T("41", [41], "Temporal", "Primary auditory cortex (Heschl's gyrus)"),
    "42": _T("42", [42], "Temporal", "Auditory association cortex (planum temporale)"),
    "28": _T("28", [28], "Temporal", "Entorhinal cortex"),
    "34": _T("34", [34], "Temporal", "Uncus / periamygdaloid cortex"),
    "35": _T("35", [35], "Temporal", "Perirhinal cortex"),
    "36": _T("36", [36], "Temporal", "Parahippocampal / ectorhinal cortex"),
    # ---- occipital ----
    "17": _T("17", [17], "Occipital", "Primary visual cortex (V1, calcarine)"),
    "18": _T("18", [18], "Occipital", "Secondary visual cortex (V2)"),
    "19": _T("19", [19], "Occipital", "Associative visual cortex (V3/V4/V5-MT)"),
    # ---- limbic / cingulate (medial surface) ----
    "24": _T("24", [24], "Limbic", "Anterior & mid-cingulate cortex"),
    "32": _T("32", [32], "Limbic", "Dorsal anterior cingulate (area 32)"),
    "25": _T("25", [25], "Limbic", "Subgenual cingulate (area 25)"),
    "23": _T("23", [23], "Limbic", "Posterior cingulate cortex"),
    "31": _T("31", [31], "Limbic", "Dorsal posterior cingulate"),
    # ---- buried / non-cortical ----
    "insula":  _T("INS", [13, 14, 15, 16], "Insular",
                  "Insular cortex (deep to the fronto-parieto-temporal operculum)", True),
    "subcort": _T("SUB", [], "Deep/Subcortical",
                  "Deep subcortical (hypothalamic hamartoma)", True),
}

# --------------------------------------------------------------------------
# geometry helpers
# --------------------------------------------------------------------------
def _push(p, cx, cy, amt):
    dx, dy = p[0] - cx, p[1] - cy
    L = hypot(dx, dy) or 1.0
    return (round(p[0] + dx / L * amt, 1), round(p[1] + dy / L * amt, 1))


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


def centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def _signed_area(pts):
    a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]; x1, y1 = pts[(i + 1) % len(pts)]
        a += x0 * y1 - x1 * y0
    return a / 2.0


def inflate(pts, d=5.0):
    """Grow a polygon ~d px along each vertex normal so neighbours overlap."""
    n = len(pts)
    if n < 3:
        return pts
    sgn = 1.0 if _signed_area(pts) > 0 else -1.0
    out = []
    for i in range(n):
        px, py = pts[(i - 1) % n]
        cx, cy = pts[i]
        nx, ny = pts[(i + 1) % n]
        e1x, e1y = cx - px, cy - py
        e2x, e2y = nx - cx, ny - cy
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


# ==========================================================================
# LATERAL VIEW — left hemisphere, anterior LEFT.  viewBox 1000 x 620
# ==========================================================================
LAT_C = (500, 300)
def L(p, amt=36):
    return _push(p, LAT_C[0], LAT_C[1], amt)

LAT_OUTLINE = [
    (98, 278), (106, 230), (126, 176), (164, 132), (216, 98), (286, 76), (352, 58),
    (430, 50), (508, 50), (582, 58), (650, 74), (712, 100), (766, 136), (812, 182),
    (848, 236), (872, 296), (880, 354), (868, 410), (842, 450), (806, 478), (772, 498),
    (716, 518), (650, 536), (580, 546), (510, 548), (444, 540), (390, 522), (346, 494),
    (316, 454), (300, 412), (296, 384), (312, 354), (330, 340),      # temporal pole
    (300, 352), (256, 364), (206, 364), (160, 350), (120, 326),      # orbital margin
]

LAT_SYLVIAN = [(330, 340), (392, 352), (460, 362), (530, 368), (600, 366), (664, 356),
               (716, 338), (748, 314)]

LATERAL_TILES = [
    ("10", [L((216, 98)), L((164, 132)), L((126, 176)), L((106, 230)), L((98, 278)),
            L((120, 326)), (166, 342), (206, 330), (216, 262), (222, 180)], (158, 232)),
    ("11", [(166, 342), L((120, 326)), L((160, 350)), L((206, 364)), (232, 356),
            (206, 330)], (176, 348)),
    ("8",  [(216, 98), L((286, 76)), (352, 58), (344, 132), (334, 202), (296, 208),
            (222, 180)], (288, 142)),
    ("6",  [(352, 58), L((420, 52)), (452, 51), (438, 130), (424, 206), (414, 258),
            (412, 300), (340, 300), (334, 202), (344, 132)], (400, 152)),
    ("9",  [(296, 208), (334, 202), (340, 300), (292, 306)], (316, 254)),
    ("46", [(222, 180), (296, 208), (292, 306), (210, 300)], (252, 244)),
    ("47", [(210, 300), (292, 306), (288, 348), (232, 356), (206, 330)], (248, 328)),
    ("45", [(292, 306), (340, 300), (348, 346), (300, 352), (288, 348)], (318, 326)),
    ("44", [(340, 300), (412, 300), (414, 340), (392, 352), (348, 346)], (376, 322)),
    ("4",  [(452, 51), L((494, 50)), (520, 50), (508, 130), (496, 206), (488, 270),
            (486, 306), (412, 300), (414, 258), (424, 206), (438, 130)], (468, 172)),
    ("3",  [(520, 50), (556, 51), (544, 128), (532, 204), (524, 268), (522, 306),
            (486, 306), (488, 270), (496, 206), (508, 130)], (522, 158)),
    ("1",  [(556, 51), (588, 53), (576, 128), (564, 202), (556, 266), (554, 304),
            (522, 306), (524, 268), (532, 204), (544, 128)], (556, 158)),
    ("2",  [(588, 53), (620, 57), (608, 130), (596, 204), (588, 264), (586, 302),
            (554, 304), (556, 266), (564, 202), (576, 128)], (588, 158)),
    ("43", [(412, 300), (486, 306), (488, 336), (444, 348), (414, 340)], (450, 324)),
    ("5",  [(620, 57), L((656, 66)), (674, 74), (660, 144), (646, 212), (638, 268),
            (588, 264), (596, 204), (608, 130)], (632, 152)),
    ("40", [(586, 302), (638, 268), (702, 298), (694, 340), (600, 366), (586, 352)],
           (640, 320)),
    ("7",  [(674, 74), L((732, 112)), (778, 150), (766, 212), (752, 272), (702, 298),
            (638, 268), (646, 212), (660, 144)], (714, 188)),
    ("39", [(702, 298), (752, 272), (742, 330), (716, 338), (694, 340)], (724, 312)),
    ("19", [(778, 150), L((812, 182)), (838, 220), (828, 288), (816, 350), (806, 408),
            (788, 460), (752, 496), (722, 460), (730, 392), (742, 330), (752, 272),
            (766, 212)], (784, 292)),
    ("18", [(838, 220), L((872, 296)), L((880, 354)), (816, 350), (828, 288)], (850, 286)),
    ("17", [L((880, 354)), L((870, 412)), L((846, 468)), L((806, 506)), (752, 496),
            (788, 460), (806, 408), (816, 350)], (836, 412)),
    # ---- temporal lobe ----
    ("38", [(330, 340), (392, 352), (386, 418), (390, 496), L((344, 470)),
            L((308, 412)), L((298, 358))], (348, 414)),
    ("22", [(392, 352), (460, 362), (530, 368), (600, 366), (664, 356), (700, 352),
            (704, 398), (398, 412)], (644, 384)),
    ("21", [(398, 412), (704, 398), (708, 452), (392, 464)], (556, 434)),
    ("20", [(392, 464), (708, 452), (716, 510), L((656, 542)), L((510, 554)),
            L((420, 536)), (378, 490)], (552, 500)),
    ("37", [(700, 352), (730, 348), (730, 390), (722, 462), (752, 496), L((726, 542)),
            (716, 510), (708, 452), (704, 398)], (712, 424)),
    # auditory areas on the supratemporal plane, inside the Sylvian
    ("41", [(468, 362), (520, 366), (518, 388), (466, 384)], (492, 375)),
    ("42", [(520, 366), (572, 368), (570, 390), (518, 388)], (544, 378)),
]

# boundaries between lobes are drawn solid (everything else is dashed)
LAT_SOLID = [
    [(520, 50), (508, 130), (496, 206), (488, 270), (486, 306)],           # central sulcus
    [(412, 300), (486, 306), (586, 302), (638, 268)],                      # frontal|parietal foot
    LAT_SYLVIAN,                                                            # Sylvian fissure
    [(778, 150), (766, 212), (752, 272), (742, 330), (730, 392), (722, 462),
     (752, 496)],                                                           # parieto/temporo-occipital
]

# ==========================================================================
# MEDIAL VIEW — left hemisphere seen from the midline, anterior LEFT. 1000 x 620
# ==========================================================================
MED_C = (490, 300)
def M(p, amt=34):
    return _push(p, MED_C[0], MED_C[1], amt)

MED_OUTLINE = [
    (100, 290), (108, 232), (130, 178), (168, 134), (220, 100), (286, 74), (358, 56),
    (436, 48), (514, 48), (588, 56), (656, 72), (716, 100), (770, 138), (816, 186),
    (850, 242), (872, 302), (878, 358), (866, 410), (842, 450), (806, 480), (766, 502),
    (716, 520), (660, 534), (600, 542), (540, 544), (480, 538), (424, 524), (384, 502),
    (352, 472), (340, 432), (360, 392),                       # temporal pole (medial)
    (340, 380), (312, 372), (300, 372),                       # notch below the frontal
    (272, 364), (236, 350), (192, 332), (148, 314), (116, 300),
]

# corpus callosum + diencephalon: anatomy, not cortex — drawn grey, not clickable
MED_CORE = [(412, 340), (436, 306), (482, 286), (544, 282), (600, 294), (638, 318),
            (652, 348), (640, 378), (600, 396), (546, 402), (494, 396), (450, 382),
            (420, 364)]

MEDIAL_TILES = [
    ("10", [M((100, 290)), M((108, 232)), M((130, 178)), M((168, 134)), (214, 108),
            (224, 188), (216, 262), (204, 316), M((148, 314)), M((116, 300))], (160, 228)),
    ("9",  [(214, 108), M((286, 74)), (318, 64), (310, 148), (300, 228), (288, 300),
            (204, 316), (216, 262), (224, 188)], (256, 192)),
    ("8",  [(310, 148), (318, 64), (374, 56), (368, 138), (366, 236), (300, 228)], (338, 152)),
    ("6",  [(374, 56), (452, 50), (444, 150), (436, 244), (366, 236), (368, 138)], (406, 148)),
    ("4",  [(452, 50), (516, 48), (508, 150), (500, 240), (436, 244), (444, 150)], (476, 146)),
    ("3",  [(516, 48), (552, 50), (544, 150), (536, 238), (500, 240), (508, 150)], (526, 142)),
    ("5",  [(552, 50), (596, 54), (588, 150), (578, 236), (536, 238), (544, 150)], (566, 142)),
    ("7",  [(596, 54), M((656, 72)), M((716, 100)), (756, 150), (748, 214), (722, 262),
            (660, 262), (600, 240), (578, 236), (588, 150)], (664, 168)),
    ("31", [(624, 278), (660, 262), (722, 262), (716, 312), (656, 322), (632, 322)], (678, 292)),
    ("23", [(632, 322), (656, 322), (662, 366), (640, 388), (618, 358)], (644, 346)),
    ("24", [(428, 256), (478, 234), (546, 232), (602, 246), (632, 278), (632, 322),
            (600, 294), (544, 282), (482, 286), (436, 306)], (524, 262)),
    ("32", [(300, 228), (366, 236), (428, 256), (436, 306), (412, 340), (376, 326),
            (356, 286), (288, 300)], (360, 282)),
    ("25", [(376, 326), (412, 340), (420, 364), (398, 384), (364, 376), (354, 346)], (388, 356)),
    ("11", [(204, 316), (288, 300), (356, 286), (376, 326), (356, 352), (330, 378),
            (300, 374), (272, 364), (236, 350), (192, 332)], (278, 336)),
    ("19", [(722, 262), (748, 214), (756, 150), M((816, 186)), M((850, 242)), M((872, 302)), (840, 296),
            (760, 306), (716, 312)], (786, 238)),
    ("17", [(716, 312), (760, 306), (840, 296), M((872, 346)), (846, 390), (762, 394),
            (700, 372), (662, 366), (656, 322)], (772, 346)),
    ("18", [(700, 372), (762, 394), (846, 390), M((842, 450)), M((806, 480)),
            M((766, 504)), (722, 456), (700, 400)], (776, 432)),
    # ---- ventromedial temporal ----
    ("38", [(352, 380), (400, 396), (404, 470), (382, 504), M((346, 470)), M((332, 424))], (372, 440)),
    ("34", [(400, 396), (446, 376), (478, 396), (474, 438), (430, 448), (404, 470)], (440, 418)),
    ("28", [(478, 396), (494, 396), (528, 414), (520, 456), (474, 438)], (498, 428)),
    ("35", [(528, 414), (546, 402), (574, 418), (566, 458), (520, 456)], (546, 436)),
    ("36", [(574, 418), (600, 396), (632, 416), (624, 462), (566, 458)], (598, 440)),
    ("37", [(632, 416), (640, 378), (662, 366), (700, 400), (722, 456), (716, 508),
            (664, 536), (632, 512), (624, 462)], (668, 456)),
    ("20", [(404, 470), (430, 448), (474, 438), (520, 456), (566, 458), (624, 462),
            (632, 512), (560, 540), (478, 542), (422, 528), (378, 500)], (500, 496)),
]

MED_SOLID = [
    [(516, 48), (508, 150), (500, 240)],                                    # central sulcus
    [(300, 228), (366, 236), (428, 256), (478, 234), (546, 232), (602, 246),
     (632, 278), (660, 262)],                                               # limbic upper border
    [(288, 300), (356, 286), (376, 326), (412, 340), (420, 364), (398, 384)],  # limbic anterior
    [(722, 262), (716, 312), (656, 322), (662, 366), (640, 388)],           # parieto-occipital
    [(336, 424), (356, 386), (402, 392), (452, 380), (500, 396), (548, 402),
     (598, 398), (636, 380), (662, 366)],                                   # limbic|temporal
]

# ==========================================================================
# DORSAL + VENTRAL — both hemispheres, anterior at TOP, mirrored about x=350
# ==========================================================================
DOR_MID = 350.0
DOR_MARGIN = [
    (350, 70), (300, 76), (252, 90), (210, 112), (174, 142), (144, 182), (122, 230),
    (106, 286), (96, 346), (92, 408), (92, 470), (100, 530), (114, 586), (138, 638),
    (168, 684), (204, 722), (248, 752), (298, 772), (350, 782),
]
VEN_MARGIN = [
    (350, 74), (302, 80), (258, 94), (218, 116), (184, 148), (158, 190), (138, 240),
    (124, 296), (116, 354), (114, 414), (118, 474), (130, 532), (150, 586), (178, 634),
    (212, 676), (254, 710), (300, 734), (350, 744),
]


def _margin_x(margin, y):
    for i in range(len(margin) - 1):
        (x0, y0), (x1, y1) = margin[i], margin[i + 1]
        if y0 <= y <= y1:
            t = 0.0 if y1 == y0 else (y - y0) / (y1 - y0)
            return x0 + (x1 - x0) * t
    return margin[-1][0] if y > margin[-1][1] else margin[0][0]


def band(margin, y0, y1, f0=0.0, f1=1.0, mid=DOR_MID, steps=7, over=26):
    """Transverse band of a hemisphere between fractional distances f0..f1."""
    pts = []
    ys = [y0 + (y1 - y0) * i / steps for i in range(steps + 1)]
    for y in ys:
        mx = _margin_x(margin, y)
        x = mid - f1 * (mid - mx)
        pts.append((x - (over if f1 >= 0.999 else 0), y))
    for y in reversed(ys):
        mx = _margin_x(margin, y)
        pts.append((mid - f0 * (mid - mx), y))
    return pts


DORSAL_BANDS = [
    ("10",  62, 148, 0.0, 1.0), ("9", 148, 252, 0.0, 1.0), ("8", 252, 332, 0.0, 1.0),
    ("6", 332, 424, 0.0, 1.0), ("4", 424, 476, 0.0, 1.0),
    ("3", 476, 506, 0.0, 1.0), ("1", 502, 528, 0.0, 1.0), ("2", 524, 552, 0.0, 1.0),
    ("5", 548, 592, 0.0, 1.0), ("7", 588, 662, 0.0, 1.0),
    ("19", 646, 706, 0.0, 1.0), ("18", 700, 746, 0.0, 1.0), ("17", 740, 788, 0.0, 1.0),
]
DORSAL_EDGE = [("46", 240, 340, 0.66, 1.0), ("40", 470, 540, 0.66, 1.0),
               ("39", 540, 618, 0.66, 1.0)]

VENTRAL_BANDS = [
    ("11",   62, 202, 0.00, 0.56), ("47",  80, 212, 0.56, 1.00),
    ("38",  192, 304, 0.00, 1.00),
    ("34",  296, 358, 0.00, 0.36), ("28", 352, 426, 0.00, 0.36),
    ("35",  420, 480, 0.00, 0.36), ("36", 474, 576, 0.00, 0.40),
    ("37",  296, 576, 0.36, 0.74), ("20", 296, 576, 0.74, 1.00),
    ("36b", 570, 636, 0.00, 0.36), ("37b", 570, 644, 0.36, 1.00),
    ("19",  618, 686, 0.00, 1.00), ("18", 680, 722, 0.00, 1.00),
    ("17",  716, 756, 0.00, 1.00),
]

# ==========================================================================
# semiology -> Brodmann tile mapping
# ==========================================================================
S1 = ["3", "1", "2"]
CING = ["24", "32", "25"]

SUB_TILES = {
    "Mesial Temporal (Amygdala / Hippocampus / Entorhinal Cortex)": ["28", "34", "35", "36"],
    "Lateral Temporal Neocortex (STG / MTG / ITG / Temporal Pole)": ["22", "21", "20", "38"],
    "DLPFC / Premotor / Frontal Eye Field (Brodmann 6/8/9/46)": ["6", "8", "9", "46"],
    "Primary Motor Cortex (M1, precentral gyrus, Brodmann 4)": ["4"],
    "Supplementary Motor Area (SMA/SSMA, mesial Brodmann 6)": ["6"],
    "Orbitofrontal / Mesiobasal Frontal (Brodmann 11/12/47)": ["11", "47"],
    "Anterior/Mid-Cingulate Cortex (ACC, Brodmann 24/25/32)": CING,
    "Primary Somatosensory Cortex (S1, postcentral gyrus, Brodmann 3/1/2)": S1,
    "Superior/Inferior Parietal Lobule, TPJ, Precuneus (Brodmann 5/7/39/40)": ["5", "7", "39", "40"],
    "Primary Visual Cortex (V1/V2, calcarine, Brodmann 17/18)": ["17", "18"],
    "Extrastriate Cortex (V3-V5/MT, lateral occipital, Brodmann 18/19/37)": ["18", "19", "37"],
    "Insular Cortex - Anterior (Brodmann 13/14/15 agranular)": ["insula"],
    "Insular Cortex - Posterior (granular, Brodmann 13 posterior)": ["insula"],
    "Insular Cortex - Bilateral / Nocturnal": ["insula"],
    "Hypothalamic Hamartoma / Deep Subcortical": ["subcort"],
    "Frontal / Precentral Operculum (Brodmann 6 / 44)": ["6", "44"],
    "Multiregional / Propagation / EEG Correlates": [],
}

SIGN_TILES = {
    5:  ["34", "28", "35", "11"],
    6:  ["insula", "43", "34"],
    7:  ["21", "22", "28", "35", "36"],
    11: ["28", "34", "35", "36", "4"],
    12: ["8", "6"],
    14: ["4", "6"],
    16: ["28", "34", "35", "36", "insula", "47"],
    18: ["21", "22", "19"],
    19: ["insula", "34", "28"],
    20: ["insula", "28", "34"],
    21: ["insula", "38", "34"],
    24: ["22", "39", "44", "45"],
    25: ["22", "44", "45", "6"],
    26: ["34", "28", "24", "subcort"],
    27: ["21", "22", "11"],
    28: ["41"],
    29: ["22"],
    30: ["22", "42"],
    31: ["22", "39"],
    32: ["22", "39", "40", "insula"],
    33: ["37", "20", "19"],
    34: ["37", "20", "19"],
    35: ["37", "20"],
    36: ["22"],
    37: ["21", "22", "28", "35", "36"],
    41: ["4"], 42: ["4"],
    43: ["8", "4"],
    45: ["6"], 46: ["6", "24"], 47: ["6"], 48: ["6", "4"], 49: ["6"],
    50: ["6", "24"], 51: ["6", "24", "11"],
    52: ["11", "47", "24", "insula"],
    53: ["11", "47"],
    54: ["11", "47"],
    55: ["11", "47", "38", "34", "28"],
    56: ["24", "32"], 57: ["24", "32", "6"], 58: ["24", "32", "11"],
    59: ["24", "32", "9", "46"],
    61: ["6", "44", "45"],
    62: S1, 63: S1, 66: S1,
    64: ["3", "1", "2", "insula", "43"],
    65: ["3", "1", "2", "5"],
    67: ["3", "1", "2", "5", "7", "43"],
    68: ["39", "40"],
    69: ["5", "7", "insula"],
    70: ["7", "39", "40"],
    71: ["5", "7", "6"],
    72: ["43", "insula"],
    73: ["17", "18"], 74: ["17"],
    75: ["18", "19", "37"],
    76: ["18", "19", "8"],
    77: ["19", "8"],
    78: ["17", "18", "19"],
    79: ["17"],
    80: ["19", "37"],
    81: ["18", "19", "37"],
    93: ["4", "6"],
    94: ["28", "34", "35", "36", "21", "22", "11"],
    95: ["11", "24", "6", "insula", "28", "34"],
    96: ["38", "21", "22"],
    97: ["4", "6"],
    98: ["28", "34", "35", "36", "11"],
    99: ["6", "24"],
    100: ["4", "43"],
    102: ["34", "28"], 103: ["34", "28"],
    107: ["4", "6"],
    108: ["22", "39"],
    109: ["6", "8", "9"],
    111: ["38", "20", "21", "22", "insula", "11"],
    112: ["28", "34", "35", "36"],
}


def tiles_for_sign(sign):
    """Brodmann tiles a sign maps onto: per-sign override, else its sub-region."""
    tiles = SIGN_TILES.get(sign.get("id"))
    if tiles is None:
        tiles = SUB_TILES.get(sign.get("sub"), [])
    out, seen = [], set()
    for t in tiles:
        if t in TILE_INFO and t not in seen:
            out.append(t); seen.add(t)
    return out
