"""per candidate row: the law and every build's behaviour per protection constant for the example combination (WSL)"""
import json, sys
from collections import Counter
from pathlib import Path
HERE = Path(__file__).resolve().parent
D = Path("/root/work/ec_cache/r3/df2908090cda")
C = json.loads(Path("/root/work/ec_cache/r3/df2908090cda368b01ff43709f51890076c56157.json").read_text(encoding="utf-8"))["cands"]
laws = json.loads((D / "laws.json").read_text(encoding="utf-8"))
beh = {p.stem[4:]: json.loads(p.read_text(encoding="utf-8"))["laws"] for p in D.glob("beh_*.json")}
out = []
for i, c in enumerate(C, 1):
    p = c["example"].split("|")
    rec = {"id": f"E{i:02d}", "row": {k: c[k] for k in ("arch", "func", "file", "line", "locs", "class", "n", "builds", "example", "majority", "dom", "repro", "family")}}
    if p[0] == "SW":
        rec["law"] = laws.get(c["example"])
        rec["per_build"] = {b: (x.get(c["example"]) or {}).get("beh") for b, x in sorted(beh.items())}
    else:
        _, cons, prot, mod, obs = p
        rec["law"] = laws.get(f"PTX|{cons}|{mod}|{obs}")
        pb = {}
        for b, x in sorted(beh.items()):
            vals = {k.split("|")[2]: v["beh"] for k, v in x.items() if k.startswith(f"PT|{cons}|") and k.endswith(f"|{mod}|{obs}") and len(k.split("|")) == 5}
            if vals:
                pb[b] = dict(Counter(vals.values()))
                if b in c["builds"]:
                    pb[b] = vals
        rec["per_build"] = pb
    out.append(rec)
(HERE / "evidence.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
print(len(out))
