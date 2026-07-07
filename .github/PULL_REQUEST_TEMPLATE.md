<!-- Thanks for contributing to the atlas. Keep the resource defensible: every
change to a figure should trace to a source. -->

## What does this PR change?

<!-- e.g. "Correct figure-of-4 lateralization %, add Kotagal 2000 evidence." -->

## Type of change
- [ ] Correction to an existing sign (`data/semiology_data.json`)
- [ ] New sign
- [ ] Evidence / citation added or updated (`enrichment/build_enrichment.py`)
- [ ] New paper integrated (also updates `corpus/manifest.csv` + `PAPERS`)
- [ ] Tooling / generator / docs

## Source
<!-- Citation(s) supporting the change: author, year, journal, specific figure. DOI ideal. -->

## Checklist
- [ ] I edited the **source** (`data/…json`, `enrichment/…py`) — **not** the generated HTML.
- [ ] `make validate` passes locally.
- [ ] `make build` succeeds and I committed the updated `enrichment/enrichment.json`.
- [ ] Every changed figure has a citation.
- [ ] I updated `CHANGELOG.md` under **[Unreleased]**.
- [ ] No copyrighted full text or PDFs were committed (only short attributed extractions).
