#!/usr/bin/env python3
"""Recompute the time and success figures of "Jev and the agentic web" from data/.

Reads data/runs.csv (one row per run) and data/task_success.csv (pass counts per
task, arm and surface), writes aggregates.json next to this study's README, and
with --check compares every recomputed number against the figure the report
states. Exit code 1 if any number is outside tolerance.

Runs with the standard library only, no network.

Usage:
    python3 scripts/aggregates.py            # write aggregates.json
    python3 scripts/aggregates.py --check    # also compare against the report
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
RUNS = STUDY / "data" / "runs.csv"
SUCCESS = STUDY / "data" / "task_success.csv"
OUT = STUDY / "aggregates.json"

SURFACES = ["browser-use", "webmcp", "nlweb"]
ARMS = ["jev", "llm"]  # jev: Jev decides each step; llm: Claude Haiku 4.5 decides

# The numbers the report states, for --check. Durations in the release are
# rounded to 0.1 s (the precision the report publishes per run), so medians and
# ratios can move by that much.
PUBLISHED = {
    "browser-use": {"median": {"jev": 1.9, "llm": 8.2}, "slowest": {"jev": 3.7, "llm": 20.7}, "speedup": 4.3, "success": {"jev": 0.78, "llm": 0.71}},
    "webmcp": {"median": {"jev": 1.4, "llm": 3.7}, "slowest": {"jev": 2.0, "llm": 7.5}, "speedup": 2.6, "success": {"jev": 1.0, "llm": 1.0}},
    "nlweb": {"median": {"jev": 2.0, "llm": 7.8}, "slowest": {"jev": 2.4, "llm": 11.5}, "speedup": 3.9, "success": {"jev": 1.0, "llm": 1.0}},
}
PUBLISHED_PAIRED = {"pairs": 120, "jev_faster": 120}
TOL = {"median": 0.15, "slowest": 0.05, "speedup": 0.2, "success": 0.005}


def load_runs() -> list[dict]:
    with RUNS.open(newline="") as f:
        return [
            {**r, "repeat": int(r["repeat"]), "seconds": float(r["seconds"])}
            for r in csv.DictReader(f)
        ]


def load_success() -> list[dict]:
    with SUCCESS.open(newline="") as f:
        return [{**r, "passed": int(r["passed"]), "runs": int(r["runs"])} for r in csv.DictReader(f)]


def compute(runs: list[dict], success: list[dict]) -> dict:
    by = defaultdict(list)
    for r in runs:
        by[(r["surface"], r["arm"])].append(r["seconds"])

    out: dict = {"surfaces": {}, "paired_runs": {}}
    for s in SURFACES:
        med = {a: round(statistics.median(by[(s, a)]), 2) for a in ARMS}
        slow = {a: max(by[(s, a)]) for a in ARMS}
        passed = {a: sum(x["passed"] for x in success if x["surface"] == s and x["arm"] == a) for a in ARMS}
        total = {a: sum(x["runs"] for x in success if x["surface"] == s and x["arm"] == a) for a in ARMS}
        out["surfaces"][s] = {
            "runs": {a: len(by[(s, a)]) for a in ARMS},
            "median_seconds": med,
            "slowest_seconds": slow,
            "speedup_median": round(med["llm"] / med["jev"], 2),
            "slowest_jev_beats_median_llm": slow["jev"] < med["llm"],
            "passed": passed,
            "success_rate": {a: round(passed[a] / total[a], 4) for a in ARMS},
        }

    # Paired runs: same surface, task and repeat, one per arm.
    pairs = defaultdict(dict)
    for r in runs:
        pairs[(r["surface"], r["task"], r["repeat"])][r["arm"]] = r["seconds"]
    complete = [p for p in pairs.values() if set(p) == set(ARMS)]
    out["paired_runs"] = {
        "pairs": len(complete),
        "jev_faster": sum(p["jev"] < p["llm"] for p in complete),
        "tied": sum(p["jev"] == p["llm"] for p in complete),
    }

    # Per-task pass counts, as a flat list for anyone who wants them.
    out["task_success"] = [
        {k: x[k] for k in ("surface", "arm", "task", "passed", "runs")} for x in success
    ]
    return out


def check(agg: dict) -> int:
    failures = 0

    def cmp(label: str, got: float, want: float, tol: float) -> None:
        nonlocal failures
        ok = abs(got - want) <= tol
        failures += 0 if ok else 1
        print(f"{'ok  ' if ok else 'FAIL'} {label:48s} recomputed {got:<8g} published {want:<8g}")

    for s in SURFACES:
        a, p = agg["surfaces"][s], PUBLISHED[s]
        for arm in ARMS:
            cmp(f"{s} median seconds ({arm})", a["median_seconds"][arm], p["median"][arm], TOL["median"])
            cmp(f"{s} slowest seconds ({arm})", a["slowest_seconds"][arm], p["slowest"][arm], TOL["slowest"])
            cmp(f"{s} success rate ({arm})", a["success_rate"][arm], p["success"][arm], TOL["success"])
        cmp(f"{s} speedup (median llm / median jev)", a["speedup_median"], p["speedup"], TOL["speedup"])
    cmp("paired runs", agg["paired_runs"]["pairs"], PUBLISHED_PAIRED["pairs"], 0)
    cmp("paired runs where Jev was faster", agg["paired_runs"]["jev_faster"], PUBLISHED_PAIRED["jev_faster"], 0)
    print(f"\n{failures} failure(s)")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    agg = compute(load_runs(), load_success())
    OUT.write_text(json.dumps(agg, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(STUDY.parent)}")
    if "--check" in argv:
        return check(agg)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
