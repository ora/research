# experiment — the experiment definition

Round-independent definition of the study. Per-domain metadata and facts live in
`../data/domains.csv` and `../data/ground_truth_facts.csv` (see
[`../data/README.md`](../data/README.md)); this folder holds the parts that aren't
domain-indexed tables.

- **`roster.json`** — the 60-domain matched core (30 AX-high / 30 AX-low): the selection design,
  the confounds controlled, and each core domain's matching covariates. Frozen; not resampled
  (see [`../data/README.md`](../data/README.md#sampling-method)). The same 60 domains are flagged
  `in_matched_core` in `../data/domains.csv`.
- **`specs/aeo-score-rubric.md`** — the accessibility-score rubric (what `ax_ratio` in
  `../data/domains.csv` scores and why).

## The tasks, in brief

Each journey gave an agent one realistic buyer question about one business, in one of three
intent categories (the `category` column in `../data/journeys.csv`): **pricing** (current plans
and costs, including any free plan/trial), **features** (main features and stated usage limits),
and **setup** (how a new user gets started). Three independent repeats per domain x category,
under a neutral system prompt with web search and plain page fetch available.

## What's not here, on purpose

The exact frozen prompt wording and the judges' grading instructions are not published, for the
same reason as in [`../data/training-knowledge-probe/`](../data/training-knowledge-probe/README.md):
the aggregate results and the per-fact verdicts (`../data/accuracy_facts.csv`, graded against
`../data/ground_truth_facts.csv`) are what's verifiable here, without exposing the underlying
prompts and judge methodology to direct replication from the published data alone.
