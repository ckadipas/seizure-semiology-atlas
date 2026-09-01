# Changelog

All notable changes to the dataset and resource are recorded here.
Format loosely follows Keep a Changelog; dates are ISO-8601.

## [Unreleased]
### Changed
- **Brodmann-map signs now honor active top-level filters and organization.** Search,
  phase, lateralization, evidence class, and every non-region organization mode constrain
  map lists, counts, density, and highlighted signs. Brain Region and within-region order
  do not affect the map. A small filter indicator names every active constraint and
  explicitly confirms that Brain Region is not applied. The Phase of Seizure control uses
  only controlled categories, including Stimulation induced; raw wording is not treated as
  a filter category. On mobile, the visible **Clear** control resets the
  search and map selection.
- **"Source figures" is now "Source statistics".** The word meant extracted numbers, not
  images, and read as neither. The section is headed *each extracted statistic per
  publication (487 from 33 papers)* and introduced as *every extracted statistic per
  publication (% Lateralization / % Localization / Observed Frequency / PPV / Specificity /
  Other Metrics), each displayed with its accompanying source text* — which also names the
  metric types up front instead of leaving them to be discovered in the filter row. The
  filter for `frequency_pct` reads **Observed frequency** to match. The sentence about the
  pooled plot is gone: it was trying to say that only the lateralization rows have a pooled
  counterpart above, and said it in a way that suggested duplication.
### Changed
- **The sensitivity section says what it actually does.** It was headed "sensitivity by
  localization (32 figures, 15 signs)" and explained itself as "population-specific, so
  reported per (sign, localization) rather than pooled across groups; mean shown when a
  group has >1 source, otherwise the single value with its k" — which named a count of
  "figures" that are not figures, and left "localization group" undefined. It now reads
  **sensitivity by seizure-onset group (15 signs)**, and says in plain words that each
  percentage is the frequency one publication reported for that sign among patients whose
  seizures started in one place, that the groups are the *source's* categories (mesial /
  mesiolateral / lateral TLE, FLE, OLE) and not this atlas's regions, and why they are
  never averaged together. The table's columns name the same thing. It also now states
  the honest current position: every percentage rests on a single publication, and they
  come from two sources.
### Changed
- **The summary panels start closed; the Brodmann map stays open.** The meta-analysis and
  the other reports opened by default, which read as the page's main structure and pushed
  the sign index — the thing the atlas is for — most of a phone screen down. Five of the
  six panels now start folded. The map is the exception: it is the front door to the atlas
  rather than a report about it. Collapse all still closes it along with everything else.
- **The page holds its text off the edge.** On a landscape tablet the region banners ran
  under the overlay scrollbar and the collapsed-toolbar puck. Side padding now honours the
  safe-area inset, and widens to clear the puck whenever the toolbar is folded.
### Fixed
- **The mobile header no longer sits beneath the iPhone camera and status bar.**
  The page header, sticky controls, and collapsed-toolbar control now honor the top
  safe-area inset while retaining the existing spacing on other displays.
- **"Collapse all" collapsed almost nothing.** It closed the cards and the sub-region
  banners but left the summary panels and all seven region banners open, so on a phone it
  barely shortened the page. Both buttons now reach every level that folds — panels,
  regions, sub-regions and cards. Measured on a tablet viewport: collapse all takes the
  page from 77,666px to 1,123px.
### Added
- **The atlas can be installed to the Home Screen**, where it runs with no address bar and
  no tab strip — a page cannot hide browser chrome any other way, and in landscape that
  chrome is most of what is left. A web manifest, the Apple standalone meta tags, a
  translucent status bar and an app icon are emitted by the build; the icon is the lateral
  plate's own silhouette, so it is drawn from the atlas rather than bolted on.
### Added
- **The search toolbar collapses.** On a phone held sideways the sticky header — region
  pills, search, filters, actions and count — took **40% of the screen** before a single
  sign was visible. A control at the end of the toolbar folds the whole thing away to a
  puck fixed at the top right, which stays put as the page scrolls and restores everything
  on a tap, focusing the search box as it does. A landscape phone (viewport under 520px
  tall) now starts collapsed; portrait and desktop are unchanged, and an explicit choice
  either way is remembered. The puck carries a dot whenever a search term or filter is
  active, so a folded toolbar can never quietly hide why the list looks short.
