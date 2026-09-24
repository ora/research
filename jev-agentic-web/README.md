# Jev and the agentic web: dataset

Data release for the report [Jev and the agentic web](https://ora.ai/blog/evaluating-jev) (ora research, September 2026). This directory is the data, not the report.

## The question

TypeSafe's [Jev](https://typesafe.ai) answers a closed question (which option, which element, yes or no) in about 150 ms at a fraction of a language model's price. We wanted to know whether Jev makes a site more accessible and usable for agents, and how that holds up across the top protocols an agent uses to work a website: browser automation, [WebMCP](https://github.com/webmachinelearning/webmcp) tools and [NLWeb](https://github.com/nlweb-ai/NLWeb) search.

## The setup

- **Site:** a warehouse, a helpdesk and a document vault we host and seed ourselves (`acme-v1`, seed 4242), so every task has a known answer or end state. Source: [`orabenchmarks/benchme`](https://github.com/orabenchmarks/benchme).
- **Agents:** simple Claude agents. Claude Haiku 4.5 writes any free text in both arms. The only difference between the arms is who makes each step's closed choice: Jev (`jev`) or Claude Haiku 4.5 from the same state (`llm`).
- **Surfaces:** `browser-use` (the pages, driven through browser-use's [jev-ultrafast](https://github.com/browser-use/jev-ultrafast), 9 tasks), `webmcp` (the tools the page registers with `navigator.modelContext`, 10 tasks), `nlweb` (the site's `/ask` endpoint, 5 tasks).
- **Runs:** 10 tasks, 5 repeats each, a fresh workspace per run. 240 runs, each verified against live state or the exact answer.

## What is in this release

| File | One row per | Columns |
|---|---|---|
| [`data/runs.csv`](data/runs.csv) | run (240 rows) | `surface`, `arm`, `task`, `repeat`, `seconds` (wall time per task, rounded to 0.1 s) |
| [`data/task_success.csv`](data/task_success.csv) | task x arm x surface (48 rows) | `passed`, `runs` (out of 5) |
| [`data/tasks.json`](data/tasks.json) | task (10) | the verbatim intent, the surfaces that offer it, the oracle used to verify it. Copied from `benchme/compose/specs/intent-tasks.json`. |
| [`aggregates.json`](aggregates.json) | | the recomputed numbers: median and slowest seconds per surface and arm, speedup, pass rates, paired-run counts |
| [`scripts/aggregates.py`](scripts/aggregates.py) | | recomputes `aggregates.json` from `data/`; `--check` compares every number against the report |

## What is not in this release

- **Per-run steps, decision times and cost split.** The report's cost figures (for example $0.0018 against $0.0233 per browser task, and the deciding / writing / search-ranking split) and the per-step decision latencies (125 to 159 ms with Jev, 1.1 to 1.2 s without) come from the harness's per-run records, which are not in this directory yet. They will be added as `data/steps.csv` and `data/costs.csv`; until then those numbers cannot be recomputed from here.
- **Raw traces:** page snapshots, element tables, model transcripts. These stay in the lab's storage.

## Reproducing the numbers

```bash
python3 scripts/aggregates.py --check
```

Standard library only, no network. Every time and success figure the report states recomputes exactly or within the 0.1 s rounding of the published per-run durations (the WebMCP median without Jev recomputes as 3.65 s against the report's 3.7 s; everything else matches).

## Cite

> ora research (2026). Jev and the agentic web: agents with Jev and without it, on a browser, WebMCP tools and NLWeb search, across 240 runs. ora.ai/research, September 2026. Data: github.com/ora/research/tree/main/jev-agentic-web

## Licence

Data (`data/`, `aggregates.json`) is [CC BY 4.0](data/LICENSE). Code (`scripts/`) is [MIT](../LICENSE).
