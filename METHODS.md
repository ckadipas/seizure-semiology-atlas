# Methods — weighted meta-analysis & source review

Educational resource, not clinical. The figures here are teaching estimates drawn
from the source library; they are not validated for individual patient decisions.
See `DISCLAIMER.md`.

## Source data

Every quantitative figure is extracted from the papers in `corpus/manifest.csv`
into `enrichment/corpus_findings.json`, where each finding carries a short
verbatim quote and a locator (page / table / section). That file is the auditable
record behind everything else. Structured, weighted observation records for the
pooled analysis live in `enrichment/observations.json`.

## Weighted pooling — `tools/meta_analysis.py`

Deterministic and reproducible: re-running on the same input always yields the
same output, and every pooled figure carries the per-study values and weights
that produced it.

Each observation's weight is

```
weight = class_base × ground_truth_mult × size_factor
```

| Factor | Values |
|---|---|
| `class_base` | Class I = 3.0, II = 2.0, III = 1.0 (study design) |
| `ground_truth_mult` | SEEG / post-op = 1.5; intracranial EEG = 1.35; imaging concordance = 1.15; video-EEG = 1.2; scalp EEG = 1.1; review = 1.0 |
| `size_factor` | `1 + log10(N)/2`, capped at 2.0, when N is reported; 1.0 otherwise (N is never assumed) |

The scheme lives in `observations.json` and is tunable — change the numbers and
re-run. For each sign the lateralization percentage is a weighted mean,
`Σ(wᵢ·vᵢ)/Σwᵢ`, reported with its across-study range, a weighted SD, the summed
weight, and a certainty tier. **Frequencies are not pooled** — they are
population-specific (% of FLE vs % of TLE vs % of EMU patients), so pooling them
would be invalid; they are listed in the source-figures table instead.

The plot offers two views of the same output: region → gyrus / Brodmann area →
sign, and semiology A–Z → region. Each sign's per-study values and weights are one
click below it.

## Review checks — `tools/adversarial_review.py`

Runs on every pull request and writes `enrichment/review_flags.json`. It flags
studies that disagree on a sign's figure, a pooled direction that contradicts the
curated card, the same figure entered under two studies or two signs, a figure
that attaches to no sign, and figures resting on a single study. These are
advisory — a genuine, disclosed disagreement (e.g. ictal spitting) is surfaced on
the relevant sign, not silently reconciled.

## Source-figures table — `generator/gen_study.py`

Every extracted figure — lateralization, frequency, localization, PPV — renders
in a searchable, type-filterable table, each row checkable against its verbatim
quote and source locator.

## Adding evidence

New figures enter through `enrichment/observations.json` (structured, attributed,
with a locator). `make build` regenerates the analysis, the review, and the HTML;
the generated JSON is committed so diffs stay legible and CI checks it in sync.
The HTML in `docs/` is a build artifact — never hand-edit it.
