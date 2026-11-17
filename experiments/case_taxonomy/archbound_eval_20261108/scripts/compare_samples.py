# Claude 2026-11-08: which of the 120 samples does archbound (v7.3-rc2, 3 scoped builds) touch, vs our boundary enumeration
import json, re, collections
SM = "/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/sample_match_v2.json"
P = json.load(open("/root/work/archbound/kernel/points.json"))["points"]
samples = json.load(open(SM))["samples"]
def locs(p):
    out = []
    for f in ("loc", "defs"):
        for x in p.get(f, []):
            m = re.match(r"(?:[a-z0-9_]+:)?(.+?):(\d+)", x)
            if m: out.append((m[1], int(m[2])))
    if p.get("commonCall"):
        m = re.match(r"(.+?):(\d+)", p["commonCall"]); out.append((m[1], int(m[2])))
    return out
names_of = lambda p: {p.get(k) for k in ("func", "missingCall", "global", "tracedFrom") if p.get(k)}
rows, cat_hits = [], collections.Counter()
for s in samples:
    ents = s.get("resolved_entities") or []
    names = {e["current_name"] for e in ents if e.get("current_name")}
    ranges = [(e["current_file"], r["start"], r["end"]) for e in ents for r in e.get("current_ranges", []) if e.get("current_file")]
    hit_cats = set()
    for p in P:
        cat = p["category"] + ("/" + p["subtype"] if p.get("subtype") else "")
        if names & names_of(p) or any(f == rf and a <= l <= b for f, l in locs(p) for rf, a, b in ranges):
            hit_cats.add(cat)
    ours_rv = s["architectures"]["riscv"]["hit"]; ours_any = s["hit"]
    rows.append((s["id"], s["check"], bool(hit_cats), ours_rv, ours_any, sorted(hit_cats)))
    for c in hit_cats: cat_hits[c] += 1
tot = collections.Counter(); 
for r in rows:
    tot[(r[1], "n")] += 1; tot[(r[1], "ab")] += r[2]; tot[(r[1], "rv")] += r[3]; tot[(r[1], "any")] += r[4]
    tot[(r[1], "both")] += r[2] and r[4]; tot[(r[1], "ab_only")] += r[2] and not r[4]; tot[(r[1], "ours_only")] += r[4] and not r[2]
print("check  n  archbound  ours_riscv  ours_3arch  both  archbound_only  ours_only")
for c in (1, 2, 3):
    print(c, tot[(c,"n")], tot[(c,"ab")], tot[(c,"rv")], tot[(c,"any")], tot[(c,"both")], tot[(c,"ab_only")], tot[(c,"ours_only")])
print("all", len(rows), sum(r[2] for r in rows), sum(r[3] for r in rows), sum(r[4] for r in rows), sum(r[2] and r[4] for r in rows), sum(r[2] and not r[4] for r in rows), sum(r[4] and not r[2] for r in rows))
print("archbound hits by category:", dict(cat_hits))
print("archbound-only:", [(r[0], r[5]) for r in rows if r[2] and not r[4]])
print("archbound hits:", [(r[0], r[1], r[5]) for r in rows if r[2]])
json.dump([dict(zip(("id","check","archbound_hit","ours_riscv_hit","ours_union_hit","archbound_categories"), r)) for r in rows],
          open("/root/work/archbound/kernel/sample_compare.json", "w"), indent=1)
