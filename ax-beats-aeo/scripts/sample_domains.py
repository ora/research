#!/usr/bin/env python3
"""Reproduce the domain sample published in data/.

This repo ships ~10% of the full study (1,056 domains / 37,927 journeys) rather than the
full run corpus, which stays internal (~3.25 GB of raw agent traces). The sample is not a
uniform random draw over rows: it is a stratified draw over DOMAINS, because every headline
number in the study is computed "domain-collapsed" (mean within domain, then mean across
domains in a group) — sampling journeys directly would over/under-weight domains with more
repeats and would silently break the matched-pair design below.

Sampling design:
  1. Keep all 60 domains of the frozen, fame+breadth-matched AX-high/AX-low core
     (experiment/roster.json — 30/30, the "clean contrast" the study's headline numbers are
     built from). Subsampling this set would defeat its own matching.
  2. From the remaining ~996 domains, draw a stratified sample proportional to each
     (ax-group x collection-batch) cell, seeded deterministically (seed=42), sized so the
     total sample lands at ~10% of all domains (106 of 1,056).

This script needs the full internal data/runs.csv and experiment/roster.json (not published
here) to run — it is included for transparency about how data/ was derived, not as something
you can run against this repo's own (already-sampled) data.

Output: sample_domains.json, a flat list of the 106 domains kept.
"""
import csv, json, random, collections
from pathlib import Path

FULL_ROOT = Path("..")  # point at a checkout of the full internal dataset to reproduce

def main():
    rows = list(csv.DictReader(open(FULL_ROOT / "data/runs.csv")))
    by_domain = collections.defaultdict(list)
    for r in rows:
        by_domain[r["domain"]].append(r)
    all_domains = set(by_domain)

    roster = json.load(open(FULL_ROOT / "experiment/roster.json"))
    core60 = set(d["domain"] for d in roster["domains"])
    rest = all_domains - core60

    def dom_group(d):
        return by_domain[d][0]["group"]

    def dom_stratum(d):
        c = collections.Counter(r["stratum"] for r in by_domain[d])
        return c.most_common(1)[0][0]

    strata = collections.defaultdict(list)
    for d in sorted(rest):
        strata[(dom_group(d), dom_stratum(d))].append(d)

    target_total = round(0.10 * len(all_domains))
    extra_needed = max(0, target_total - len(core60))

    rng = random.Random(42)
    total_rest = len(rest)
    alloc = {k: extra_needed * len(v) / total_rest for k, v in strata.items()}
    floor_alloc = {k: int(v) for k, v in alloc.items()}
    remainder = extra_needed - sum(floor_alloc.values())
    for k, _ in sorted(alloc.items(), key=lambda kv: -(kv[1] - int(kv[1])))[:remainder]:
        floor_alloc[k] += 1

    picked = []
    for k, v in strata.items():
        v = list(v)
        rng.shuffle(v)
        picked.extend(v[: floor_alloc[k]])

    sample_domains = sorted(core60 | set(picked))
    assert len(sample_domains) == target_total
    Path("sample_domains.json").write_text(json.dumps(sample_domains, indent=1))
    print(f"wrote {len(sample_domains)} domains ({len(core60)} core + {len(picked)} stratified) to sample_domains.json")

if __name__ == "__main__":
    main()
