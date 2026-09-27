# AX is the New AEO: dataset

[![Code license: MIT](https://img.shields.io/badge/code%20license-MIT-green.svg)](LICENSE)
[![Data license: CC BY 4.0](https://img.shields.io/badge/data%20license-CC%20BY%204.0-lightgrey.svg)](data/LICENSE)
[![Python 3, stdlib only](https://img.shields.io/badge/python-3%20%C2%B7%20stdlib%20only-blue.svg)](scripts/build_aggregates.py)
[![Data: 3,816 journeys, 106 domains](https://img.shields.io/badge/data-3%2C816%20journeys%20%C2%B7%20106%20domains-orange.svg)](data/)
[![Paper: ora research](https://img.shields.io/badge/paper-ora%20research-black.svg)](https://ora.ai/research)

This directory is a data release, not the paper. It publishes a reproduction sample of the data
behind the "AX is the New AEO" study (whether AI agents ground their answers on a business's own
site vs. third-party sources, and whether that's driven by agent accessibility rather than
answer-engine optimization) plus the scripts to recompute the study's aggregate numbers from it.

**Paper:** *AX is the New AEO* — Ido Finder, Assaf Elovic, Gad Shalev; ora research (era labs),
September 2026 — [ora.ai/research](https://ora.ai/research). `data/aggregates.json` and
`scripts/build_aggregates.py --check` recompute the paper's aggregate numbers from the sample
published here (see [Reproducing the numbers](#reproducing-the-numbers)).

This directory also includes a second, separate experiment in
[`data/training-knowledge-probe/`](data/training-knowledge-probe/): the data behind a related but
distinct figure ("how much of the answer comes from the model's training knowledge"), published
as final aggregated verdicts only. See its own README.

## What's in this directory, and what isn't

The full study ran **37,927 agent journeys against 1,056 domains** (4 harnesses x 3 intents x
repeats), producing about 3.25 GB of raw per-run traces. Neither the raw corpus nor the paper
itself is in this directory.

What is published in [`data/`](data/) is a **stratified ~10% domain sample** (106 domains,
3,816 journeys) of the normalized, per-journey data, consolidated into 4 flat CSVs, plus the
script to recompute every aggregate number from it. See
[`data/README.md`](data/README.md) for the exact sampling method and a full reconciliation table
(published numbers vs. numbers recomputed from the sample).

This means: numbers recomputed here from the 10% sample reproduce the study's published numbers
to within a reasonable delta, not byte-for-byte, because they run on ~10% of the domains. That
delta is measured and documented, not hidden.

## Repository layout

| Path | What it holds |
|---|---|
| [`data/`](data/) | The reproduction sample, as 4 flat CSVs: `journeys.csv` (one row per run, with judged endorsement/hedge/attribution/accuracy signals merged in), `accuracy_facts.csv` and `ground_truth_facts.csv` (long-format fact detail), and `domains.csv` (one row per domain), plus the generated `aggregates.json`. Own [README](data/README.md). |
| [`data/training-knowledge-probe/`](data/training-knowledge-probe/) | A separate experiment, nested here because it's still data: final aggregated verdicts (`figure-points.csv`, `series.csv`) behind the training-knowledge figure. Own [README](data/training-knowledge-probe/README.md). |
| [`scripts/`](scripts/) | One script, `build_aggregates.py` (pure standard library): recomputes `data/aggregates.json` from `data/` and reconciles it against the study's published numbers (`--check`). How `data/` was derived (sampling, consolidation) is documented in [`data/README.md`](data/README.md). |

## The experiment, in brief

Round-independent definition of the study, needed to interpret `data/`. Per-domain metadata
and facts live in `data/domains.csv` and `data/ground_truth_facts.csv` (see
[`data/README.md`](data/README.md)); this section describes the parts that aren't
domain-indexed tables.

**The scores.** The *treatment* score (`ax_ratio` in `data/domains.csv`) is the ora ranker's
accessibility layer — what an agent meets on arrival: robots.txt stance toward agents, bot
blocking, how much text survives a raw no-JavaScript fetch, and gating of key pages. The two
AEO *controls* are `discovery` (the ora ranker's discovery-layer score: how
answer-engine-ready the site's content is) and `citation_breadth` (how widely third-party
sources already cover the domain). All three are described in the paper's Method section.

**The tasks.** Each journey gave an agent one realistic buyer question about one business, in
one of three intent categories (the `category` column in `data/journeys.csv`): **pricing**
(current plans and costs, including any free plan/trial), **features** (main features and
stated usage limits), and **setup** (how a new user gets started). Each prompt is a natural
user request built from a frozen template with the business's own domain filled in, for
example (pricing): *"I'm looking for a service that fits my budget. Can you find out what
subscription options are available at {domain} and what they cost?"* Three independent
repeats per domain x category, under a neutral system prompt with web search and plain page
fetch available.

## Reproducing the numbers

```bash
cd scripts
python3 build_aggregates.py --check
```

This reads `data/journeys.csv` and `data/domains.csv` and writes a single file,
`data/aggregates.json`: every scalar plus the by-industry, by-accessibility-bin, and
by-source-x-arm breakdowns as named tables. No dependencies beyond Python 3's standard library.
`--check` prints a reconciliation against the study's published numbers (baked into the script).
Accuracy comes in both the paper's stratified paired estimator (`acc_paired_*`) and a simpler
pooled split; see [`data/README.md`](data/README.md) for the two estimators and for how closely
each cell reproduces from a 10% sample.

## Status

First public release, September 2026, accompanying the paper. Data and reproduction scripts
only; the paper itself is published separately.

## Citing

```bibtex
@techreport{finder2026ax,
  title       = {AX is the New AEO},
  author      = {Finder, Ido and Elovic, Assaf and Shalev, Gad},
  institution = {ora research (era labs)},
  year        = {2026},
  month       = sep,
  url         = {https://ora.ai/research}
}
```

## Contributing

- Open an issue for unclear methodology, questions about the data, or a specific number you
  can't reproduce.
- Challenges to a measured number are welcome: that's what the reproduction sample and script
  are for.

## License

Code (`scripts/`) is MIT, see [`LICENSE`](LICENSE). The dataset (`data/`, including
`data/training-knowledge-probe/`) is CC BY 4.0, see
[`data/LICENSE`](data/LICENSE). (c) 2026 era labs (ora.ai).
