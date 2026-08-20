# Seizure Semiology Atlas

A source-grounded educational reference for localizing and lateralizing seizure semiology. It is intended for teaching and self-study, not clinical decision-making. See [`DISCLAIMER.md`](DISCLAIMER.md).

## Source of truth

This public repository is a generated, redacted consumer of the private canonical Semiology Atlas database. Its only active website data input is [`data/atlas_bundle.json`](data/atlas_bundle.json), produced after private source review and owner approval. Do not hand-edit that bundle or treat website prose as source evidence.

Older files under `data/`, `enrichment/`, and `corpus/` are retained as historical artifacts. They do not drive the website build and are not independent scientific authorities.

| Path | Role |
|---|---|
| `data/atlas_bundle.json` | Generated public bundle: signs, reviewed findings, statistics, anatomy links, and weighted analyses. |
| `tools/validate_atlas_bundle.py` | Public-safe integrity and privacy check. |
| `generator/gen_study.py` | Renders the self-contained website into `docs/`. |
| `generator/brain_atlas.py` | Renders Brodmann anatomy from the same bundle. |
| `generator/assets/` | Reference brain plates. |
| `docs/` | Generated website output. Do not hand-edit. |

Source PDFs, extracted full text, owner comments, review packets, and audit artifacts remain only in the private `ckadipas/semiology_refs` repository.

## Build locally

```bash
make validate
make build
make serve
```

The build uses the Python standard library and does not regenerate or consult the legacy enrichment pipeline.

## Updating the atlas

Scientific updates follow one path:

1. A paper or correction is submitted and registered for owner Gate A.
2. Source review and all audit material remain private.
3. Unresolved sign identity, anatomy, evidence class, study type, sample size, and statistic-use questions are decided by the owner.
4. The owner approves an exact Gate-B integration packet and public diff.
5. The redacted bundle and generated website are updated deterministically.
6. Deployment requires separate owner authorization.

The public intake workflow only acknowledges or registers a request. It cannot download papers, invoke a model, edit scientific data, open a scientific pull request, or publish results.

## Weighted analyses

The website preserves the previously defined weighting method and explains it in ordinary language. Evidence class sets the starting score; the way seizure origin was confirmed (for example SEEG, postoperative outcome, video EEG, or review) adjusts it; and reported sample size adds a limited bonus. Every contributing study result and weight remains visible. No newly reviewed statistic enters a weighted analysis until the owner approves its source profile and its exact analytic use.

## Current generated release

- 57 reviewed source reports
- 1,710 public findings
- 1,216 source-reported statistics
- 99 established atlas signs
- 19 evidence-weighted lateralizing analyses from 69 historical contributions

## Licensing

Code: **MIT** ([`LICENSE`](LICENSE)). Dataset and documentation: **CC BY-NC-SA 4.0** ([`LICENSE-CONTENT`](LICENSE-CONTENT)). Source articles are not redistributed.
