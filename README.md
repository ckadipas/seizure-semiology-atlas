# Seizure Semiology Atlas

A **living, version-controlled, source-grounded** educational reference of
localizing & lateralizing seizure semiology for epilepsy trainees. The dataset is
the source of truth; a build step renders a single self-contained interactive
HTML page that is published to GitHub Pages.

> ⚠️ **Educational & training reference only — not a tool for clinical
> decision-making.** See [`DISCLAIMER.md`](DISCLAIMER.md).

---

## What's here

| Path | Role |
|---|---|
| `data/semiology_data.json` | **Source of truth** — the curated signs (human-edited). |
| `enrichment/build_enrichment.py` | Authors the corpus layer → `enrichment/enrichment.json`. |
| `enrichment/enrichment.json` | Evidence, new signs, paper library, chart data (committed; CI checks it's in sync). |
| `generator/gen_study.py` | Renders the self-contained HTML into `docs/`. |
| `tools/validate_data.py` | Schema + integrity gate (runs in CI). |
| `tools/intake_paper.py` | Screens, de-dups, extracts & queues a new paper. |
| `schema/sign.schema.json` | JSON Schema for a sign record. |
| `corpus/manifest.csv` | Bibliographic metadata for the source library. |
| `corpus/corpus_extract_summary.md` | Human-readable ledger of source-grounded figures. |
| `intake/INTAKE.md` | The paper-intake standard operating procedure. |
| `CITATION.cff` | Citation metadata (for a citable public release / Zenodo DOI). |
| `docs/…​.html` | **Build artifact** — produced by CI, deployed to Pages. Do not edit. |

Not committed (git-ignored, kept local): the working corpus of PDFs
(`corpus/pdfs/`) and their extracted text (`corpus/txt/`). This repo publishes
only *derived* content — the dataset and short, attributed factual extractions —
so it never redistributes copyrighted journal articles.

---

## Quickstart

```bash
make validate     # schema + integrity checks
make build        # rebuild enrichment.json + render docs/…​.html
make serve        # build, then serve at http://localhost:8000
```
No `pip install` required — the build uses the Python standard library only.

Add a new paper:
```bash
make intake PDF=intake/inbox/your_paper.pdf
```

---

## Publish to GitHub Pages (one-time)

This repo is designed to be **public-safe**: it commits only the dataset and
short, attributed extractions — never the source PDFs or full article text (those
are git-ignored). A public repo gets **GitHub Pages for free** (no paid plan
needed). The bundle already contains an initial commit, so you don't need to
`git init`.

```bash
tar -xzf seizure-semiology-atlas.tar.gz && cd seizure-semiology-atlas

# create the public repo and push (GitHub CLI):
gh repo create seizure-semiology-atlas --public --source=. --push
# — or, via the GitHub UI, create an empty repo then:
#     git remote add origin git@github.com:<you>/seizure-semiology-atlas.git
#     git push -u origin main
```

Then in the repo on GitHub:
1. **Settings → Pages → Build and deployment → Source: “GitHub Actions.”**
2. Replace placeholders: `@OWNER` in `.github/CODEOWNERS` and
   `.github/ISSUE_TEMPLATE/config.yml`; `<YOUR NAME>` in `LICENSE`; and the author
   fields in `CITATION.cff`.
3. Push to `main` → the **Build & Deploy** workflow renders the page and
   publishes it; the public Pages URL appears in the workflow's `deploy` step and
   under Settings → Pages (typically `https://<you>.github.io/seizure-semiology-atlas/`).
4. **Recommended — Settings → Branches → protect `main`:** require the
   **Validate PR** check and one review, so corrections always land through a
   gated PR rather than a direct push.

**Optional — mint a citable DOI.** Link the repo to
[Zenodo](https://zenodo.org) (Zenodo → GitHub → toggle the repo on), then publish
a GitHub *Release*. Zenodo archives that release and issues a DOI you can cite;
update `CITATION.cff` with it.

**Prefer private instead?** Everything works identically in a private repo; only
private-repo *Pages* requires a GitHub Pro/Team/Enterprise plan. Use
`gh repo create … --private` if so.

Share access via **Settings → Collaborators** (or a Team). Collaborators can
propose corrections with the issue forms or PRs; CI validates every change.

---

## How updating works (the loop you asked for)

- **You** edit `data/semiology_data.json` (or `build_enrichment.py`), run
  `make build`, commit, push → the site redeploys.
- **A collaborator** who spots an error opens a *🩺 Report a correction* issue,
  or a PR editing the source. CI gates it; you review; merge redeploys.
- **A new paper** is nominated via a *📄 Submit a paper for intake* issue or
  `make intake`, screened per [`intake/INTAKE.md`](intake/INTAKE.md), and its
  short attributed findings are wired into the dataset.

Because the HTML is regenerated from validated source on every merge, the
resource stays internally consistent and every figure remains traceable.

---

## Design decisions

**The visualization is a lateralizing-reliability chart from Loddenkemper &
Kotagal 2005 (Table 1)** — how often each classic sign points to the correct
*side*. It answers *which hemisphere, and how reliably*, a claim the primary
literature supports.

**Literature-mined meta-analyses are not used as an evidence source.** A large
sample size does not fix bad labels: when phenomenologically unrelated signs are
bundled into one category and paired with sparse localization cells, the
resulting odds ratios can be large but artifactual. Quantitative figures here
come from primary series with disciplined sign definitions and an explicit ground
truth (SEEG, postoperative seizure-freedom, or imaging/neurophysiology
concordance).

**Preserved teaching threads:** the French anatomo-electro-clinical / network
framework (semiology as a dynamic network trajectory; the *order* of signs often
localizes better than any one sign), and the Marashly 2015 corollary (two
independent reliable signs, same side → lateralization ≈ 100%).

---

## Current state
101 signs · 31-paper source library · 32 signs source-grounded (42 findings) ·
one lateralizing-reliability chart.

## Licensing
Code: **MIT** ([`LICENSE`](LICENSE)). Dataset & documentation:
**CC BY-NC-SA 4.0** ([`LICENSE-CONTENT`](LICENSE-CONTENT)). The repo does not
redistribute source articles; only short attributed extractions are included.

## A note on validation
Builds are validated structurally (schema, integrity, geometry, successful
render). Pixel-level rendering should be confirmed in a modern browser — open the
Pages URL (or `make serve`) in Chrome/Safari/Firefox.
