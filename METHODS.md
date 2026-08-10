# Methods — weighted averages & source review

> **This is not a meta-analysis.** There is no protocol, no prespecified eligibility
> criteria, no reproducible search, no risk-of-bias instrument, no inverse-variance
> weighting, no confidence intervals and no heterogeneity statistics. What follows is a
> transparent weighted average of the percentages extracted from the source library,
> published with every contributing value and the weight it carried so the arithmetic
> can be checked. It should be read as a summary of what this library reports, not as
> evidence synthesis.

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

**What `N` is, and what it is not.** `N` is the size of the study's *cohort*, not the
number of patients the lateralization percentage was actually computed over. Those are
usually different, often by a lot: Wyllie 1986 is a 37-patient study whose version
figure rests on 27, and a 500-patient series reporting a sign seen in 12 would carry the
weight of 500. The per-sign denominator is not recorded in the ledger — where a source
states it, it appears verbatim in the observation's note and nowhere else. So
`size_factor` is a rough proxy for how substantial the study is, **not** a measure of
how precisely that percentage was estimated, and it must not be read as one. Ten of the
sixteen studies report no N at all, where the factor is 1.0 and does nothing.

**Where the weighting decides the answer, the answer says so.** On most signs the
weighted and unweighted means agree to within a point. On three they do not — because
a light review and a heavy series disagree, and the weights, not the data, pick the
winner. Those figures publish the plain mean beside the weighted one (*"unweighted mean
77%"*), so a reader can see how much of the number is the scheme's doing. The threshold
is 5 points; below it the second figure would be noise.

The scheme lives in `observations.json` and is tunable — change the numbers and
re-run. For each sign the lateralization percentage is a weighted mean,
`Σ(wᵢ·vᵢ)/Σwᵢ`, reported with its across-study range, the summed weight, and a
certainty tier. A weighted SD is shown only from four contributing studies up:
below that it is a spread statistic over two or three points, which is noise
dressed as precision. **Frequencies are not pooled** — they are population-specific
(% of FLE vs % of TLE vs % of EMU patients), so pooling them would be invalid; they
are listed in the source-statistics table instead.

### Three kinds of number that are never averaged

A value in the ledger is not automatically a measurement. Three provenance marks say
it is not, and the page prints which one applies beside the number rather than showing
a figure it silently declines to use:

| Mark | What it is |
|---|---|
| `secondary_citation` | a source restating a figure someone else measured; names it in `restates` |
| `review_synthesis` | a review's own summary across several series — it restates no single one of them |
| `interpolated_midpoint` | a point estimate the curator derived from a reported range (`value_range`) |

The last two exist because both were previously recorded as restatements of a specific
study, which was false in both cases. Loddenkemper's postictal-dysphasia figure is *"80–100%
across series (midpoint 90)"* — a synthesis, not a restatement of Gabr 1989. Loddenkemper's
dystonia figure was marked as restating Roh 1996 on nothing but `100 == 100`, while its own
note names Yen. And Blair's postictal-aphasia *85* is the midpoint of a quoted "~80–90%":
nobody measured 85, yet it was being averaged, raising that sign to `k = 4` and generating a
weighted SD over a number the curator had invented.

### Restatements are not averaged

A narrative review reporting a figure it took from a series is not a second
measurement of that figure. Such an observation is marked
`provenance: secondary_citation` and names the study it restates; it stays visible
on the sign as a corroborating citation, labelled *restates X — not averaged*, and
is excluded from both the mean and `k`. This applies whether the study it restates
is the primary series itself or a second review of that same series — two reviews
citing one cohort are still one cohort. `tools/adversarial_review.py` flags any
unmarked pair that looks like this, and the check blocks CI, so the count beside a
pooled percentage cannot quietly drift back to counting citations instead of
studies.

### Certainty tiers

`k` is the number of studies contributing a percentage — restatements excluded, and
direction-only sources never counted, since they measured nothing. The first
matching rule wins:

| Tier | Rule |
|---|---|
| review only | every value in the pool came from a narrative review |
| single source | `k ≤ 1` |
| contested | the studies disagree by ≥ 25 points, at any `k ≥ 2` |
| well supported | `k ≥ 3` and they agree within 25 points |
| moderate | `k = 2` and they agree within 25 points |

Summed weight never sets the tier: a single heavy study is still a single study,
and disagreement outranks count — two studies 38 points apart are not better
evidence than two that agree.

**`review only` is the restatement rule one level up.** Excluding a review that restates
another source still leaves a review standing in for a series, and six signs here are in
exactly that position: every percentage behind them is Loddenkemper 2005 or Blair 2012
quoting a cohort this library has never read. Calling that *"1 study with a percentage"*
describes who repeated the number, not who measured it, so those figures now read *"1
review with a percentage · review only — no primary series here"* and carry the lowest
certainty. Two reviews on one sign with no series between them is worse still — it is
the shape of a single cohort quoted twice, and unlike the unmarked-restatement check it
cannot be caught by comparing values, because the two reviews may disagree about what
the cohort said. *Lower facial weakness* is that case: 86% and 75%, both traceable in
their own notes to a 50-patient series. Such a figure is a pointer to the original
paper, not evidence this atlas has checked.

The plot offers two views of the same output: region → gyrus / Brodmann area →
sign, and semiology A–Z → region. Each sign's per-study values and weights are one
click below it.

## Figures on the sign cards — one ledger, no re-typing

A card shows only figures that trace to a ledger, so the card and the rest of the
page can never disagree:

- **Lateralization** comes from the sign's `observations.json` entry (linked by
  explicit `sign_ids`); the card prints the same pooled value and per-study sources
  as the top plot.
