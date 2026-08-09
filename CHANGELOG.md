# Changelog

All notable changes to the dataset and resource are recorded here.
Format loosely follows Keep a Changelog; dates are ISO-8601.

## [Unreleased]
### Added
- **The Brodmann map follows the repo's own structure.** It was first written as a
  feature bolted onto the generator: 39 areas, 17 sub-region rules, 79 per-sign
  overrides, 80 label positions and 231 outline points all lived as Python literals
  inside `generator/brain_atlas.py`, with a second label-position system layered on
  top of the first, a separate one-off gate script, and two authoring scripts that
  duplicated the same segmentation code. That is not how this repo works. All of that
  curation now lives in **`data/brodmann_map.json`**, a hand-edited source of truth
  beside `data/semiology_data.json`, validated against **`schema/brodmann.schema.json`**
  by the existing **`tools/validate_data.py`** gate — one gate, one CI step, as before.
  `generator/brain_atlas.py` is now a 130-line renderer (was 518) holding geometry
  maths and no knowledge; the duplicate label system is gone (one position per area
  per view, in data); and the two plate scripts are one `tools/brodmann_plate.py`
  sharing their segmentation. The rendered page is byte-for-byte unchanged apart from
  two inconsistencies the refactor fixed (clip-path ids and `aria-label` casing).
- **New papers flow onto the Brodmann map.** A sign added by intake under an
  existing sub-region inherits that sub-region's cortical areas and appears on the
  map with no manual step — verified end to end. A sign that introduces a *new*
  sub-region needs one line of mapping, and the build now says so precisely rather
  than failing cryptically: the error names the sub-region, points at
  `mapping.by_sub` in `data/brodmann_map.json`, and lists the available area ids.
  The intake workflow prompt and `intake/INTAKE.md` both carry the requirement, and
  the intake's publishing step now commits `data/brodmann_map.json` alongside the
  findings, so a mapping added during extraction reaches the pull request.
- **The map is under the ledger's sync oversight.** Its curation is keyed by sign id
  and sub-region string, so it could drift silently: an intake that added a sign,
  renamed a sub-region or renumbered an id would have left signs off the map with
  every gate still passing. `tools/validate_data.py` now fails the build if a rendered
  sign maps to no area (unless declared unmapped with a reason), a per-sign entry no
  longer names the sign it was written for, a sub-region rule is orphaned, a dataset
  sub-region has no rule, a referenced area is undefined, or a defined area is drawn
  in no view without being marked buried. Per-sign entries record the **sign name**
  alongside the id, so drift is reviewable in the diff rather than merely detectable.
  Coverage is reported every run (110/111 signs, 39 areas, 4 views, 1 declared
  unmapped).
- **Interactive Brodmann map — "where each semiology localizes".** A new figure at the
  top of the page maps every sign in the dataset onto the Brodmann areas it localizes to,
  across three schematic surface views of one hemisphere: **lateral, dorsal and ventral**.
  Each numbered area is clickable (and keyboard-reachable); selecting one opens a panel
  listing the semiology localized there, ordered by evidence tier, with its phase,
  lateralizing value and evidence level — and clicking a row jumps to that sign's full
  card in the index below. A **hemisphere switch (left/right)** mirrors the view and
  re-reads each sign for that side: contralateral/ipsilateral signs are restated as the
  body side they appear on, and dominant-only signs are dimmed when the non-dominant
  hemisphere is shown. An optional *shade by density* toggle tints areas by how many
  signs they carry; the default presentation is deliberately plain. Areas with no
  surface representation — **insula (13–16)**, **cingulate (24/32)** and deep
  subcortical — are offered as separate chips rather than being silently dropped, and
  the one sign with no lobar localization is declared under the figure.
  The mapping is derived from the dataset's own `sub`/`loc` localization fields (which
  already name Brodmann areas), refined per sign where the record is more specific; the
  brain outlines are schematic drawings authored for this atlas, not traced artwork.
- **Integrated Abou-Khalil's seizure-semiology chapter** (in Misulis et al., *Atlas of
  EEG, Seizure Semiology, and Management*, 3rd ed., Oxford Univ. Press 2022, §3.4). This
  authoritative textbook is added to the source library and now **corroborates the
  lateralizing direction of 13 existing signs** — forced version, dystonic/tonic/clonic
  posturing, figure-of-4, somatosensory aura, ictal spitting, ictal vomiting,
  preserved-responsiveness automatisms, ipsilateral automatisms, unilateral eye-blinking,
  postictal nose-wiping and postictal aphasia — as a qualitative (directional) source in
  the meta-analysis ledger. Each carries a short attributed quote and page locator; being
  directional, they add a corroborating citation without altering any pooled percentage.
  This retires several signs that had rested on a single citation (e.g. ictal spitting and
  ictal vomiting now show three concordant sources).
- **Three new right-temporal lateralizing signs** the chapter describes and the atlas
  lacked: **ictal drinking automatism**, **postictal cough**, and **postictal urinary
  urgency** (all non-dominant/right temporal, evidence level III, cited to the chapter).
  Every added quote was mechanically checked against the source text; no full text or PDF
  is committed (short attributed extractions only).
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
  data is the verified frequency-within-a-group findings. Each carries a `sens` list of
  `{card_id, group, value}` entries; the meta engine computes per-(sign, localization)
  descriptive statistics and the card (tagged **corpus**), a new **Descriptive
  statistics — sensitivity by localization** report section, and the explorer all render
  the same numbers. **32 figures across 15 signs**, including temporal SEEG-subtype
  sensitivities (mesial / mesiolateral / lateral, from Maillard 2004) whose `M/ML/L %`
  are parsed straight from the tabulated values — so e.g. epigastric aura reads
  mesial 46% ▸ mesiolateral 39% ▸ lateral 8%. Coverage is deliberately sparse (the
  corpus reports these inconsistently); each figure shows its source count `k`. Tag
  another finding and all three surfaces update on the next build.
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
