# AGENTS.md — Seizure Semiology Atlas public repository

Read this file before changing the public atlas.

## Authority and active data route

- The repository owner is the final clinical and scientific authority.
- The binding private review method is V30. Source PDFs, text, owner comments, review materials, dossiers, and audit artifacts remain only in `ckadipas/semiology_refs`.
- Private evidence work must also follow `skills/curating-semiology-evidence/SKILL.md` and `protocol/CLASSIFICATION_AND_ATOMIC_LEDGER_CONTRACT.md` in that repository.
- This public repository is a generated/redacted consumer. Its only active website data input is `data/atlas_bundle.json`, exported from the private canonical relational database after owner approval.
- Legacy `data/`, `enrichment/`, and `corpus/` artifacts do not drive the build and are not evidence sources.

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

The public intake workflow may only acknowledge or register a request for private Gate-A preparation. It may not download source files, perform source review, write scientific content, create a scientific pull request, or publish output.

## Build and validation

Run `make validate` and `make build`. The validator checks only the generated public bundle; the generator reads only that bundle. Do not revive the legacy enrichment/review pipeline, and never hand-edit generated HTML.
