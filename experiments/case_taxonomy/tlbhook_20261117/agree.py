"""tlbhook criteria: raw agreement and Cohen's kappa (3 classes). python agree.py -> agreement.json"""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
a = {x["k"]: x for x in json.loads((HERE / "claude.json").read_text(encoding="utf-8"))}
b = {x["k"]: x for x in json.loads((HERE / "codex_blind/codex.json").read_text(encoding="utf-8"))}
ks = sorted(set(a) & set(b))
cls = ["可能", "不可能", "说不清"]
pairs = [(a[k]["verdict"], b[k]["verdict"]) for k in ks]
n = len(pairs)
po = sum(x == y for x, y in pairs) / n
ca, cb = Counter(x for x, _ in pairs), Counter(y for _, y in pairs)
pe = sum(ca[c] * cb[c] for c in cls) / (n * n)
kappa = (po - pe) / (1 - pe) if pe < 1 else None
dis = [{"k": k, "loc": a[k]["loc"], "claude": a[k]["verdict"], "codex": b[k]["verdict"]} for k in ks if a[k]["verdict"] != b[k]["verdict"]]
both_possible = [k for k in ks if a[k]["verdict"] == b[k]["verdict"] == "可能"]
out = {"n": n, "missing": sorted(set(a) ^ set(b)), "raw_agreement": round(po, 3), "kappa": None if kappa is None else round(kappa, 3),
       "claude": dict(ca), "codex": dict(cb), "disagreements": dis, "both_possible": both_possible,
       "note": "kappa is undefined/degenerate when one annotator uses a single class"}
(HERE / "agreement.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=1))
