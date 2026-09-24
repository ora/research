#!/usr/bin/env python3
"""Consolidate the scattered per-file data (data/accuracy/*.jsonl, data/endorsement/*.jsonl,
data/anti-rec.jsonl, data/answer-attribution.jsonl, data/domain-industry.csv,
data/domain-vertical.csv, experiment/sources/domain-registry.csv,
experiment/ground-truth/*.json — ~80 files) into 4 flat CSVs:

  data/journeys.csv           one row per agent journey (was runs.csv), with endorsement,
                               hedge-flag, attribution, and accuracy-summary columns merged in
                               (all keyed 1:1 on run_id, verified no fan-out before merging)
  data/accuracy_facts.csv     one row per judged atomic fact (long format; run-level summary
                               columns live on journeys.csv instead, so this file is reference
                               detail, not required to reproduce the aggregates)
  data/domains.csv            one row per domain (registry score/fame/AEO proxies + G2 industry
                               + matched-core / ground-truth-coverage flags)
  data/ground_truth_facts.csv one row per captured ground-truth fact per domain (long format)

This was a one-time transform: it ran once against the original scattered layout to produce the
4 files above, and those files then replaced the originals in this repo. It is kept for
provenance/transparency, not meant to be re-run here — its inputs (data/accuracy/, etc.) no
longer exist in this repo, the same way sample_domains.py's input (the full internal dataset)
was never published here either.

scripts/build_aggregates.py reads the consolidated files directly.
"""
import csv, json, collections
from pathlib import Path

W = Path(__file__).resolve().parent.parent
D = W / "data"
E = W / "experiment"

def load_jsonl(p):
    return [json.loads(l) for l in open(p)] if p.exists() else []

def b01(x):
    return 1 if x else 0

# ---------------------------------------------------------------- journeys.csv
# some source columns are not carried over into the published tables: fields that are
# 1:1-derivable from a kept column, filenames pointing at unpublished raw traces, and
# pipeline bookkeeping not needed to interpret or reproduce the results.
DROP_RUN_FIELDS = {"harness", "family", "file"}
runs = list(csv.DictReader(open(D / "runs.csv")))
by_run = {r["run_id"]: r for r in runs}
run_fields = [c for c in runs[0].keys() if c not in DROP_RUN_FIELDS]

END_C = {d["run_id"]: d for d in load_jsonl(D / "endorsement/claude.jsonl")}
END_G = {d["run_id"]: d for d in load_jsonl(D / "endorsement/gpt.jsonl")}
for rid, r in by_run.items():
    c, g = END_C.get(rid), END_G.get(rid)
    r["endorse_strength_claude"] = c["strength"] if c else ""
    r["endorse_reason_claude"] = c["reason"] if c else ""
    r["endorse_strength_gpt"] = g["strength"] if g else ""
    r["endorse_reason_gpt"] = g["reason"] if g else ""

AR = load_jsonl(D / "anti-rec.jsonl")
for d in AR:
    r = by_run.get(d["run_id"])
    if not r: continue
    r["antirec_reason"] = d.get("reason", "")
    for k in ("punts_to_source", "outside_sourced", "access_disclaimer", "staleness_memory", "vague_noncommittal"):
        r[f"antirec_{k}"] = b01(d.get(k))

ATTR = load_jsonl(D / "answer-attribution.jsonl")
for d in ATTR:
    r = by_run.get(d["run_id"])
    if not r: continue
    for k in ("first_party_grounding", "external_share", "search_share", "memory_leak"):
        r[f"attr_{k}"] = d.get(k, "")

ACC = []
for f in sorted((D / "accuracy").glob("*.jsonl")):
    arm = "-".join(f.stem.split("-")[:-1]); cat = f.stem.split("-")[-1]
    for line in open(f):
        d = json.loads(line); d["arm"] = arm; d["category"] = cat
        ACC.append(d)
acc_fact_rows = []
for d in ACC:
    r = by_run.get(d["run_id"])
    if r:
        r["acc_n_facts"] = d.get("n_facts", "")
        r["acc_n_correct"] = d.get("n_correct", "")
        r["acc_n_partial"] = d.get("n_partial", "")
        r["acc_n_incorrect"] = d.get("n_incorrect", "")
        r["acc_n_not_addressed"] = d.get("n_not_addressed", "")
        r["acc_no_answer"] = b01(d.get("no_answer"))
    for i, v in enumerate(d.get("verdicts") or []):
        acc_fact_rows.append({
            "run_id": d["run_id"], "domain": d.get("domain", r["domain"] if r else ""),
            "arm": d["arm"], "category": d["category"],
            "fact_index": i, "fact_text": v.get("fact", ""),
            "verdict": v.get("verdict", ""), "evidence": v.get("evidence", ""),
        })

