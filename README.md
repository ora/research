# ora research: datasets

The data and reproduction scripts behind the research published at [ora.ai/research](https://ora.ai/research). Each directory is a data release, not the paper: it holds the normalized per-run data (or a documented sample of it), the scripts that recompute every number the report states, and a README that says what is in the release and what is not.

## Studies

| Directory | Report | What is published |
|---|---|---|
| [`ax-beats-aeo/`](ax-beats-aeo/) | [AX is the new AEO](https://ora.ai/blog/ax-is-the-new-aeo) | A stratified 10% domain sample of 37,927 agent journeys across 1,056 sites (106 domains, 3,816 journeys) as flat CSVs, plus `scripts/build_aggregates.py --check`, which recomputes the study's aggregate numbers and reports the delta against the published ones. |
| [`jev-agentic-web/`](jev-agentic-web/) | [Jev and the agentic web](https://ora.ai/blog/evaluating-jev) | The 10 task specs, one row per run for all 240 runs (surface, arm, task, repeat, seconds), task-level pass counts, and `scripts/aggregates.py`, which recomputes the time and success figures in the report. |

## How a study is laid out

```
<study>/
  README.md          the question, the setup, what is and is not in the release, how to cite
  data/              flat CSV or JSON, one row per unit of observation, plus a data README
  scripts/           recomputes every published number from data/; runs with no network
  aggregates.json    the recomputed numbers, checked in so a diff shows any drift
```

Every number in a report must be recomputable from the directory. If a release is a sample rather than the full corpus, the README says so, states the sampling method, and carries a reconciliation table (published number, recomputed number, delta). Raw per-run traces, screenshots and model transcripts are not committed here; they stay in the lab's storage and are described in each README.

## Related repositories

- [`orabenchmarks/benchme`](https://github.com/orabenchmarks/benchme): the seeded warehouse, helpdesk and document vault, the task corpus and the verifier used by the Jev study.
- [`agentready-org/standard`](https://github.com/agentready-org/standard): the open agent-readiness standard the AX study scores against.
- [`ora/ax`](https://github.com/ora/ax): the CLI that scores a site's agent readiness.

## Licence

Code (`scripts/`) is MIT. Data (`data/`) is CC BY 4.0. Both licences are reproduced per study. Cite a study using the `Cite` section of its README.

## Contact

research@ora.ai
