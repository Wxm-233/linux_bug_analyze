"""commitmode_tlb criteria 一-三: fifth engine TLB (tlbhook2) in commit-level mode; dev set + held-out set. WSL, no build.

    python3 cmtlb.py selftest
    python3 cmtlb.py engine <rev>      -> /root/work/commitmode_cache/TLB/<rev>.json
    python3 cmtlb.py runall [N]        -> runs missing TLB jobs for both data sets, N parallel (default 4), runall.log
    python3 cmtlb.py score             -> results.json, report/<commit>.json
Read-only imports of commitmode_20261117/commitmode.py and tlbhook2_20261117/tlbhook2.py; nothing is written there.
"""
import json
import re
import subprocess
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "commitmode_20261117"))
sys.path.insert(0, str(CT / "tlbhook2_20261117"))
import commitmode as M  # noqa: E402
import tlbhook2 as T2  # noqa: E402

CACHE = Path("/root/work/commitmode_cache/TLB")
DEV = CT / "commitmode_20261117"
HO = CT / "heldout_commit_20261117"
TAINTED = {"d95f1a542c3d", "7a92fc8b4d20", "7d3332be011e", "65d4b9c53017", "550a7d60bd5e"}   # criteria 二


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


def sigs(R):
    """criteria 一.2"""
    out = []
    for x in R["arch"] + R["common"] + R["r1"]:
        r = x["rule"]
        if r == "T1a":
            out.append({"file": f"arch/{x['arch']}", "func": "flush_cache_vmap", "line": 0, "sig": f"T1a|{x['arch']}"})
        elif r == "T1c":
            out.append({"file": x["file"], "func": x["func"], "line": x["line"], "sig": f"T1c|{x['arch']}"})
        elif r == "R1":
            out.append({"file": x["file"], "func": x["func"], "line": x["line"], "sig": f"R1|{x['arch']}|{x['region']}|{norm(x['what'])}"})
        else:
            out.append({"file": x["file"], "func": x["func"], "line": x["line"], "sig": f"{r}|{norm(x['what'])}"})
    return out


def in_scope(p):
    """criteria 一.4: files tlbhook2.files_of reads"""
    return (p in T2.V1.GENERIC or T2.V1.common_scope(p) or bool(re.match(r"arch/[^/]+/include/asm/.*\.h$", p))
            or bool(re.match(r"arch/[^/]+/mm/[^/]+\.c$", p)) or bool(re.match(r"arch/[^/]+/Kconfig$", p)))


def engine(rev):
    p = CACHE / f"{rev}.json"
    if p.exists():
        return json.loads(p.read_text())
    t0 = time.time()
    try:
        if M.full(rev) != rev:
            raise ValueError(f"not a full commit id: {rev}")
        R = T2.run(rev)
        if len(R["regions"]) < 10:
            raise ValueError(f"only {len(R['regions'])} architectures read")
        cands = sigs(R)
        res = {"engine": "TLB", "rev": rev, "ok": True, "n": len(cands), "secs": round(time.time() - t0, 1), "cands": cands}
    except Exception:
        res = {"engine": "TLB", "rev": rev, "ok": False, "error": traceback.format_exc()[-2000:], "secs": round(time.time() - t0, 1), "cands": []}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res))
    return res


def datasets():
    dev = json.loads((DEV / "dataset.json").read_text())
    ho = json.loads((HO / "heldout_set.json").read_text())
    return {"dev": dev, "heldout": ho}


def touches(c):
    return any(in_scope(f) for f in M.git("diff", "--name-only", f"{c}^", c).split("\n") if f)


def jobs():
    out = []
    for ds in datasets().values():
        for it in ds["positives"] + ds["negatives"]:
            c = M.full(it["commit"])
            if touches(c):
                for rev in (M.full(c + "^"), c):
                    if rev not in out:
                        out.append(rev)
    return out


def runall(n=4):
    todo = [r for r in jobs() if not (CACHE / f"{r}.json").exists()]
    log = open(HERE / "runall.log", "a")
    print(f"start {len(todo)} TLB jobs", file=log, flush=True)
    running, t0 = [], time.time()
    while todo or running:
        running = [pr for pr in running if pr.poll() is None]
        while todo and len(running) < n:
            r = todo.pop(0)
            running.append(subprocess.Popen([sys.executable, str(HERE / "cmtlb.py"), "engine", r], stdout=log, stderr=subprocess.STDOUT))
        print(f"{round(time.time() - t0)}s todo={len(todo)} running={len(running)}", file=log, flush=True)
        time.sleep(15)
    print("all done", round(time.time() - t0), file=log, flush=True)


def tlb_new(c):
    """criteria 一.3/一.4: (status, new candidates)"""
    c = M.full(c)
    if not touches(c):
        return "skip", []
    res = []
    for rev in (M.full(c + "^"), c):
        p = CACHE / f"{rev}.json"
        res.append(json.loads(p.read_text()) if p.exists() else None)
    if any(r is None or not r["ok"] for r in res):
        return "error", []
    return "ok", [dict(x, engine="TLB") for x in M.compare(res[0], res[1], M.renames(c))]


