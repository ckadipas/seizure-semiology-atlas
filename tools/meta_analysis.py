#!/usr/bin/env python3
"""Deterministic weighted-average engine (run in CI).

    This is NOT a meta-analysis and must not be labelled one. There is no
    protocol, no prespecified eligibility, no reproducible search, no
    risk-of-bias instrument, no inverse-variance weighting, no confidence
    interval and no heterogeneity statistic. It is a transparent weighted
    average of the percentages this atlas extracted, shown with every
    contributing value and the weight it carried.

Reads enrichment/observations.json (structured, source-traceable records), applies
the transparent weighting scheme declared in that file, pools the lateralization
percentage for each semiology across its contributing studies, and writes
enrichment/meta_analysis.json for the generator to render.

Design principles:
  * ROBUST + REPRODUCIBLE  - all arithmetic is deterministic; re-running always
    yields the same output.
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


def certainty(n_studies, total_weight, spread=None):
    """
    How well supported a pooled figure is. This is a function of how many
    independent studies carry a number, never of the weight they add up to: a
    single heavy study is still a single study. It is also capped when the
    studies disagree, because a tier must not rise as the evidence conflicts.
    """
    if n_studies <= 1:
        return "single_source"
    tier = "well_supported" if n_studies >= 3 else "moderate"
    if spread is not None and spread >= 25 and tier == "well_supported":
        tier = "moderate"          # they do not agree; do not call it settled
    return tier


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
        "sign_ids": sign.get("sign_ids", []),
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
            # a spread statistic over 2-3 points is noise dressed as precision
            "wsd": round(math.sqrt(var), 1) if len(numeric) >= 4 else None,
            "total_weight": round(wsum, 2),
            "certainty": certainty(len(numeric), wsum, round(max(vals) - min(vals), 1)),
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


def build_sensitivity():
    """Sensitivity per sign, per seizure-onset group, computed from the master ledger.

    How often a sign appears among patients whose seizures start in one place:
    P(sign | onset group). The raw values are the frequency-within-a-group findings in
    corpus_findings.json that were tagged (sens_card_ids + sens_for). A group is the
    source publication's own category - mesial / mesiolateral / lateral TLE, FLE, OLE -
    not this atlas's regions, so values are kept per (sign, group) and never averaged
    across groups. k counts the publications behind a value. Any tagged finding appears
    here on the next build; nothing is hand-entered downstream.
    """
    path = os.path.join(ROOT, "enrichment", "corpus_findings.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        corpus = json.load(f)

    by_card = {}          # cid -> {group -> [source dicts]}
    spec_points = 0
    for p in corpus.get("papers", []):
        cite = (p.get("cite") or "?").split(".")[0][:46]
        for fnd in p.get("findings", []):
            if fnd.get("metric") == "specificity":
                spec_points += 1
            for entry in fnd.get("sens", []):
                v = entry.get("value")
                cid = entry.get("card_id")
                grp = entry.get("group")
                if not isinstance(v, (int, float)) or cid is None or not grp:
                    continue
                src = {"cite": cite, "value": v, "n": fnd.get("n"),
                       "locator": fnd.get("locator") or "", "quote": fnd.get("quote") or "",
                       "phenomenon": fnd.get("phenomenon") or ""}
                by_card.setdefault(cid, {}).setdefault(grp, []).append(src)

    cards = {}
    n_points = 0
    for cid, conds in by_card.items():
        rows = []
        for cond, srcs in conds.items():
            vals = [s["value"] for s in srcs]
            n_points += len(vals)
            rows.append({
                "cond": cond,
                "mean": round(sum(vals) / len(vals), 1),
                "low": min(vals), "high": max(vals), "k": len(vals),
                "sources": srcs,
            })
        rows.sort(key=lambda r: (-r["high"], r["cond"]))
        cards[str(cid)] = {"conditions": rows}

    pubs = sorted({s["cite"] for blk in cards.values()
                   for c in blk["conditions"] for s in c["sources"]})
    multi = sum(1 for blk in cards.values() for c in blk["conditions"] if c["k"] > 1)
    state = (f"Every percentage here currently rests on a single publication; they come from "
             f"{len(pubs)} sources in the library."
             if not multi else
             f"{multi} of these rest on more than one publication; the rest on a single one. "
             f"They come from {len(pubs)} sources in the library.")
    return {
        "method": ("Sensitivity is how often a sign shows up among patients whose seizures start in "
                   "one particular place. Each percentage below is the frequency a source publication "
                   "reported for that sign within one of its patient groups \u2014 for example, "
                   "epigastric aura in 46% of the patients whose onset was mesial temporal. The groups "
                   "are the source's own categories (mesial / mesiolateral / lateral temporal, frontal, "
                   "occipital, and so on), not this atlas's own regions. Percentages are kept separate "
                   "per group instead of being averaged together, because a sign can be common where "
                   "seizures start in one place and rare where they start in another. k is the number "
                   "of publications behind a percentage; where more than one reports the same sign in "
                   "the same group, the mean and the range across them are shown. " + state),
        "note_specificity": ("Specificity would need the sign's rate in the other onset groups \u2014 the "
                             "false-positive side \u2014 and the source library reports that for "
                             f"{'no sign at all' if spec_points == 0 else 'essentially no sign'}"
                             f" ({spec_points} across the whole corpus). Specificity on a sign card is "
                             "therefore a curator teaching estimate, marked 'est.', and is not computed."),
        "coverage": {"cards_with_sensitivity": len(cards), "data_points": n_points,
                     "publications": len(pubs),
                     "specificity_points_in_corpus": spec_points},
        "by_card": cards,
    }


def build():
    with open(os.path.join(ROOT, "enrichment", "observations.json")) as f:
        obs = json.load(f)
    scheme = obs["weighting"]
    studies = obs["studies"]

    signs = [pool_sign(s, studies, scheme) for s in obs["signs"]]
    sensitivity = build_sensitivity()

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
        "_doc": "Generated by tools/meta_analysis.py from enrichment/observations.json + the "
                "sensitivity tags in corpus_findings.json. Do not hand-edit.",
        "weighting": scheme,
        "n_signs": len(signs),
        "by_region": by_region,
        "by_sign": by_sign,
        "sensitivity": sensitivity,
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
    if sensitivity:
        cov = sensitivity["coverage"]
        print(f"  sensitivity (P(sign|localization)): {cov['data_points']} data points across "
              f"{cov['cards_with_sensitivity']} signs; specificity figures in corpus: "
              f"{cov['specificity_points_in_corpus']}")
    return out


if __name__ == "__main__":
    build()
