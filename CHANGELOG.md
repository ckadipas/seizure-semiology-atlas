# Changelog

All notable changes to the dataset and resource are recorded here.
Format loosely follows Keep a Changelog; dates are ISO-8601.

## [Unreleased]
### Changed
- **Single source of truth.** Each curated sign card is now linked (by explicit id,
  not fragile substring) to its meta-analysis ledger entry, and renders the SAME
  pooled lateralization figure and the SAME per-study source list as the top plot —
  so a sign shows identical stats and citations everywhere (previously the card and
  the plot were computed from two disconnected paths and could disagree, e.g. forced
  version showed 40–50%/75–80% on the card but 98.6% across 6 studies in the plot).
- **Single source of truth extended to predictive value.** Cards now surface the
  corpus PPV figures for their sign, drawn from the same `corpus_findings.json`
  ledger the source-figures explorer renders, linked by each finding's explicit
  `card_ids` (assigned by exact phenomenon match, never fuzzy). 28 PPV figures across
  10 signs (version, tonic/dystonic/clonic posturing, figure-of-4, preserved-
  responsiveness automatisms, nose-wiping, Todd's palsy, epigastric aura) now appear
  identically on the card and in the explorer, each with population context and its
  verbatim quote. Ambiguous or aggregate PPV figures (asymmetric clonic *ending*, the
  M2e naming collision, multi-sign combinations, hemianopia) are deliberately left
  explorer-only rather than force-attached.
- **Sensitivity is now computed from the master ledger.** Sensitivity of a sign for a
  localization = `P(sign | localization)` — its frequency within that group — so the raw
  data is the verified frequency-within-a-group findings. Eleven such findings across
  nine signs are now tagged in the ledger (`sens_card_ids` + `sens_for`); the meta engine
  computes per-(sign, localization) descriptive statistics and the card (tagged
  **corpus**), a new **Descriptive statistics — sensitivity by localization** report
  section, and the explorer all render the same numbers. Tag another finding and all
  three update on the next build. A note states the method; coverage counts are shown.
- **Specificity stays a marked estimate, honestly.** It needs the sign's rate in the
  *other* localization groups, which the corpus reports for essentially no sign, so it is
  not computed — card specificity is tagged **est.** with a tooltip, never fabricated.
  Sensitivity on signs with no localization-conditioned frequency is likewise **est.**
### Verified
- **Adversarial re-verification of the corpus against source text.** Every recorded
  finding was re-read against its paper: 485/489 confirmed (99.2%), 4 corrected, 0
  fabricated. Corrections: Loddenkemper ictal-speech direction → dominant; a
  Serafetinides metrazol-vs-amygdala misattribution; a Bonini Group-4 v-test note. Two
  byte-identical duplicate papers were removed (33 papers / 487 findings).
### Fixed
- **Consolidated a duplicate sign.** "Late forced/tonic head version" (#12) and
  "Forced contralateral tonic head/eye version" (#60) were the same sign filed under
  two regions; merged into one card under the frontal FEF home.
- **Ictal spitting marked contested.** The card cited Kellinghaus 2003 (dominant)
  while the pooled corpus (Loddenkemper, Fakhoury) lateralizes non-dominant — now
  surfaced as a genuine conflict rather than a silent single-side claim.
- The adversarial review now flags **duplicate cards** and **card↔ledger direction
  mismatches** through the explicit link.
### Added
- **Ictal central apnea** and **postictal central apnea** added as new mesial-temporal
  signs (Lacuey 2024; Meletti 2025; Ochoa-Urrea 2025): objective breathing cessation
  that predicts mesial temporal onset (OR 3.8, spec 0.82) — distinct from the
  subjective dyspnea aura.
- **Intake can now propose new signs.** A submitted paper describing a well-evidenced
  sign not yet in the atlas is added under `new_signs` in `intake_findings.json`
  (merged into the atlas at build time) rather than declined — the maintainer approves
  by merging the pull request. `tools/check_provenance.py` validates each proposed
  new-sign record and lets findings attach to it.
- **Weighted meta-analysis** (top foldable plot): each semiology's lateralization
  percentage pooled across every source that reports it, weighted by evidence
  class and ground-truth directness (`tools/meta_analysis.py`, deterministic).
  Two nested views — region → gyrus/Brodmann → sign, and semiology A–Z → region —
  with the full per-study value + weight breakdown on expand. Structured source
  data lives in `enrichment/observations.json`; method documented in `METHODS.md`.
- **Source-figures table**: every extracted figure (lateralization, frequency,
  localization, PPV) rendered as a searchable, type-filterable table, each row
  checkable against its verbatim quote and source locator. Frequency/localization/
  PPV figures are population-specific and are listed here rather than pooled.
- **Full-corpus extraction**: every paper in the library extracted into
  `enrichment/corpus_findings.json` (short verbatim quote + locator per figure) —
  the record behind the analysis. This multi-sourced signs that previously rested
  on a single review: forced version pools 5 studies (~99%), postictal dysphasia 5
  (92%), and dystonic posturing, tonic, clonic, eye-blinking, somatosensory aura,
  Todd's palsy, nose-wiping and others each gained independent sources. Added a
  contralateral lower facial (mimetic) weakness sign.
- **Source-review checks** (`tools/adversarial_review.py`): flags studies that
  disagree on a sign, a pooled direction that contradicts the curated card,
  duplicated figures, orphaned figures, single-source figures, a PPV figure linked
  to a non-existent card, a PPV direction that contradicts the card it is shown on,
  a sensitivity-tagged finding pointing at a missing card / naming no group / sitting
  on a non-frequency figure, and records which signs have a computed sensitivity vs
  an estimate → `enrichment/review_flags.json`. CI regenerates and sync-checks the
  generated JSON; `make review` reruns the analysis + review.
### Fixed
- Corrected a propagated misreading: Roh 1996 forced version was recorded as "89%
  contralateral"; the source shows version contralateral in 14/14 (100%) — the
  "89" was "89 seizures" (34 dystonia + 17 tonic + 24 clonic + 14 version, all
  contralateral).
### Changed
- Front-page declutter: trimmed the intro, removed the header stat badges and
  decorative emoji, and collapsed the reliability chart and framework callout into
  closed-by-default disclosures so the sign index is visible on landing.
- Subregions are collapsible banners under each region, collapsed by default;
  search/filter auto-expands matches.

## [1.0.0]
### Added
- 100 curated localizing/lateralizing signs across 7 regions.
- Corpus enrichment: source-grounded findings; ictal dysprosody from Montavont
  2005; source library from the paper corpus.
- Lateralizing-reliability chart sourced from Loddenkemper & Kotagal 2005 (Table 1).
