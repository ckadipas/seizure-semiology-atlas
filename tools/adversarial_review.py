#!/usr/bin/env python3
"""Deterministic source-review checks.

Catches the checkable failure modes the resource must guard against as new
evidence is added:

  * CONFLICT        - studies for one semiology disagree on the lateralization figure
                      beyond a tolerance (heterogeneity -> "conflicting evidence").
  * DIRECTION_CLASH - the pooled direction contradicts the curated sign's latcode.
  * DOUBLE_COUNT    - a narrative review and a primary series report near-identical
                      figures for the same sign; the review may simply be citing the
                      primary study, so pooling both risks counting one datum twice.
  * DUPLICATE       - the exact same finding text is attributed to two different
                      papers, or one paper is listed twice for a single sign
                      (repeated-upload / merge artifact).
  * ORPHAN_STEM     - an observation's sign_stem matches no curated sign name, so the
                      figure would not attach to anything (traceability break).
  * SINGLE_SOURCE   - a pooled figure rests on one study only (low robustness).
  * PPV_ORPHAN_LINK - a corpus PPV finding's card_ids point at a card that doesn't exist.
  * PPV_DIRECTION_CLASH - a directional PPV finding contradicts the latcode of the card
                      it is surfaced on (the card and the explorer would disagree).
  * SENS_SPEC_ESTIMATE  - informational: cards' sensitivity/specificity are curator
                      teaching estimates, not corpus-pooled (the corpus reports none).

Emits enrichment/review_flags.json and prints a summary in CI. Advisory by default;
pass --strict to exit non-zero when any CONFLICT / DIRECTION_CLASH / DUPLICATE /
ORPHAN_STEM flag is present.

Checking whether a figure faithfully reflects its paper needs the source text and
is done during intake review, not here.
"""
import json
import os
import sys

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
CONFLICT_TOL = 25      # percentage-point spread that trips a CONFLICT flag (genuine
                       # disagreement; smaller same-direction spread is shown as the
                       # row's range whisker + weighted SD, not the conflict panel)
DOUBLE_TOL = 2.0       # review vs primary within this many points -> possible double-count


def load(*parts):
    with open(os.path.join(ROOT, *parts)) as f:
        return json.load(f)


