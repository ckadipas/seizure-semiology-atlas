# AGENTS.md — Seizure Semiology Atlas public repository

This is the mandatory entry point for every agent or contributor. Read this file, `README.md`, `DISCLAIMER.md`, and `intake/INTAKE.md` before inspecting or changing scientific content.

## Authority and source of truth

- The repository owner is the final clinical and scientific authority.
- Source PDFs, images, extracted full text, model outputs, review rows, dossiers, and audits belong only in the private `ckadipas/semiology_refs` repository.
- The binding review protocol is private `semiology_refs/AGENTS.md`, release V29. It requires immutable source locators, stable `sign_id` mapping, independent review, statistical/laterality QA, and two owner gates.
- This public repository is a generated/redacted consumer. Existing website text, generated files, curator prose, prior-agent output, and the handoff are not independent source evidence.

## Scientific red zone

Without an exact owner-approved Gate-B packet and diff, do not edit scientific behavior or content in:

- `data/semiology_data.json`
- `data/brodmann_map.json`
- `enrichment/*.json`
- `enrichment/build_enrichment.py`
- `tools/meta_analysis.py`
- `generator/gen_study.py`
- `corpus/manifest.csv`
- generated `docs/` content
- any workflow or script that can transform model output into repository content

Do not mint, renumber, reuse, or change the meaning of a `sign_id`. Source-native terminology must be extracted privately before mapping to a pinned `sign_id` and registry semantic-version digest. A new sign remains a prospective token until owner-approved integration.

## Intake gates

A submitted issue, attachment, DOI, link, label, upload, or repository presence is not authorization to analyze or integrate a source.

1. Gate A: the owner approves the exact source/content hash or deterministic child scope, frozen release, representation, and private review budget.
2. Private review: source and all audit artifacts remain in `semiology_refs`.
3. Owner packet: proposed facts, locators, QA, mapping, bundles, and exact destination diff are presented without modifying this repository.
4. Gate B: the owner approves the exact closed packet and integration diff.
5. Deterministic integration may then apply only that approved diff. Deployment is separately authorized.

No agent or workflow may invoke Claude—or any other model—and then commit, push, open a scientific PR, or modify repository data from the output. `.github/workflows/intake.yml` is limited to Gate-A registration/acknowledgement and must not gain content-write permissions, attachment processing, model invocation, or publishing steps without explicit owner approval.

## Generated files and validation

Never hand-edit generated HTML or generated analysis files. When an exact Gate-B integration is eventually authorized, edit only the approved source rows, run the repository validators/build, inspect the complete diff and rendered output, and stop before deployment unless deployment was separately approved.

Only the owner may waive or change these rules, and only explicitly for a named scope.
