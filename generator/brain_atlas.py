#!/usr/bin/env python3
"""
brain_atlas.py — geometry and semiology mapping for the interactive Brodmann figure.

Three schematic surface views of one hemisphere (lateral, dorsal, ventral) are
drawn as tiled Brodmann areas. Each tile is a hand-placed polygon; outer edges
deliberately overshoot the silhouette and are trimmed by an SVG clipPath, so the
brain edge is always exactly the silhouette curve. Tiles are stroked in the panel
background colour, which renders the gutters between areas without needing a
perfectly gapless hand-authored parcellation.

Nothing here is patient data or copyrighted figure content: the outlines are
schematic drawings authored for this atlas, and the area/sign mapping is derived
from the dataset's own localization fields.
"""
from math import hypot

# --------------------------------------------------------------------------
# Brodmann tiles: a tile is one clickable unit and may cover >1 numbered area
# (e.g. S1 is conventionally treated as 3/1/2 together, as the dataset does).
# --------------------------------------------------------------------------
TILE_INFO = {
    "4":     dict(label="4",     bas=[4],        lobe="Frontal",   name="Primary motor cortex (precentral gyrus)"),
    "6":     dict(label="6",     bas=[6],        lobe="Frontal",   name="Premotor & supplementary motor area (SMA)"),
    "8":     dict(label="8",     bas=[8],        lobe="Frontal",   name="Frontal eye field"),
    "9":     dict(label="9",     bas=[9],        lobe="Frontal",   name="Dorsolateral prefrontal cortex (superior)"),
    "10":    dict(label="10",    bas=[10],       lobe="Frontal",   name="Frontopolar cortex"),
    "11":    dict(label="11",    bas=[11],       lobe="Frontal",   name="Orbitofrontal cortex (medial orbital)"),
    "44":    dict(label="44",    bas=[44],       lobe="Frontal",   name="Pars opercularis (Broca's area)"),
    "45":    dict(label="45",    bas=[45],       lobe="Frontal",   name="Pars triangularis (Broca's area)"),
    "46":    dict(label="46",    bas=[46],       lobe="Frontal",   name="Dorsolateral prefrontal cortex (middle frontal)"),
    "47":    dict(label="47",    bas=[47],       lobe="Frontal",   name="Pars orbitalis / lateral orbitofrontal"),
    "3-1-2": dict(label="3·1·2", bas=[3, 1, 2],  lobe="Parietal",  name="Primary somatosensory cortex (postcentral gyrus)"),
    "5":     dict(label="5",     bas=[5],        lobe="Parietal",  name="Superior parietal lobule (somatosensory association)"),
    "7":     dict(label="7",     bas=[7],        lobe="Parietal",  name="Superior parietal lobule / precuneus"),
    "39":    dict(label="39",    bas=[39],       lobe="Parietal",  name="Angular gyrus (temporo-parietal junction)"),
    "40":    dict(label="40",    bas=[40],       lobe="Parietal",  name="Supramarginal gyrus"),
    "43":    dict(label="43",    bas=[43],       lobe="Parietal",  name="Subcentral area / parietal operculum (S2, gustatory)"),
    "20":    dict(label="20",    bas=[20],       lobe="Temporal",  name="Inferior temporal gyrus"),
    "21":    dict(label="21",    bas=[21],       lobe="Temporal",  name="Middle temporal gyrus"),
    "22":    dict(label="22",    bas=[22],       lobe="Temporal",  name="Superior temporal gyrus (Wernicke's area posteriorly)"),
    "38":    dict(label="38",    bas=[38],       lobe="Temporal",  name="Temporal pole"),
    "37":    dict(label="37",    bas=[37],       lobe="Temporal",  name="Fusiform / occipitotemporal gyrus"),
    "41-42": dict(label="41·42", bas=[41, 42],   lobe="Temporal",  name="Primary & association auditory cortex (Heschl's gyrus)"),
    "28":    dict(label="28",    bas=[28],       lobe="Temporal",  name="Entorhinal cortex"),
    "34":    dict(label="34",    bas=[34],       lobe="Temporal",  name="Uncus / periamygdaloid cortex"),
    "35":    dict(label="35",    bas=[35],       lobe="Temporal",  name="Perirhinal cortex"),
    "36":    dict(label="36",    bas=[36],       lobe="Temporal",  name="Parahippocampal / ectorhinal cortex"),
    "17":    dict(label="17",    bas=[17],       lobe="Occipital", name="Primary visual cortex (V1, calcarine)"),
    "18":    dict(label="18",    bas=[18],       lobe="Occipital", name="Secondary visual cortex (V2)"),
    "19":    dict(label="19",    bas=[19],       lobe="Occipital", name="Associative visual cortex (V3/V4/V5-MT)"),
    # buried / medial areas — not on a lateral, dorsal or ventral surface
    "insula": dict(label="INS",  bas=[13, 14, 15, 16], lobe="Insular",
                   name="Insular cortex (deep to the fronto-parieto-temporal operculum)", buried=True),
    "cing":   dict(label="24/32", bas=[24, 32, 25, 33], lobe="Frontal",
                   name="Cingulate cortex (medial surface — ACC / mid-cingulate)", buried=True),
    "subcort": dict(label="SUB", bas=[], lobe="Deep/Subcortical",
                    name="Deep subcortical (hypothalamic hamartoma)", buried=True),
}

