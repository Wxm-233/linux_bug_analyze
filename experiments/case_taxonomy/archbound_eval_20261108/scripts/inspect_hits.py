import json, re
SM = "/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/sample_match_v2.json"
P = json.load(open("/root/work/archbound/kernel/points.json"))["points"]
S = {s["id"]: s for s in json.load(open(SM))["samples"]}
for sid in ["A123", "A303", "B494", "A192", "B558", "A118", "A274"]:
    s = S[sid]; ents = s["resolved_entities"]
    names = {e["current_name"] for e in ents}
    ranges = [(e["current_file"], r["start"], r["end"]) for e in ents for r in e.get("current_ranges", [])]
    print(f"== {sid} check{s['check']}: {s['subject'][:90]}")
    print("   entities:", sorted(names)[:6])
    for p in P:
        ns = {p.get(k) for k in ("func", "missingCall", "global", "tracedFrom") if p.get(k)}
        ls = []
        for f in ("loc", "defs"):
            for x in p.get(f, []):
                m = re.match(r"(?:[a-z0-9_]+:)?(.+?):(\d+)", x)
                if m: ls.append((m[1], int(m[2])))
        if p.get("commonCall"):
            m = re.match(r"(.+?):(\d+)", p["commonCall"]); ls.append((m[1], int(m[2])))
        if names & ns or any(f == rf and a <= l <= b for f, l in ls for rf, a, b in ranges):
            q = {k: v for k, v in p.items() if k not in ("archs",)}
            print("   ->", json.dumps(q, ensure_ascii=False)[:260])
