# data — reproduction sample

The full study ran 37,927 agent journeys against 1,056 domains. This folder holds a
**stratified ~20% domain sample** of the same normalized data the study's published numbers
(see the paper reference in the [root README](../README.md)) were computed from: **206 domains,
7,412 journeys**, consolidated into 4 flat
CSVs. It is not a random 20% of rows; see [Sampling method](#sampling-method) for why, and
[Reconciliation](#reconciliation) for how closely the sample reproduces the published numbers.

The raw per-run traces (~3.25 GB, one JSON file per journey) are not published; everything below
is already the normalized, tabular layer derived from them.

`training-knowledge-probe/` is a separate experiment nested in this folder because it's still
data, not because it's sampled the same way — see its own [README](training-knowledge-probe/README.md).

## Files

Every column below survived a pass that asked, per column, whether it's read by
`build_aggregates.py`, and if not, whether it's still necessary to verify a specific documented
claim (sampling strata, fame/AEO matching, ground-truth coverage) or genuinely useful to a
reader (e.g. which underlying model an arm actually ran). Source columns that were 1:1-derivable
from a kept column, pipeline bookkeeping, or filenames pointing at unpublished raw traces were
not carried over.

- **`journeys.csv`** — one row per agent journey (7,412 rows, 49 columns): the core per-run
  facts (grounding, searches, cost, turns, duration, blocks, evidence shares, outcome), which
  underlying model the arm actually ran, plus, merged in on `run_id`, every other per-run signal
  the study collected:
  - `endorse_strength_{claude,gpt}` / `endorse_reason_{claude,gpt}` — 0-4 recommendation-strength
    grade from two independent judge models, and their stated reason.
  - `antirec_*` — hedge/red-flag judge: five boolean patterns (`access_disclaimer`,
    `outside_sourced`, `vague_noncommittal`, `punts_to_source`, `staleness_memory`) and the
    judge's free-text reason.
  - `attr_*` — answer-composition judge (first-party / external / search / memory-recall share
    of the final answer). The study ran this judge on a seeded, arm-and-group-balanced
    subsample (1,199 of its 37,927 journeys); populated here for the 249 of those rows that
    land on the sampled domains, blank elsewhere.
  - `acc_*` — accuracy-judge summary for runs that were fact-checked against ground truth
    (`n_facts`, `n_correct`, `n_partial`, `n_incorrect`, `n_not_addressed`, `no_answer`).
    Populated for 1,918 of 7,412 rows; blank elsewhere. The atomic, per-fact verdicts these
    summarize are in `accuracy_facts.csv`.

  `group` = ax-high/ax-low (median split on the accessibility score). `stratum` = which
  collection wave the run belongs to (`batch-00..03`). `repeat` is the run's index within its
  domain x arm x category cell; every cell holds 3 journeys except `sphere.com` on `eve`, whose
  three cells hold 5 between them (the full study has 31 such short cells out of 12,656), and a
  `repeat` above 3 marks a replacement run for an attempt that failed to complete. The judge free-text fields
  (`endorse_reason_*`, `antirec_reason`) are stored truncated to 80 characters. The two runs
  with `acc_no_answer` = 1 produced no answer text, so every fact is `n_not_addressed` and
  they have no rows in `accuracy_facts.csv`.

- **`accuracy_facts.csv`** (24,051 rows) — one row per judged atomic fact: `run_id, domain, arm,
  category, fact_index, fact_text, verdict, evidence`. Long format because a single run can be
  judged against many facts; the per-run roll-up (`n_correct` etc.) already lives on
  `journeys.csv`, so this file is reference detail (e.g. "which specific facts did AX-low miss"),
  not required to reproduce the aggregates.

- **`domains.csv`** (206 rows, 11 columns) — one row per sampled domain: `brand`, `group`,
  `industry` / `fine_vertical` (G2 taxonomy), `ax_ratio` (the accessibility score, the
  treatment), `discovery` (one of the two AEO proxies), `tranco_rank` / `training_presence`
  (the fame-matching variables), `citation_breadth` (the other AEO proxy), and a derived
  flag: `has_ground_truth` (a ground-truth capture exists for the domain; 92 domains — for
  two of them, `chime.com` and `nursa.com`, the capture yielded no extractable facts, so
  `ground_truth_facts.csv` covers the other 90, and the accuracy grading 89 of those).

- **`ground_truth_facts.csv`** (2,147 rows, 90 domains) — one row per captured ground-truth fact:
  `domain, block (pricing/features/setup), field, fact_text`. Captured from each business's own
  site; `accuracy_facts.csv` verdicts are graded against these. List-valued facts (a pricing
  plan, a feature, a setup step) are one row each; a few scalar facts (e.g. `auth_method`,
  `pricing_model_notes`) are one row with `field` naming what it is. Structured sub-fields of a
  pricing plan (price, currency, ...) are flattened into `fact_text` as `key=value` pairs rather
  than kept as separate numeric columns.

## aggregates.json — the derived view

`../scripts/build_aggregates.py` rolls `journeys.csv` + `domains.csv` into a single
**`aggregates.json`**: a flat `{token: value}` map of every scoreboard number (grounding
composition, cost/turns/searches by arm, endorsement and hedge breakdowns, accuracy by source
and by intent — both the simple pooled split and the study's published stratified *paired*
estimator, `acc_paired_*`), plus the by-industry, by-accessibility-bin, and by-source-x-arm
tables as named lists in the same file — one file, not a folder of per-concern CSVs. The
searches-by-accessibility table uses 4 coarse bins (the paper's figure uses 9 over 1,056
domains; on a 206-domain sample the narrow bins get thin and single search-heavy domains bend
the curve). This repo ships it
**already computed from the sample**; re-run the script (`--check`) to regenerate it and see the
reconciliation printout.

## Consolidation

Upstream, each measurement and judge pass produces its own file. For this public repo everything
is consolidated into the 4 files above: the judged signals (`endorse_*`, `antirec_*`, `attr_*`,
`acc_*`) merge onto `journeys.csv` because each is keyed 1:1 on `run_id` (verified no duplicate
keys before merging, so the merge cannot fan out rows); domain-level metadata merges into
`domains.csv`; and the per-run atomic facts and the per-domain ground truth stay as their own
long-format tables (`accuracy_facts.csv`, `ground_truth_facts.csv`) because each run or domain
maps to *many* fact rows.

## Sampling method

Every headline number in the study is "domain-collapsed": a metric is averaged within each
domain first, then those domain means are averaged within a group (ax-high / ax-low). That means
the right sampling unit is the **domain**, not the row.

The sample is a seeded, stratified draw of 206 of the study's 1,056 domains (101 ax-high,
105 ax-low): stratified by ax-group and collection wave (`stratum`), and weighted towards
domains with a ground-truth capture so the accuracy tables have enough fact-checked answers to
recompute.

Every other file is filtered to the same 206 domains: journeys by `domain`, the judged signals
merged onto them by `run_id` (joined back through the sampled journeys), and ground truth by
whichever of the 206 domains have a captured ground-truth record with extractable facts (90 of
the 92 captured; ground truth was only captured for a subset of the full study too).

## Reconciliation

Recomputing `data/aggregates.json` from this ~20% sample and comparing to the published, full-corpus
numbers:

| metric | full corpus (1,056 domains) | this sample (206 domains) |
|---|---|---|
| On-site answer share, AX-high / AX-low (judged subset) | 78% / 58% | 87% / 50% |
| First-party evidence share, hi / lo (all runs) | 0.776 / 0.549 | 0.787 / 0.522 |
| Grounded (first-party) answer rate, hi / lo | 78% / 56% | 78% / 51% |
| Web searches by accessibility (4 coarse bins) | 4.3 → 3.0 → 2.2 → 1.9 | 4.3 → 3.2 → 2.1 → 2.2 |
| Turns, hi / lo | 5.5 / 6.8 | 5.7 / 6.9 |
| Duration (s), hi / lo | 48 / 55 | 51 / 59 |
| Block ratio (lo / hi) | 2.1x | 2.4x |
| Cost premium (lo vs hi, mean over arms) | 64% | 73% |
| Web-search ratio, claude-agent arm | 2.4x | 2.5x |
| Web-search ratio, openclaw arm | 1.5x | 1.6x |
| Endorsement top-grade rate, hi / lo | 20% / 11% | 22% / 11% |
| Hedge: access-disclaimer, hi / lo (lift) | 4% / 16% (4.4x) | 4% / 17% (4.3x) |
| **Accuracy, paired (published): site vs web** | 48.3% / 34.3% (+14.0pp, +41%) | 47.7% / 35.1% (+12.7pp, +36%) |
| Accuracy, paired: empty-answer diff (site − web) | −18.3pp | −17.0pp |
| Accuracy, paired diff by intent (pricing / features / setup) | +23.5 / +6.8 / +0.4pp | +23.7 / +3.4 / +0.8pp |
| Accuracy, pooled: site vs web | 53% / 38% | 54% / 36% |
| Fact fate (site): stated wrong / never mentioned | 4% / 29% | 3% / 30% |
| Fact fate (web): stated wrong / never mentioned | 6% / 45% | 5% / 50% |
| Accuracy by intent, pooled, pricing (site / web) | 63% / 43% | 67% / 41% |
| Accuracy by intent, pooled, features (site / web) | 50% / 39% | 49% / 38% |

Every direction and every large effect reproduces. Absolute values typically land
within a few points; ratios and lifts computed from smaller sub-groups (e.g. a single hedge
pattern within a single harness, or endorsement broken out by arm *and* industry) move more,
because a ~20% domain sample means roughly 5x fewer domains inside any one narrow slice; the
coarse searches curve, for instance, flattens in its top bin (26 domains), and these are inherently
noisier statistics even in the full corpus. Treat this repo's `data/aggregates.json` as good for
verifying the shape and the headline claims, not as a byte-for-byte replica of the published
scoreboard.

Two rows in the table deserve a word on estimators:

- **Accuracy** is published from a stratified *paired* estimator (cells = domain x arm x
  category, only cells with both a site-built and a web-built answer count, each business one
  vote), because the agent chooses whether to ground on the site and site-built answers
  concentrate on the easier businesses — a pooled split overstates the site advantage that
  pairing removes. `build_aggregates.py` computes both: the `acc_paired_*` tokens are the
  published estimator (on this sample they give a +36% lift against the published +41%, and
  reproduce the setup null at +0.8pp; the pooled setup split shows +9% here, which is exactly the
  bias pairing exists to remove), and the plain `acc_*` / `verdict_*` tokens are the simpler pooled split, kept for
  the corpus-wide view.
- **Answer composition** (the on-site answer share row) comes from an LLM-judge pass run on a
  seeded, arm-and-group-balanced subsample of the full study (1,199 of 37,927 journeys; 249 of
  them fall in this sample's 206 domains), so it is the noisiest headline row here. The
  first-party evidence share row directly below it is the mechanical, full-coverage companion
  measured on every run, and it reproduces almost exactly.

## License

CC BY 4.0, see [`LICENSE`](LICENSE).
