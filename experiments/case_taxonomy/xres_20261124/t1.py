import sys, json, gzip
sys.path.insert(0, ".")
import xres as X
entries = json.load(gzip.open(X.LB / "funcs.json.gz", "rt"))
edges = json.load(gzip.open(X.LB / "edges.json.gz", "rt"))["direct"]
js, n = X.jobs_for("riscv", edges, entries)
print("jobs", len(js), "callers", n)
job = [j for j in js if j[1]["file"].endswith("/mm/mprotect.c")][0]
b, u, sites = X.one(job)
print(u, len(sites))
for s in sites:
    if s["F"] in ("change_pud_range",) :
        print(json.dumps(s, ensure_ascii=False))