### Changed
- **The dorsal view drops BA 17, 18 and 19 and re-places the rest.** The occipital areas
  are not visible from above on this plate, so numbering them there pointed at cortex the
  reader cannot see; dorsal now carries 13 numerals instead of 16. All three remain on the
  lateral, medial and ventral views, so no area and no sign loses its place on the map.
  The other 13 dorsal numerals move to positions taken from the in-page editor.
### Fixed
- **The label editor showed white blobs instead of numbers.** The numeral carried a fat
  white stroke as its fingertip target, drawn behind the glyph by `paint-order`. When the
  disc became the numeral's background that paint-order went, so the stroke painted over
  the digits — a 34px-wide blob per number on a phone. The **disc** is the drag handle
  now (19px, 26px on a phone) and the numeral just rides it, so there is no halo to cover
  anything.
### Changed
- **Nothing on the page explains the build any more.** The map's panel quoted the rule that
  mapped a sign, named `data/brodmann_map.json` and said what would make the build fail;
  the figure footnote counted signs "not placed on the map". None of that is a reader's
  business. The panel keeps only the one line that changes how a sign is read — whether it
  is expected from the hemisphere on screen — and the footnote is gone.
- **Shade by density uses a blue→red ramp.** Six anchors interpolated continuously, with
  OKLCH lightness strictly decreasing 0.87 → 0.47 and chroma rising, routed blue → violet →
  red so it never passes through green: it reads as magnitude, not as two colours, and the
  worst adjacent pair clears CVD separation at ΔE 8.0 under deuteranopia. The numeral flips
  to white where the disc is dark enough to need it. Counts are skewed (median 4, max 30),
  so the scale is square-rooted, and the key's gradient stops are placed back through the
  square — the bar is a linear count axis, so the compression at the low end is visible
  rather than hidden. Areas with no signs keep a plain white disc, which is a different
  statement from "few".
### Changed
- **Nothing is drawn over the cortex any more.** The map shaded each area with an
  outline traced off the reference plate. Traced or not, an outline of an area whose
  boundary the plate does not draw is a guess, and 80 of them tiling the surface read
  as ill-fitting blocks that fought the numbers underneath. They are gone from the
  page: a view is now the plate and its numerals, and the numeral is the whole of the
  interface — it is what is drawn, what highlights, and what is clicked. The disc behind
  each numeral carries the state (plain, has-signs, hover, selected, traced, density),
  which is also how the published Brodmann plates label themselves. With nothing drawing
  them, the outlines are gone from the source too: `data/brodmann_map.json` drops from
  103 KB to 26 KB (no `points`, `outline`, `core`, `solid`, `margin` or `mid` — a view is
  a `viewBox`, a plate and a list of numerals), `generator/brain_atlas.py` loses the
  smoothing and polygon maths and is now a 67-line loader, and `tools/brodmann_plate.py`
  loses its `trace` and `regions` commands, keeping only the `clean` step that made the
  plate images. `tools/validate_data.py` asks an area for a numeral position, not an
  outline. The rendered page is byte-identical, which is the proof the outlines were
  already reaching no one.
### Fixed
- **The right hemisphere really flips now.** The plate was mirrored with a CSS transform
  on SVG content, which is not honoured consistently — on iOS the numerals moved and the
  brain stayed put, so every area sat on the wrong gyrus. The plate is now mirrored with
  a plain SVG `transform` attribute set from script, which every engine honours.
  Confirmed by measurement: BA 17 sits 0.94 of the way across the plate on the left and
  0.06 on the right, and returns exactly on switching back.
### Added
- **The last Brodmann areas the map lacked are available.** BA 48 (retrosubicular) on
  the medial view and BA 52 (parainsular) on the lateral, both parked at a placeholder
  position to be dragged into place in the label editor. With 12, 26, 27, 29, 30 and 33
  added earlier, all **49 human Brodmann areas** are now on the map; 49-51 were never
  assigned in the human brain.
