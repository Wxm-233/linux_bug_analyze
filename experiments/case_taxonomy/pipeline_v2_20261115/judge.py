"""Per kernel x mode x template: valid / violated counts over 3 runs (proprules criteria 五). python judge.py <tag>"""
import json
import re
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
tag = sys.argv[1]
agg, details = {}, {}
for f in sorted((HERE / "runs" / tag).glob("*.log")):
    m = re.match(r"(.+)_(plain|mte)\.run(\d)\.log", f.name)
    kt, mode, i = m.groups()
    text = re.sub(r"\x1b(c|\[[0-9;?]*[A-Za-z])", "", f.read_text(errors="replace"))  # amendment 2.3: terminal codes
    text = re.sub(r"\[\s*\d+\.\d+\][^\n]*\n", "", text)
    per = {}  # amendment 2.1: a run is valid if >=1 attempt is valid, violated if any valid attempt violated
    for l in text.splitlines():
        if not l.startswith('{"t"'):
            continue
        j = json.loads(l)
        p = per.setdefault(j["t"], {"valid": 0, "violated": 0, "attempts": 0})
        p["attempts"] += 1
        p["valid"] |= j["valid"]
        p["violated"] |= bool(j["valid"] and j["violated"])
        if (j["valid"] and j["violated"]) or not j["valid"]:
            details.setdefault((kt, mode, j["t"]), []).append(j["detail"])
    for t, p in per.items():
        a = agg.setdefault((kt, mode, t), {"runs": 0, "valid": 0, "violated": 0, "attempts": 0})
        a["runs"] += 1
        a["valid"] += p["valid"]
        a["violated"] += p["violated"]
        a["attempts"] += p["attempts"]
temps = sorted({k[2] for k in agg}, key=lambda t: (t[0] != "Z", t[0] != "T", t))
kms = sorted({(k[0], k[1]) for k in agg})
lines = ["kernel_mode".ljust(22) + " ".join(t.rjust(5) for t in temps)]
for km in kms:
    cells = []
    for t in temps:
        a = agg.get((km[0], km[1], t))
        cells.append("  -  " if not a else (f"{a['violated']}/{a['valid']}" + ("*" if a["valid"] < a["runs"] else "")).rjust(5))
    lines.append(f"{km[0]}_{km[1]}".ljust(22) + " ".join(cells))
lines.append("cell = violated/valid runs; * = some runs invalid")
lines.append("== violated or invalid details")
for k, v in sorted(details.items()):
    lines.append(f"{k}: {v[:3]}")
(HERE / f"judge_{tag}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
(HERE / f"judge_{tag}.json").write_text(json.dumps({f"{k[0]}|{k[1]}|{k[2]}": v for k, v in agg.items()}, indent=1), encoding="utf-8")
print("\n".join(lines))
