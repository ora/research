# scripts

- **`build_aggregates.py`** — reads `../data/journeys.csv` + `../data/domains.csv`, writes a
  single `../data/aggregates.json` (every scalar plus the by-industry / by-bin / by-source-x-arm
  tables). Pure standard library, no dependencies. `python3 build_aggregates.py --check` also
  prints a reconciliation against the study's published numbers.
- **`sample_domains.py`** — the stratified 10%-domain sampling method used to build `../data/`
  from the full internal dataset. Documents the method; needs the full (unpublished) dataset to
  actually run.
- **`consolidate.py`** — the one-time script that turned the original ~80-file per-judge layout
  (a `runs.csv`, per-arm accuracy `.jsonl` files, endorsement/anti-rec/attribution `.jsonl`
  files, per-domain metadata CSVs, and 62 per-domain ground-truth JSON files) into the 4
  consolidated CSVs in `../data/`. Documents the method; not re-runnable against this repo's own
  already-consolidated data (see `../data/README.md#consolidation`).