### Fixed
- **Three pairs of Brodmann areas were named as if they were the same region.**
  BA 9 and BA 46 both read "dorsolateral prefrontal cortex"; BA 5 and BA 7 both read
  "superior parietal lobule"; BA 23 and BA 31 both read as posterior cingulate. Each
  pair is now named for what distinguishes it: **BA 9** is *dorsomedial & dorsolateral
  prefrontal cortex (superior frontal gyrus)* — it occupies the superior frontal gyrus
  and wraps over the convexity onto the medial surface, which is why the map draws it
  on the lateral, medial *and* dorsal views, so calling it dorsolateral alone was
  misleading — leaving **BA 46** (middle frontal gyrus) as the dorsolateral prefrontal
  cortex proper. **BA 5** is the anterior somatosensory association strip and **BA 7**
  the posterior lobule that becomes the precuneus medially; **BA 23** is the ventral
  posterior cingulate against **BA 31**'s dorsal. Separately, **BA 8** was named
  "frontal eye field" for the whole area when the field is only its posterior part.
- **The map's shading follows the anatomy, and the numerals are individually clickable.**
  Two faults, one cause: every area was a hand-drawn polygon, grown 7px along each
  vertex normal so neighbours would overlap and never show a gap. The result read as
  blocks laid over the plate rather than regions of it, and because those inflated
  polygons *were* the click targets, a large one covered its smaller neighbours —
  BA 9 could not be clicked at all, and the temporal areas took a huge swathe of the
  figure. Now **`tools/brodmann_plate.py regions`** derives each outline from the plate
  itself: it rebuilds the graticule and crosshairs out of the picture, separates the
  drawn boundary lines from the finer sulcal shading, and lets each numeral claim
  outward until it meets a drawn boundary or a change of tint. The plate does not draw
  one patch per Brodmann area — the frontal band alone carries 8, 10 and 11 — so where
  a patch holds several numerals it is subdivided between them, each keeping the drawn
  edge as its outer border; all 82 outlines across the four views come from this.
  Clicking is now a separate thing from shading: the shading takes no pointer events at
  all, and the target is a disc the size of the numeral, centred on it. Verified in a
  browser that every one of the 82 numerals selects its own area, that no two targets
  overlap, and that dragging a numeral in the label editor carries its target with it.
  `generator/brain_atlas.py` loses the polygon-inflation, band and margin maths this
  made redundant (130 → 98 lines).
- **The hemisphere switch flipped the outlines but not the plate underneath**, so the
  right-hemisphere lateral and medial views put every area on the wrong gyrus. The
  photograph now mirrors with them.
- **Lateral BA 17's numeral sat outside the brain**, drawn in the white margin.
- **The ventral view drew BA 36 and BA 37 twice each.** Each was listed as two adjacent
  bands making up one region — a way to describe a shape the old band geometry could not
  state in one go. Under plate-derived outlines a single numeral grows into the whole
  drawn region, so the second entries are gone; without that, each of those areas would
  have carried two outlines and two competing hit targets. `tools/validate_data.py` now
  fails the build if a view draws an area more than once, or draws one with no outline or
  no numeral position — unlike a name, this is exactly the kind of defect a mechanical
  check does catch.
### Added
- **The Brodmann map now reads both ways.** It answered "which signs localize here?"; it
  now also answers "where does *this* sign localize?" Every sign card carries a **Brodmann
  areas** row — the area chips plus **Show on map** — and pressing it lights up every area
  that sign localizes to, across whichever views draw them, landing on the view that shows
  most of the set and flagging the others with a dot. Non-traced numerals fade so the set
  reads at a glance; a single chip traces the set *and* opens that one area; each area in
  the panel drills through to its own sign list with a one-tap way back.
  The panel states **why** those areas: either the sign's own entry in
  `data/brodmann_map.json` (quoting the name it was recorded against) or the sub-region rule
  it inherits — the same provenance `tools/validate_data.py` gates, so the map explains its
  reasoning rather than asserting it. Card and figure read the one mapping through one
  accessor (`brain_atlas.mapping_for_sign`), so they cannot disagree: verified in-browser
  that all 111 cards' chips equal the figure's own index, 110 mapped and 1 declared
  unmapped. Areas with no surface (insula, cingulate, deep) trace as their chips; a sign not
  expected from the displayed hemisphere says so.
