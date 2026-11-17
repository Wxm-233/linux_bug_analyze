"""s5dyn criteria 四: per kernel -> valid / anomalous runs, verdict.   python judge.py <tag>  -> judge_<tag>.{json,txt}"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
tag = sys.argv[1]
S5WARN = re.compile(r"WARNING:.*mm/internal\.h:42[02]")
CRASH = re.compile(r"Oops|Unable to handle|BUG:|Kernel panic", re.I)
OTHER = re.compile(r"Bad swap|WARNING:", re.I)
res = {}
for f in sorted((HERE / "runs" / tag).glob("*.log")):
    name, i = re.match(r"(.+)\.run(\d)\.log", f.name).groups()
    text = re.sub(r"\x1b(c|\[[0-9;?]*[A-Za-z])", "", f.read_text(errors="replace"))
    lines = text.splitlines()
    start = next((k for k, l in enumerate(lines) if '{"t":"S5start"' in l), len(lines))
    phase = [l.strip()[:220] for l in lines[start:] if not l.lstrip().startswith("{")]
    s5warn = [l for l in phase if S5WARN.search(l)]
    crash = [l for l in phase if CRASH.search(l)]
    other = [l for l in phase if OTHER.search(l) and not S5WARN.search(l)]
    recs = {}
    for l in lines:
        m = re.search(r"\{\"t\":.*\}", l)
        if m:
            try:
                j = json.loads(m.group(0))
                recs[j["t"]] = j
            except json.JSONDecodeError:
                pass
    a, pre, s5, hang = recs.get("S5a"), recs.get("S5pre"), recs.get("S5"), recs.get("S2hang")   # amendment 1
    row = {"run": i, "s5warn": s5warn[:3], "n_s5warn": len(s5warn), "crash": crash[:3], "other": sorted(set(other))[:3],
           "end": "@@END" in text, "hang": bool(hang), "tries": (recs.get("S5tries") or {}).get("tries")}
    p = pre or a
    if p:
        setup = p["ahp_before"] >= 2048 and p["exclusive"] == 0 and '"30"' in json.dumps(p["before"]["ex_types"]) and p["large"]
        reached = bool(s5warn or crash) or (a is not None and (a["after"]["present"] < 504 or a["after"]["ex_types"] != p["before"]["ex_types"]))
        valid = setup and reached
        row.update({"valid": int(valid), "setup": int(setup), "reached": int(reached), "anomalous": bool(valid and (s5warn or crash)),
                    "ahp": [p["ahp_before"], p["ahp_after_ex"]], "large": p["large"], "kpf0": p["kpf0"], "before": p["before"],
                    "after": (a or {}).get("after"), "reclaim": (a or {}).get("reclaim"),
                    "bad_pages": (s5 or {}).get("bad_pages"), "sigbus": (s5 or {}).get("sigbus")})
    else:
        row.update({"valid": 0, "anomalous": False, "why": (s5 or {}).get("why", "no S5pre/S5a record"), "child": recs.get("CHILD")})
    res.setdefault(name, []).append(row)


def verdict(rows):
    v = [x for x in rows if x["valid"]]
    a = sum(x["anomalous"] for x in v)
    if len(v) < 2:
        return "无效", len(v), a
    if a >= 2:
        return "复现", len(v), a
    if a == 0:
        return "不复现", len(v), a
    return "不稳定", len(v), a


L, out = [], {}
for name, rows in sorted(res.items()):
    out[name] = {"verdict": verdict(rows), "runs": rows}
    L.append(f"{name}: {out[name]['verdict']}")
    for x in rows:
        if "before" in x:
            L.append(f"   run{x['run']} valid={x['valid']} setup={x['setup']} reached={x['reached']} tries={x['tries']} ahp={x['ahp']} "
                     f"large={x['large']} before={x['before']} after={x['after']} bad={x['bad_pages']} bus={x['sigbus']} "
                     f"hang={x['hang']} s5warn={x['n_s5warn']} crash={len(x['crash'])}")
        else:
            L.append(f"   run{x['run']} invalid: {x.get('why')} {x.get('child', '')}")
        for k in ("s5warn", "crash", "other"):
            if x[k]:
                L.append(f"      {k}: " + " | ".join(x[k]))
(HERE / f"judge_{tag}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
(HERE / f"judge_{tag}.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
