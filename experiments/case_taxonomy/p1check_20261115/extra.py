import sys, json; sys.path.insert(0,'.')
import evaluate as E, p1check as C
out={}
for c in ["bd1f2b2ace84","3faa3ebc89c1","65529295607f"]:
    files=[p for p in E.git("show","--name-only","--format=",c).split("\n") if p and C.in_scope(p)]
    rows=[]
    for p in files:
        for h in E.hunks(c,p):
            accs={m.group(1) for _,t in h[4] for m in C.ACC_RX.finditer(t)}
            if accs:
                r=E.score_hunk(c,p,h,accs)
                rows.append({"file":p,"accessors":sorted(accs),"funcs":r["funcs_parent"],"hit":r["hit"],"gone":r["gone_after_fix"],
                             "parent":[(x["func"],x["line"],x["accessor"],x["origin"]) for x in r["parent_findings"]]})
    out[c]=rows; print(c, [(r["file"],r["funcs"],r["hit"],r["gone"],r["parent"][:4]) for r in rows])
json.dump(out,open("extra_p1_codex.json","w"),indent=1)
