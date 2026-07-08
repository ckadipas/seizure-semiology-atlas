# Changelog

All notable changes to the dataset and resource are recorded here.
Format loosely follows Keep a Changelog; dates are ISO-8601.

## [Unreleased]
### Added
- **Full-corpus extraction (37 papers).** Every paper in the library was read in
  full and machine-extracted into `enrichment/corpus_findings.json` (599 findings,
  each with a short verbatim quote + locator for verification) — the auditable raw
  material behind the meta-analysis. This multi-sourced signs that previously
  rested on Loddenkemper alone: forced version now pools 5 studies (Loddenkemper,
  Wyllie, Kotagal, Roh, Fakhoury; pooled ~99%), postictal dysphasia 5 (Gabr,
  Maillard SEEG, Serafetinides, Loddenkemper, Blair; pooled 92%), and dystonic
  posturing, tonic, clonic, and eye-blinking each gained an independent primary
  source. Added a new contralateral sign (lower facial/mimetic weakness, Blair).
  Alim-Marvasti 2022 was extracted for the record but remains excluded from the
  analysis (literature-mined; see README).
### Fixed
- **Corrected a propagated misreading:** Roh 1996 forced version was recorded as
  "89% contralateral"; full-text reading shows version was contralateral in 14/14
  (100%) — the "89" was "89 seizures" (34 dystonia + 17 tonic + 24 clonic + 14
  version, all contralateral). Also flagged (in the extraction notes) that the two
  Bonini files and the two McGonigal "On seizure semiology" files are duplicate
  uploads of one paper each, and three internal inconsistencies in Elwan 2018.
### Added (earlier)
- **Weighted meta-analysis** (top foldable plot): each semiology's lateralization
  percentage pooled across every source that reports it, weighted by evidence
  class and ground-truth directness (`tools/meta_analysis.py`, deterministic).
  Two nested views — region → gyrus/Brodmann → sign, and semiology A–Z → region —
  with the full per-study value + weight breakdown on expand, so every figure is
  traceable. Structured source data lives in `enrichment/observations.json`;
  method documented in `METHODS.md`.
- **Adversarial clinical review.** Deterministic checker (`tools/adversarial_review.py`)
  flags conflicts, direction clashes, duplicates/double-counts, orphaned figures,
  and single-source figures → `enrichment/review_flags.json`. Genuine conflicts
  surface in a new on-page "Conflicting evidence" panel (e.g. ictal spitting:
  review reports non-dominant, curated card localizes dominant — surfaced, not
  reconciled); robustness caveats show inline per sign. A manual LLM reviewer
  workflow (`.github/workflows/review.yml`) re-reads the actual PDFs on the CI
  runner to catch misreadings the mechanical pass cannot.
- CI now regenerates and sync-checks `meta_analysis.json` and `review_flags.json`
  alongside `enrichment.json`; `make review` reruns the analysis + review.
- Repository scaffold: version-controlled data, CI build/deploy, validation gate,
  issue/PR templates, and a paper-intake pipeline.
- Public-repo publishing path (free GitHub Pages) and `CITATION.cff` for a
  citable release (Zenodo-DOI ready).
- Late forced head version: corroborating Foldvary-Schaefer & Unnwongse 2011
  evidence — version-accompanied head deviation is contralateral, whereas
  non-versive head rotation tends to be ipsilateral.
- Footer "Contribute a paper or correction" link to the GitHub issue chooser.
- Automated paper-intake pipeline (`.github/workflows/intake.yml`): a PDF attached
  to an `intake` issue is read by **Claude Code** (`anthropics/claude-code-action`,
  authenticated with a `CLAUDE_CODE_OAUTH_TOKEN` from your Claude subscription — no
  separate API key), which writes short, **page-cited** findings and opens a PR for
  owner approval. Machine-added evidence lives in `enrichment/intake_findings.json`;
  `tools/check_provenance.py` gates every finding on a source page. Evidence entries
  can now carry a `pg` page reference, shown on the sign's evidence panel.
- Late forced head version: added Wyllie et al. 1986 (Neurology) — the
  foundational series establishing versive (forced, sustained) head/eye
  deviation as reliably contralateral and non-versive turning as
  non-localizing. Added to the source library (from intake issue #7).
### Changed
- Front-page declutter: trimmed the intro to a single instruction line, removed
  the header stat badges and decorative emoji, and collapsed the
  lateralizing-reliability chart and framework callout into closed-by-default
  disclosures so the sign index is visible on landing.
- Subregions are now collapsible banners under each region (e.g. Mesial Temporal
  under Temporal), collapsed by default; search/filter auto-expands matches, and
  Expand/Collapse all now cover subregions.

## [1.0.0]
### Added
- 100 curated localizing/lateralizing signs across 7 regions.
- Corpus enrichment: 42 source-grounded findings across 32 signs; ictal
  dysprosody added from Montavont 2005; 31-paper source library.
- Lateralizing-reliability chart sourced from Loddenkemper & Kotagal 2005 (Table 1).
### Removed
- Alim-Marvasti 2022 probabilistic layer (see README §Design decisions for the
  rationale — literature-mined taxonomy produced artifactual odds ratios).
