# experiment — the experiment definition

Round-independent definition of the study. Per-domain metadata and facts live in
`../data/domains.csv` and `../data/ground_truth_facts.csv` (see
[`../data/README.md`](../data/README.md)); this folder holds the parts that aren't
domain-indexed tables.

- **`specs/aeo-score-rubric.md`** — the AEO on-site scoring rubric behind the study's AEO
  *controls* (the framing the `discovery` and `citation_breadth` proxies in
  `../data/domains.csv` derive from). The *treatment* score (`ax_ratio`) is the ora ranker's
  accessibility layer — what an agent meets on arrival: robots.txt stance toward agents, bot
  blocking, how much text survives a raw no-JavaScript fetch, and gating of key pages — as
  described in the paper's Method section.

## The tasks, in brief

Each journey gave an agent one realistic buyer question about one business, in one of three
intent categories (the `category` column in `../data/journeys.csv`): **pricing** (current plans
and costs, including any free plan/trial), **features** (main features and stated usage limits),
and **setup** (how a new user gets started). Each prompt is a natural user request built from a
frozen template with the business's own domain filled in, for example (pricing): *"I'm looking
for a service that fits my budget. Can you find out what subscription options are available at
{domain} and what they cost?"* Three independent repeats per domain x category, under a neutral
system prompt with web search and plain page fetch available.

