"""which candidate / which fix produced each new alignment under C (diagnostic only)"""
import json, sys
from pathlib import Path
sys.setrecursionlimit(20000)
import archsig as A
HERE = Path(__file__).resolve().parent
res = json.loads((HERE / "results.json").read_text())
ds = A.datasets()
for name in ("dev", "heldout"):
    items = {A.M.full(it["commit"])[:12]: it for it in ds[name]["positives"]}
    for r in res[name]["rows"]:
        if r["kind"] != "pos" or not (r.get("alC") and not r.get("alA")):
            continue
        it = items[r["commit"]]
        old = {fn for _, fn in it.get("fix_funcs", [])}
        print("==", name, r["info"][:70], "| dataset fixes", it.get("fixes"))
        cands = r["old_new"] + r["expand"]
        for f in A.fixes_for(A.M.full(it["commit"]))[:12]:
            fns = {fn for _, fn in A.DSET.touched_funcs(f)}
            hit = [c for c in cands if c["func"] in fns and c["func"] not in old]
            if hit:
                subj = A.M.git("log", "-1", "--format=%h %s", f).strip()
                for c in hit[:4]:
                    print("   fix", subj[:80], "<-", c["engine"], c["file"], c["func"], c["sig"][:60], "expand" if c.get("expand") else "")
