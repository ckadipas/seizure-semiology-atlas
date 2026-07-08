#!/usr/bin/env python3
"""Deterministic weighted meta-analysis engine (the "statistical agent", run as CI).

Reads enrichment/observations.json (structured, source-traceable records), applies
the transparent weighting scheme declared in that file, pools the lateralization
percentage for each semiology across its contributing studies, and writes
enrichment/meta_analysis.json for the generator to render.

Design principles the resource demands:
  * ROBUST + REPRODUCIBLE  - all arithmetic is deterministic Python, not an LLM
    guessing numbers at build time. Re-running always yields the same output.
  * TRACEABLE              - every pooled figure carries the exact per-study values
    and the weight each contributed, so you can see where and how it was derived.
  * TUNABLE               - the weighting scheme lives in observations.json; change
    it and re-run to see every figure update.

Educational resource - not for clinical decision-making.
"""
import json
import math
import os

def _find_root(start):
    d = os.path.dirname(os.path.abspath(start))
    while True:
        if os.path.exists(os.path.join(d, ".atlas-root")):
            return d
        p = os.path.dirname(d)
        if p == d:
            return os.path.dirname(os.path.abspath(start))
        d = p

ROOT = _find_root(__file__)
REGION_ORDER = ["Temporal", "Frontal", "Parietal", "Occipital",
                "Insular", "Deep/Subcortical", "Multiregional/Propagation"]


def size_factor(n, cap):
    """1 + log10(N)/2, capped; 1.0 when N is unknown (never fabricated)."""
    if not n or n <= 0:
        return 1.0
    return min(cap, 1.0 + math.log10(n) / 2.0)


def study_weight(study, scheme):
    base = scheme["class_base"].get(study.get("class"), 1.0)
    gt = scheme["ground_truth_mult"].get(study.get("ground_truth"), 1.0)
    sz = size_factor(study.get("n"), scheme.get("size_cap", 2.0))
    return base, gt, sz, round(base * gt * sz, 3)


def certainty(n_studies, total_weight):
    if n_studies >= 3 or total_weight >= 6.0:
        return "well_supported"
    if n_studies == 2 or total_weight >= 3.0:
        return "moderate"
    return "single_source"


def pool_sign(sign, studies, scheme):
    numeric, qualitative = [], []
    for obs in sign["observations"]:
        st = studies.get(obs["study"], {})
        base, gt, sz, w = study_weight(st, scheme)
        row = {
            "study": obs["study"],
            "cite": st.get("cite", obs["study"]),
            "eclass": st.get("class"),
            "ground_truth": st.get("ground_truth"),
            "n": st.get("n"),
            "weight": w,
            "weight_parts": {"class_base": base, "ground_truth_mult": gt, "size_factor": round(sz, 3)},
            "pg": obs.get("pg"),
            "freq": obs.get("freq"),
            "note": obs.get("note", ""),
        }
        if isinstance(obs.get("value"), (int, float)):
            row["value"] = obs["value"]
            numeric.append(row)
        else:
            row["qualitative"] = obs.get("qualitative", "supportive")
            qualitative.append(row)

    result = {
        "sign": sign["sign"],
        "sign_stem": sign.get("sign_stem"),
        "lobe": sign["lobe"],
        "gyrus": sign.get("gyrus", ""),
        "ba": sign.get("ba", ""),
        "metric": sign.get("metric", "lateralization"),
        "direction": sign["direction"],
        "contested": sign.get("contested"),
        "contributions": numeric + qualitative,
        "n_studies": len(numeric),
        "n_qualitative": len(qualitative),
    }

    if numeric:
        wsum = sum(r["weight"] for r in numeric)
        vals = [r["value"] for r in numeric]
        pooled = sum(r["weight"] * r["value"] for r in numeric) / wsum if wsum else 0.0
        # weighted standard deviation (population form, weights as frequencies)
        var = sum(r["weight"] * (r["value"] - pooled) ** 2 for r in numeric) / wsum if wsum else 0.0
        result.update({
            "pooled": round(pooled, 1),
            "low": min(vals),
            "high": max(vals),
            "spread": round(max(vals) - min(vals), 1),
            "wsd": round(math.sqrt(var), 1),
            "total_weight": round(wsum, 2),
            "certainty": certainty(len(numeric), wsum),
        })
    else:
        # qualitative-only sign (direction known, no poolable percentage)
        wsum = sum(r["weight"] for r in qualitative)
        result.update({
            "pooled": None,
            "low": None, "high": None, "spread": None, "wsd": None,
            "total_weight": round(wsum, 2),
            "certainty": certainty(len(qualitative), wsum) if len(qualitative) > 1 else "single_source",
        })
    return result


def build():
    with open(os.path.join(ROOT, "enrichment", "observations.json")) as f:
        obs = json.load(f)
    scheme = obs["weighting"]
    studies = obs["studies"]

    signs = [pool_sign(s, studies, scheme) for s in obs["signs"]]

    # ---- View (i): lobe -> (gyrus/BA subgroup) -> signs ----
    by_region = []
    for lobe in REGION_ORDER:
        group_signs = [s for s in signs if s["lobe"] == lobe]
        if not group_signs:
            continue
        subgroups = {}
        order = []
        for s in group_signs:
            key = (s["gyrus"], s["ba"])
            if key not in subgroups:
                subgroups[key] = []
                order.append(key)
            subgroups[key].append(s)
        by_region.append({
            "lobe": lobe,
            "groups": [{"gyrus": g, "ba": b, "signs": subgroups[(g, b)]} for (g, b) in order],
        })

    # ---- View (ii): semiology alphabetical ----
    by_sign = sorted(signs, key=lambda s: s["sign"].lower())

    out = {
        "_doc": "Generated by tools/meta_analysis.py from enrichment/observations.json. Do not hand-edit.",
        "weighting": scheme,
        "n_signs": len(signs),
        "by_region": by_region,
        "by_sign": by_sign,
    }
    with open(os.path.join(ROOT, "enrichment", "meta_analysis.json"), "w") as f:
        json.dump(out, f, indent=1)

    pooled = [s for s in signs if s["pooled"] is not None]
    print("meta_analysis.json written.")
    print(f"  signs: {len(signs)}  ({len(pooled)} with a pooled percentage, "
          f"{len(signs) - len(pooled)} qualitative-only)")
    multi = [s for s in pooled if s["n_studies"] >= 2]
    print(f"  multi-study pooled signs: {len(multi)}")
    for s in multi:
        print(f"    {s['sign']:<38} pooled {s['pooled']:>5}%  "
              f"(range {s['low']}-{s['high']}, {s['n_studies']} studies, "
              f"weight {s['total_weight']}, {s['certainty']})")
    return out


if __name__ == "__main__":
    build()
