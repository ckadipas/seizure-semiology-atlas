# Contributing

The atlas is an educational reference built from an owner-reviewed private evidence ledger. The public repository receives generated scientific data and website files.

## Submit a paper or report a correction

Use the [paper submission form](https://github.com/ckadipas/seizure-semiology-atlas/issues/new?template=new-paper.yml) with a DOI or stable publisher or repository link. A short note is optional; contributors do not need to extract findings or classify a study.

For a correction, identify the displayed sign or result, describe the problem, and provide the supporting citation and page, table, or section when available. See [paper intake](intake/INTAKE.md) for the review process.

Public issues and pull requests are public records. Keep source PDFs, page photographs, full article text, private review materials, personal identifiers, and private correspondence or working notes out of them. Source files belong in the private evidence archive.

## Scientific and website changes

Scientific relationships are corrected in the private ledger under owner approval. The maintained private renderer supplies website changes. Approved records and their consumers are then exported together into this repository.

Do not edit generated HTML, compressed projections, or normalized data independently. Legacy files such as `data/semiology_data.json` and `enrichment/build_enrichment.py` are not the authoring path for the current normalized atlas. See [METHODS.md](METHODS.md).

Documentation and repository tooling changes can be proposed directly through a pull request. Keep the change focused and describe the resulting behavior or corrected guidance.

## Review and validation

Public changes enter protected `main` through a pull request. Before merging:

- Inspect the exact diff and release-facing metadata for unintended content.
- Keep citations and source locators with any approved scientific changes.
- Use the narrow checks relevant to the change. Documentation edits need content and link review; a scientific release needs its approved export and release-identity validation.
- Keep source originals and private review artifacts in their private archive.

Do not run a full scientific rebuild merely to validate an editorial change.

## Production deployment

Automatic Git deployments are disabled. A merge alone does not publish a production update. Production uploads require a merged pull request, successful validation of its exact commit, and the authorized deployment scope. Verify the resulting live site separately.

See [README.md](README.md) for current artifact paths and [DISCLAIMER.md](DISCLAIMER.md) for the educational-use boundary.
