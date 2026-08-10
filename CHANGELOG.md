# Changelog

All notable changes to the dataset and resource are recorded here.
Format loosely follows Keep a Changelog; dates are ISO-8601.

## [Unreleased]
### Fixed
- **The page printed two citations that were simply wrong.** Loddenkemper's postictal-dysphasia
  90% was marked as restating Gabr 1989; its own note says *"80–100% across series (midpoint
  90)"* — a synthesis of several series, not a restatement of one. Loddenkemper's dystonia 100%
  was marked as restating Roh 1996 on nothing but `100 == 100`, while its note names Yen. Both
  now carry `review_synthesis`, which excludes them from the average without inventing a target.
- **A number nobody measured was being averaged.** Blair's postictal-aphasia *85* is the midpoint
  of a quoted "~80–90%". It was raising that sign to `k = 4` and generating a weighted SD of 2.1
  — a dispersion statistic over a value the curator had interpolated. Marked
  `interpolated_midpoint` with its `value_range`; the sign is now `k = 3` on three genuine series
  (Gabr 92, Maillard 92, Serafetinides 94), pooled 92.8%, and the manufactured SD is gone.
- **A predictive value was sitting in a lateralization pool.** Kinney's hemifield 100% is recorded
  in the source ledger as `ppv` — P(onset side | sign), not the share of cases falling one way.
  A new `metric_mismatch` check records it, and blocks the build if such a figure ever reaches an
  average (it is currently excluded as a restatement, so no number moves today).
- **The review tool's findings reached nobody.** `flag_by_sign` was built by the generator on
  every run and never read; `METHODS.md`, the `build_meta` docstring and `review_flags.json`
  all described a "conflicting-evidence panel" that did not exist. Two high-severity conflicts
  (38 and 30 points) were flagged on every build and shown to no reader. Flags now render on
  the sign they were raised against.
- **The checker was reading rows the engine had discarded.** `pooled_rows` filtered on `restates`
  alone, so the two new exclusion kinds — which have no `restates` target — read as pooled and
  produced three false `unmarked_restatement` flags at high severity. It now asks the same
  question the engine asks.
- **`CONTESTED_POINTS = 25  # the one place this threshold is defined`** was not the one place;
  `CONFLICT_TOL = 25` sat in the other file. The review tool imports it now.
- **The ledger claimed every numeric value traces to `corpus_findings.json`.** Seven of forty do
  not — some are curator arithmetic over a quoted fraction (Serafetinides 16/17 → 94), one comes
  from a paper absent from that file entirely (Wyllie 1986). The note now says so, and a new
  `untraceable_value` check publishes the count on every run instead of leaving it to a sentence.
- **`README.md` claimed all quantitative figures come from primary series with an explicit ground
  truth.** False for the six `review only` signs. It now says which, and points at the label.
- **Residual "meta-analysis" wording** in `Makefile`, `validate.yml`, the ledger `_doc` and a CSS
  comment that ships in the built page.
