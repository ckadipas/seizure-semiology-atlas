# Cloudflare Pages Hosting Design

## Status

Cloudflare Pages is the production delivery layer for `www.semiologyatlas.org`. GitHub remains the version-controlled public source and automatically triggers each Cloudflare deployment.

## Authority and data boundaries

- The private evidence repository and master ledger remain the scientific source of truth and are not modified by this hosting change.
- The public `ckadipas/seizure-semiology-atlas` repository remains the generated, redacted deployment source.
- The Cloudflare GitHub App is restricted to that public repository; it has no access to the private evidence repository or unrelated repositories.
- Cloudflare builds and serves only the generated `docs/` static site.

## Deployment architecture

The Cloudflare Pages project `semiology-atlas` is connected directly to `ckadipas/seizure-semiology-atlas` with these production settings:

- Production branch: `main`
- Automatic deployments: enabled
- Framework preset: None
- Build command: `python3 generator/gen_study.py`
- Build output directory: `docs`
- Root directory: repository root

No Cloudflare API token or account-wide deployment secret is stored in GitHub. Cloudflare receives repository access through its GitHub App, limited to the single public repository.

GitHub Pages may remain available at its `github.io` address as a fallback, but it no longer owns the atlas custom domain. The public workflow therefore retains its existing GitHub Pages deployment while Cloudflare independently deploys every push to `main`.

## Production domain

Squarespace remains the registrar and DNS provider. The production record is:

- Type: `CNAME`
- Host: `www`
- Target: `semiology-atlas.pages.dev`

The canonical production URL is `https://www.semiologyatlas.org/`. Cloudflare provisions and renews HTTPS for that hostname. Apex-domain behavior for `https://semiologyatlas.org/` is a separate DNS or redirect configuration and is not required for the verified `www` deployment.

## Verification record

The initial Cloudflare deployment built public commit `0b163700178664cdbf80f25bc70279d8e55833cc`. Both the Cloudflare project URL and `https://www.semiologyatlas.org/` loaded the complete atlas over HTTPS with the title `Seizure Semiology — Interactive Study Reference`.

No additional test suite was introduced for this migration.

## Rollback

Cloudflare deployment settings can be disconnected without changing repository history. GitHub Pages remains available as a fallback at its repository URL, and DNS can be repointed if Cloudflare delivery must be rolled back.