- **The Brodmann map follows the repo's own structure.** It was first written as a
  feature bolted onto the generator: 39 areas, 17 sub-region rules, 79 per-sign
  overrides, 80 label positions and 231 outline points all lived as Python literals
  inside `generator/brain_atlas.py`, with a second label-position system layered on
  top of the first, a separate one-off gate script, and two authoring scripts that
  duplicated the same segmentation code. That is not how this repo works. All of that
  curation now lives in **`data/brodmann_map.json`**, a hand-edited source of truth
  beside `data/semiology_data.json`, validated against **`schema/brodmann.schema.json`**
  by the existing **`tools/validate_data.py`** gate — one gate, one CI step, as before.
  `generator/brain_atlas.py` is now a 130-line renderer (was 518) holding geometry
  maths and no knowledge; the duplicate label system is gone (one position per area
  per view, in data); and the two plate scripts are one `tools/brodmann_plate.py`
  sharing their segmentation. The rendered page is byte-for-byte unchanged apart from
  two inconsistencies the refactor fixed (clip-path ids and `aria-label` casing).
- **New papers flow onto the Brodmann map.** A sign added by intake under an
  existing sub-region inherits that sub-region's cortical areas and appears on the
  map with no manual step — verified end to end. A sign that introduces a *new*
  sub-region needs one line of mapping, and the build now says so precisely rather
  than failing cryptically: the error names the sub-region, points at
  `mapping.by_sub` in `data/brodmann_map.json`, and lists the available area ids.
  The intake workflow prompt and `intake/INTAKE.md` both carry the requirement, and
  the intake's publishing step now commits `data/brodmann_map.json` alongside the
  findings, so a mapping added during extraction reaches the pull request.
- **The map is under the ledger's sync oversight.** Its curation is keyed by sign id
  and sub-region string, so it could drift silently: an intake that added a sign,
  renamed a sub-region or renumbered an id would have left signs off the map with
  every gate still passing. `tools/validate_data.py` now fails the build if a rendered
  sign maps to no area (unless declared unmapped with a reason), a per-sign entry no
  longer names the sign it was written for, a sub-region rule is orphaned, a dataset
  sub-region has no rule, a referenced area is undefined, or a defined area is drawn
  in no view without being marked buried. Per-sign entries record the **sign name**
  alongside the id, so drift is reviewable in the diff rather than merely detectable.
  Coverage is reported every run (110/111 signs, 39 areas, 4 views, 1 declared
  unmapped).
- **Interactive Brodmann map — "where each semiology localizes".** A new figure at the
  top of the page maps every sign in the dataset onto the Brodmann areas it localizes to,
  across three schematic surface views of one hemisphere: **lateral, dorsal and ventral**.
  Each numbered area is clickable (and keyboard-reachable); selecting one opens a panel
  listing the semiology localized there, ordered by evidence tier, with its phase,
  lateralizing value and evidence level — and clicking a row jumps to that sign's full
  card in the index below. A **hemisphere switch (left/right)** mirrors the view and
  re-reads each sign for that side: contralateral/ipsilateral signs are restated as the
  body side they appear on, and dominant-only signs are dimmed when the non-dominant
  hemisphere is shown. An optional *shade by density* toggle tints areas by how many
  signs they carry; the default presentation is deliberately plain. Areas with no
  surface representation — **insula (13–16)**, **cingulate (24/32)** and deep
  subcortical — are offered as separate chips rather than being silently dropped, and
  the one sign with no lobar localization is declared under the figure.
  The mapping is derived from the dataset's own `sub`/`loc` localization fields (which
  already name Brodmann areas), refined per sign where the record is more specific; the
  brain outlines are schematic drawings authored for this atlas, not traced artwork.
