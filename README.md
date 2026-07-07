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

## Publish to a private GitHub Pages site (one-time)

Private-repo Pages requires a **GitHub Pro/Team/Enterprise** plan.

```bash
# from the repo root, after unpacking:
git init -b main
git add .
git commit -m "Seizure Semiology Atlas: initial version-controlled release"
gh repo create seizure-semiology-atlas --private --source=. --push
# (or create the repo in the GitHub UI and: git remote add origin … ; git push -u origin main)
```

Then in the repo on GitHub:
1. **Settings → Pages → Build and deployment → Source: “GitHub Actions.”**
2. Edit `.github/CODEOWNERS` and the `LICENSE` files: replace `@OWNER` / `<YOUR
   NAME>` with your handle/name.
3. Push to `main` → the **Build & Deploy** workflow builds and publishes the
   page; the private Pages URL appears in the workflow's `deploy` step and under
   Settings → Pages.
4. (Recommended) **Settings → Branches → protect `main`**: require the
   **Validate PR** check and a review, so corrections land through PRs.

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

**Alim-Marvasti 2022 ("Probabilistic landscape") was deliberately removed and
should not be re-added as an evidence source.** Its literature-mined taxonomy
produces semiotically incoherent categories (e.g. "whole-body / other
automatisms" bundling blinking, cough, gelastic, dacrystic, nose-wiping) paired
with sparse localization cells, yielding large but artifactual odds ratios (the
~OR 14 to hypothalamus is a few gelastic/hamartoma cases). Big *N* does not fix
bad labels, and leading a teaching resource with that plot mis-educates. A future
quantitative layer, if wanted, should come from SEEG-anchored primary series with
disciplined sign definitions and explicit ground truth.

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
