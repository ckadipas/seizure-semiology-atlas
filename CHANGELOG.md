# Changelog

All notable changes to the dataset and resource are recorded here.
Format loosely follows Keep a Changelog; dates are ISO-8601.

## [Unreleased]
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
  duplicated figures, orphaned figures, and single-source figures →
  `enrichment/review_flags.json`. CI regenerates and sync-checks the generated
  JSON; `make review` reruns the analysis + review.
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
