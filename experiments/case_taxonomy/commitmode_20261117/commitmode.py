"""commitmode criteria 一/三: commit-level mode. WSL, no build.

    python3 commitmode.py selftest
    python3 commitmode.py check <commit>      -> report/<commit>.json (runs the engines if not cached)
    python3 commitmode.py runall              -> fills the engine cache for the whole development set (parallel)
    python3 commitmode.py score               -> results.json, results.md
"""
import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engines as E  # noqa: E402

KSRC = "/root/repos/linux"
ENGS = ("P1", "XV", "ORD", "WT")
HEAVY = {"P1", "XV"}


def git(*a):
    return subprocess.run(["git", "-C", KSRC, *a], capture_output=True, text=True).stdout


def full(c):
    return git("rev-parse", "--verify", "-q", c + "^{commit}").strip()


def k_in_scope(p):
    return (p.endswith(".h") and p.startswith("include/linux/")) or (p.endswith(".c") and p.startswith(("mm/", "kernel/", "lib/", "fs/proc/")))


def extra_of(c):
    """criteria 一.1: directories of out-of-scope .c files the commit changes (P1/XV only)"""
    fs = [p for p in git("diff", "--name-only", f"{c}^", c).split("\n") if p]
    return sorted({f.rsplit("/", 1)[0] + "/" for f in fs if f.endswith(".c") and "/" in f and not k_in_scope(f)})


def renames(c):
    out = {}
    for ln in git("diff", "-M", "--name-status", f"{c}^", c).split("\n"):
        parts = ln.split("\t")
        if len(parts) == 3 and parts[0].startswith("R"):
            out[parts[1]] = parts[2]
    return out


def jobs_of(c):
    c = full(c)
    ex = extra_of(c)
    out = []
    for rev in (full(c + "^"), c):
        for e in ENGS:
            out.append((e, rev, tuple(ex) if e in HEAVY else ()))
    return out


def sig(r):
    return (r["file"], r["func"], r["sig"])


def compare(parent_res, child_res, ren):
    """criteria 一.3/一.4: multiset difference of signatures, parent side mapped through renames"""
    pc = Counter((ren.get(f, f), fn, s) for f, fn, s in map(sig, parent_res["cands"]))
    cc = Counter(map(sig, child_res["cands"]))
    new = []
    for k, n in cc.items():
        extra = n - pc.get(k, 0)
        if extra > 0:
            rows = [r for r in child_res["cands"] if sig(r) == k]
            new += rows[-extra:]
    return sorted(new, key=lambda r: (r["file"], r["line"]))