- **Integrated Abou-Khalil's seizure-semiology chapter** (in Misulis et al., *Atlas of
  EEG, Seizure Semiology, and Management*, 3rd ed., Oxford Univ. Press 2022, §3.4). This
  authoritative textbook is added to the source library and now **corroborates the
  lateralizing direction of 13 existing signs** — forced version, dystonic/tonic/clonic
  posturing, figure-of-4, somatosensory aura, ictal spitting, ictal vomiting,
  preserved-responsiveness automatisms, ipsilateral automatisms, unilateral eye-blinking,
  postictal nose-wiping and postictal aphasia — as a qualitative (directional) source in
  the meta-analysis ledger. Each carries a short attributed quote and page locator; being
  directional, they add a corroborating citation without altering any pooled percentage.
  This retires several signs that had rested on a single citation (e.g. ictal spitting and
  ictal vomiting now show three concordant sources).
- **Three new right-temporal lateralizing signs** the chapter describes and the atlas
  lacked: **ictal drinking automatism**, **postictal cough**, and **postictal urinary
  urgency** (all non-dominant/right temporal, evidence level III, cited to the chapter).
  Every added quote was mechanically checked against the source text; no full text or PDF
  is committed (short attributed extractions only).
### Changed
- **Single source of truth.** Each curated sign card is now linked (by explicit id,
  not fragile substring) to its meta-analysis ledger entry, and renders the SAME
  pooled lateralization figure and the SAME per-study source list as the top plot —
  so a sign shows identical stats and citations everywhere (previously the card and
  the plot were computed from two disconnected paths and could disagree, e.g. forced
  version showed 40–50%/75–80% on the card but 98.6% across 6 studies in the plot).
