# Paper intake — how a paper becomes content

Every figure in the resource stays traceable to a disciplined source. Intake is
where that discipline is enforced.

```
 nominate ──► screen ──► extract ──► integrate ──► build ──► review ──► merge
```

## 1. Nominate
Open a *"Submit a paper"* issue (DOI + why it's relevant), or drop the PDF in
`intake/inbox/` and run `make intake PDF=intake/inbox/your_paper.pdf` to hash it,
check for duplicates, and extract text to `corpus/txt/` (local, git-ignored).

## 2. Screen
Keep it only if it reports **localizing or lateralizing** semiology. Prefer
explicit sign definitions, a stated ground truth (postoperative seizure-freedom,
SEEG, or imaging/neurophysiology concordance), and a stated N. Be wary of
literature-mined meta-analyses — a large N does not fix bad labels.

## 3. Extract
Pull the specific figures — direction, percentage or PPV, sample size — as short,
attributed statements, each with the source page. Do **not** paste long passages,
and do **not** commit the PDF or full text — only the short attributed figures.

## 4. Integrate (edit the source, never the HTML)
- Add the bibliographic row to `corpus/manifest.csv` and a 4-tuple to `PAPERS` in
  `enrichment/build_enrichment.py`.
- Add each figure as a structured record in `enrichment/observations.json` (with
  its page/locator), or an evidence call in `build_enrichment.py`.
- **Keep the Brodmann map in step.** Every sign has to reach the map. A new sign
  whose `sub` already exists inherits that sub-region's cortical areas
  automatically — nothing to do. If the sign introduces a **new** `sub`, add it to
  `mapping.by_sub` in `data/brodmann_map.json` with the area ids it localizes to
  (the ids are the keys of `areas` in that file, e.g. `"4"`, `"22"`, `"3-1-2"`,
  `"insula"`). If one sign localizes more precisely than its sub-region, give it a
  `mapping.by_sign` entry keyed by its id — `{"sign": "<exact name>", "areas": [...]}`,
  the name recorded so the mapping can be audited later. If a sign genuinely has no
  cortical-surface localization, list it under `mapping.unmapped` with a reason.
  `make validate` fails if a sign would fall off the map, so this is not optional.

## 5. Build, review, merge
```bash
make build      # validates, regenerates the analysis + review, renders the HTML
git diff        # the generated JSON changes should be legible
```
Commit the source and the regenerated JSON, update `CHANGELOG.md`, and open a
pull request. Every submission is reviewed before it is merged.
