"""Verdicts of ctxcheck2 (criteria 四 + amendment 1, 二). Pure Python.

    python judge2.py <tag> <target arch> <pre kernel> <fix kernel> <ref kernel:arch> <ref kernel:arch>
        -> judge_<tag>.json and a printed summary.   Logs: runs/<tag>/<kernel>.run<i>.log.gz
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location("warn_parse", HERE.parent / "dbgassert_dev_20261111" / "warn_parse.py")
WP = importlib.util.module_from_spec(_s)
_s.loader.exec_module(WP)
CTX = re.compile(r"sleeping function called from invalid context|BUG: scheduling while atomic|inconsistent lock state|"
                 r"possible circular locking dependency|suspicious RCU usage|Invalid wait context")
STATE = re.compile(r"in_atomic\(\): *(\d+), *irqs_disabled\(\): *(\d+)")
PCNT = re.compile(r"preempt_count: *([0-9a-f]+)")


def signature(e):
    """criteria 四.3: normalised first line (line numbers dropped) + state values"""
    first = re.sub(r":N\b", "", e["first"])
    txt = "\n".join(e["text"])
    m, p = STATE.search(txt), PCNT.search(txt)
    st = f"in_atomic={m.group(1)},irqs_disabled={m.group(2)}" if m else ""
    if p:
        st += f",preempt_count={p.group(1)}"
    return first + (" | " + st if st else "")


def load(tag, k):
    runs = []
    for i in (1, 2, 3):
        f = HERE / "runs" / tag / f"{k}.run{i}.log.gz"
        p = WP.parse(f)
        ev = [dict(e, sig=signature(e)) for e in p["events"] if CTX.search("\n".join(e["text"]))]
        notes = re.findall(r'\{"cnote":"([^"]*)"\}', __import__("gzip").open(f).read().decode("utf-8", "replace"))
        runs.append({"complete": p["complete"], "cases": p["cases_seen"], "ctx": ev, "notes": notes})
    return runs


def case_status(runs, cid):
    n = sum(1 for r in runs if any(e.get("case") == cid for e in r["ctx"]))
    return "报" if n >= 2 else "不报" if n == 0 else "不稳"


def boot_status(runs):
    sigs = {}
    for r in runs:
        for s in {e["sig"] for e in r["ctx"] if e["phase"] == "boot"}:
            sigs[s] = sigs.get(s, 0) + 1
    if any(v * 2 >= len(runs) for v in sigs.values()):
        return "报", sigs
    return ("不报" if not sigs else "不稳"), sigs


def cross(statuses):
    """criteria 四.5 over {arch: status}"""
    if any(v == "不稳" for v in statuses.values()):
        return "不判", []
    on = sorted(a for a, v in statuses.items() if v == "报")
    if len(statuses) == 2:  # only one reference built: criteria 四.5 cannot be applied, report only
        return {0: "一致（单参照）", 1: "一方报（单参照）", 2: "两方都报（单参照）"}[len(on)], on
    return {0: "一致", 1: "与众不同", 2: "部分架构告警", 3: "全部告警"}[len(on)], on


def main():
    tag, tgt, pre, fix = sys.argv[1:5]
    refs = [x.split(":") for x in sys.argv[5:]]
    K = {pre: tgt, fix: tgt, **{k: a for k, a in refs}}
    data = {k: load(tag, k) for k in K}
    cids = sorted({e["case"] for d in data.values() for r in d for e in r["ctx"] if e.get("case")}, key=int)
    res = {"tag": tag, "target": tgt, "runs": {k: [{"complete": r["complete"], "cases": r["cases"], "ctx": len(r["ctx"])}
                                                 for r in d] for k, d in data.items()},
           "cases": {}, "boot": {}, "strong": [], "weak": [], "noise_fix": []}
    for cid in cids:
        st = {k: case_status(d, cid) for k, d in data.items()}
        v_pre, on_pre = cross({tgt: st[pre], **{a: st[k] for k, a in refs}})
        v_fix, on_fix = cross({tgt: st[fix], **{a: st[k] for k, a in refs}})
        ex = {k: sorted({e["sig"] for r in d for e in r["ctx"] if e.get("case") == cid}) for k, d in data.items()}
        res["cases"][cid] = {"status": st, "pre_verdict": [v_pre, on_pre], "fix_verdict": [v_fix, on_fix], "signatures": ex}
        if tgt in on_pre and st[fix] == "不报":
            (res["strong"] if v_pre == "与众不同" else res["weak"] if v_pre == "部分架构告警" else []).append(cid)
        if st[fix] == "报":
            res["noise_fix"].append(cid)
    bs = {k: boot_status(d) for k, d in data.items()}
    res["boot"] = {k: {"status": s, "sigs": g} for k, (s, g) in bs.items()}
    v_pre, on_pre = cross({tgt: bs[pre][0], **{a: bs[k][0] for k, a in refs}})
    res["boot_verdict"] = [v_pre, on_pre]
    if tgt in on_pre and bs[fix][0] == "不报":
        (res["strong"] if v_pre == "与众不同" else res["weak"] if v_pre == "部分架构告警" else []).append("boot")
    res["notes"] = {k: sorted({n for r in d for n in r["notes"]}) for k, d in data.items()}
    (HERE / f"judge_{tag}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf8")
    sys.stdout.reconfigure(encoding="utf8")
    for k, v in res["runs"].items():
        print(k, v)
    for cid, v in res["cases"].items():
        print("case", cid, v["status"], "pre:", v["pre_verdict"], "fix:", v["fix_verdict"])
    print("boot:", {k: v["status"] for k, v in res["boot"].items()}, "verdict", res["boot_verdict"])
    print("STRONG", res["strong"], "WEAK", res["weak"], "fix still reports", res["noise_fix"])
    for k, v in res["notes"].items():
        print("notes", k, v[:12])


if __name__ == "__main__":
    main()
