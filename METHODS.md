# Methods and source review

The atlas is an educational reference. Its evidence summaries are not validated for individual patient decisions. See [DISCLAIMER.md](DISCLAIMER.md).

## Scientific source of truth

The private SQLite evidence ledger holds the reviewed scientific records. The public atlas receives a deterministic export of that ledger. Source publications, private review records, and the website have distinct roles: the publications supply evidence, the private review establishes the approved records, and the website presents their generated projection.

Each source finding and reported statistic retains its citation, source locator, population, unit, and available numerator and denominator. Localization, lateralization, phase, and classification remain separate relationships. Missing information on one axis does not erase an explicit relationship on another.

## Reported results and evidence scores

Source-reported measurements retain their study context. A frequency, predictive value, or other statistic is not interchangeable with the atlas's evidence score.

The current website's **About the scores** explanation defines the displayed score:

- Each study contributes once for a sign and for localization or lateralization.
- Its weight combines the recorded evidence class, study method, and sample size. The score adds the contributing study weights.
- Dots indicate the number of papers: one, two, or three or more. They do not indicate certainty.
- Scores are not probabilities or pooled study results.
- When a filter selects only part of a study's results, that study's score is withheld. Reviews and cited reports remain available without counting the same study again.

The approved scoring method is maintained with the private ledger. Adding a paper does not automatically assign an evidence class or make it eligible to contribute to a score. Changes to weights or scientific interpretation require owner approval.

## Current public artifacts

The current website uses `docs/index.html`, `docs/atlas_projection.mjs`, and `docs/atlas-projection.json.gz`. The normalized relationship graph is distributed as `data/atlas_bundle.normalized.json.gz`; `review/normalized-relationship-manifest.json` binds the release artifacts.

Legacy data and generator files remain for compatibility. Their historical pooling calculations and curator estimates do not describe the current normalized website and must not be edited as a route to updating its evidence.

## Review, integration, and publication

A [paper submission](intake/INTAKE.md) registers a nomination for private review. The owner approves the exact source and review scope, then the proposed records and integration diff. Approved scientific changes are integrated in the private ledger before the public artifacts are regenerated together.

Release validation checks that the exported website and normalized data belong to the same release. A successful build establishes technical consistency; it does not independently establish scientific correctness or verify what is serving on the live site.

See [CONTRIBUTING.md](CONTRIBUTING.md) for contributions and [README.md](README.md) for the current release and deployment workflow.
