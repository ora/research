#!/usr/bin/env python3
"""Build the aggregated, normalized view of the experiment — the layer from which every
published headline number (paper forthcoming) is deterministically derived.

Reads the consolidated data/ layer (journeys.csv + domains.csv — see data/README.md for how
these were consolidated from the original per-file layout), computes every reported metric,
and writes a single file:

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

ARMS = ["vanilla-claude-agent", "vanilla-claude-code", "vanilla-openclaw", "deep-eve-gpt5.4"]
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
BIN_EDGES = [(0.0,0.15),(0.15,0.28),(0.28,0.38),(0.38,0.45),(0.45,0.50),
             (0.65,0.73),(0.73,0.80),(0.80,0.87),(0.87,1.01)]   # middle .50-.65 excluded by design
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
# NOTE: the study's published site-vs-web accuracy figures come from a stratified *paired*
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

n_scalars = sum(1 for v in M.values() if not isinstance(v, (list, dict)))
json.dump(M, open(D / "aggregates.json", "w"), indent=1)
print(f"wrote data/aggregates.json ({n_scalars} scalar tokens + {len(M) - n_scalars} table entries)")

# ---------------------------------------------------------------- reconciliation vs published numbers
if "--check" in sys.argv:
    BAKED = {
      "total_journeys_round":38000,"n_domains":1058,
      "comp_pages_hi":78,"comp_external_hi":3,"comp_search_hi":12,"comp_memory_hi":7,
      "comp_pages_lo":58,"comp_external_lo":7,"comp_search_lo":25,"comp_memory_lo":10,
      "cost_mean_premium_pct":63,"cost_premium_pct_vanilla-openclaw":92,"cost_premium_pct_vanilla-claude-agent":92,
      "cost_premium_pct_vanilla-claude-code":55,"cost_premium_pct_deep-eve-gpt5.4":11,
      "turns_hi":5.5,"turns_lo":6.8,"turns_lift_pct":23,"dur_hi":48,"dur_lo":55,"dur_lift_pct":15,
      "block_ratio":2.1,"grounded_hi_pct":78,"grounded_lo_pct":56,
      "searches_hi_vanilla-claude-agent":0.4,"searches_lo_vanilla-claude-agent":0.9,"searches_ratio_vanilla-claude-agent":2.4,
      "searches_hi_vanilla-claude-code":0.1,"searches_lo_vanilla-claude-code":0.3,"searches_ratio_vanilla-claude-code":3.3,
      "searches_hi_vanilla-openclaw":6.9,"searches_lo_vanilla-openclaw":10.4,"searches_ratio_vanilla-openclaw":1.5,
      "searches_hi_deep-eve-gpt5.4":1.2,"searches_lo_deep-eve-gpt5.4":1.9,"searches_ratio_deep-eve-gpt5.4":1.6,
      "endorse_hi_pct":20,"endorse_lo_pct":11,"endorse_ratio":1.9,"endorse_weak_ratio":2.4,
      "endorse_ratio_pricing":2.2,
      "hedge_hi_access_disclaimer":4,"hedge_lo_access_disclaimer":16,"hedge_lift_access_disclaimer":4.3,
      "hedge_hi_outside_sourced":5,"hedge_lo_outside_sourced":15,"hedge_lift_outside_sourced":2.9,
      "hedge_hi_vague_noncommittal":7,"hedge_lo_vague_noncommittal":12,"hedge_lift_vague_noncommittal":1.8,
      "hedge_hi_punts_to_source":15,"hedge_lo_punts_to_source":22,"hedge_lift_punts_to_source":1.4,
      "answered_anyway_pct":99,
      "acc_site_pct":None,"acc_web_pct":None,"acc_source_lift_pct":25,"acc_empty_site_pct":3,"acc_empty_web_pct":11,"acc_empty_ratio":3.4,
      "acc_answers":2426,"acc_facts":30633,"acc_domains":131,
      "verdict_site_correct":38,"verdict_site_partial":29,"verdict_site_incorrect":3,"verdict_site_not_addressed":30,
      "verdict_web_correct":30,"verdict_web_partial":23,"verdict_web_incorrect":7,"verdict_web_not_addressed":40,
      "acc_site_pricing":66,"acc_web_pricing":55,"acc_lift_pricing":21,
      "acc_site_features":52,"acc_web_features":38,"acc_lift_features":36,
      "acc_site_setup":26,"acc_web_setup":18,"acc_lift_setup":42,
    }
    print("\n  token                                    computed   baked   ok")
    ok=bad=0
    for k,bv in BAKED.items():
        cv=M.get(k)
        if bv is None: status="·(info)";
        else:
            match = cv is not None and abs(cv-bv) <= (0.1 if isinstance(bv,float) else 1)
            status="OK" if match else "**MISS**"
            ok+=match; bad+=(not match)
        print(f"  {k:40s} {str(cv):>8}  {str(bv):>6}   {status}")
    print(f"\n  matched {ok} / {ok+bad} checked baked values")
