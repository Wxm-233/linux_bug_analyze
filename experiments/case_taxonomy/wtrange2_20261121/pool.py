"""post-freeze statistic (not a gate): frozen range analysis over every covered unreviewed WT entry. WSL.
    python3 pool.py -> pool_rng.json + summary
"""
import json, sys
from collections import Counter
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind2 as B2
import rng as R
import blind
B = B2.B
blind.check_frozen()
out = []
for r in B.unreviewed():
    us = B2.units(r["file"], r["func"])
    if not us:
        continue
    src_text = B2.git("show", f"{B.REV}:{r['file']}")
    per = {}
    for b, tu in us:
        e = B.ccdb(b)[tu]; orig = B.ccdb(b).get(r["file"]); B.ccdb(b)[r["file"]] = e
        try:
            fn, diag = B.ast_of(b, r["file"], r["func"])
        finally:
            if orig is None: del B.ccdb(b)[r["file"]]
            else: B.ccdb(b)[r["file"]] = orig
        if fn:
            per[b] = [dict(x, sig=s) for s in dict.fromkeys(r["sigs"]) for x in R.status_for(fn, r["file"], r["line"], s, src_text)]
    out.append({"id": r["id"], "overall": R.overall(per), "per_build": per})
(HERE / "pool_rng.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
c = Counter(x["overall"] for x in out)
conv = Counter(c2["status"] for x in out for cs in x["per_build"].values() for c2 in cs)
print(json.dumps({"entries": len(out), "overall": dict(c), "conversions": dict(conv)}, ensure_ascii=False))
