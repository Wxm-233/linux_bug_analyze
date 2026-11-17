"""s4dyn criteria 四: per kernel x MGLRU mode -> valid / anomalous runs, verdict (S2 rules of p1dyn).
    python judge.py <tag>  -> judge_<tag>.{json,txt}"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
tag = sys.argv[1]
KERR = re.compile(r"Bad swap|BUG[: ]|WARNING:|Oops|Unable to handle|Kernel panic", re.I)
res = {}
for f in sorted((HERE / "runs" / tag).glob("*.log")):
    name, i = re.match(r"(.+)\.run(\d)\.log", f.name).groups()
    text = re.sub(r"\x1b(c|\[[0-9;?]*[A-Za-z])", "", f.read_text(errors="replace"))
    lines = text.splitlines()
    start = next((k for k, l in enumerate(lines) if '{"t":"MGLRU"' in l), len(lines))   # only the test phase counts
    kerr = [l.strip()[:200] for l in lines[start:] if KERR.search(l) and not l.lstrip().startswith("{")]
    boot_kerr = [l.strip()[:200] for l in lines[:start] if KERR.search(l)]
    recs = {}
    for l in lines:
        m = re.search(r"\{\"t\":.*\}", l)
        if m:
            try:
                j = json.loads(m.group(0))
                recs[j["t"]] = j
            except json.JSONDecodeError:
                pass
    r = res.setdefault(name, {"runs": []})
    mg, s2a, s2, hang = recs.get("MGLRU"), recs.get("S2a"), recs.get("S2"), recs.get("S2hang")
    row = {"run": i, "env": recs.get("ENV"), "mglru": mg, "kerr": kerr, "boot_kerr": boot_kerr, "end": "@@END" in text}
    mg_ok = bool(mg) and mg["want"] in (0, 1) and mg["on"] == mg["want"]
    if s2a and "after" in s2a:
        bad_types = {t: n for t, n in s2a["after"]["types"].items() if t not in ("0", "30")}
        bad_pages = (s2 or {}).get("bad_pages", 0)
        bus = (s2 or {}).get("sigbus", 0)
        ex_ok = s2a["exclusive"] == 0 and (s2a["before"]["swap"] > 0 or s2a["check_before"] == -1)
        an = bool(bad_types) or bad_pages > 0 or bus > 0 or bool(hang) or any(re.search(r"Bad swap|BUG|WARNING|Oops", k) for k in kerr)
        row.update({"valid": int(ex_ok and mg_ok), "anomalous": bool(ex_ok and mg_ok and an), "before": s2a["before"],
                    "after": s2a["after"], "bad_types": bad_types, "bad_pages": bad_pages, "sigbus": bus, "hang": bool(hang),
                    "reclaim": s2a["reclaim"], "check": [s2a["check_before"], s2a["check_after"]]})
    else:
        row.update({"valid": 0, "anomalous": False, "why": (s2 or {}).get("why", "no S2a record"), "child": recs.get("CHILD")})
    if not mg_ok:
        row["why_mglru"] = mg
    r["runs"].append(row)


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
for name, r in sorted(res.items()):
    out[name] = {"verdict": verdict(r["runs"]), "runs": r["runs"]}
    L.append(f"{name}: {out[name]['verdict']}")
    for x in r["runs"]:
        mgs = (x.get("mglru") or {}).get("enabled")
        if "after" in x:
            L.append(f"   run{x['run']} valid={x['valid']} mglru={mgs} before={x['before']['types']}/{x['before']['present']}p "
                     f"after={x['after']['types']}/{x['after']['present']}p bad_types={x['bad_types']} bad={x['bad_pages']} "
                     f"bus={x['sigbus']} hang={x['hang']} reclaim={x['reclaim']} check={x['check']}")
        else:
            L.append(f"   run{x['run']} invalid: {x.get('why')} {x.get('child', '')} mglru={mgs}")
        if x["kerr"]:
            L.append("      kernel: " + " | ".join(sorted(set(x["kerr"]))[:4]))
(HERE / f"judge_{tag}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
(HERE / f"judge_{tag}.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
