# Seizure Semiology Atlas

A source-grounded educational reference for localizing and lateralizing seizure semiology. See [DISCLAIMER.md](DISCLAIMER.md).

## Website

Search once, then browse **Signs**, **Weighted evidence**, or **Sources**. Signs can be organized by brain region or classification. Weighted evidence uses the same organization, with separate localization and lateralization views. Sources collect each paper's results beneath its title, authors, and DOI.

The Brodmann map shows numbered areas. Brain-region filters and classifications remain separate from Brodmann areas.

The page footer links to the simplified paper submission form, full disclaimer,
content license, and code license. The educational-use notice and license names
remain visible. Public synchronization and deployment validation require these
footer resources; verify their visibility and destinations on the deployed site.

## Data and release files

This repository receives generated data from the private SQLite evidence ledger. Scientific relationships are reviewed there and exported together; the public website is not an evidence source.

| Path | Purpose |
|---|---|
| `docs/index.html`, `docs/atlas_projection.mjs`, `docs/atlas-projection.json.gz` | Current standalone website and its generated data. |
| `data/atlas_bundle.normalized.json.gz` | Compressed normalized relationship graph for the current release. |
| `review/normalized-relationship-manifest.json` | Public release identity linking the generated artifacts. |
| `release.json`, `CHANGELOG.md` | Version, date, and release notes. |
| `tools/validate_normalized_atlas_release.py` | Checks that the current website and normalized graph belong to the same release. |

The older `data/atlas_bundle.json`, `data/brodmann_map.json`, and legacy generator remain compatibility fixtures. They do not replace the current website. Source PDFs and private scientific review records are not distributed here.

## Local use

```bash
make build
make serve
```

The build runs compatibility checks, restores the committed current website, and validates its release identity. To change scientific data or the website, update the maintained private ledger or renderer and export a new release. Do not edit generated files independently.

Cloudflare Pages uses `python3 generator/gen_study.py` with `docs` as its output directory. When a normalized release is present, this command validates the committed website without regenerating it. `make check-deployment` checks the same command and confirms it leaves the website unchanged.

## Scientific updates

GitHub intake registers a submission for private source review. It cannot change scientific data or publish results. The owner approves source review and the exact proposed integration before a deterministic update; explicit approval for direct repository work applies to its stated scope. Deployment follows the authorized release scope.

Source terms, citations, populations, and individual measurements remain traceable. Localization, lateralization, phase, and classification are separate relationships. An unspecified value on one axis does not erase an explicit value on another.

Weighted evidence retains the approved scoring method. A new study does not receive an evidence class or contribute to a score merely because it has been added to the database.

## Licensing

Code: **MIT** ([LICENSE](LICENSE)). Dataset and documentation: **CC BY-NC-SA 4.0** ([LICENSE-CONTENT](LICENSE-CONTENT)). Source articles are not redistributed.
