#!/usr/bin/env python3
"""Deterministic source-review checks.

Catches the checkable failure modes the resource must guard against as new
evidence is added:

  * CONFLICT        - studies for one semiology disagree on the lateralization figure
                      beyond a tolerance (heterogeneity -> "conflicting evidence").
  * DIRECTION_CLASH - the pooled direction contradicts the curated sign's latcode.
  * UNMARKED_RESTATEMENT - two averaged sources report near-identical figures for one
                      sign and at least one is a review, which usually means the review
                      is citing the other rather than measuring anything; pooling both
                      counts one datum twice. Two primary series agreeing is replication
                      and is not flagged.
  * ORPHAN_RESTATEMENT - an observation's `restates` names a study that is not in
                      observations.json, so the card would cite a source that does not
                      exist.
  * DUPLICATE       - the exact same finding text is attributed to two different
                      papers, or one paper is listed twice for a single sign
                      (repeated-upload / merge artifact).
  * ORPHAN_STEM     - an observation's sign_stem matches no curated sign name, so the
                      figure would not attach to anything (traceability break).
  * SINGLE_SOURCE   - a pooled figure rests on one study only (low robustness).
  * PPV_ORPHAN_LINK - a corpus PPV finding's card_ids point at a card that doesn't exist.
  * PPV_DIRECTION_CLASH - a directional PPV finding contradicts the latcode of the card
                      it is surfaced on (the card and the explorer would disagree).
  * SENS_ORPHAN_LINK / SENS_NO_CONDITION / SENS_BAD_METRIC - a frequency finding tagged
                      as sensitivity data links to a missing card, names no localization
                      group, or is not a numeric frequency figure.
  * SENS_SPEC_PROVENANCE - informational: which signs have a computed sensitivity vs a
                      curator estimate, and that specificity is always an estimate.

Emits enrichment/review_flags.json and prints a summary in CI. Advisory by default;
pass --strict (which CI does) to exit non-zero on the flags that mark a defect a
curator must fix: UNMARKED_RESTATEMENT, ORPHAN_RESTATEMENT, DIRECTION_CLASH,
DUPLICATE, DUPLICATE_CARD, ORPHAN_STEM and the PPV / sensitivity link checks. A
CONFLICT is a fact about the literature rather than a defect, so it is surfaced on
the page and never blocks; SINGLE_SOURCE likewise.

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
            if f.get("metric") == "ppv":
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
            # ---- SENSITIVITY tags: each `sens` entry promotes a frequency-within-a-group
            #      figure to a computed sensitivity; it must resolve to a card, name its
            #      group, carry a numeric value, and sit on a frequency finding.
            if f.get("sens"):
                if f.get("metric") != "frequency_pct":
                    flag("sens_bad_metric", "high", f.get("phenomenon", "?"),
                         f"sensitivity tags must sit on a frequency figure; this is "
                         f"metric '{f.get('metric')}' ({cite}).")
                for entry in f["sens"]:
                    if not entry.get("group"):
                        flag("sens_no_condition", "high", f.get("phenomenon", "?"),
                             f"a sensitivity entry names no localization group ({cite}).")
                    if not isinstance(entry.get("value"), (int, float)):
                        flag("sens_bad_metric", "high", f.get("phenomenon", "?"),
                             f"a sensitivity entry has a non-numeric value '{entry.get('value')}' ({cite}).")
                    if entry.get("card_id") not in by_id:
                        flag("sens_orphan_link", "high", f.get("phenomenon", "?"),
                             f"sensitivity entry links to card #{entry.get('card_id')}, which does not exist ({cite}).")

    # ---- Sensitivity/specificity provenance (informational, once). Sensitivity is now
    #      computed as P(sign|localization) from tagged frequency findings; specificity
    #      still cannot be (corpus lacks the false-positive side) and stays an estimate.
    corpus_spec = sum(1 for p in corpus.get("papers", [])
                      for f in p.get("findings", []) if f.get("metric") == "specificity")
    sens_cards = {e.get("card_id") for p in corpus.get("papers", []) for f in p.get("findings", [])
                  for e in (f.get("sens") or [])}
    flag("sens_spec_provenance", "info", "(cards)",
         f"sensitivity is computed as P(sign|localization) for {len(sens_cards)} sign(s) from tagged "
         f"ledger frequencies (marked 'corpus'); the rest, and ALL specificity, remain curator "
         f"estimates (marked 'est.') because the corpus reports {corpus_spec} specificity figure(s).")

    for s in meta["by_sign"]:
        contribs = s["contributions"]
        # every row carrying a percentage, vs. only the rows that were averaged.
        # A marked restatement carries a value but is not part of the figure, so it
        # must not be quoted as a disagreeing study or named as the single source.
        numeric = [c for c in contribs if "value" in c]
        pooled_rows = [c for c in numeric if not c.get("restates")]

        # ORPHAN_STEM - the figure attaches to no curated sign
        stem = (s.get("sign_stem") or "").lower()
        if stem and not any(stem in nm for nm in sign_names):
            flag("orphan_stem", "high", s["sign"],
                 f"sign_stem '{stem}' matches no curated sign name; this figure would not attach.")

        # CONFLICT - studies disagree beyond tolerance
        if s.get("spread") is not None and s["spread"] >= CONFLICT_TOL:
            vals = ", ".join(f"{c['cite']} {c['value']}%" for c in pooled_rows)
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

        # UNMARKED_RESTATEMENT - a review reporting a figure another averaged source
        # already reports, without being marked as restating it. Once marked, the
        # pooling engine drops it, so a flag here means one measurement is still
        # being averaged as two.
        #
        # Any pair with a review on at least one side qualifies. Restricting this to
        # review-vs-primary missed the commoner case entirely: two reviews citing the
        # same series neither of them ran. Three signs sat in the pool that way -
        # Loddenkemper 2005 and Kinney 2019 at 100 / 93 / 89% - while this check
        # reported nothing, because it never paired two reviews with each other.
        #
        # Primary-vs-primary is left alone: separate cohorts landing on the same
        # figure is replication, which is the one thing here that earns k = 2.
        for i, a in enumerate(pooled_rows):
            for b in pooled_rows[i + 1:]:
                if abs(a["value"] - b["value"]) > DOUBLE_TOL:
                    continue
                a_rev, b_rev = a.get("ground_truth") == "review", b.get("ground_truth") == "review"
                if not (a_rev or b_rev):
                    continue
                kind = ("two reviews report the same figure - they may be citing one series"
                        if a_rev and b_rev else
                        "the review may be citing the primary series")
                flag("unmarked_restatement", "high", s["sign"],
                     f"{'review' if a_rev else 'primary'} {a['cite']} ({a['value']}%) and "
                     f"{'review' if b_rev else 'primary'} {b['cite']} ({b['value']}%) agree within "
                     f"{DOUBLE_TOL} points - {kind}; pooling both counts one measurement twice. "
                     f"Mark the restating observation `provenance: secondary_citation`.")

        # ORPHAN_RESTATEMENT - `restates` must name a study in observations.json, or the
        # page prints an attribution that traces to nothing.
        for c in numeric:
            if c.get("restates") and c["restates"] not in obs.get("studies", {}):
                flag("orphan_restatement", "high", s["sign"],
                     f"{c['cite']} is marked as restating '{c['restates']}', which is not a study "
                     f"in observations.json; the card would cite a source that does not exist.")

        # SINGLE_SOURCE - low robustness
        if s.get("pooled") is not None and s["n_studies"] == 1:
            flag("single_source", "low", s["sign"],
                 f"pooled figure rests on a single study ({pooled_rows[0]['cite'] if pooled_rows else '?'}); "
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
        "tolerances": {"conflict_points": CONFLICT_TOL, "restatement_points": DOUBLE_TOL},
        "summary": by_kind,
        "flags": flags,
    }
    with open(os.path.join(ROOT, "enrichment", "review_flags.json"), "w") as f:
        json.dump(out, f, indent=1)

    print("adversarial review:", (", ".join(f"{k}={v}" for k, v in sorted(by_kind.items())) or "no flags"))
    for fl in flags:
        print(f"  [{fl['severity']:>6}] {fl['kind']:<15} {fl['sign']}: {fl['detail']}")

    if "--strict" in sys.argv:
        # A conflict is a fact about the literature, not a defect a build can fix -
        # it is surfaced, not blocked. An unmarked restatement IS a defect: it means
        # one measurement is being averaged as two, and a curator must mark it.
        # Every other high-severity kind blocks too: a flag raised to high and then
        # left out of this list is a check that only looks like one.
        blocking = [f for f in flags if f["kind"] in ("unmarked_restatement", "orphan_restatement",
                                                       "direction_clash", "duplicate", "duplicate_card",
                                                       "orphan_stem", "ppv_orphan_link", "ppv_direction_clash",
                                                       "sens_orphan_link", "sens_no_condition", "sens_bad_metric")]
        if blocking:
            print(f"\nSTRICT: {len(blocking)} blocking flag(s).")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(review())
