# Methods — weighted meta-analysis & adversarial review

This resource is **educational, not clinical**. The figures below are teaching
estimates drawn from the source library; they are not validated for individual
patient decisions. See `DISCLAIMER.md`.

The atlas has three cooperating layers — the "three agents" — deliberately split
by what each is good at: deterministic arithmetic stays in code, semantic
judgement stays in the LLM, and presentation stays in the generator.

```
 observations.json ─►  meta_analysis.py   ─►  meta_analysis.json ─┐
 (source-attributed    (STATISTICAL agent:                        │
  numbers + weights)     deterministic pooling)                   ├─► gen_study.py ─► docs/*.html
                     ─►  adversarial_review.py ─► review_flags.json┘   (DATAVIZ layer:
                          (REVIEWER agent, mechanical half)             the top foldable plot)
                     ─►  review.yml (REVIEWER agent, semantic half, reads the PDFs on CI)
```

## 1. Statistical layer — `tools/meta_analysis.py`

Deterministic, reproducible, and traceable **by design**. No LLM computes any
number here: re-running the script on the same input always yields the same
output, and every pooled figure carries the exact per-study values and weights
that produced it. That is what makes the numbers auditable.

**Input.** `enrichment/observations.json` holds one structured record per
source observation: the sign, its lobe / gyrus / broad Brodmann area, the
lateralizing direction, the reported percentage, the source study, and (where
known) the page. A `studies` table declares each study's evidence class,
ground-truth type, and sample size.

**Weighting.** Each observation's weight is

```
weight = class_base × ground_truth_mult × size_factor
```

| Factor | Values |
|---|---|
| `class_base` | Class I = 3.0, II = 2.0, III = 1.0 (study design quality) |
| `ground_truth_mult` | SEEG / post-op seizure-freedom = 1.5; intracranial EEG = 1.35; imaging concordance = 1.15; video-EEG = 1.2; scalp EEG = 1.1; review = 1.0; none = 0.9 |
| `size_factor` | `1 + log10(N)/2`, capped at 2.0, when N is reported; 1.0 otherwise (N is **never fabricated**) |

The scheme is intentionally **transparent and tunable** — it lives in
`observations.json`; change the numbers, re-run, and every figure on the page
updates. Higher evidence class and more direct ground truth earn more weight,
exactly as the resource's own evidence tiers (see the site footer) intend.

**Pooling.** For each sign the lateralization percentage is a weighted mean,
`Σ(wᵢ·vᵢ)/Σwᵢ`, reported with its across-study range, a weighted SD, the summed
weight, and a certainty tier (well-supported / moderate / single-source) from
the study count and total weight. **Frequencies are *not* pooled** — they are
population-specific (% of FLE vs % of TLE vs % of EMU patients) and pooling them
would be invalid, so they are listed descriptively.

**Two nested views**, both from the same output: (i) region → gyrus / Brodmann
area → sign; (ii) semiology A–Z → region. Individual values and their weights
sit one click below each sign.

## 2. Reviewer layer — `tools/adversarial_review.py` + `.github/workflows/review.yml`

Splits into what each half can actually verify.

**Mechanical half (runs on every PR, deterministic).**
`tools/adversarial_review.py` emits `enrichment/review_flags.json`:

- **conflict** — studies disagree on a sign's figure beyond 15 points.
- **direction_clash** — the pooled direction contradicts the curated card.
- **double_count** — a review and a primary series report near-identical figures
  (the review may simply be citing the primary study).
- **duplicate** — the same finding text attributed to two papers, or one study
  entered twice for a sign (a repeated-upload artifact).
- **orphan_stem** — a figure that attaches to no curated sign.
- **single_source** — a pooled figure resting on one study (low robustness).

Genuine **conflict / direction_clash / orphan_stem** flags surface in the page's
"Conflicting evidence" panel — **surfaced, not silently reconciled**. Robustness
caveats (single-source, double-count) show inline under each sign. The checker is
advisory in CI: it never blocks a legitimate, disclosed conflict.

**Semantic half (manual, LLM, on the CI runner).** `review.yml` runs Claude Code
to read the *actual paper* — the one thing the deterministic pass cannot do — and
judge whether each extracted figure faithfully reflects its source (misreadings),
whether weights/classes are defensible, and whether conflicts were missed. It
runs on the runner precisely because the runner can download issue PDF
attachments. Manual trigger is the spend gate; opening its report/PR is the
publish gate. It commits only derived data and its Markdown report — never a PDF
or long source text (the IP boundary).

## 3. Dataviz layer — `generator/gen_study.py`

The top foldable plot. A dense, directly-labelled, 538/NYT-style small-multiples
view: a reliability strip per sign (weighted marker + across-study range),
direction by colour, certainty by pips, with the full per-study weight breakdown
on expand. Self-contained inline SVG/CSS/JS — no external libraries — so it stays
fast and CSP-safe. The HTML is a build artifact; never hand-edit it.

## Adding evidence

New numbers enter through `enrichment/observations.json` (structured, attributed,
page-cited) — by hand for a correction, or via the intake pipeline for a new
paper. `make build` regenerates the analysis, the review, and the HTML; the
generated JSON is committed so diffs stay legible and CI checks it in sync.
