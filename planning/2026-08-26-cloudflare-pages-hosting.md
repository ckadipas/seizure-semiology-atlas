# Cloudflare Pages Hosting Implementation Record

## Completed configuration

- [x] Created the Cloudflare Pages project `semiology-atlas`.
- [x] Connected the public GitHub repository `ckadipas/seizure-semiology-atlas`.
- [x] Restricted the Cloudflare GitHub App installation to that repository only.
- [x] Configured `main` as the production branch.
- [x] Configured `python3 generator/gen_study.py` as the build command.
- [x] Configured `docs` as the build output directory.
- [x] Enabled automatic deployment after pushes to `main`.
- [x] Verified the generated atlas at `https://semiology-atlas.pages.dev/`.
- [x] Added `www.semiologyatlas.org` to the Cloudflare Pages project.
- [x] Set Squarespace DNS `www` to CNAME `semiology-atlas.pages.dev`.
- [x] Verified the full atlas at `https://www.semiologyatlas.org/` over HTTPS.

## Repository alignment

- Cloudflare uses its repository-restricted GitHub App; no Wrangler action, Cloudflare API token, or account-wide secret is required.
- The public GitHub workflow retains its existing generator and GitHub Pages fallback.
- `docs/CNAME` is removed because the custom hostname now belongs to Cloudflare rather than GitHub Pages.
- Future pushes to public `main` automatically trigger Cloudflare builds from the same generated public repository.

## Operational boundary

This hosting change does not alter the private evidence repository, master ledger, scientific synthesis, renderer behavior, or atlas data. It changes only how the already-generated public site is delivered.