### Fixed
- **Six pooled figures had no study behind them at all.** Excluding a review that
  restates another source still leaves a review standing in for a series, and after the
  last fix six signs were in exactly that position: every percentage behind them is
  Loddenkemper 2005 or Blair 2012 quoting a cohort this library has never read. Three of
  them were the signs that fix had just relabelled **1 study with a percentage · single
  source** — which describes who repeated the number, not who measured it. There is now
  a **`review only`** tier, tested before every other, and those figures read *"1 review
  with a percentage · review only — no primary series here"* with a panel saying the
  figure is a pointer to the original paper rather than evidence this atlas has checked.
  Affected: *hemifield visual aura* 100%, *postictal (Todd's) palsy* 93%, *unilateral
  somatosensory aura* 89%, *ictal vomiting* 81%, *ictal spitting* 75%, and *lower facial
  weakness* 80.5%. No percentage changes; what changes is the claim about who measured it.
- **`lower facial weakness` was published as two agreeing studies.** It was **moderate ·
  k = 2** on Loddenkemper 86% and Blair 75% — both narrative reviews, and both notes name
  a 50-patient series. The near-identical-value check could never catch it: it needs
  agreement within 2 points, and these differ by 11 precisely because two reviews can
  disagree about what one cohort said. Two reviews on a sign with no primary series
  between them is now flagged on that shape alone, regardless of the values.
- **A review's figure was pooled as a second measurement whenever nobody had traced it.**
  Fourteen review percentages were being averaged as independent measurements; nine
  others, traced, had already dropped out. The seven that sit beside a primary series are
  now flagged (`untraced_review_figure`) with the study count they are inflating, so the
  backlog is visible on every run instead of resting on the absence of a note.
- **The weighting scheme decided three figures, silently.** On most signs the weighted
  and unweighted means agree within a point; on three they do not, because a light review
  and a heavy series disagree and the weights pick the winner — *automatisms with
  preserved responsiveness* 67.6% against a plain mean of 81%, *postictal nose-wiping*
  66.4% against 77%, *unilateral clonic activity* 96.6% against 91.5%. Each now prints
  the plain mean beside the weighted one, so the reader can see how much of the number is
  the scheme's doing rather than the data's.
- **A sensitivity figure could count one publication twice.** `k` was the number of
  tagged rows while the caption called it publications, and the mean was taken over rows
  — so a paper reporting the same sign-in-group frequency in two places would have got
  double the influence and an inflated `k`. Nothing in the corpus triggers it yet; the
  engine now collapses within a publication before averaging across publications, which
  is the rule restatements already get upstream.
- **Unweighted rows still drew a sliver of weight bar.** The previous change replaced the
  weight *number* with a dash on rows that were never averaged, but `.mc-bar` carries
  `min-width:3px`, so a zero-width bar still painted a 3px block beside the dash. The
  element is now omitted entirely on those rows.
- **"range 93–93%"** was printed wherever a figure rested on one value — the arithmetic
  of a single number dressed up as a spread. The range is shown only when there is one.
### Changed
- **`METHODS.md` says what `N` actually is.** It is the study's cohort size, not the
  number of patients the lateralization percentage was computed over — usually different,
  often by a lot (Wyllie 1986 is a 37-patient study whose version figure rests on 27).
  The per-sign denominator is not in the ledger; where a source states it, it appears in
  the observation's note and nowhere else. `size_factor` is therefore a proxy for how
  substantial a study is, not for how precisely it estimated that percentage, and ten of
  the sixteen studies report no N at all, where it is 1.0 and does nothing. Also recorded:
  sensitivity means are unweighted while lateralization means are weighted, so the two
  kinds of figure are not comparable.
### Fixed
- **The restatement check could not see the commonest restatement.** It compared each
  review against the *primary series* in the same pool, so two reviews citing one series
  neither of them ran never formed a pair — and that is exactly what was in the data.
  Loddenkemper & Kotagal 2005 and Kinney, Kovac & Diehl 2019 report the identical figure
  for three signs, and Kinney's own note names the series both are quoting: *hemifield
  visual aura* 100% (*Salanova series*), *postictal Todd's palsy* 93% (*Kellinghaus
  series*), *unilateral somatosensory aura* 89%. All three were published as **2 studies ·
  moderate** while the review printed zero flags. Each is one measurement: the three now
  read **1 study with a percentage · 1 restatement excluded · single source**. The
  percentages themselves do not move — 100, 93 and 89% — only the claim about how well
  attested they are. Any unmarked pair within 2 points with a review on either side is now
  flagged and blocks CI; two *primary* series agreeing is left alone, since separate
  cohorts landing on the same figure is replication, the one thing here that earns k = 2.
- **`restates` pointed wherever it was typed.** Nine hand-entered targets, rendered
  straight onto the card as *"restates X — not averaged"*, and nothing checked that X was
  a study in the file. A typo would have printed an attribution tracing to nothing. A
  target that names no study is now a blocking flag.
- **The ledger's tier rule contradicted its own next line.** `observations.json` said
  *moderate* covered "k >= 3 where the studies disagree by 25 points or more" directly
  above *contested* claiming the same signs at any k. The code has only ever returned one
  of them. The rule is now published in the order it is tested, and `METHODS.md` states it
  too — the third round of this same defect, which kept recurring because the tiers were
  documented in one file and implemented in another.
- **A restatement could be quoted as a study that disagrees.** The reviewer's notion of
  "the values behind this figure" still included rows the engine had excluded, so a
  conflict flag could have listed a restatement among the disagreeing percentages, and a
  single-source flag could have named it as the source. No sign currently has both, so
  nothing was visibly wrong — it was waiting on the next paper.
- **`duplicate_card` was raised to high severity and left out of the blocking list** — the
  same "check that only looks like one" the previous change fixed for
  `unmarked_restatement`, one flag over. Every high-severity kind blocks now.
- **The build required Python 3.12.** One gridline in the forest plot put a backslash
  inside an f-string expression, which is a syntax error before 3.12 — so `make build`
  died on Ubuntu 22.04 and Debian 12 while CI, pinned to 3.12, stayed green and
  `CONTRIBUTING.md` promised nothing but "Python 3, standard library only". Verified
  building on 3.10, 3.11, 3.12 and 3.13.
### Changed
- **`METHODS.md` documents the rules the code actually runs.** It claimed the review
  checks "are advisory" while CI has been failing builds on them, and never mentioned
  `unmarked_restatement` — the flag most likely to stop a change — at all; it now names
  what blocks and what is only surfaced. It promised a weighted SD on every pooled figure,
  which the engine has stopped emitting below four studies. And the restatement rule, the
  one thing a reader needs to reproduce an average that visibly skips some of the rows
  beneath it, was undocumented; it and the certainty tiers are now written down where the
  method is described.