# --------------------------------------------------------------------------
# geometry helpers
# --------------------------------------------------------------------------
def _push(p, cx, cy, amt):
    """Move a point radially away from the view centre (to overshoot the clip)."""
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
    """
    Grow a polygon by ~d px along each vertex's outward normal. Every tile is
    inflated, so neighbours overlap instead of abutting: with the painter's-order
    draw and a background-coloured stroke, the later tile's edge becomes the
    visible seam and hairline gaps between areas cannot appear.
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
        # outward normals of the two adjacent edges (rotate edge by -90 * winding)
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
# LATERAL VIEW  (left hemisphere, anterior to the LEFT)   viewBox 1000 x 680
# ==========================================================================
LAT_C = (500, 320)
def L(p, amt=36):
    return _push(p, LAT_C[0], LAT_C[1], amt)

# Silhouette: frontal pole at the left, occipital pole at the right, the temporal
# lobe below a Sylvian notch whose apex points posteriorly at (352,322).
LAT_OUTLINE = [
    (98, 278), (106, 230), (126, 176), (164, 132), (216, 98), (280, 74), (352, 58),
    (430, 50), (508, 50), (582, 58), (650, 74), (712, 100), (766, 136), (812, 182),
    (848, 236), (872, 296), (880, 354), (868, 410), (844, 452), (812, 484), (788, 500),
    (740, 520), (672, 540), (600, 550), (530, 552), (468, 542), (418, 520), (374, 488),
    (338, 448), (312, 406), (300, 380), (316, 352), (330, 340),   # temporal pole
    (300, 318), (250, 308), (196, 300), (150, 296), (114, 298),   # notch + orbital margin
]

LAT_SYLVIAN = [(330, 340), (392, 352), (460, 362), (530, 368), (600, 366), (664, 356),
               (716, 338), (748, 314)]

# tiles are drawn in list order; each is inflated so neighbours overlap
LATERAL_TILES = [
    ("10", [L((98, 278)), L((106, 230)), L((126, 176)), L((164, 132)), (216, 98),
            (224, 174), (218, 244), (206, 288), L((150, 296)), L((114, 298))], (156, 228)),
    ("9",  [(216, 98), L((258, 84)), (300, 72), (288, 148), (272, 216), (218, 244),
            (224, 174)], (252, 160)),
    ("46", [(218, 244), (272, 216), (262, 268), (206, 288)], (238, 256)),
    ("47", [(206, 288), (262, 268), (262, 308), L((206, 306)), L((152, 300))], (226, 294)),
    ("8",  [(300, 72), L((340, 62)), (378, 57), (360, 134), (342, 210), (272, 216),
            (288, 148)], (324, 146)),
    ("45", [(272, 216), (342, 210), (336, 268), (338, 330), (300, 318), (262, 308),
            (262, 268)], (302, 268)),
    ("6",  [(378, 57), L((416, 53)), (452, 51), (436, 128), (420, 204), (412, 256),
            (336, 264), (342, 210), (360, 134)], (396, 152)),
    ("44", [(336, 264), (412, 256), (414, 328), (392, 352), (330, 340), (338, 330)], (372, 302)),
    ("4",  [(452, 51), L((494, 50)), (536, 50), (520, 130), (504, 206), (492, 278),
            (494, 320), (410, 320), (412, 256), (420, 204), (436, 128)], (472, 172)),
    ("3-1-2", [(536, 50), L((578, 54)), (618, 62), (600, 140), (584, 214), (574, 282),
               (576, 320), (494, 320), (492, 278), (504, 206), (520, 130)], (556, 174)),
    ("5",  [(618, 62), L((656, 74)), (690, 90), (674, 162), (658, 232), (584, 214),
            (600, 140)], (640, 150)),
    ("40", [(584, 214), (658, 232), (650, 296), (654, 356), (600, 372), (576, 362),
            (574, 282)], (614, 292)),
    ("7",  [(690, 90), L((736, 118)), (778, 150), (766, 212), (752, 272), (658, 232),
            (674, 162)], (718, 180)),
    ("39", [(658, 232), (752, 272), (742, 330), (716, 340), (654, 356), (650, 296)], (700, 294)),
    ("19", [(778, 150), L((812, 182)), (838, 220), (828, 288), (816, 350), (806, 408),
            (788, 460), (752, 496), (722, 460), (730, 390), (742, 330), (752, 272),
            (766, 212)], (784, 292)),
    ("18", [(838, 220), L((872, 296)), L((880, 354)), (816, 350), (828, 288)], (850, 286)),
    ("17", [L((880, 354)), L((870, 412)), L((846, 468)), L((806, 506)), (752, 496),
            (788, 460), (806, 408), (816, 350)], (836, 412)),
    ("43", [(410, 320), (576, 320), (578, 360), (500, 378), (440, 366), (414, 328)], (494, 342)),
    # ---- temporal lobe ----
    ("38", [(330, 340), (392, 352), (386, 418), (390, 496), L((344, 470)),
            L((308, 412)), L((298, 358))], (348, 414)),
    ("22", [(392, 352), (460, 362), (530, 368), (600, 366), (664, 356), (700, 352),
            (704, 398), (398, 412)], (644, 382)),
    ("21", [(398, 412), (704, 398), (708, 452), (392, 464)], (556, 434)),
    ("20", [(392, 464), (708, 452), (716, 510), L((656, 542)), L((510, 554)),
            L((420, 536)), (378, 490)], (552, 500)),
    ("37", [(700, 352), (730, 348), (730, 390), (722, 460), (752, 496), L((726, 542)),
            (716, 512), (708, 452), (704, 398)], (716, 428)),
    ("41-42", [(494, 370), (580, 374), (578, 396), (492, 392)], (536, 384)),
]

# ==========================================================================
# DORSAL VIEW (from above, anterior at TOP, left hemisphere = viewer's left)
# viewBox 700 x 880 — right hemisphere is the mirror of the left
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
    """Lateral margin x at a given y (linear interpolation down the outline)."""
    for i in range(len(margin) - 1):
        (x0, y0), (x1, y1) = margin[i], margin[i + 1]
        if y0 <= y <= y1:
            t = 0.0 if y1 == y0 else (y - y0) / (y1 - y0)
            return x0 + (x1 - x0) * t
    return margin[-1][0] if y > margin[-1][1] else margin[0][0]


def band(margin, y0, y1, f0=0.0, f1=1.0, mid=DOR_MID, steps=7, over=26):
    """
    Polygon covering a transverse band of a hemisphere, between fractional
    distances f0..f1 from the midline out to the lateral margin.
    f1 == 1.0 overshoots past the margin so the clipPath trims it cleanly.
    """
    pts = []
    ys = [y0 + (y1 - y0) * i / steps for i in range(steps + 1)]
    for y in ys:                      # outer edge, anterior -> posterior
        mx = _margin_x(margin, y)
        x = mid - f1 * (mid - mx)
        pts.append((x - (over if f1 >= 0.999 else 0), y))
    for y in reversed(ys):            # inner edge, posterior -> anterior
        mx = _margin_x(margin, y)
        pts.append((mid - f0 * (mid - mx), y))
    return pts


# (tile, y0, y1, f0, f1) — anterior to posterior down the hemisphere
DORSAL_BANDS = [
    ("10",    62,  148, 0.0, 1.0),
    ("9",    148,  252, 0.0, 1.0),
    ("8",    252,  332, 0.0, 1.0),
    ("6",    332,  424, 0.0, 1.0),
    ("4",    424,  476, 0.0, 1.0),
    ("3-1-2",476,  528, 0.0, 1.0),
    ("5",    528,  578, 0.0, 1.0),
    ("7",    578,  662, 0.0, 1.0),
    ("19",   646,  706, 0.0, 1.0),
    ("18",   700,  746, 0.0, 1.0),
    ("17",   740,  788, 0.0, 1.0),
]
# lateral-edge areas visible at the convexity margin (drawn over the bands)
DORSAL_EDGE = [
    ("46",  240, 340, 0.66, 1.0),
    ("40",  470, 540, 0.66, 1.0),
    ("39",  540, 618, 0.66, 1.0),
]

VENTRAL_BANDS = [
    ("11",    62,  202, 0.00, 0.56),
    ("47",    80,  212, 0.56, 1.00),
    ("38",   192,  304, 0.00, 1.00),
    ("34",   296,  358, 0.00, 0.36),
    ("28",   352,  426, 0.00, 0.36),
    ("35",   420,  480, 0.00, 0.36),
    ("36",   474,  576, 0.00, 0.40),
    ("37",   296,  576, 0.36, 0.74),
    ("20",   296,  576, 0.74, 1.00),
    ("36b",  570,  636, 0.00, 0.36),   # rendered as 36 (no second label)
    ("37b",  570,  644, 0.36, 1.00),   # rendered as 37
    ("19",   618,  686, 0.00, 1.00),
    ("18",   680,  722, 0.00, 1.00),
    ("17",   716,  756, 0.00, 1.00),
]

# ==========================================================================
# semiology -> Brodmann tile mapping
#   1) a default per dataset sub-region (the dataset names the areas itself)
#   2) per-sign overrides where the record's `loc` field is more specific
# ==========================================================================
SUB_TILES = {
    "Mesial Temporal (Amygdala / Hippocampus / Entorhinal Cortex)": ["28", "34", "35", "36"],
    "Lateral Temporal Neocortex (STG / MTG / ITG / Temporal Pole)": ["22", "21", "20", "38"],
    "DLPFC / Premotor / Frontal Eye Field (Brodmann 6/8/9/46)": ["6", "8", "9", "46"],
    "Primary Motor Cortex (M1, precentral gyrus, Brodmann 4)": ["4"],
    "Supplementary Motor Area (SMA/SSMA, mesial Brodmann 6)": ["6"],
    "Orbitofrontal / Mesiobasal Frontal (Brodmann 11/12/47)": ["11", "47"],
    "Anterior/Mid-Cingulate Cortex (ACC, Brodmann 24/25/32)": ["cing"],
    "Primary Somatosensory Cortex (S1, postcentral gyrus, Brodmann 3/1/2)": ["3-1-2"],
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

# refinements taken from each record's own localization text
SIGN_TILES = {
    5:  ["34", "28", "35", "11"],            # olfactory aura: amygdala/uncus + OFC
    6:  ["insula", "43", "34"],              # gustatory: insula + parietal operculum
    7:  ["21", "22", "28", "35", "36"],      # experiential: neocortex + hippocampus
    11: ["28", "34", "35", "36", "4"],       # dystonic posturing (BG loop, motor output)
    12: ["8", "6"],                          # forced version: FEF
    14: ["4", "6"],                          # figure-of-4
    16: ["28", "34", "35", "36", "insula", "47"],   # ictal spitting
    18: ["21", "22", "19"],                  # unilateral blinking
    19: ["insula", "34", "28"],              # ictal tachycardia (right insula)
    20: ["insula", "28", "34"],              # ictal bradycardia/asystole
    21: ["insula", "38", "34"],              # piloerection
    24: ["22", "39", "44", "45"],            # postictal aphasia
    25: ["22", "44", "45", "6"],             # ictal aphasia / speech arrest
    26: ["34", "28", "cing", "subcort"],     # dacrystic
    27: ["21", "22", "11"],                  # gelastic, temporal neocortical
    28: ["41-42"],                           # simple auditory aura
    29: ["22"],
    30: ["22", "41-42"],
    31: ["22", "39"],
    32: ["22", "39", "40", "insula"],        # vertiginous aura / TPJ
    33: ["37", "20", "19"],                  # micropsia / macropsia
    34: ["37", "20", "19"],                  # metamorphopsia
    35: ["37", "20"],                        # formed semantic visual
    36: ["22"],                              # paraphasia
    37: ["21", "22", "28", "35", "36"],      # dreamy state
    41: ["4"], 42: ["4"],
    43: ["8", "4"],                          # postictal gaze deviation
    45: ["6"], 46: ["6", "cing"], 47: ["6"], 48: ["6", "4"], 49: ["6"],
    50: ["6", "cing"], 51: ["6", "cing", "11"],
    52: ["11", "47", "cing", "insula"],      # hypermotor
    53: ["11", "47"],                        # OFC olfactory hallucination
    54: ["11", "47"],                        # sniffing automatisms
    55: ["11", "47", "38", "34", "28"],      # nocturnal quasi-purposeful
    59: ["cing", "9", "46"],                 # ictal cursing
    61: ["6", "44", "45"],                   # negative motor
    64: ["3-1-2", "insula", "43"],           # ictal pain
    65: ["3-1-2", "5"],                      # genital/perineal (paracentral)
    67: ["3-1-2", "5", "7", "43"],           # kinesthetic hallucination
    68: ["39", "40"],                        # out-of-body / TPJ
    69: ["5", "7", "insula"],                # rotatory body sensation
    70: ["7", "39", "40"],                   # visuospatial neglect
    71: ["5", "7", "6"],                     # alien limb
    72: ["43", "insula"],                    # gustatory, parietal opercular
    73: ["17", "18"], 74: ["17"],
    75: ["18", "19", "37"],                  # colour (V4, lingual-fusiform)
    76: ["18", "19", "8"],                   # tonic eye deviation (occipital eye field)
    77: ["19", "8"],                         # ictal nystagmus
    78: ["17", "18", "19"],                  # peri-ictal headache
    79: ["17"],                              # postictal scotoma
    80: ["19", "37"],                        # V5/MT motion
    81: ["18", "19", "37"],                  # geometric hallucination
    93: ["4", "6"],                          # BATS
    94: ["28", "34", "35", "36", "21", "22", "11"],  # temporal sequence
    95: ["11", "cing", "6", "insula", "28", "34"],   # hypermotor vs hypomotor
    96: ["38", "21", "22"],                  # TIRDA
    97: ["4", "6"],                          # postictal flaccidity
    98: ["28", "34", "35", "36", "11"],      # goal-directed automatisms
    99: ["6", "cing"],                       # axial tonic
    100: ["4", "43"],                        # tongue biting/deviation
    102: ["34", "28"], 103: ["34", "28"],    # ictal / postictal central apnoea
    107: ["4", "6"],                         # asymmetric terminal activity
    108: ["22", "39"],                       # immediate postictal speech
    109: ["6", "8", "9"],                    # ictal pupillary dilatation (frontal)
    111: ["38", "20", "21", "22", "insula", "11"],   # temporal-plus marker
    112: ["28", "34", "35", "36"],           # ability to warn
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