extra_fields = ["endorse_strength_claude", "endorse_reason_claude", "endorse_strength_gpt", "endorse_reason_gpt",
    "antirec_reason", "antirec_punts_to_source", "antirec_outside_sourced",
    "antirec_access_disclaimer", "antirec_staleness_memory", "antirec_vague_noncommittal",
    "attr_first_party_grounding", "attr_external_share", "attr_search_share", "attr_memory_leak",
    "acc_n_facts", "acc_n_correct", "acc_n_partial", "acc_n_incorrect",
    "acc_n_not_addressed", "acc_no_answer"]
journey_fields = run_fields + extra_fields
with open(D / "journeys.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=journey_fields)
    w.writeheader()
    for r in runs:
        w.writerow({k: r.get(k, "") for k in journey_fields})
print(f"journeys.csv: {len(runs)} rows x {len(journey_fields)} cols")

with open(D / "accuracy_facts.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["run_id", "domain", "arm", "category",
                                       "fact_index", "fact_text", "verdict", "evidence"])
    w.writeheader()
    w.writerows(acc_fact_rows)
print(f"accuracy_facts.csv: {len(acc_fact_rows)} rows")

# ---------------------------------------------------------------- domains.csv
registry = {r["domain"]: r for r in csv.DictReader(open(E / "sources/domain-registry.csv"))}
industry = {r["domain"]: r for r in csv.DictReader(open(D / "domain-industry.csv"))}
core60 = set(d["domain"] for d in json.load(open(E / "roster.json"))["domains"])
gt_domains = set(p.stem for p in (E / "ground-truth").glob("*.json"))

domain_fields = ["domain", "brand", "group", "industry", "fine_vertical",
    "ax_ratio", "discovery", "tranco_rank", "training_presence",
    "citation_breadth", "in_matched_core", "has_ground_truth"]
domain_rows = []
for dom in sorted(set(registry) | set(industry)):
    reg = registry.get(dom, {}); ind = industry.get(dom, {})
    domain_rows.append({
        "domain": dom, "brand": reg.get("brand", ""),
        "group": ind.get("group", reg.get("group", "")),
        "industry": ind.get("industry", ""), "fine_vertical": ind.get("fine_vertical", ""),
        "ax_ratio": reg.get("ax_ratio", ""),
        "discovery": reg.get("discovery", ""),
        "tranco_rank": reg.get("tranco_rank", ""), "training_presence": reg.get("training_presence", ""),
        "citation_breadth": reg.get("citation_breadth", ""),
        "in_matched_core": b01(dom in core60), "has_ground_truth": b01(dom in gt_domains),
    })
with open(D / "domains.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=domain_fields)
    w.writeheader(); w.writerows(domain_rows)
print(f"domains.csv: {len(domain_rows)} rows x {len(domain_fields)} cols")

# ---------------------------------------------------------------- ground_truth_facts.csv
LIST_FIELDS = {  # (block, json_key) -> singular field label
    ("pricing", "plans"): "plan",
    ("features", "main_features"): "main_feature",
    ("features", "usage_limits"): "usage_limit",
    ("setup", "setup_steps"): "setup_step",
    ("setup", "sdks"): "sdk",
    ("setup", "key_integrations"): "key_integration",
}
SCALAR_FIELDS = {  # (block, json_key) -> field label
    ("pricing", "free_plan"): "free_plan",
    ("pricing", "pricing_model_notes"): "pricing_model_notes",
    ("setup", "auth_method"): "auth_method",
    ("setup", "has_public_api"): "has_public_api",
}
gt_rows = []
for p in sorted((E / "ground-truth").glob("*.json")):
    d = json.load(open(p))
    dom = d["domain"]
    blocks = {"pricing": d.get("facts") or {}, "features": d.get("facts_features") or {},
              "setup": d.get("facts_setup") or {}}
    for block, obj in blocks.items():
        for key, items in obj.items():
            if (block, key) in LIST_FIELDS and isinstance(items, list):
                label = LIST_FIELDS[(block, key)]
                for item in items:
                    if isinstance(item, dict):  # e.g. a pricing plan record
                        text = " | ".join(f"{k}={v}" for k, v in item.items() if v not in (None, ""))
                    else:
                        text = str(item)
                    gt_rows.append({"domain": dom, "block": block, "field": label, "fact_text": text})
            elif (block, key) in SCALAR_FIELDS and items not in (None, ""):
                gt_rows.append({"domain": dom, "block": block, "field": SCALAR_FIELDS[(block, key)], "fact_text": str(items)})
with open(D / "ground_truth_facts.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["domain", "block", "field", "fact_text"])
    w.writeheader(); w.writerows(gt_rows)
print(f"ground_truth_facts.csv: {len(gt_rows)} rows, {len(gt_domains)} domains")