- **Predictive value (PPV)** comes from `corpus_findings.json` — the same records
  the source-figures table renders — surfaced on the card through each finding's
  explicit `card_ids`, assigned by an exact phenomenon match (never a fuzzy one).
  PPV is population-specific, so it is listed per source with its context, not
  pooled. Ambiguous or aggregate PPV figures are left in the table only.
- **Sensitivity** is **computed** as `P(sign | localization)` — how often the sign
  appears within a localization group, which is exactly a frequency-within-that-group
  figure. Qualifying verified frequency findings carry a `sens` list in the ledger,
  each entry `{card_id, group, value}`; one finding can feed several groups at once
  (e.g. a temporal SEEG paper that reports a sign's rate in mesial vs mesiolateral vs
  lateral subtypes contributes three entries, its `M/ML/L %` parsed straight from the
  tabulated value). The meta engine groups every entry per (sign, localization) and the
  card (tagged `corpus`), the *Descriptive statistics — sensitivity by localization*
  section, and the explorer all read the same numbers. Tag another finding and every
  one of them updates on the next build. Coverage is sparse and uneven — the corpus
  reports these frequencies inconsistently — so each figure shows its source count `k`;
  a card with no localization-conditioned frequency keeps a curator estimate tagged
  `est.`. `k` counts **publications**, not tagged rows: a paper reporting the same
  sign-in-group frequency in two places is collapsed to its own mean first, so it cannot
  contribute twice or inflate `k` — the same rule restatements get upstream. These means
  are unweighted, unlike the lateralization figures, because the group denominators are
  not recorded; the two kinds of number are not comparable and should not be read
  side by side as if they were.
- **Specificity** is **not computed**: it needs the sign's rate in the *other*
  localization groups (the false-positive side), which this corpus reports for
  essentially no sign. Card specificity therefore stays a curator teaching estimate,
  tagged `est.` — never fabricated as a source figure.

## Review checks — `tools/adversarial_review.py`

**Its findings are shown on the page.** Each flag renders on the sign it was raised
against, in the expanded row of the top plot. Until recently they were computed on every
build, written to `review_flags.json`, indexed by the generator into a variable that was
never read, and shown to nobody — while three files described a "conflicting-evidence
panel" that did not exist. Two high-severity conflicts, 38 and 30 points, were flagged on
every run and reached no reader.

Runs on every pull request and writes `enrichment/review_flags.json`. It flags
studies that disagree on a sign's figure, an unmarked restatement, a `restates`
target that names no study, a pooled direction that contradicts the curated card,
the same figure entered under two studies or two signs, a figure that attaches to
no sign, figures resting on a single study, a PPV figure whose `card_ids` point at
a card that does not exist, a PPV direction that contradicts the card it is
surfaced on, and a sensitivity-tagged finding that links to a missing card, names
no localization group, or sits on a non-frequency figure. It also records which
signs have a computed sensitivity vs a curator estimate.

CI runs it with `--strict`, and the split matters:

- **Blocking** — everything that means the data is wrong about itself: an unmarked
  restatement, a `restates` naming a study that does not exist, a direction clash,
  a duplicate study or duplicate card, an orphaned sign stem, and the PPV /
  sensitivity link checks. A curator has to fix these before the change lands.
- **Advisory** — `conflict`, `single_source`, `review_only_figure` and
  `untraced_review_figure`. A genuine, disclosed disagreement (e.g. ictal spitting) is a
  fact about the literature, not a defect a build can repair; it is surfaced on the
  relevant sign, not silently reconciled, and never fails the build. The two review
  flags describe how thin the evidence is: the fix is a curator tracing a citation, or
  the library gaining the paper the review was quoting. Neither is something a build can
  do, so neither blocks — but both are counted and printed on every run.
  `untraced_review_figure` currently stands at seven: review percentages pooled beside a
  primary series as though they were independent second measurements, on the strength of
  nobody having traced them yet. Nine others have been traced and dropped out of their
  averages; these are the ones still waiting.

## Source-figures table — `generator/gen_study.py`

Every extracted figure — lateralization, frequency, localization, PPV — renders
in a searchable, type-filterable table, each row checkable against its verbatim
quote and source locator.

## Adding evidence

New figures enter through `enrichment/observations.json` (structured, attributed,
with a locator). `make build` regenerates the analysis, the review, and the HTML;
the generated JSON is committed so diffs stay legible and CI checks it in sync.
The HTML in `docs/` is a build artifact — never hand-edit it.
