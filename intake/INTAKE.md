# Paper intake — standard operating procedure

How a new paper becomes source-grounded content in the atlas. The goal is that
**every figure in the resource remains traceable to a disciplined source** — the
intake gate is where that discipline is enforced.

```
   nominate ──► screen ──► extract ──► integrate ──► build ──► review ──► merge
  (issue/PR)   (in scope?  (figures &  (edit source)  (make    (PR + CI)  (deploy)
                reliable?)   card)                     build)
```

## 0. Two ways to nominate
- **No-code:** open a *"📄 Submit a paper for intake"* issue (DOI + why relevant).
- **Hands-on:** drop the PDF in `intake/inbox/` and run:
  ```bash
  make intake PDF=intake/inbox/your_paper.pdf
  ```
  This hashes it, checks for duplicates, extracts text to `corpus/txt/` (local,
  git-ignored), and scaffolds an intake card in `intake/queue/`.

## 1. Screen (is it in scope, and is it trustworthy?)
Keep it only if it reports **localizing or lateralizing** semiology. Then judge
reliability. Prefer:
- disciplined, explicit sign **definitions**;
- an explicit **ground truth** (postoperative seizure-freedom, SEEG, or
  imaging/neurophysiology concordance);
- a stated **N**.

⚠️ **Be wary of literature-mined meta-analyses.** A large *N* does not fix bad
labels. If a paper lumps phenomenologically unrelated signs into one category and
pairs it with a sparse localization cell, its odds ratios can be artifacts. This
is exactly why **Alim-Marvasti 2022 was removed** (see README §Design decisions).
When in doubt, favor SEEG-anchored primary series (e.g. Maillard 2004 temporal
subtypes; Bonini 2014 / Khoo 2023 frontal).

## 2. Extract
Pull the specific figures — direction (contra/ipsi/dominant/non-dominant),
percentage or PPV, sample size — into the intake card's findings table. Keep
each finding **short and attributed** (a paraphrased factual statement + the
citation and N). Do **not** paste long passages; do **not** commit the PDF or
full text.

For scanned PDFs with no text layer, OCR locally:
```bash
pdftoppm -r 300 -png paper.pdf pg
for i in pg-*.png; do tesseract "$i" - >> corpus/txt/<slug>.txt; done
```

## 3. Integrate (edit the SOURCE, never the HTML)
1. Add the bibliographic row to `corpus/manifest.csv` (status `integrated`) and a
   4-tuple to `PAPERS` in `enrichment/build_enrichment.py`.
2. For each finding, add an evidence call in `build_enrichment.py`:
   ```python
   add("figure-of-4", "Kotagal 2000",
       "Extended elbow contralateral to onset in 94.4% of secondarily-generalized seizures.")
   ```
   The first argument is a **substring of the target sign's name** — that's how
   evidence attaches to signs at build time.
3. If the paper surfaces a genuinely new sign, append a full record to `NEW`
   (with an `_ev` list). It receives an auto-assigned id.

## 4. Build, review, merge
```bash
make build          # validates, rebuilds enrichment.json, renders the HTML
git diff            # read the diff — enrichment.json changes should be legible
```
Commit the source **and** the regenerated `enrichment/enrichment.json`, update
`CHANGELOG.md`, open a PR. CI re-validates and re-builds; on merge to `main` the
Pages site redeploys automatically. Move the finished intake card out of
`intake/queue/`.
