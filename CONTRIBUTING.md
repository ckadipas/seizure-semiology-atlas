# Contributing

This is a **living, source-grounded** reference. The governing principle: the
**data is the source of truth; the HTML is a build artifact.** Never hand-edit
the generated HTML — it is produced by CI and overwritten on every build.

## The mental model

```
data/semiology_data.json ─┐
                          ├─► generator/gen_study.py ─► docs/…​.html ─► GitHub Pages
enrichment/enrichment.json┘        (build artifact — do not edit)
        ▲
        └── enrichment/build_enrichment.py   (authors evidence, new signs, papers, chart data)
```

## How changes reach production (the trust model)

Nothing is published except through a pull request the **owner merges**. That
merge is the single manual gate; everything after it is automatic.

```
propose ──► PR ──► CI validates ──► OWNER approves & merges ──► auto-deploy ──► live
(anyone,   (open)  (schema +        (only a maintainer can      (build → Pages
 via fork)          enrichment       merge to protected `main`)   → smoke-check)
                    sync gate)
```

- **`main` is a protected branch.** No one can push content straight to it; all
  changes arrive as PRs, and only a maintainer can merge. Outside contributors
  fork and open a PR — they cannot publish on their own.
- **CI gates every PR.** `validate.yml` runs the schema/integrity check and
  verifies `enrichment.json` is in sync with its generator. A PR cannot go green
  (and therefore cannot be merged) until both pass.
- **The owner's merge is the approval.** An automated assistant may *prepare* a
  change and open the PR, but it does not merge — no submission auto-integrates
  or auto-publishes. A human with merge rights always decides.
- **After merge, it is hands-off.** A push to `main` triggers
  `build-deploy.yml`: rebuild the HTML, deploy to Pages, then a post-deploy
  smoke check that fails loudly if the live site is not serving. No local build,
  no manual step.

This is deliberate: it means the approval button is the throttle. Spam,
low-quality submissions, or a well-meaning-but-wrong edit all stop at the same
place — the merge — and never reach readers without a maintainer's sign-off.

## Prerequisites
Python 3 (standard library only for the build). `poppler-utils` is optional and
only used by the paper-intake tool. No `pip install` is needed to build.

## Common tasks

**Correct a sign.** Edit its record in `data/semiology_data.json`. Keep enum
fields valid (see `schema/sign.schema.json`). Then:
```bash
make validate && make build
```

**Add a sign.** Append a record with a unique `id` and valid
`region`/`sub`/`latcode`/`phase`/`evid`. To fold into an existing subregion
block, match the `sub` string **exactly**.

**Add or fix evidence / a citation.** Edit `enrichment/build_enrichment.py`
(an `add("<sign-stem>", "<Paper YEAR>", "<finding>")` line), then `make build`
and commit the regenerated `enrichment/enrichment.json`.

**Integrate a new paper.** Follow `intake/INTAKE.md`.

## Before you open a PR
- `make validate` passes (CI runs the same check and will block otherwise).
- `make build` succeeds and you committed the updated `enrichment/enrichment.json`
  (CI verifies it is in sync with `build_enrichment.py`).
- Every changed figure cites a source.
- You updated `CHANGELOG.md` under **[Unreleased]**.
- You committed **no** copyrighted PDFs or full article text — only short,
  attributed extractions. (`corpus/pdfs/` and `corpus/txt/` are git-ignored.)

## Scientific standard
Favor disciplined primary series and SEEG-anchored studies with explicit ground
truth. Treat literature-mined meta-analyses skeptically (see README §Design
decisions). When sources disagree, represent the disagreement rather than
flattening it.

## Not for clinical use
See `DISCLAIMER.md`. This resource is for education and training only.
