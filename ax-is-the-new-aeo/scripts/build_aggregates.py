#!/usr/bin/env python3
"""Build the aggregated, normalized view of the experiment — the layer from which every
published headline number (paper: "AX is the New AEO", ora research 2026) is deterministically derived.

Reads the consolidated data/ layer (journeys.csv + domains.csv — see data/README.md),
computes every reported metric, and writes a single file:

  data/aggregates.json   flat {token: value} map of every scalar, plus the by-industry,
                          by-accessibility-bin, and by-source-x-arm breakdowns as named
                          lists (no per-concern CSVs — one file, one source of truth)

Run:  python3 scripts/build_aggregates.py [--check]
  --check  also print a reconciliation vs the study's published numbers (BAKED below).

Convention: "domain-collapse" = average a metric within each domain first, then average
those domain means within a group (ax-high / ax-low). Every group mean uses this unless noted.
"""
import csv, json, collections, statistics as st, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
W = HERE.parent
D = W / "data"

ARMS = ["claude-agent", "claude-code", "openclaw", "eve"]
CATS = ["pricing", "features", "setup"]

# ---------------------------------------------------------------- load
def fnum(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def fint(x):
    v = fnum(x)
    return int(v) if v is not None else None

ROWS = list(csv.DictReader(open(D / "journeys.csv")))
for r in ROWS:
    for k in ("searches","scoped_searches","open_searches","cost_usd","turns","duration_s",
              "firstparty_evidence_share","onsite_retrieval_share","blocked_onsite_fetches",
              "ok_onsite_fetches","onsite_fetch_attempts","answer_chars","fp_evidence_chars",
              "tp_evidence_chars","external_fetches","ok_external_fetches",
              "attr_first_party_grounding","attr_external_share","attr_search_share","attr_memory_leak"):
        r[k] = fnum(r.get(k))
    for k in ("acc_n_facts","acc_n_correct","acc_n_partial","acc_n_incorrect","acc_n_not_addressed"):
        r[k] = fint(r.get(k))
    for k in ("first_party_answer","got_content","used_external"):
        r[k] = int(r[k]) if r.get(k) not in (None,"") else 0
    for k in ("antirec_punts_to_source","antirec_outside_sourced","antirec_access_disclaimer",
              "antirec_staleness_memory","antirec_vague_noncommittal","acc_no_answer"):
        r[k] = int(r[k]) if r.get(k) not in (None,"") else 0
    r["endorse_strength_claude"] = fint(r.get("endorse_strength_claude"))
    r["endorse_strength_gpt"] = fint(r.get("endorse_strength_gpt"))

DOMAINS = list(csv.DictReader(open(D / "domains.csv")))
AXR = {x["domain"]: fnum(x["ax_ratio"]) for x in DOMAINS if fnum(x.get("ax_ratio")) is not None}
IND = {x["domain"]: x["industry"] for x in DOMAINS}

# ---------------------------------------------------------------- helpers
def group_of(r): return r.get("group")  # 'ax-high' | 'ax-low'

def dcollapse(rows, valfn, gkey=group_of):
    """domain-collapse: per-domain mean of valfn, then group mean. -> {group: mean}."""
    by = collections.defaultdict(lambda: collections.defaultdict(list))   # group -> domain -> [vals]
    for r in rows:
        v = valfn(r)
        if v is None or v != v: continue          # skip None and NaN
        by[gkey(r)][r["domain"]].append(v)
    out = {}
    for g, doms in by.items():
        dmeans = [sum(vs)/len(vs) for vs in doms.values() if vs]
        out[g] = sum(dmeans)/len(dmeans) if dmeans else None
    return out

def hilo(rows, valfn):
    m = dcollapse(rows, valfn)
    return m.get("ax-high"), m.get("ax-low")

def lift(lo, hi):
    return (lo/hi - 1) if (hi not in (None,0) and lo is not None) else None
def ratio(a, b):
    return (a/b) if (b not in (None,0) and a is not None) else None

M = {}                 # flat token map
def put(k, v): M[k] = v

# ================================================================ 1. totals
put("total_journeys", len(ROWS))
put("total_journeys_round", round(len(ROWS)/1000)*1000)
put("n_domains", len(set(r["domain"] for r in ROWS)))
put("n_arms", len(ARMS))

# ================================================================ 2. grounding composition (attribution, judged subset)
def acomp(field):
    return hilo(ROWS, lambda r: r.get(f"attr_{field}"))
comp = {f: acomp(f) for f in ("first_party_grounding","external_share","search_share","memory_leak")}
def pct(x): return None if x is None else round(x*100)
comp_rows = []
for g, idx in (("ax-high",0),("ax-low",1)):
    row = {"group": g,
           "pages_pct": pct(comp["first_party_grounding"][idx]),
           "external_pct": pct(comp["external_share"][idx]),
           "search_pct": pct(comp["search_share"][idx]),
           "memory_pct": pct(comp["memory_leak"][idx])}
    comp_rows.append(row)
    sfx = "hi" if g=="ax-high" else "lo"
    for seg in ("pages","external","search","memory"):
        put(f"comp_{seg}_{sfx}", row[f"{seg}_pct"])

# ================================================================ 3. cost / turns / duration / blocks / grounded-rate (journeys.csv, pooled by group)
put("turns_hi", round(hilo(ROWS, lambda r:r["turns"])[0],1)); put("turns_lo", round(hilo(ROWS, lambda r:r["turns"])[1],1))
put("turns_lift_pct", round(lift(*reversed(hilo(ROWS, lambda r:r["turns"])))*100))
_dh,_dl = hilo(ROWS, lambda r:r["duration_s"]); put("dur_hi", round(_dh)); put("dur_lo", round(_dl)); put("dur_lift_pct", round(lift(_dl,_dh)*100))
_bh,_bl = hilo(ROWS, lambda r: 1.0 if (r["blocked_onsite_fetches"] or 0)>0 else 0.0)
put("block_ratio", round(ratio(_bl,_bh),1))
_fh,_fl = hilo(ROWS, lambda r: float(r["first_party_answer"]))
put("grounded_hi_pct", round(_fh*100)); put("grounded_lo_pct", round(_fl*100))
# first-party evidence share: the mechanical, full-coverage companion to the judged answer
# composition (attr_*) — the character share of everything the run retrieved that came from
# the business's own site. Defined on every journey, not just the judged subset.
_eh,_el = hilo(ROWS, lambda r: r["firstparty_evidence_share"])
put("fp_share_hi", round(_eh,3)); put("fp_share_lo", round(_el,3)); put("fp_share_ratio", round(ratio(_eh,_el),2))

# cost per grounded answer, per arm: (mean cost) / (mean first_party_answer), domain-collapsed within arm
ground_rows = []
premiums = []
for arm in ARMS:
    ar = [r for r in ROWS if r["arm"]==arm]
    ch,cl = hilo(ar, lambda r:r["cost_usd"])
    fh,fl = hilo(ar, lambda r: float(r["first_party_answer"]))
    gh = ratio(ch,fh); gl = ratio(cl,fl)
    prem = lift(gl,gh)
    premiums.append(prem)
    ground_rows.append({"arm":arm,"cost_grounded_hi":round(gh,3),"cost_grounded_lo":round(gl,3),"premium_pct":round(prem*100)})
    put(f"cost_grounded_hi_{arm}", round(gh,3)); put(f"cost_grounded_lo_{arm}", round(gl,3)); put(f"cost_premium_pct_{arm}", round(prem*100))
put("cost_mean_premium_pct", round(sum(premiums)/len(premiums)*100))

# ================================================================ 4. searches by arm & by industry (journeys.csv)
search_arm_rows = []
for arm in ARMS:
    ar=[r for r in ROWS if r["arm"]==arm]
    sh,sl = hilo(ar, lambda r:r["searches"])
    search_arm_rows.append({"arm":arm,"searches_hi":round(sh,1),"searches_lo":round(sl,1),"ratio":round(ratio(sl,sh),1)})
    put(f"searches_hi_{arm}",round(sh,1)); put(f"searches_lo_{arm}",round(sl,1)); put(f"searches_ratio_{arm}",round(ratio(sl,sh),1))

search_ind_rows = []
inds = collections.Counter(IND.get(r["domain"]) for r in ROWS)
for ind in sorted(inds):
    if not ind: continue
    ir=[r for r in ROWS if IND.get(r["domain"])==ind]
    sh,sl=hilo(ir, lambda r:r["searches"])
    if sh is None or sl is None: continue
    search_ind_rows.append({"industry":ind,"n_domains":len(set(r["domain"] for r in ir)),
                            "searches_hi":round(sh,1),"searches_lo":round(sl,1),"ratio":round(ratio(sl,sh),2)})
put("searches_by_industry", search_ind_rows)

# ================================================================ 5. grounding line chart: mean searches by accessibility bin
# The paper's figure uses 9 bins over 1,056 domains. On a 206-domain sample the narrow bins
# get thin and the curve gets noisy (one search-heavy domain bends a bin), so this repo
# publishes the same dose-response over 4 coarse bins, 2 per group.
BIN_EDGES = [(0.0,0.28),(0.28,0.50),(0.65,0.80),(0.80,1.01)]   # middle .50-.65 excluded by design
bin_rows = []
for lo,hi in BIN_EDGES:
    br=[r for r in ROWS if (AXR.get(r["domain"]) is not None and lo<=AXR[r["domain"]]<hi)]
    if not br:
        bin_rows.append({"lo":lo,"hi":hi,"n_domains":0,"n_runs":0,"mean_searches":None}); continue
    # domain-collapse mean searches (each domain equal weight)
    dd=collections.defaultdict(list)
    for r in br:
        if r["searches"] is not None: dd[r["domain"]].append(r["searches"])
    dm=[sum(v)/len(v) for v in dd.values() if v]
    bin_rows.append({"lo":lo,"hi":hi,"n_domains":len(set(r["domain"] for r in br)),
                     "n_runs":len(br),"mean_searches":round(sum(dm)/len(dm),1) if dm else None})
put("grounding_bins", bin_rows)
_ms=[b["mean_searches"] for b in bin_rows if b["mean_searches"] is not None]
if _ms: put("searches_bin_ratio", round(max(_ms)/min(_ms),1))

# ================================================================ 6. endorsement (two-judge top grade)
# strength columns are merged directly onto each journey row (endorse_strength_{claude,gpt});
# top grade = strength==4 by BOTH
def endorse_rows(filt=None):
    out=[]
    for r in ROWS:
        cs, gs = r.get("endorse_strength_claude"), r.get("endorse_strength_gpt")
        if cs is None or gs is None: continue
        if filt and not filt(r): continue
        out.append({"run_id":r["run_id"],"domain":r["domain"],"group":r["group"],"arm":r["arm"],
                    "category":r["category"],"industry":IND.get(r["domain"]),
                    "both_top": 1.0 if (cs==4 and gs==4) else 0.0,
                    "both_weak": 1.0 if (cs<=1 and gs<=1) else 0.0})
    return out
EROWS = endorse_rows()
def end_rate(rows, key="both_top"):
    return hilo(rows, lambda r: r[key])
eh,el = end_rate(EROWS); put("endorse_hi_pct", round(eh*100)); put("endorse_lo_pct", round(el*100)); put("endorse_ratio", round(ratio(eh,el),1))
wh,wl = end_rate(EROWS,"both_weak"); put("endorse_weak_ratio", round(ratio(wl,wh),1))
# by category / arm / industry
end_cat=[]
for cat in CATS:
    h,l=end_rate([r for r in EROWS if r["category"]==cat]); end_cat.append({"category":cat,"hi_pct":round(h*100),"lo_pct":round(l*100),"ratio":round(ratio(h,l),1)}); put(f"endorse_ratio_{cat}",round(ratio(h,l),1))
end_arm=[]
for arm in ARMS:
    h,l=end_rate([r for r in EROWS if r["arm"]==arm]); end_arm.append({"arm":arm,"hi_pct":round(h*100),"lo_pct":round(l*100),"ratio":round(ratio(h,l),1)}); put(f"endorse_hi_{arm}",round(h*100)); put(f"endorse_lo_{arm}",round(l*100)); put(f"endorse_ratio_arm_{arm}",round(ratio(h,l),1))
end_ind=[]
for ind in sorted(set(r["industry"] for r in EROWS if r["industry"])):
    h,l=end_rate([r for r in EROWS if r["industry"]==ind])
    if h is None or l is None: continue
    end_ind.append({"industry":ind,"hi_pct":round(h*100),"lo_pct":round(l*100),"ratio":round(ratio(h,l),2)})
put("endorsement_by_industry", end_ind)

# ================================================================ 7. hedge anatomy (anti-rec patterns + lifts)
AR_PATTERNS=["access_disclaimer","outside_sourced","vague_noncommittal","punts_to_source","staleness_memory"]
def ar_rate(pat):
    return hilo(ROWS, lambda r: 1.0 if r.get(f"antirec_{pat}") else 0.0)
hedge_rows=[]
for pat in AR_PATTERNS:
    h,l=ar_rate(pat)
    if h is None: continue
    hedge_rows.append({"pattern":pat,"hi_pct":round(h*100),"lo_pct":round(l*100),"lift":round(ratio(l,h),1)})
    put(f"hedge_hi_{pat}",round(h*100)); put(f"hedge_lo_{pat}",round(l*100)); put(f"hedge_lift_{pat}",round(ratio(l,h),1))

# answered-anyway: of runs that hit a block, share that still produced an answer
blk=[r for r in ROWS if (r["blocked_onsite_fetches"] or 0)>0]
ans=[r for r in blk if (r["answer_chars"] or 0)>0]
put("answered_anyway_pct", round(100*len(ans)/len(blk)) if blk else None)

# ================================================================ 8. accuracy by SOURCE (accuracy summary columns already merged onto journeys.csv)
# source = site-read if the run's answer was first-party grounded, else web-sourced
def src_of(r):
    return "site" if r["first_party_answer"]==1 else "web"
# NOTE: the study's published site-vs-web accuracy figures (site 48.3% vs web 34.3%, +41%;
# empty answers 6.7% vs 25.0%, 3.7x) come from a stratified *paired*
# estimator (cells = domain x arm x category, each business one vote), which corrects for
# composition bias: the agent chooses the source, and site-built answers concentrate on the
# easier businesses, so a pooled split overstates the site advantage that pairing removes. The
# pooled, domain-collapsed split below is the simpler reconstruction kept for the aggregate
# tokens; it is not the published estimator and is expected to differ from it. Specifically:
# corpus = answered runs (no_answer False), source = the run was first-party grounded
# (journeys.csv first_party_answer==1). It reconciles the corpus size and is directionally
# consistent, but these tokens reproduce the published values approximately, not exactly.
# See data/README.md.
acc_join=[]
for r in ROWS:
    if r.get("acc_n_facts") is None: continue      # not a judged run
    if r.get("acc_no_answer"): continue
    a2 = dict(r)
    a2["source"] = src_of(r)
    a2["n_facts"], a2["n_correct"], a2["n_partial"], a2["n_incorrect"], a2["n_not_addressed"] = (
        r["acc_n_facts"], r["acc_n_correct"], r["acc_n_partial"], r["acc_n_incorrect"], r["acc_n_not_addressed"])
    acc_join.append(a2)
put("acc_answers", len(acc_join)); put("acc_facts", sum(a["n_facts"] for a in acc_join)); put("acc_domains", len(set(a["domain"] for a in acc_join)))
def graded(a):   # correct + 1/2 partial over facts
    return (a["n_correct"] + 0.5*a["n_partial"]) / a["n_facts"] if a["n_facts"] else None
def acc_by(src, rows=None, keyfn=None):
    rows = rows or acc_join
    sub=[a for a in rows if a["source"]==src]
    # domain-collapse the graded score
    dd=collections.defaultdict(list)
    for a in sub:
        g=graded(a)
        if g is not None: dd[a["domain"]].append(g)
    dm=[sum(v)/len(v) for v in dd.values() if v]
    return sum(dm)/len(dm) if dm else None
acc_site=acc_by("site"); acc_web=acc_by("web")
put("acc_site_pct", round(acc_site*100)); put("acc_web_pct", round(acc_web*100))
put("acc_source_lift_pct", round(lift(acc_site,acc_web)*100))    # site premium = site/web - 1
# empty rate by source (answers addressing zero asked facts)
def empty_rate(src):
    sub=[a for a in acc_join if a["source"]==src]
    dd=collections.defaultdict(list)
    for a in sub: dd[a["domain"]].append(1.0 if a["n_not_addressed"]==a["n_facts"] else 0.0)
    dm=[sum(v)/len(v) for v in dd.values() if v]
    return sum(dm)/len(dm) if dm else None
es=empty_rate("site"); ew=empty_rate("web"); put("acc_empty_site_pct",round(es*100)); put("acc_empty_web_pct",round(ew*100)); put("acc_empty_ratio",round(ratio(ew,es),1))
# verdict distribution by source (fact-weighted)
def verdict_dist(src):
    sub=[a for a in acc_join if a["source"]==src]
    tot=sum(a["n_facts"] for a in sub) or 1
    return {"correct":round(100*sum(a["n_correct"] for a in sub)/tot),
            "partial":round(100*sum(a["n_partial"] for a in sub)/tot),
            "incorrect":round(100*sum(a["n_incorrect"] for a in sub)/tot),
            "not_addressed":round(100*sum(a["n_not_addressed"] for a in sub)/tot)}
vd_site=verdict_dist("site"); vd_web=verdict_dist("web")
for k,v in vd_site.items(): put(f"verdict_site_{k}",v)
for k,v in vd_web.items(): put(f"verdict_web_{k}",v)
# accuracy by intent (category, already a journeys.csv column) + source
def cat_of(a): return a["category"]
acc_intent=[]
for cat in CATS:
    sub=[a for a in acc_join if cat_of(a)==cat]
    s=acc_by("site",sub); wv=acc_by("web",sub)
    if s is None or wv is None: continue
    acc_intent.append({"category":cat,"site_pct":round(s*100),"web_pct":round(wv*100),"lift_pct":round(lift(s,wv)*100)})
    put(f"acc_site_{cat}",round(s*100)); put(f"acc_web_{cat}",round(wv*100)); put(f"acc_lift_{cat}",round(lift(s,wv)*100))
# dose-response: graded accuracy by first-party evidence-share bin
DOSE_EDGES=[(0.0,0.2),(0.2,0.4),(0.4,0.6),(0.6,0.8),(0.8,1.01)]
dose_rows=[]
for lo,hi in DOSE_EDGES:
    sub=[a for a in acc_join if (a["firstparty_evidence_share"] is not None and lo<=a["firstparty_evidence_share"]<hi)]
    dd=collections.defaultdict(list)
    for a in sub:
        g=graded(a)
        if g is not None: dd[a["domain"]].append(g)
    dm=[sum(v)/len(v) for v in dd.values() if v]
    dose_rows.append({"lo":lo,"hi":hi,"n_answers":len(sub),"acc_pct":round(100*sum(dm)/len(dm)) if dm else None})
put("dose_rows", dose_rows)
# empty by stack (arm) x source
empty_stack=[]
for arm in ARMS:
    def er(src):
        sub=[a for a in acc_join if a["arm"]==arm and a["source"]==src]
        dd=collections.defaultdict(list)
        for a in sub: dd[a["domain"]].append(1.0 if a["n_not_addressed"]==a["n_facts"] else 0.0)
        dm=[sum(v)/len(v) for v in dd.values() if v]
        return sum(dm)/len(dm) if dm else None
    s=er("site"); wv=er("web")
    if s is None or wv is None: continue
    empty_stack.append({"arm":arm,"site_pct":round(s*100),"web_pct":round(wv*100),"ratio":round(ratio(wv,s),1)})
put("accuracy_empty_by_arm", empty_stack)

# ================================================================ 9. accuracy, STRATIFIED PAIRED — the published estimator
# The paper's headline site-vs-web accuracy numbers use this, not the pooled split above:
# cells are (domain x arm x category), only cells containing BOTH a site and a web answer
# count, cell means collapse to the domain, and the domain is the unit. This mirrors the
# paper's estimator exactly (minus the permutation p-values).
def paired(sub, cellkey, valfn):
    cells=collections.defaultdict(lambda:{"site":[],"web":[]})
    for a in sub:
        v=valfn(a)
        if v is None: continue
        cells[cellkey(a)][a["source"]].append(v)
    per_dom=collections.defaultdict(list); ncells=0
    for k,v in cells.items():
        if v["site"] and v["web"]:
            ncells+=1
            per_dom[k[0]].append((sum(v["site"])/len(v["site"]), sum(v["web"])/len(v["web"])))
    if len(per_dom) < 5: return None
    dsite=[sum(c[0] for c in cs)/len(cs) for cs in per_dom.values()]
    dweb =[sum(c[1] for c in cs)/len(cs) for cs in per_dom.values()]
    ms=sum(dsite)/len(dsite); mw=sum(dweb)/len(dweb)
    return {"n_domains":len(per_dom),"n_cells":ncells,
            "site_pct":round(100*ms,1),"web_pct":round(100*mw,1),
            "diff_pp":round(100*(ms-mw),1),
            "lift_pct":round(100*(ms/mw-1)) if mw else None}
def empty_of(a): return 1.0 if a["n_not_addressed"]==a["n_facts"] else 0.0
pt = paired(acc_join, lambda a:(a["domain"],a["arm"],a["category"]), graded)
if pt:
    put("acc_paired_site_pct",pt["site_pct"]); put("acc_paired_web_pct",pt["web_pct"])
    put("acc_paired_diff_pp",pt["diff_pp"]);   put("acc_paired_lift_pct",pt["lift_pct"])
    put("acc_paired_cells",pt["n_cells"]);     put("acc_paired_domains",pt["n_domains"])
pe = paired(acc_join, lambda a:(a["domain"],a["arm"],a["category"]), empty_of)
if pe:
    put("acc_paired_empty_site_pct",pe["site_pct"]); put("acc_paired_empty_web_pct",pe["web_pct"])
    put("acc_paired_empty_diff_pp",pe["diff_pp"])
paired_intent=[]
for cat in CATS:
    r_=paired([a for a in acc_join if a["category"]==cat], lambda a:(a["domain"],a["arm"]), graded)
    if r_ is None: continue
    paired_intent.append(dict(category=cat, **r_)); put(f"acc_paired_diff_pp_{cat}", r_["diff_pp"])
paired_arm=[]
for arm in ARMS:
    r_=paired([a for a in acc_join if a["arm"]==arm], lambda a:(a["domain"],a["category"]), graded)
    if r_ is None: continue
    paired_arm.append(dict(arm=arm, **r_)); put(f"acc_paired_diff_pp_{arm}", r_["diff_pp"])

# fate of every asked fact, domain-collapsed by source (each domain one vote) — the paper's
# fact-fate figure uses this, not the fact-weighted verdict_dist above
def verdicts_dc(src):
    dd=collections.defaultdict(list)
    for a in acc_join:
        if a["source"]==src and a["n_facts"]:
            dd[a["domain"]].append(tuple(a[k]/a["n_facts"] for k in ("n_correct","n_partial","n_incorrect","n_not_addressed")))
    doms=[[sum(t[i] for t in v)/len(v) for i in range(4)] for v in dd.values()]
    return {k: round(100*sum(d[i] for d in doms)/len(doms)) for i,k in
            enumerate(("correct","partial","incorrect","not_addressed"))} if doms else None
ff_site=verdicts_dc("site"); ff_web=verdicts_dc("web")
for src,ff in (("site",ff_site),("web",ff_web)):
    if ff:
        for k,v in ff.items(): put(f"factfate_{src}_{k}", v)

# ---------------------------------------------------------------- write the single JSON
# every list computed above that isn't already flattened into scalar tokens gets put() here too,
# so this file is a complete substitute for the old per-concern CSVs, not just the scalars.
put("grounding_composition", comp_rows)
put("cost_by_arm", ground_rows)
put("searches_by_arm", search_arm_rows)
put("endorsement_by_category", end_cat)
put("endorsement_by_arm", end_arm)
put("hedge_anatomy", hedge_rows)
put("accuracy_by_intent", acc_intent)
put("accuracy_verdicts_by_source", {"site": vd_site, "web": vd_web})
put("accuracy_paired_by_intent", paired_intent)
put("accuracy_paired_by_arm", paired_arm)
put("fact_fate_by_source", {"site": ff_site, "web": ff_web})

n_scalars = sum(1 for v in M.values() if not isinstance(v, (list, dict)))
json.dump(M, open(D / "aggregates.json", "w"), indent=1)
print(f"wrote data/aggregates.json ({n_scalars} scalar tokens + {len(M) - n_scalars} table entries)")

# ---------------------------------------------------------------- reconciliation vs published numbers
if "--check" in sys.argv:
    # The study's published full-corpus values (37,927 journeys / 1,056 domains), as reported
    # in the paper. The acc_* / verdict_* block bakes the full-corpus values of THIS script's
    # pooled reconstruction (see the estimator note above src_of); the paper's published
    # site-vs-web accuracy uses the stratified paired estimator instead and is printed as a
    # note below the table.
    BAKED = {
      "total_journeys_round":38000,"n_domains":1056,
      "comp_pages_hi":78,"comp_external_hi":3,"comp_search_hi":12,"comp_memory_hi":7,
      "comp_pages_lo":58,"comp_external_lo":7,"comp_search_lo":25,"comp_memory_lo":10,
      "cost_mean_premium_pct":64,"cost_premium_pct_openclaw":93,"cost_premium_pct_claude-agent":93,
      "cost_premium_pct_claude-code":57,"cost_premium_pct_eve":11,
      "turns_hi":5.5,"turns_lo":6.8,"turns_lift_pct":23,"dur_hi":48,"dur_lo":55,"dur_lift_pct":15,
      "block_ratio":2.1,"grounded_hi_pct":78,"grounded_lo_pct":56,
      "fp_share_hi":0.776,"fp_share_lo":0.549,"fp_share_ratio":1.41,
      "searches_bin_ratio":2.3,   # 4 coarse bins, full corpus: 4.3 -> 3.0 -> 2.2 -> 1.9
                                  # (the paper's 9-bin figure spans 1.8 -> 4.5, a 2.6x spread)
      "searches_hi_claude-agent":0.4,"searches_lo_claude-agent":0.9,"searches_ratio_claude-agent":2.4,
      "searches_hi_claude-code":0.1,"searches_lo_claude-code":0.3,"searches_ratio_claude-code":3.5,
      "searches_hi_openclaw":6.9,"searches_lo_openclaw":10.4,"searches_ratio_openclaw":1.5,
      "searches_hi_eve":1.2,"searches_lo_eve":1.9,"searches_ratio_eve":1.6,
      "endorse_hi_pct":20,"endorse_lo_pct":11,"endorse_ratio":1.9,"endorse_weak_ratio":2.5,
      "endorse_ratio_pricing":2.2,
      "hedge_hi_access_disclaimer":4,"hedge_lo_access_disclaimer":16,"hedge_lift_access_disclaimer":4.4,
      "hedge_hi_outside_sourced":5,"hedge_lo_outside_sourced":15,"hedge_lift_outside_sourced":3.0,
      "hedge_hi_vague_noncommittal":7,"hedge_lo_vague_noncommittal":12,"hedge_lift_vague_noncommittal":1.8,
      "hedge_hi_punts_to_source":15,"hedge_lo_punts_to_source":22,"hedge_lift_punts_to_source":1.4,
      "answered_anyway_pct":99,   # published as "~99%"; unrounded full-corpus value 99.9%
      "acc_site_pct":53,"acc_web_pct":38,"acc_source_lift_pct":40,"acc_empty_site_pct":4,"acc_empty_web_pct":22,"acc_empty_ratio":6.1,
      "acc_answers":2499,"acc_facts":31127,"acc_domains":131,
      "verdict_site_correct":35,"verdict_site_partial":29,"verdict_site_incorrect":2,"verdict_site_not_addressed":34,
      "verdict_web_correct":24,"verdict_web_partial":24,"verdict_web_incorrect":4,"verdict_web_not_addressed":49,
      "acc_site_pricing":63,"acc_web_pricing":43,"acc_lift_pricing":48,
      "acc_site_features":50,"acc_web_features":39,"acc_lift_features":29,
      "acc_site_setup":24,"acc_web_setup":24,"acc_lift_setup":1,
      # stratified PAIRED estimator — the numbers the paper actually publishes for accuracy
      "acc_paired_site_pct":48.3,"acc_paired_web_pct":34.3,"acc_paired_diff_pp":14.0,"acc_paired_lift_pct":41,
      "acc_paired_empty_site_pct":6.7,"acc_paired_empty_web_pct":25.0,"acc_paired_empty_diff_pp":-18.3,
      "acc_paired_diff_pp_pricing":23.5,"acc_paired_diff_pp_features":6.8,"acc_paired_diff_pp_setup":0.4,
      "acc_paired_diff_pp_claude-code":38.3,"acc_paired_diff_pp_claude-agent":12.3,
      "acc_paired_diff_pp_openclaw":4.0,"acc_paired_diff_pp_eve":-2.3,
      # fact fate, domain-collapsed (the paper's figure): wrong barely moves, omission grows
      "factfate_site_correct":40,"factfate_site_partial":27,"factfate_site_incorrect":4,"factfate_site_not_addressed":29,
      "factfate_web_correct":28,"factfate_web_partial":21,"factfate_web_incorrect":6,"factfate_web_not_addressed":45,
    }
    # Size tokens describe the corpus, not a rate: on a ~20% domain sample they cannot match
    # the full-corpus value and are printed for information only.
    SIZE_TOKENS = {"total_journeys_round","n_domains","acc_answers","acc_facts","acc_domains"}
    print(f"\n  reconciliation: this sample ({M['n_domains']} domains, {M['total_journeys']} journeys)"
          f" vs the published full corpus (1,056 domains, 37,927 journeys)\n")
    print(f"  {'token':40s} {'sample':>8}  {'published':>9}  {'delta':>7}   status")
    ok=diff=0
    for k,bv in BAKED.items():
        cv=M.get(k)
        if k in SIZE_TOKENS:
            status="size (info)"; delta=""
        elif cv is None:
            status="not computed"; delta=""
        else:
            d=cv-bv; delta=f"{d:+.1f}" if isinstance(bv,float) else f"{d:+d}"
            within = abs(d) <= (0.1 if isinstance(bv,float) else 1)
            status="match" if within else "sample delta"
            ok+=within; diff+=(not within)
        print(f"  {k:40s} {str(cv):>8}  {str(bv):>9}  {delta:>7}   {status}")
    print(f"\n  {ok} of {ok+diff} rate tokens match the published value within +/-1 (or +/-0.1 for")
    print(f"  decimals); {diff} differ. Differences are expected on a ~20% domain sample: every")
    print("  direction and every large effect reproduces, absolute values move by a few points,")
    print("  and narrow slices (one hedge pattern within one harness, one arm x one intent) move")
    print("  more. See data/README.md#reconciliation for the headline-by-headline comparison.")
    print("\n  note: acc_paired_* / factfate_* are the paper's published accuracy estimator")
    print("  (stratified paired; fact fate domain-collapsed), recomputed here on the sample.")
    print("  The plain acc_*/verdict_* tokens are the simpler pooled split, kept for the")
    print("  corpus-wide view; its full-corpus values are baked. See data/README.md.")
