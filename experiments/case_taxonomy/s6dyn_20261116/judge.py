"""s6dyn criteria 四: per cell -> valid / anomalous runs, verdict.   python judge.py <tag> -> judge_<tag>.{json,txt}"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
tag = sys.argv[1]
ANOM = re.compile(r"WARNING:|BUG:|Oops|Unable to handle|Kernel panic", re.I)
res = {}
for f in sorted((HERE / "runs" / tag).glob("*.log")):
    name, i = re.match(r"(.+)\.run(\d)\.log", f.name).groups()
    lines = re.sub(r"\x1b(c|\[[0-9;?]*[A-Za-z])", "", f.read_text(errors="replace")).splitlines()
    start = next((k for k, l in enumerate(lines) if '{"t":"S6start"' in l), len(lines))
    phase = [l.strip()[:220] for l in lines[start:] if not l.lstrip().startswith("{")]
    anom = [l for l in phase if ANOM.search(l)]
    xa = [l for l in phase if "lib/xarray.c" in l or "xas_split_alloc" in l]
    recs = {}
    for l in lines:
        m = re.search(r"\{\"t\":.*\}", l)
        if m:
            try:
                j = json.loads(m.group(0))
                recs[j["t"]] = j
            except json.JSONDecodeError:
                pass
    env, a, b, s = recs.get("ENV") or {}, recs.get("S6a"), recs.get("S6b"), recs.get("S6")
    valid = bool(env.get("zram_swap") == 0 and env.get("mode_ok") and a)
    bad = (s or {}).get("bad", 0) or 0
    row = {"run": i, "valid": int(valid), "anomalous": bool(valid and (anom or bad)), "env": env, "S6a": a, "S6b": b,
           "bad": bad, "anom": anom[:4], "xarray": xa[:3], "end": any("@@END" in l for l in lines)}
    res.setdefault(name, []).append(row)


def verdict(rows):
    v = [x for x in rows if x["valid"]]
    n = sum(x["anomalous"] for x in v)
    if len(v) < 2:
        return "无效", len(v), n
    if n >= 2:
        return "复现", len(v), n
    return ("不复现" if n == 0 else "不稳定"), len(v), n


L, out = [], {}
for name, rows in sorted(res.items()):
    out[name] = {"verdict": verdict(rows), "whole_pmd_folio_runs": sum(1 for x in rows if (x["S6a"] or {}).get("whole_pmd_folio")),
                 "runs": rows}
    L.append(f"{name}: {out[name]['verdict']} whole_pmd_folio={out[name]['whole_pmd_folio_runs']}")
    for x in rows:
        L.append(f"   run{x['run']} valid={x['valid']} mode={x['env'].get('selected')} S6a={x['S6a']} S6b={x['S6b']} bad={x['bad']} end={x['end']}")
        for l in x["anom"]:
            L.append(f"      {l}")
(HERE / f"judge_{tag}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
(HERE / f"judge_{tag}.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