- **Single source of truth extended to predictive value.** Cards now surface the
  corpus PPV figures for their sign, drawn from the same `corpus_findings.json`
  ledger the source-figures explorer renders, linked by each finding's explicit
  `card_ids` (assigned by exact phenomenon match, never fuzzy). 28 PPV figures across
  10 signs (version, tonic/dystonic/clonic posturing, figure-of-4, preserved-
  responsiveness automatisms, nose-wiping, Todd's palsy, epigastric aura) now appear
  identically on the card and in the explorer, each with population context and its
  verbatim quote. Ambiguous or aggregate PPV figures (asymmetric clonic *ending*, the
  M2e naming collision, multi-sign combinations, hemianopia) are deliberately left
  explorer-only rather than force-attached.
- **Sensitivity is now computed from the master ledger.** Sensitivity of a sign for a
  localization = `P(sign | localization)` — its frequency within that group — so the raw
  data is the verified frequency-within-a-group findings. Each carries a `sens` list of
  `{card_id, group, value}` entries; the meta engine computes per-(sign, localization)
  descriptive statistics and the card (tagged **corpus**), a new **Descriptive
  statistics — sensitivity by localization** report section, and the explorer all render
  the same numbers. **32 figures across 15 signs**, including temporal SEEG-subtype
  sensitivities (mesial / mesiolateral / lateral, from Maillard 2004) whose `M/ML/L %`
  are parsed straight from the tabulated values — so e.g. epigastric aura reads
  mesial 46% ▸ mesiolateral 39% ▸ lateral 8%. Coverage is deliberately sparse (the
  corpus reports these inconsistently); each figure shows its source count `k`. Tag
  another finding and all three surfaces update on the next build.
- **Specificity stays a marked estimate, honestly.** It needs the sign's rate in the
  *other* localization groups, which the corpus reports for essentially no sign, so it is
  not computed — card specificity is tagged **est.** with a tooltip, never fabricated.
  Sensitivity on signs with no localization-conditioned frequency is likewise **est.**
### Verified
- **Adversarial re-verification of the corpus against source text.** Every recorded
  finding was re-read against its paper: 485/489 confirmed (99.2%), 4 corrected, 0
  fabricated. Corrections: Loddenkemper ictal-speech direction → dominant; a
  Serafetinides metrazol-vs-amygdala misattribution; a Bonini Group-4 v-test note. Two
  byte-identical duplicate papers were removed (33 papers / 487 findings).
### Fixed
- **Consolidated a duplicate sign.** "Late forced/tonic head version" (#12) and
  "Forced contralateral tonic head/eye version" (#60) were the same sign filed under
  two regions; merged into one card under the frontal FEF home.
- **Ictal spitting marked contested.** The card cited Kellinghaus 2003 (dominant)
  while the pooled corpus (Loddenkemper, Fakhoury) lateralizes non-dominant — now
  surfaced as a genuine conflict rather than a silent single-side claim.
- The adversarial review now flags **duplicate cards** and **card↔ledger direction
  mismatches** through the explicit link.
### Added
- **Ictal central apnea** and **postictal central apnea** added as new mesial-temporal
  signs (Lacuey 2024; Meletti 2025; Ochoa-Urrea 2025): objective breathing cessation
  that predicts mesial temporal onset (OR 3.8, spec 0.82) — distinct from the
  subjective dyspnea aura.
- **Intake can now propose new signs.** A submitted paper describing a well-evidenced
  sign not yet in the atlas is added under `new_signs` in `intake_findings.json`
  (merged into the atlas at build time) rather than declined — the maintainer approves
  by merging the pull request. `tools/check_provenance.py` validates each proposed
  new-sign record and lets findings attach to it.
- **Weighted meta-analysis** (top foldable plot): each semiology's lateralization
  percentage pooled across every source that reports it, weighted by evidence
  class and ground-truth directness (`tools/meta_analysis.py`, deterministic).
  Two nested views — region → gyrus/Brodmann → sign, and semiology A–Z → region —
  with the full per-study value + weight breakdown on expand. Structured source
  data lives in `enrichment/observations.json`; method documented in `METHODS.md`.
- **Source-figures table**: every extracted figure (lateralization, frequency,
  localization, PPV) rendered as a searchable, type-filterable table, each row
  checkable against its verbatim quote and source locator. Frequency/localization/
  PPV figures are population-specific and are listed here rather than pooled.
- **Full-corpus extraction**: every paper in the library extracted into
  `enrichment/corpus_findings.json` (short verbatim quote + locator per figure) —
  the record behind the analysis. This multi-sourced signs that previously rested
  on a single review: forced version pools 5 studies (~99%), postictal dysphasia 5
  (92%), and dystonic posturing, tonic, clonic, eye-blinking, somatosensory aura,
  Todd's palsy, nose-wiping and others each gained independent sources. Added a
  contralateral lower facial (mimetic) weakness sign.
- **Source-review checks** (`tools/adversarial_review.py`): flags studies that
  disagree on a sign, a pooled direction that contradicts the curated card,
  duplicated figures, orphaned figures, single-source figures, a PPV figure linked
  to a non-existent card, a PPV direction that contradicts the card it is shown on,
  a sensitivity-tagged finding pointing at a missing card / naming no group / sitting
  on a non-frequency figure, and records which signs have a computed sensitivity vs
  an estimate → `enrichment/review_flags.json`. CI regenerates and sync-checks the
  generated JSON; `make review` reruns the analysis + review.
### Fixed
- Corrected a propagated misreading: Roh 1996 forced version was recorded as "89%
  contralateral"; the source shows version contralateral in 14/14 (100%) — the
  "89" was "89 seizures" (34 dystonia + 17 tonic + 24 clonic + 14 version, all
  contralateral).
### Changed
- Front-page declutter: trimmed the intro, removed the header stat badges and
  decorative emoji, and collapsed the reliability chart and framework callout into
  closed-by-default disclosures so the sign index is visible on landing.
- Subregions are collapsible banners under each region, collapsed by default;
  search/filter auto-expands matches.

## [1.0.0]
### Added
- 100 curated localizing/lateralizing signs across 7 regions.
- Corpus enrichment: source-grounded findings; ictal dysprosody from Montavont
  2005; source library from the paper corpus.
- Lateralizing-reliability chart sourced from Loddenkemper & Kotagal 2005 (Table 1).