def check(c, run_missing=True):
    c = full(c)
    p = full(c + "^")
    ex = extra_of(c)
    ren = renames(c)
    out = {"commit": c[:12], "info": git("log", "-1", "--format=%h|%cs|%s", c).strip(), "extra": ex, "renames": len(ren),
           "engines": {}, "new": []}
    for e in ENGS:
        x = tuple(ex) if e in HEAVY else ()
        res = []
        for rev in (p, c):
            path = E.cache_path(e, rev, x)
            if not path.exists():
                if not run_missing:
                    res.append(None)
                    continue
                subprocess.run([sys.executable, str(HERE / "engines.py"), e, rev, *x], check=False)
            res.append(json.loads(path.read_text()) if path.exists() else None)
        if any(r is None or not r["ok"] for r in res):
            out["engines"][e] = {"status": "error", "errors": [None if r is None else (r.get("error") or "")[-400:] for r in res]}
            continue
        new = compare(res[0], res[1], ren)
        out["engines"][e] = {"status": "ok", "parent": res[0]["n"], "child": res[1]["n"], "new": len(new)}
        out["new"] += [dict(r, engine=e) for r in new]
    out["flag_all"] = bool(out["new"])
    out["flag_noA"] = any(not (r["engine"] == "WT" and r["sig"].startswith("A|")) for r in out["new"])
    rep = HERE / "report"
    rep.mkdir(exist_ok=True)
    (rep / f"{c[:12]}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


def runall(maxheavy=5, maxlight=3):
    ds = json.loads((HERE / "dataset.json").read_text())
    commits = [p["commit"] for p in ds["positives"]] + [n["commit"] for n in ds["negatives"]]
    todo, seen = [], set()
    for c in commits:
        for j in jobs_of(c):
            if j not in seen and not E.cache_path(*j).exists():
                seen.add(j)
                todo.append(j)
    todo.sort(key=lambda j: j[0] not in HEAVY)          # start heavy jobs first
    running = []
    t0 = time.time()
    log = open(HERE / "runall.log", "a")
    print(f"start {len(todo)} jobs", file=log, flush=True)
    while todo or running:
        running = [(j, pr) for j, pr in running if pr.poll() is None]
        nh = sum(1 for j, _ in running if j[0] in HEAVY)
        nl = len(running) - nh
        for j in list(todo):
            if (j[0] in HEAVY and nh < maxheavy) or (j[0] not in HEAVY and nl < maxlight):
                pr = subprocess.Popen([sys.executable, str(HERE / "engines.py"), j[0], j[1], *j[2]], stdout=log, stderr=subprocess.STDOUT)
                running.append((j, pr))
                todo.remove(j)
                if j[0] in HEAVY:
                    nh += 1
                else:
                    nl += 1
        print(f"{round(time.time() - t0)}s todo={len(todo)} running={len(running)}", file=log, flush=True)
        time.sleep(10)
    print("all done", round(time.time() - t0), file=log, flush=True)


def score():
    ds = json.loads((HERE / "dataset.json").read_text())
    rows = []
    for kind, items in (("pos", ds["positives"]), ("neg", ds["negatives"])):
        for it in items:
            r = check(it["commit"], run_missing=False)
            r["kind"] = kind
            if kind == "pos":
                names = {fn for _, fn in it["fix_funcs"]}
                hits = [x for x in r["new"] if x["func"] in names or
                        (x["engine"] == "WT" and x["sig"].startswith("A|arg:") and x["sig"].split("|")[1][4:].split("#")[0] in names)]
                r["aligned"] = bool(hits)
                r["aligned_hits"] = [f"{x['engine']} {x['file']}:{x['line']} {x['func']} {x['sig'][:80]}" for x in hits][:10]
                r["lines"] = it["lines"]
                r["scanned_files"] = len(it["files"])
            else:
                r["for"] = it["for"]
            rows.append(r)
    P = [r for r in rows if r["kind"] == "pos"]
    N = [r for r in rows if r["kind"] == "neg"]
    err = sum(1 for r in rows for e in r["engines"].values() if e["status"] == "error")
    per = {}
    for e in ENGS:
        per[e] = {"pos_flag": sum(1 for r in P if any(x["engine"] == e for x in r["new"])),
                  "pos_aligned": sum(1 for r in P if any(h.startswith(e + " ") for h in r.get("aligned_hits", []))),
                  "neg_flag": sum(1 for r in N if any(x["engine"] == e for x in r["new"])),
                  "errors": sum(1 for r in rows if r["engines"].get(e, {}).get("status") == "error")}
    res = {"n_pos": len(P), "n_neg": len(N),
           "recall_all": sum(r["flag_all"] for r in P), "recall_noA": sum(r["flag_noA"] for r in P),
           "aligned": sum(r["aligned"] for r in P),
           "fp_all": sum(r["flag_all"] for r in N), "fp_noA": sum(r["flag_noA"] for r in N),
           "engine_errors": err, "engine_runs": len(rows) * len(ENGS), "per_engine": per, "rows": rows}
    (HERE / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(f"positives {len(P)}: flagged(all) {res['recall_all']}  flagged(noA) {res['recall_noA']}  aligned {res['aligned']}")
    print(f"negatives {len(N)}: flagged(all) {res['fp_all']}  flagged(noA) {res['fp_noA']}")
    print("engine errors", err, "/", res["engine_runs"], "| per engine", per)
    for r in P:
        print("P", "ALIGN" if r["aligned"] else ("flag " if r["flag_all"] else "-    "), r["info"][:60], {e: v.get("new", v["status"]) for e, v in r["engines"].items()})
    for r in N:
        print("N", "FLAG " if r["flag_all"] else "-    ", "noA" if r["flag_noA"] else "   ", r["info"][:60], {e: v.get("new", v["status"]) for e, v in r["engines"].items()})


def selftest():
    a = {"cands": [{"file": "a.c", "func": "f", "line": 10, "sig": "x"}, {"file": "old.c", "func": "g", "line": 5, "sig": "y"}]}
    b = {"cands": [{"file": "a.c", "func": "f", "line": 12, "sig": "x"}, {"file": "a.c", "func": "f", "line": 20, "sig": "x"},
                   {"file": "new.c", "func": "g", "line": 7, "sig": "y"}, {"file": "a.c", "func": "h", "line": 30, "sig": "z"}]}
    new = compare(a, b, {"old.c": "new.c"})
    got = sorted((r["func"], r["line"]) for r in new)
    ok = got == [("f", 20), ("h", 30)]
    print("selftest(commitmode)", "PASS" if ok else f"FAIL {got}")
    return ok


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if cmd == "check":
        r = check(sys.argv[2])
        print(json.dumps({k: v for k, v in r.items() if k != "new"}, ensure_ascii=False), "\nnew:")
        for x in r["new"]:
            print(" ", x["engine"], f"{x['file']}:{x['line']}", x["func"], x["sig"][:100])
    elif cmd == "runall":
        runall()
    elif cmd == "score":
        score()
