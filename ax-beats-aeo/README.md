# AX beats AEO: dataset

This directory is a data release, not the paper. It publishes a reproduction sample of the data
behind the "AX beats AEO" study (whether AI agents ground their answers on a business's own
site vs. third-party sources, and whether that's driven by agent accessibility rather than
answer-engine optimization) plus the scripts to recompute the study's aggregate numbers from it.

**Paper:** forthcoming from the [ora.ai](https://ora.ai) research lab (era labs). This README
will be updated with a link on publication; until then, `data/aggregates.json` and
`scripts/build_aggregates.py --check` are the closest thing to the published numbers available
here (see [Reproducing the numbers](#reproducing-the-numbers)).

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
script to recompute every aggregate number from it. The sample keeps the full 60-domain matched
core intact (subsampling it would break its own fame/breadth matching) and adds a proportionally
stratified draw from the remaining domains. See [`data/README.md`](data/README.md) for the exact
method and a full reconciliation table (published numbers vs. numbers recomputed from the
sample).

This means: numbers recomputed here from the 10% sample reproduce the study's published numbers
to within a reasonable delta, not byte-for-byte, because they run on ~10% of the domains. That
delta is measured and documented, not hidden.

## Repository layout

| Path | What it holds |
|---|---|
| [`data/`](data/) | The reproduction sample, as 4 flat CSVs: `journeys.csv` (one row per run, with judged endorsement/hedge/attribution/accuracy signals merged in), `accuracy_facts.csv` and `ground_truth_facts.csv` (long-format fact detail), and `domains.csv` (one row per domain), plus the generated `aggregates.json`. Own [README](data/README.md). |
| [`data/training-knowledge-probe/`](data/training-knowledge-probe/) | A separate experiment, nested here because it's still data: final aggregated verdicts (`figure-points.csv`, `series.csv`) behind the training-knowledge figure. Own [README](data/training-knowledge-probe/README.md). |
| [`experiment/`](experiment/) | The main study's experiment definition needed to interpret `data/`: the 60-domain matched core (`roster.json`), a plain-language description of the three task intents, and the accessibility-score rubric. Exact prompt wording and judge instructions are deliberately not published (see its README). |
| [`scripts/`](scripts/) | `build_aggregates.py` (pure standard library, reproduces `data/aggregates.json` from `data/`), and two provenance scripts documenting how `data/` was derived: `sample_domains.py` (the 10% domain sample) and `consolidate.py` (the ~80-file to 4-file consolidation). |

## Reproducing the numbers

```bash
cd scripts
python3 build_aggregates.py --check
```

This reads `data/journeys.csv` and `data/domains.csv` and writes a single file,
`data/aggregates.json`: every scalar plus the by-industry, by-accessibility-bin, and
by-source-x-arm breakdowns as named tables. No dependencies beyond Python 3's standard library.
`--check` prints a reconciliation against the study's published numbers (baked into the script;
see [`data/README.md`](data/README.md) for why some cells differ, by sampling and by one known,
documented methodology gap unrelated to sampling).

## Status

First public release, 2026. Data only; the paper is forthcoming.

## Contributing

- Open an issue for unclear methodology, questions about the data, or a specific number you
  can't reproduce.
- Challenges to a measured number are welcome: that's what the reproduction sample and script
  are for.

## License

Code (`scripts/`) is MIT, see [`LICENSE`](LICENSE). The dataset (`data/`, including
`data/training-knowledge-probe/`, and `experiment/`) is CC BY 4.0, see
[`data/LICENSE`](data/LICENSE). (c) 2026 era labs (ora.ai).
