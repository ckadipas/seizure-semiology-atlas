# Seizure Semiology Atlas

A source-grounded educational reference for localizing and lateralizing seizure semiology. It is intended for teaching and self-study, not clinical decision-making. See [`DISCLAIMER.md`](DISCLAIMER.md).

## Source of truth

This public repository is a generated, redacted consumer of the private canonical Semiology Atlas database. Its only scientific website data input is [`data/atlas_bundle.json`](data/atlas_bundle.json), produced after private source review and owner approval. The bundle contains one generated `evidence_context` relationship graph: every region, classification, reviewed finding, study result, weighted summary, Brodmann association, manuscript view, filter, and count resolves through that graph. [`data/brodmann_map.json`](data/brodmann_map.json) supplies presentation-only label coordinates. Do not hand-edit the generated bundle or treat website prose as source evidence.

Other older files under `data/`, `enrichment/`, and `corpus/` are retained as historical artifacts. They do not drive the website build and are not independent scientific authorities.

| Path | Role |
|---|---|
| `data/atlas_bundle.json` | Generated public bundle and shared evidence-context graph for every scientific view. |
| `data/brodmann_map.json` | Owner-edited presentation coordinates for Brodmann labels; no scientific mapping authority. |
| `tools/validate_atlas_bundle.py` | Public-safe integrity and privacy check. |
| `generator/gen_study.py` | Renders the self-contained website into `docs/`. |
| `generator/brain_atlas.py` | Renders Brodmann anatomy from the bundle with label positions from the presentation map. |
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

Source-native wording and phase remain visible, while approved variants resolve through the same immutable `sign_id`. Each atomic statistic is rendered once and referenced through every valid facet. A panel may not invent a fallback relationship, select one arbitrary family, or maintain a separate scientific mapping. If views disagree, repair the private relationship or exporter and regenerate the entire site.

The public intake workflow only acknowledges or registers a request. It cannot download papers, perform source review, edit scientific data, open a scientific pull request, or publish results.

## Weighted analyses

The website preserves the previously defined weighting method and explains it in ordinary language. Evidence class sets the starting score; the way seizure origin was confirmed (for example SEEG, postoperative outcome, video EEG, or review) adjusts it; and reported sample size adds a limited bonus. Every contributing study result and weight remains visible. No newly reviewed statistic enters a weighted analysis until the owner approves its source profile and its exact analytic use.

## Current generated release

- 77 reviewed source reports consolidated into 73 canonical manuscripts
- 4,120 public findings
- 4,518 source-reported atomic statistics
- 378 established atlas signs
- 756 sign-axis summaries: one localization and one lateralization row per sign
- 66 canonical manuscripts contribute weighted evidence; 1 remains linked with
  authority metadata pending and 6 are context/reference works without a linked
  sign-axis contribution

## Licensing

Code: **MIT** ([`LICENSE`](LICENSE)). Dataset and documentation: **CC BY-NC-SA 4.0** ([`LICENSE-CONTENT`](LICENSE-CONTENT)). Source articles are not redistributed.
