# training-knowledge-probe

A second, separate experiment, nested here because it's still data: it backs the "how much of
the answer comes from the model's training knowledge" figure, not the AX-vs-AEO grounding/
accuracy claims that the rest of `data/` is about. Published as its own figure (paper/blog post
forthcoming, like the main study).

## What it measures

7 OpenAI model generations, gpt-4.1 (2025-04) through gpt-5.6 (2026), were each asked the same
90 buyer questions about 30 businesses (pricing / features / getting-started), with optional web
tools. Each answer was judged claim-by-claim for whether it was supported by fetched evidence or
came from the model's own training knowledge, and rolled up into a memory-share percentage per
model generation. The trend is the figure: across this span, the share of the answer resting on
training knowledge fell (ρ=-0.86, p=0.014; 51.5% → 13.9%).

The published scope is the reasoning-era span the finding is defined on: gpt-4.1 onward. Earlier
model generations were probed under a different protocol whose results aren't comparable to this
series, so they're out of scope for this release.

## Files

- **`figure-points.csv`** — the exact plotted values: memory-share % grouped into the four
  release cohorts the chart shows (gpt-4.1 · gpt-5/5.1/5.2 · gpt-5.4/5.5 · gpt-5.6), plus the
  "this study" endpoint, which is the main AX-vs-AEO experiment's own training-knowledge share
  (`comp_memory_hi`/`comp_memory_lo` in [`../aggregates.json`](../aggregates.json)).
- **`series.csv`** — the per-model-generation aggregate: release date, run/judged counts,
  zero-tool-call rate, memory share (with its bootstrap 95% CI, `memory_share_ci_low`/`_high`,
  10k resamples over domains), web share, first-party share, tool calls per answer, evidence
  volume. One row per model generation (7 rows), already averaged across all 90 questions for
  that model. The CI lets you assess the trend's significance yourself rather than take the
  reported p-value on faith, without needing the underlying per-question judgments.

## What's not here, on purpose

Only the final, aggregated-per-model verdicts are published. Not included: the individual
per-question judged attributions, the exact question wording, the system prompts given to the
probed models, or the judge's grading instructions. Those are internal so the underlying prompts
and judge methodology aren't exposed to direct scrutiny/replication attempts from the published
data alone; the aggregate series is what the figure is built from and what's reproducible here.

## License

CC BY 4.0, same as [`../`](../README.md) — see [`../LICENSE`](../LICENSE).
