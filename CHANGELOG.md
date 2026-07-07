# Changelog

All notable changes to the dataset and resource are recorded here.
Format loosely follows Keep a Changelog; dates are ISO-8601.

## [Unreleased]
### Added
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
