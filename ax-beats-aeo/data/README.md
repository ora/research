# data — reproduction sample

The full study ran 37,927 agent journeys against 1,056 domains. This folder holds a
**stratified ~10% domain sample** of the same normalized data the study's published numbers
(paper forthcoming) were computed from: **106 domains, 3,816 journeys**, consolidated into 4 flat
CSVs. It is not a random 10% of rows; see [Sampling method](#sampling-method) for why, and
[Reconciliation](#reconciliation) for how closely the sample reproduces the published numbers.

The raw per-run traces (~3.25 GB, one JSON file per journey) are not published; everything below
is already the normalized, tabular layer derived from them.

`training-knowledge-probe/` is a separate experiment nested in this folder because it's still
data, not because it's sampled the same way — see its own [README](training-knowledge-probe/README.md).

## Files

Every column below survived a pass that asked, per column, whether it's read by
`build_aggregates.py`, and if not, whether it's still necessary to verify a specific documented
claim (sampling strata, fame/AEO matching, ground-truth coverage) or genuinely useful and free of
risk (e.g. which underlying model an arm actually ran). Source columns that were 1:1-derivable
from a kept column, pipeline bookkeeping, or filenames pointing at unpublished raw traces were
not carried over.

- **`journeys.csv`** — one row per agent journey (3,816 rows, 49 columns): the core per-run
  facts (grounding, searches, cost, turns, duration, blocks, evidence shares, outcome), which
  underlying model the arm actually ran, plus, merged in on `run_id`, every other per-run signal
  the study collected:
  - `endorse_strength_{claude,gpt}` / `endorse_reason_{claude,gpt}` — 0-4 recommendation-strength
    grade from two independent judge models, and their stated reason.
  - `antirec_*` — hedge/red-flag judge: five boolean patterns (`access_disclaimer`,
    `outside_sourced`, `vague_noncommittal`, `punts_to_source`, `staleness_memory`) and the
    judge's free-text reason.
  - `attr_*` — answer-composition judge (first-party / external / search / memory-recall share
    of the final answer). Populated for a judged subset (133 of 3,816 rows); blank elsewhere.
  - `acc_*` — accuracy-judge summary for runs that were fact-checked against ground truth
    (`n_facts`, `n_correct`, `n_partial`, `n_incorrect`, `n_not_addressed`, `no_answer`).
    Populated for 1,524 of 3,816 rows; blank elsewhere. The atomic, per-fact verdicts these
    summarize are in `accuracy_facts.csv`.

  `group` = ax-high/ax-low (median split on the accessibility score). `stratum` = which
  collection wave (`roster` = the 60-domain matched core, `batch-01..03` = the expansion waves).

- **`accuracy_facts.csv`** (19,422 rows) — one row per judged atomic fact: `run_id, domain, arm,
  category, fact_index, fact_text, verdict, evidence`. Long format because a single run can be
  judged against many facts; the per-run roll-up (`n_correct` etc.) already lives on
  `journeys.csv`, so this file is reference detail (e.g. "which specific facts did AX-low miss"),
  not required to reproduce the aggregates.

- **`domains.csv`** (106 rows, 12 columns) — one row per sampled domain: `brand`, `group`,
  `industry` / `fine_vertical` (G2 taxonomy), `ax_ratio` (the accessibility score, the
  treatment), `discovery` (one of the two AEO proxies), `tranco_rank` / `training_presence`
  (the fame-matching variables), `citation_breadth` (the other AEO proxy), and two derived
  flags: `in_matched_core` (one of the 60 matched-core domains) and `has_ground_truth`.

- **`ground_truth_facts.csv`** (1,625 rows, 62 domains) — one row per captured ground-truth fact:
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
and by intent), plus the by-industry, by-accessibility-bin, and by-source-x-arm tables as named
lists in the same file — one file, not a folder of per-concern CSVs. This repo ships it
**already computed from the sample**; re-run the script (`--check`) to regenerate it and see the
reconciliation printout.

## Consolidation

This data was originally organized as ~80 separate files (a `runs.csv`, 12 per-arm accuracy
`.jsonl` files, 2 endorsement `.jsonl` files, an anti-rec `.jsonl`, an answer-attribution
`.jsonl`, a domain-industry and a domain-vertical CSV, a per-domain accessibility-score registry,
and 62 individual per-domain ground-truth JSON files), matching how the research pipeline keeps
each judge's output separate. For this public repo those are consolidated into the 4 files
above: `endorse_*`, `antirec_*`, `attr_*`, and `acc_*` merge onto `journeys.csv` because they're
each keyed 1:1 on `run_id` (verified no duplicate keys before merging, so the merge cannot
fan out rows); domain-level files merge into `domains.csv`; the per-run atomic facts and the
per-domain ground truth stay as their own long-format tables (`accuracy_facts.csv`,
`ground_truth_facts.csv`) because each run or domain maps to *many* fact rows.
`../scripts/consolidate.py` is the exact script; it's kept for provenance and isn't re-runnable
against this repo's own (already-consolidated) data, the same way `sample_domains.py` isn't (see
its docstring).

## Sampling method

Every headline number in the study is "domain-collapsed": a metric is averaged within each
domain first, then those domain means are averaged within a group (ax-high / ax-low). That means
the right sampling unit is the **domain**, not the row, and it means one specific domain set
cannot be shrunk without changing what it measures: the study's clean 30-vs-30 contrast is built
from a *fame- and citation-breadth-matched* 60-domain core (`experiment/roster.json`), and
subsampling that core would break its own matching.

So the sample is built in two parts:

1. **Keep all 60 domains of the matched core** (30 AX-high / 30 AX-low), unchanged.
2. **From the remaining ~996 domains**, draw a sample proportionally stratified by
   (ax-group x collection-batch), seeded deterministically (`seed=42`), sized so the total lands
   at 10% of all domains (106 of 1,056: 60 core + 46 stratified).

`../scripts/sample_domains.py` is the exact script (it needs the full internal dataset to run,
so it documents the method rather than being runnable against this already-sampled repo).

Every other file is filtered to the same 106 domains: journeys by `domain`, the judged signals
merged onto them by `run_id` (joined back through the sampled journeys), and ground truth by
whichever of the 106 domains have a captured ground-truth record (62 of them; ground truth was
only captured for a subset of the full study too).

## Reconciliation

Recomputing `data/aggregates.json` from this 10% sample and comparing to the published, full-corpus
numbers:

| metric | full corpus (1,056 domains) | this sample (106 domains) |
|---|---|---|
| On-site answer share, AX-high / AX-low | 78% / 58% | 85% / 46% |
| Grounded (first-party) answer rate, hi / lo | 78% / 56% | 78% / 51% |
| Turns, hi / lo | 5.5 / 6.8 | 5.9 / 6.8 |
| Duration (s), hi / lo | 48 / 55 | 57 / 61 |
| Block ratio (lo / hi) | 2.1x | 2.3x |
| Cost premium (lo vs hi, mean over arms) | 64% | 62% |
| Web-search ratio, claude-agent-sdk arm | 2.4x | 2.3x |
| Web-search ratio, openclaw arm | 1.5x | 1.6x |
| Endorsement top-grade rate, hi / lo | 20% / 11% | 22% / 14% |
| Hedge: access-disclaimer, hi / lo (lift) | 4% / 16% (4.4x) | 3% / 17% (5.0x) |
| Accuracy, site-grounded vs web-sourced | 53% / 38% | 53% / 34% |
| Accuracy verdict mix (site): correct / not-addressed | 35% / 34% | 35% / 34% |
| Accuracy by intent, pricing (site / web) | 63% / 43% | 68% / 42% |
| Accuracy by intent, features (site / web) | 50% / 39% | 47% / 37% |

Every direction and every large effect reproduces. Absolute values typically land within a few
points; ratios and lifts computed from smaller sub-groups (e.g. a single hedge pattern within a
single harness, or endorsement broken out by arm *and* industry) move more, because a 10% domain
sample means roughly 10x fewer domains inside any one narrow slice, and these are inherently
noisier statistics even in the full corpus. Treat this repo's `data/aggregates.json` as good for
verifying the shape and the headline claims, not as a byte-for-byte replica of the published
scoreboard.

`build_aggregates.py --check` also flags one gap that predates sampling entirely: the study's
published site-vs-web accuracy figures (`acc_source_lift_pct` and related) come from a stratified
*paired* estimator (cells = domain x arm x category, each business one vote), which corrects for
composition bias. Because the agent chooses whether to ground on the site, site-built answers
concentrate on the easier businesses, so a pooled split overstates the site advantage that
pairing removes. This repo computes only the simpler pooled reconstruction, so those particular
tokens reproduce the published values approximately rather than exactly, in the full corpus and
in this sample alike. (The accuracy dose-response chart, which is the section's headline, does
reproduce.)

## License

CC BY 4.0, see [`LICENSE`](LICENSE).