def score_set(name, ds, old):
    oldrows = {r["commit"][:12]: r for r in old["rows"]}
    rows = []
    for kind, items in (("pos", ds["positives"]), ("neg", ds["negatives"])):
        for it in items:
            c12 = M.full(it["commit"])[:12]
            o = oldrows[c12]
            st, new = tlb_new(it["commit"])
            names = {fn for _, fn in it.get("fix_funcs", [])}
            tl_al = [x for x in new if x["func"] in names] if kind == "pos" else []
            r = {"commit": c12, "kind": kind, "info": o["info"], "tainted": c12 in TAINTED, "categories": it.get("categories"),
                 "old_flag": o["flag_all"], "old_flag_noA": o["flag_noA"], "old_aligned": o.get("aligned", False),
                 "tlb_status": st, "tlb_new": [f"{x['file']}:{x['line']} {x['func']} {x['sig'][:90]}" for x in new],
                 "tlb_flag": bool(new), "tlb_aligned": bool(tl_al)}
            r["flag5"] = r["old_flag"] or r["tlb_flag"]
            r["flag5_noA"] = r["old_flag_noA"] or r["tlb_flag"]
            r["aligned5"] = r["old_aligned"] or r["tlb_aligned"]
            rows.append(r)
            (HERE / "report").mkdir(exist_ok=True)
            (HERE / "report" / f"{c12}.json").write_text(json.dumps(r, indent=1, ensure_ascii=False))

    def summ(P, N):
        return {"n_pos": len(P), "n_neg": len(N),
                "recall4": sum(r["old_flag"] for r in P), "recall5": sum(r["flag5"] for r in P),
                "recall4_noA": sum(r["old_flag_noA"] for r in P), "recall5_noA": sum(r["flag5_noA"] for r in P),
                "aligned4": sum(r["old_aligned"] for r in P), "aligned5": sum(r["aligned5"] for r in P),
                "fp4": sum(r["old_flag"] for r in N), "fp5": sum(r["flag5"] for r in N),
                "fp4_noA": sum(r["old_flag_noA"] for r in N), "fp5_noA": sum(r["flag5_noA"] for r in N),
                "tlb_pos_flag": sum(r["tlb_flag"] for r in P), "tlb_pos_aligned": sum(r["tlb_aligned"] for r in P),
                "tlb_neg_flag": sum(r["tlb_flag"] for r in N),
                "tlb_errors": sum(r["tlb_status"] == "error" for r in P + N), "tlb_skipped": sum(r["tlb_status"] == "skip" for r in P + N)}
    P = [r for r in rows if r["kind"] == "pos"]
    N = [r for r in rows if r["kind"] == "neg"]
    out = {"all": summ(P, N)}
    if name == "heldout":
        out["clean"] = summ([r for r in P if not r["tainted"]], N)
        out["tainted"] = summ([r for r in P if r["tainted"]], [])
    out["rows"] = rows
    return out


def score():
    dss = datasets()
    res = {}
    for name, d, oldp in (("dev", dss["dev"], DEV / "results.json"), ("heldout", dss["heldout"], HO / "results.json")):
        res[name] = score_set(name, d, json.loads(oldp.read_text()))
    (HERE / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    for name, r in res.items():
        for part in [k for k in ("all", "clean", "tainted") if k in r]:
            s = r[part]
            print(f"{name}/{part}: pos {s['n_pos']} recall {s['recall4']}->{s['recall5']} (noA {s['recall4_noA']}->{s['recall5_noA']}) "
                  f"aligned {s['aligned4']}->{s['aligned5']} | neg {s['n_neg']} fp {s['fp4']}->{s['fp5']} | "
                  f"TLB pos {s['tlb_pos_flag']} aligned {s['tlb_pos_aligned']} neg {s['tlb_neg_flag']} err {s['tlb_errors']} skip {s['tlb_skipped']}")
        for row in r["rows"]:
            if row["tlb_new"]:
                print(" ", name, row["kind"], "T" if row["tainted"] else " ", "ALIGN" if row["tlb_aligned"] else "flag ", row["info"][:55])
                for x in row["tlb_new"][:6]:
                    print("      ", x)


def selftest():
    R = {"arch": [{"rule": "T1a", "arch": "riscv"}, {"rule": "T1c", "arch": "riscv", "file": "arch/riscv/include/asm/kfence.h", "func": "kp", "line": 3}],
         "common": [{"rule": "T2", "file": "mm/a.c", "func": "f", "line": 9, "what": "set_pte_at(&init_mm)"}],
         "r1": [{"rule": "R1", "arch": "riscv", "file": "mm/kasan/shadow.c", "func": "g", "line": 5, "region": "kasan", "what": "flush_cache_vmap(a b)"}]}
    s = sigs(R)
    got = {(x["file"], x["func"], x["sig"]) for x in s}
    a = {"cands": s[:2]}
    b = {"cands": [dict(x, line=x["line"] + 7) for x in s]}
    new = M.compare(a, b, {})
    checks = [("T1a sig", ("arch/riscv", "flush_cache_vmap", "T1a|riscv") in got),
              ("R1 sig", ("mm/kasan/shadow.c", "g", "R1|riscv|kasan|flush_cache_vmap(ab)") in got),
              ("line shift not new, two added", sorted(x["func"] for x in new) == ["f", "g"]),
              ("scope arch mm", in_scope("arch/riscv/mm/init.c") and in_scope("arch/riscv/include/asm/x/y.h") and in_scope("arch/x86/Kconfig")),
              ("scope common", in_scope("mm/vmalloc.c") and in_scope("include/linux/mm.h") and not in_scope("drivers/a.c")),
              ("scope not arch kernel", not in_scope("arch/riscv/kernel/entry.S"))]
    bad = 0
    for nm, ok in checks:
        bad += not ok
        print("ok " if ok else "BAD", nm)
    print("selftest(cmtlb)", "PASS" if not bad else f"FAIL {bad}")
    return not bad


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if cmd == "engine":
        r = engine(sys.argv[2])
        print("TLB", sys.argv[2][:12], "ok" if r["ok"] else "ERROR", r.get("n"), r["secs"], "s", (r.get("error") or "")[-300:], flush=True)
    elif cmd == "runall":
        runall(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    elif cmd == "jobs":
        print(len(jobs()))
    elif cmd == "score":
        score()