### Fixed
- **The page showed a value it had just refused to average.** Marking a review as a
  restatement kept it out of the average but left it rendering as an ordinary row with a
  weight bar, so figure-of-4 read *"range 90–90%, 1 study with a percentage"* above a table
  listing Loddenkemper at 89%. That was worse than the double counting it replaced: the
  correction was invisible and the page looked broken. A restatement now says so where it
  is shown — *"89% — restates Kotagal 2000, not averaged"* — and draws no weight bar.
- **Restatements and dissenting sources were being counted as "direction-only sources".**
  Figure-of-4 advertised *3 direction-only sources* when one of them reported a percentage
  and another argues the sign is unreliable. The count now separates direction-only from
  restatements-excluded, and the card's library chip counts studies contributing a
  percentage rather than every contribution attached to the sign.
- **A second tier definition contradicted the code.** `observations.json` still published
  the old rule (*"well_supported: n_studies >= 3 OR total_weight >= 6.0"*) after the code
  stopped using weight — the same defect the previous change claimed to fix, inverted. The
  ledger now publishes the rule that is implemented.
- **The certainty cap was unreachable.** Capping a spread ≥ 25 sign at *moderate* could
  only demote k ≥ 3, and every disagreeing sign in this corpus is k = 2 — so it fired on
  none of 19. Disagreement is now its own tier, **contested**, which sits below moderate
  and applies at any k. Two signs earn it: *automatisms with preserved responsiveness*
  (62–100%) and *postictal nose-wiping* (62–92%). The legend no longer claims weight is
  involved.
- **A sign with no percentage at all could be tiered from its restatement count**; it is
  now always *single source*.
- **CI did not gate on the new flag.** `unmarked_restatement` was raised to severity high
  but was absent from the blocking list, and the workflow ran the reviewer advisory-only —
  so the claim that this could not return quietly was false. It now blocks the build.
  Genuine literature *conflicts* stay advisory: they are facts about the evidence, not
  defects a build can fix.
- **`METHODS.md` opened with "This is not a weighted average."** A global find-and-replace
  rewrote the subject of the disclaimer it was meant to add, so the document denied the
  method it documents, two lines above asserting it.
### Fixed
- **A review restating a primary series was being counted as a second study.** Six
  observations were Loddenkemper & Kotagal 2005 reporting a number that Wyllie, Roh,
  Kotagal or Gabr had already contributed to the same average — the atlas's own review tool
  had flagged all of them as probable double counts, at severity *low*, and pooled them
  anyway. Observations now carry **`provenance`**: one marked `secondary_citation` names the
  study it restates, stays visible as a corroborating citation, and is never averaged.
  Consequences are real and mostly downward: *figure-of-4* falls from 2 studies to 1
  (89.8% → 90.0%, now **single source**), *ictal dysphasia* and *preserved ictal speech*
  likewise; *unilateral dystonic posturing* drops to k=2 and *moderate*. The detector was
  retargeted from "we knowingly double count" to **unmarked restatement, severity high**,
  so the same fault cannot be re-introduced silently. Nine flags before, zero now.
### Fixed
- **The atlas was calling one study "three studies".** A pooled percentage was printed
  beside a count that added the direction-only sources — which corroborate a side but
  measure nothing. *Ictal spitting* read **75% · 3 studies** when one study carried the
  number; *ictal vomiting* **81% · 4 studies** on one; *unilateral ipsilateral automatisms*
  **88% · 4 studies** on one. **16 signs** were affected. The count now says *"N studies
  with a percentage"* and lists direction-only sources separately.
- **The certainty tier could rise as the evidence got worse.** `certainty()` returned
  *well supported* whenever the summed weight reached 6.0, **regardless of how many studies
  there were** — contradicting the tier definition published in `observations.json`. It is
  now a function of k, and is capped at *moderate* when the studies disagree by ≥25 points.
  *Automatisms with preserved responsiveness* (100% vs 62%) and *postictal nose-wiping*
  (62% vs 92%) were both labelled well supported; both now read moderate.
- **"Weighted SD 0" implied perfect replication of a single number.** Five signs showed it
  where the two "studies" were a primary series and a review restating it. The statistic is
  no longer computed below k=4, where it cannot carry information.
### Changed
- **It is no longer called a meta-analysis.** There is no protocol, no prespecified
  eligibility, no reproducible search, no risk-of-bias instrument, no inverse-variance
  weighting, no confidence intervals and no heterogeneity statistics — so the label claimed
  an evidential status the method does not have. The section is **"Weighted average of
  reported lateralization — not a meta-analysis"**, and says so again in its own
  description; `METHODS.md` opens with the same disclaimer. The sort control that read
  *reliability ↓* now reads *percentage ↓*, which is what it actually sorts by.
### Changed
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
