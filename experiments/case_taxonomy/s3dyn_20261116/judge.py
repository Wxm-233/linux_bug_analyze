"""s3dyn criteria 五: per kernel -> valid runs, per-case outcomes, verdict.   python judge.py <tag> -> judge_<tag>.{json,txt}"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
tag = sys.argv[1]
KERR = re.compile(r"BUG[: ]|WARNING:|Oops|Unable to handle|Kernel panic", re.I)
CTRL = ["C1w_alloc", "C1w_hole", "C1r_alloc", "C1r_hole", "C2w", "C2r"]
TS = ["T1", "T2", "T3", "T4"]
res = {}
for f in sorted((HERE / "runs" / tag).glob("*.log")):
    name, i = re.match(r"(.+)\.run(\d)\.log", f.name).groups()
    text = re.sub(r"\x1b(c|\[[0-9;?]*[A-Za-z])", "", f.read_text(errors="replace"))
    lines = text.splitlines()
    recs = {}
    for l in lines:
        m = re.search(r"@@R (\{.*\})", l)
        if m:
            j = json.loads(m.group(1))
            recs[j["t"]] = j
    c0_at = next((k for k, l in enumerate(lines) if '"t":"C0"' in l), len(lines))
    kerr = [l.strip()[:200] for l in lines[c0_at:] if KERR.search(l) and "@@R" not in l]
    warn_ipl = any("insert_page_into_pte_locked" in l for l in lines[c0_at:])
    end = any(l.startswith("@@END") for l in lines)
    c0 = recs.get("C0", {}).get("res") == "OK"
    ctrl_ok = all(recs.get(c, {}).get("res") == "OK" for c in CTRL)
    valid = end and c0 and ctrl_ok
    r = res.setdefault(name, {"runs": []})
    r["runs"].append({"run": i, "valid": valid, "end": end, "C0": recs.get("C0"),
                      "ctrl": {c: recs.get(c, {}).get("res") for c in CTRL},
                      "T": {t: {k: recs.get(t, {}).get(k) for k in ("res", "how", "ms", "pm_uffd_wp", "pm_present", "minflt_at_kill")}
                            for t in TS},
                      "warn_insert_page_into_pte_locked": warn_ipl, "kerr": kerr[:12]})
for name, r in res.items():
    vr = [x for x in r["runs"] if x["valid"]]
    r["valid"] = f"{len(vr)}/{len(r['runs'])}"
    r["outcomes"] = {}
    for t in TS:
        pre = [x for x in vr if x["T"][t]["pm_uffd_wp"] == 1]
        r["outcomes"][t] = {"precondition_ok": len(pre), "counts": dict(Counter(x["T"][t]["res"] for x in pre))}
    r["warn_runs"] = sum(x["warn_insert_page_into_pte_locked"] for x in r["runs"])


def frac(name, t, want):
    o = res.get(name, {}).get("outcomes", {}).get(t)
    if not o or not o["precondition_ok"]:
        return None
    return o["counts"].get(want, 0) / max(1, int(res[name]["valid"].split("/")[0]))


verdict = {}
plain, f3 = "plain", "F3"
for t in ("T1", "T2"):
    a, b = frac(plain, t, "SIGBUS"), frac(f3, t, "OK")
    ok_plain = frac(plain, t, "OK")
    if a is None or b is None:
        v = "无法验证（前提或有效运行不足）"
    elif a >= 2 / 3 and b >= 2 / 3:
        v = "复现"
    elif ok_plain == 1:
        v = "不复现"
    else:
        v = "说不清"
    verdict[t] = v
main = "复现" if "复现" in verdict.values() else ("不复现" if all(v == "不复现" for v in verdict.values()) else "说不清")
for t in ("T3", "T4"):
    a, b = frac(plain, t, "HANG"), frac(f3, t, "OK")
    verdict[t] = "同一根因的第二种后果（成立）" if (a is not None and b is not None and a >= 2 / 3 and b >= 2 / 3) else "不成立或说不清"
out = {"tag": tag, "kernels": res, "verdict_per_case": verdict, "main_verdict": main}
(HERE / f"judge_{tag}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
with open(HERE / f"judge_{tag}.txt", "w", encoding="utf-8") as fo:
    for name, r in res.items():
        print(f"== {name} valid {r['valid']} warn_runs {r['warn_runs']}", file=fo)
        for x in r["runs"]:
            print(f"  run{x['run']} valid={x['valid']} end={x['end']} C0={x['C0']} ctrl={x['ctrl']}", file=fo)
            for t in TS:
                print(f"    {t} {x['T'][t]}", file=fo)
            for k in x["kerr"]:
                print(f"    kerr: {k}", file=fo)
        print(f"  outcomes {r['outcomes']}", file=fo)
    print("verdict", verdict, "main", main, file=fo)
print(open(HERE / f"judge_{tag}.txt", encoding="utf-8").read())
