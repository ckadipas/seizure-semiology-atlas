# AGENTS.md — Seizure Semiology Atlas public repository

Read this file before changing the public atlas.

## Operational command hygiene

- Use the repository Makefile and the owner workspace's maintained `turtle_time/semiology_console.tcsh` for repeated build, validation, release, deployment, and status operations.
- Do not add date-stamped, stage-stamped, task-specific, or otherwise uniquely named shell/Python wrapper scripts for ordinary operations.
- A true one-off diagnostic belongs only in `/private/tmp` and must be removed in the same task. If it may be reused, add a documented Makefile target or console action instead.

## Authority and active data route

- The repository owner is the final clinical and scientific authority.
- The binding private review method is V30. Source PDFs, text, owner comments, review materials, dossiers, and audit artifacts remain only in `ckadipas/semiology_refs`.
- Private evidence work must also follow `skills/curating-semiology-evidence/SKILL.md` and `protocol/CLASSIFICATION_AND_ATOMIC_LEDGER_CONTRACT.md` in that repository.
- This public repository is a generated/redacted consumer. Its only active website data input is `data/atlas_bundle.json`, exported from the private canonical relational database after owner approval.
- Legacy `data/`, `enrichment/`, and `corpus/` artifacts do not drive the build and are not evidence sources.

## One generated evidence graph

- `data/atlas_bundle.json` contains one generated evidence-context graph anchored by immutable `sign_id`, finding, and statistic identities. Every scientific view—region and classification browse, reviewed findings, study results, weighted evidence, Brodmann maps, Source Library, filters, and counts—must query that same graph.
- Source-native wording, phase, subtype, and provenance remain visible, but approved variants resolve through their canonical `sign_id`. The generator may not create identity, anatomy, classification, or evidence relationships from wording.
- Approved sign classification supplies stable public placement. Finding- and sequence-level classifications are additional context and may not move a canonical sign into `General`, `Other`, or `Unlocalized`.
- Each atomic statistic is rendered once and may appear under multiple valid facets only by reference. Panel-specific scientific stores, first-match selection, copied values, and fallback maps are forbidden.
- A positive localization or lateralization relationship must survive every applicable projection. Missing normalization remains an explicit linkage issue and must not be displayed as absence.
- Fix discrepancies in the private ledger or exporter, then regenerate. Never hand-edit `docs/` or patch one panel to hide a projection failure.

## Scientific red zone

Without an exact owner-approved Gate-B packet and diff, do not change:

- `data/atlas_bundle.json`
- `generator/gen_study.py`
- `generator/brain_atlas.py`
- generated `docs/` content
- validation or deployment workflows
- any scientific identity, mapping, statistic, weight, or presentation rule

Never mint, renumber, reuse, or change the meaning of a `sign_id`, source finding identity, statistic identity, region identity, or Brodmann identity. Never infer a synonym, anatomy link, evidence class, source type, sample size, statistic use, or conflict resolution. Unresolved questions stay unresolved until the owner decides them.

## Required gates

Every submission follows: owner Gate A → private V30 source review → owner adjudication packet → owner Gate B for the exact integration diff → deterministic integration → separately authorized deployment.

These intake gates do not block direct repository work that the owner explicitly instructs and approves in the active task. Record that exact scope once; do not request the same integration, correction, commit, push, merge, or deployment approval again.

The public intake workflow may only acknowledge or register a request for private Gate-A preparation. It may not download source files, perform source review, write scientific content, create a scientific pull request, or publish output.

## Build and validation

Run `make validate` and `make build`. The validator checks evidence-context integrity, cross-view relationship parity, atomic-statistic ownership, public-safe fields, and bundle integrity; the generator reads only that validated bundle. Do not revive the legacy enrichment/review pipeline, and never hand-edit generated HTML.

The generated display must use clinical hierarchy rather than the flat storage table: region → Aura/Seizure/Lateralizing signs/Diagnostic signs → selected ordering → primary feature → sign, or published classification order → category → alphabetical primary feature → sign. Summary and evidence history use the same provenance set. Public cards show the concrete direction/anatomy and basic counts instead of generic interpretation labels; evidence history is closed by default; technical identifiers remain in advanced provenance; nested banners remain inside their parents and readable; desktop uses available width and mobile stacks.

Deployment is not proved by a successful workflow, HTTP 200, or screenshot alone. Rebuild from the published commit and require the Cloudflare Pages origin `index.html` bytes to match the generated file exactly. The custom domain may differ only by Cloudflare's hidden `/cdn-cgi/content` anchor; remove that managed injection and require the remaining bytes to match. Any other difference is a failed deployment.
