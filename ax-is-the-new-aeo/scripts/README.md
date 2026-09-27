# scripts

One script, runnable against this repo's own data:

- **`build_aggregates.py`** — reads `../data/journeys.csv` + `../data/domains.csv`, writes a
  single `../data/aggregates.json` (every scalar plus the by-industry / by-bin / by-source-x-arm
  tables; accuracy comes in both the pooled split and the study's published stratified paired
  estimator, `acc_paired_*`). Pure standard library, no dependencies.
  `python3 build_aggregates.py --check` also prints a reconciliation against the study's
  published numbers.

How `../data/` itself was derived from the full study (the domain sampling and the
consolidation into 4 flat CSVs) is documented in [`../data/README.md`](../data/README.md).
