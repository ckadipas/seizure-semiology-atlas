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
  * REVIEW_ONLY_FIGURE - every value behind a pooled percentage is a narrative review
                      quoting a cohort this library has not read, so no series here
                      measured the figure and k counts reviews rather than measurements.
  * UNTRACED_REVIEW_FIGURE - a review's percentage is averaged beside a primary series
                      as an independent second measurement, without the series it took
                      the figure from having been identified.
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
the page and never blocks; SINGLE_SOURCE, REVIEW_ONLY_FIGURE and
UNTRACED_REVIEW_FIGURE likewise — they describe how thin the evidence is, and the
fix is a curator tracing a citation or the library gaining a paper, neither of
which a build can do.

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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meta_analysis import CONTESTED_POINTS, NOT_MEASURED   # noqa: E402

# The spread that trips a CONFLICT flag is the same spread that makes a figure
# `contested` upstream - imported, not re-typed, because two copies of one number in
# two files is a divergence waiting to happen, and the comment on the original
# claimed to be "the one place this threshold is defined" while this line existed.
CONFLICT_TOL = CONTESTED_POINTS
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
        # A value that was kept out of the average must not be quoted back as a
        # disagreeing study or named as the single source. Keying that on `restates`
        # alone was wrong the moment a second kind of exclusion existed: a review's
        # cross-series summary and an interpolated midpoint have no `restates` target,
        # so they read as pooled here while the engine ignored them. Ask the same
        # question the engine asks.
        numeric = [c for c in contribs if "value" in c]
        pooled_rows = [c for c in numeric
                       if c.get("provenance") not in NOT_MEASURED and not c.get("restates")]

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
        known = set(obs.get("studies", {}))
        for c in numeric:
            if c.get("restates") and c["restates"] not in known:
                flag("orphan_restatement", "high", s["sign"],
                     f"{c['cite']} is marked as restating '{c['restates']}', which is neither a study "
                     f"nor a declared external source in observations.json; the card would cite a "
                     f"source that does not exist.")

        # METRIC_MISMATCH - a predictive value is not a lateralization percentage. PPV
        # is P(onset side | sign); a lateralization figure is the share of cases falling
        # to one side. Averaging one into the other is a category error, not a rounding
        # one, and it is live in this library: Kinney's hemifield 100% is recorded in the
        # source ledger as `ppv`.
        want = s.get("metric", "lateralization")
        for c in contribs:
            sm = c.get("source_metric")
            if sm and sm != want and want == "lateralization":
                pooled_in = "value" in c and not c.get("provenance")
                flag("metric_mismatch", "high" if pooled_in else "medium", s["sign"],
                     f"{c['cite']} contributes a figure the source ledger records as '{sm}', not a "
                     f"lateralization percentage"
                     + (" - and it is being averaged into one." if pooled_in else
                        " (currently excluded from the average, so it changes no number today)."))

        # SINGLE_SOURCE - low robustness. Only where that one source is a series: a
        # lone review is the weaker review_only case below, and calling it "a single
        # study" here would reintroduce the very wording that flag exists to correct.
        if s.get("pooled") is not None and s["n_studies"] == 1 and s.get("n_primary") == 1:
            flag("single_source", "low", s["sign"],
                 f"pooled figure rests on a single study ({pooled_rows[0]['cite'] if pooled_rows else '?'}); "
                 f"treat as provisional until corroborated.")

        # REVIEW_ONLY_FIGURE - no series in this library measured this. Every value in
        # the pool is a narrative review quoting a cohort that was never read here, so
        # "1 study with a percentage" describes who repeated the number, not who
        # measured it. This is the restatement problem one level up: excluding a review
        # that restates another review still leaves a review standing in for a series.
        revs = [c for c in pooled_rows if c.get("ground_truth") == "review"]
        if s.get("pooled") is not None and s.get("n_primary") == 0:
            vals = ", ".join(f"{c['cite']} {c['value']}%" for c in revs)
            extra = ("" if len(revs) < 2 else
                     " Two reviews on one sign with no primary series between them is the shape of a "
                     "single cohort quoted twice; differing figures do not rule that out, so the "
                     "near-identical-value check will not catch it.")
            flag("review_only_figure", "medium", s["sign"],
                 f"every averaged value is a narrative review quoting a series this library has not "
                 f"read ({vals}); k counts reviews, not measurements.{extra}")

        # UNTRACED_REVIEW_FIGURE - a review's percentage averaged beside a primary series
        # as though it were a second, independent measurement of the same thing. It
        # usually is not: it is a figure the review took from somewhere. Where the source
        # is identified the observation becomes `secondary_citation` and drops out of the
        # average; until then it is being pooled on the strength of not having been traced.
        if s.get("n_primary") and revs:
            vals = ", ".join(f"{c['cite']} {c['value']}%" for c in revs)
            nr, np_ = len(revs), s["n_primary"]
            flag("untraced_review_figure", "medium", s["sign"],
                 f"{nr} review figure{'' if nr == 1 else 's'} ({vals}) "
                 f"{'is' if nr == 1 else 'are'} averaged beside "
                 f"{np_} primary series as {'an independent measurement' if nr == 1 else 'independent measurements'}. "
                 f"A review usually took its number from somewhere; if that source is one of the series "
                 f"already here, this figure is being counted twice and should drop out of the average.")

    # ---- UNTRACEABLE_VALUE. observations.json used to assert that every numeric value
    #      was drawn from corpus_findings.json. Seven were not - some are honest curator
    #      arithmetic over a quoted fraction (16/17 -> 94), some come from a paper whose
    #      findings are not in that file at all. The claim is now accurate, and this
    #      check keeps it that way: the count is published on every run rather than
    #      resting on a sentence nobody re-checked.
    corpus_vals = {}
    for p in corpus.get("papers", []):
        key = (p.get("cite") or "").lower()
        corpus_vals[key] = {float(f["value"]) for f in p.get("findings", [])
                            if isinstance(f.get("value"), (int, float))}

    def corpus_has(study, value):
        surname, year = study.split()[0].lower(), study.split()[-1]
        cands = [v for k, v in corpus_vals.items() if surname in k and year in k] or \
                [v for k, v in corpus_vals.items() if surname in k]
        if not cands:
            return None                      # paper not represented in the ledger
        return any(float(value) in v for v in cands)

    untraceable = []
    for s in obs.get("signs", []):
        for o in s.get("observations", []):
            if not isinstance(o.get("value"), (int, float)):
                continue
            hit = corpus_has(o["study"], o["value"])
            if hit is not True:
                untraceable.append(f"{s['sign']} / {o['study']} {o['value']:g}%"
                                   + (" (paper absent from corpus_findings.json)" if hit is None else ""))
    if untraceable:
        flag("untraceable_value", "low", "(ledger)",
             f"{len(untraceable)} numeric observation value(s) have no matching numeric finding in "
             f"corpus_findings.json, so they cannot be checked against a quote and locator.",
             untraceable)

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
        blocking = [f for f in flags
                    if f["kind"] in ("unmarked_restatement", "orphan_restatement",
                                     "direction_clash", "duplicate", "duplicate_card",
                                     "orphan_stem", "ppv_orphan_link", "ppv_direction_clash",
                                     "sens_orphan_link", "sens_no_condition", "sens_bad_metric")
                    # a mismatched metric blocks only where it reaches the average; kept
                    # visible but non-blocking while it sits excluded, so the guard is
                    # in place before the case that needs it arrives
                    or (f["kind"] == "metric_mismatch" and f["severity"] == "high")]
        if blocking:
            print(f"\nSTRICT: {len(blocking)} blocking flag(s).")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(review())