def review():
    obs = load("enrichment", "observations.json")
    meta = load("enrichment", "meta_analysis.json")
    data = load("data", "semiology_data.json")
    enr = load("enrichment", "enrichment.json")
    try:
        corpus = load("enrichment", "corpus_findings.json")
    except FileNotFoundError:
        corpus = {"papers": []}

    flags = []

    def flag(kind, severity, sign, detail, evidence=None):
        flags.append({"kind": kind, "severity": severity, "sign": sign,
                      "detail": detail, "evidence": evidence or []})

    sign_names = [d["sign"].lower() for d in data] + [n["sign"].lower() for n in enr.get("new_signs", [])]
    by_id = {d["id"]: d for d in data}

    # ---- PPV card-link integrity (single-source: cards surface corpus PPV findings
    #      via each finding's explicit card_ids). Every linked id must resolve to a
    #      card, and a directional PPV must not contradict that card's lateralization.
    _dirclash = {("ipsi", "contra"), ("contra", "ipsi"),
                 ("dominant", "nondominant"), ("nondominant", "dominant")}
    for p in corpus.get("papers", []):
        cite = (p.get("cite") or "?").split(".")[0][:40]
        for f in p.get("findings", []):
            if f.get("metric") != "ppv":
                continue
            for cid in f.get("card_ids", []) or []:
                card = by_id.get(cid)
                if not card:
                    flag("ppv_orphan_link", "high", f.get("phenomenon", "?"),
                         f"PPV finding links to card #{cid}, which does not exist ({cite}).")
                    continue
                fdir, cdir = f.get("direction") or "", card.get("latcode")
                if (cdir, fdir) in _dirclash:
                    flag("ppv_direction_clash", "high", card["sign"],
                         f"PPV finding direction '{fdir}' contradicts card #{cid} latcode "
                         f"'{cdir}' ({cite}: {f.get('value_text','')}).")

    # ---- Sensitivity/specificity provenance (informational, once): the corpus
    #      reports essentially no sens/spec, so the card figures are curator teaching
    #      estimates. Record it so the invariant is visible, not silently assumed.
    corpus_ss = sum(1 for p in corpus.get("papers", [])
                    for f in p.get("findings", []) if f.get("metric") in ("sensitivity", "specificity"))
    flag("sens_spec_estimate", "info", "(all cards)",
         f"sensitivity/specificity on cards are curator teaching estimates, not pooled: "
         f"the source corpus contains {corpus_ss} sens/spec figure(s) total. Cards mark these 'est.'.")

    for s in meta["by_sign"]:
        contribs = s["contributions"]
        numeric = [c for c in contribs if "value" in c]

        # ORPHAN_STEM - the figure attaches to no curated sign
        stem = (s.get("sign_stem") or "").lower()
        if stem and not any(stem in nm for nm in sign_names):
            flag("orphan_stem", "high", s["sign"],
                 f"sign_stem '{stem}' matches no curated sign name; this figure would not attach.")

        # CONFLICT - studies disagree beyond tolerance
        if s.get("spread") is not None and s["spread"] >= CONFLICT_TOL:
            vals = ", ".join(f"{c['cite']} {c['value']}%" for c in numeric)
            flag("conflict", "high", s["sign"],
                 f"studies disagree by {s['spread']} points on the {s['direction']} figure "
                 f"(pooled {s['pooled']}%, range {s['low']}-{s['high']}%).",
                 [vals])

        # CROSS-SECTION CONSISTENCY via the explicit card link (not substring).
        # DUPLICATE_CARD: one analyzed sign mapping to >1 curated card = duplicate cards.
        linked = s.get("sign_ids", []) or []
        if len(linked) > 1:
            names = ", ".join(f"#{cid} '{by_id[cid]['sign']}'" for cid in linked if cid in by_id)
            flag("duplicate_card", "high", s["sign"],
                 f"maps to {len(linked)} curated cards that are the same sign ({names}); consolidate to one.")
        # DIRECTION_CLASH: the card the plot feeds must agree with the pooled direction.
        for cid in linked:
            d = by_id.get(cid)
            if d and d["latcode"] in ("contra", "ipsi", "dominant", "nondominant") and d["latcode"] != s["direction"]:
                flag("direction_clash", "high", s["sign"],
                     f"pooled direction '{s['direction']}' conflicts with curated card #{cid} "
                     f"'{d['sign']}' latcode '{d['latcode']}'.")

        # DUPLICATE - same study twice for one sign
        seen = {}
        for c in contribs:
            seen[c["study"]] = seen.get(c["study"], 0) + 1
        for study, cnt in seen.items():
            if cnt > 1:
                flag("duplicate", "medium", s["sign"],
                     f"study '{study}' contributes {cnt} observations to one sign (possible repeated upload).")

        # DOUBLE_COUNT - review and primary report near-identical figures
        reviews = [c for c in numeric if c.get("ground_truth") == "review"]
        primaries = [c for c in numeric if c.get("ground_truth") != "review"]
        for r in reviews:
            for p in primaries:
                if abs(r["value"] - p["value"]) <= DOUBLE_TOL:
                    flag("double_count", "low", s["sign"],
                         f"review {r['cite']} ({r['value']}%) and primary {p['cite']} ({p['value']}%) "
                         f"agree within {DOUBLE_TOL} points - the review may be citing the primary series; "
                         f"pooling both slightly double-weights this datum.")

        # SINGLE_SOURCE - low robustness
        if s.get("pooled") is not None and s["n_studies"] == 1:
            flag("single_source", "low", s["sign"],
                 f"pooled figure rests on a single study ({numeric[0]['cite'] if numeric else '?'}); "
                 f"treat as provisional until corroborated.")

    # cross-sign: identical finding text attributed to two different papers
    finding_index = {}
    for key, findings in enr.get("evidence", {}).items():
        for fnd in findings:
            finding_index.setdefault(fnd["f"].strip(), set()).add(fnd["p"])
    for text, papers in finding_index.items():
        if len(papers) > 1:
            flag("duplicate", "medium", "(evidence library)",
                 f"identical finding text attributed to {len(papers)} papers: {', '.join(sorted(papers))}.",
                 [text[:160]])

    by_kind = {}
    for fl in flags:
        by_kind.setdefault(fl["kind"], 0)
        by_kind[fl["kind"]] += 1

    out = {
        "_doc": "Generated by tools/adversarial_review.py. Advisory review flags consumed by the "
                "page's conflicting-evidence panel. Regenerate; do not hand-edit.",
        "tolerances": {"conflict_points": CONFLICT_TOL, "double_count_points": DOUBLE_TOL},
        "summary": by_kind,
        "flags": flags,
    }
    with open(os.path.join(ROOT, "enrichment", "review_flags.json"), "w") as f:
        json.dump(out, f, indent=1)

    print("adversarial review:", (", ".join(f"{k}={v}" for k, v in sorted(by_kind.items())) or "no flags"))
    for fl in flags:
        print(f"  [{fl['severity']:>6}] {fl['kind']:<15} {fl['sign']}: {fl['detail']}")

    if "--strict" in sys.argv:
        blocking = [f for f in flags if f["kind"] in ("conflict", "direction_clash", "duplicate",
                                                       "orphan_stem", "ppv_orphan_link", "ppv_direction_clash")]
        if blocking:
            print(f"\nSTRICT: {len(blocking)} blocking flag(s).")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(review())
