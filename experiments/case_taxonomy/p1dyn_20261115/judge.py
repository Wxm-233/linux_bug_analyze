"""p1dyn criteria 四/五: per kernel x suspect -> valid / anomalous runs, verdict.   python judge.py <tag>  -> judge_<tag>.{json,txt}"""
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
    raw = f.read_text(errors="replace")
    text = re.sub(r"\x1b(c|\[[0-9;?]*[A-Za-z])", "", raw)
    lines = text.splitlines()
    s1_at = next((k for k, l in enumerate(lines) if '{"t":"S1"' in l), len(lines))  # amendment 2.3: only S2-phase lines
    kerr = [l.strip()[:200] for l in lines[s1_at:] if KERR.search(l) and not l.lstrip().startswith("{")]
    boot_kerr = [l.strip()[:200] for l in lines[:s1_at] if KERR.search(l)]
    recs = {}
    for l in text.splitlines():
        m = re.search(r"\{\"t\":.*\}", l)
        if m:
            try:
                j = json.loads(m.group(0))
                recs[j["t"]] = j
            except json.JSONDecodeError:
                pass
    r = res.setdefault(name, {"runs": 0, "S1": [], "S2": [], "env": [], "kerr": [], "boot_kerr": []})
    r["boot_kerr"].append(boot_kerr)
    r["runs"] += 1
    r["env"].append(recs.get("ENV"))
    r["kerr"].append(kerr)
    s1 = recs.get("S1")
    if s1:
        an = s1["anom"]["ref"] + s1["anom"]["lazy"] + s1["anom"]["pdirty"]
        r["S1"].append({"run": i, "valid": s1["valid"], "anomalous": bool(s1["valid"] and an > 0), "anom": s1["anom"],
                        "mig_ok": s1["mig_ok"], "samples": s1["samples"], "base": s1["base"], "extreme": s1["extreme"],
                        "thp": [s1["thp_before"], s1["end"]["ahp"]], "mig_errno": s1["mig_errno"], "sdirty": s1.get("sdirty")})
    else:
        r["S1"].append({"run": i, "valid": 0, "anomalous": False, "why": "no S1 record"})
    s2a, s2, hang = recs.get("S2a"), recs.get("S2"), recs.get("S2hang")  # amendment 2.2
    if s2a and "after" in s2a:
        bad_types = {t: n for t, n in s2a["after"]["types"].items() if t not in ("0", "30")}
        bad_pages = (s2 or {}).get("bad_pages", 0)
        bus = (s2 or {}).get("sigbus", 0)
        valid = int(s2a["exclusive"] == 0 and (s2a["before"]["swap"] > 0 or s2a["check_before"] == -1))
        an = bool(bad_types) or bad_pages > 0 or bus > 0 or bool(hang) or any(re.search(r"Bad swap|BUG|WARNING|Oops", k) for k in kerr)
        r["S2"].append({"run": i, "valid": valid, "anomalous": bool(valid and an), "before": s2a["before"], "after": s2a["after"],
                        "bad_types": bad_types, "bad_pages": bad_pages, "sigbus": bus, "hang": bool(hang), "reclaim": s2a["reclaim"],
                        "check": [s2a["check_before"], s2a["check_after"]], "exclusive": s2a["exclusive"]})
    else:
        r["S2"].append({"run": i, "valid": 0, "anomalous": False, "why": (s2 or {}).get("why", "no S2a record"),
                        "child": recs.get("CHILD")})


def verdict(rows):
    v = [x for x in rows if x["valid"]]
    a = sum(x["anomalous"] for x in v)
    if len(v) >= 2 and a >= 2:
        return "复现", len(v), a
    if len(v) >= 2 and a == 0:
        return "不复现", len(v), a
    return "说不清", len(v), a


L = []
out = {}
for name, r in sorted(res.items()):
    out[name] = {"S1": verdict(r["S1"]), "S2": verdict(r["S2"]), "detail": r}
    L.append(f"{name}: S1 {out[name]['S1']}  S2 {out[name]['S2']}")
    for s in ("S1", "S2"):
        for x in r[s]:
            if s == "S1" and "anom" in x:
                L.append(f"   S1 run{x['run']} valid={x['valid']} anom={x['anom']} mig_ok={x['mig_ok']} samples={x['samples']} "
                         f"base={x['base']} extreme={x['extreme']} thp={x['thp']} sdirty={x.get('sdirty')}")
            elif s == "S2" and "after" in x:
                L.append(f"   S2 run{x['run']} valid={x['valid']} before={x['before']['types']}/{x['before']['present']}p "
                         f"after={x['after']['types']}/{x['after']['present']}p bad_types={x['bad_types']} bad={x['bad_pages']} "
                         f"bus={x['sigbus']} hang={x['hang']} reclaim={x['reclaim']} check={x['check']}")
            else:
                L.append(f"   {s} run{x['run']} invalid: {x.get('why')} {x.get('child', '')}")
    ke = sorted({k for ks in r["kerr"] for k in ks})
    if ke:
        L.append("   kernel(S2 phase): " + " | ".join(ke[:6]))
    bk = sorted({k for ks in r["boot_kerr"] for k in ks})
    if bk:
        L.append("   kernel(boot, not counted): " + " | ".join(bk[:3]))
(HERE / f"judge_{tag}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
(HERE / f"judge_{tag}.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
