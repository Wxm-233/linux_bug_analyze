"""heldout_commit criteria 四/五: build the held-out set from the adjudicated labels, run the frozen engines, score. WSL.

    python3 heldout_run.py build    -> heldout_set.json
    python3 heldout_run.py runall   -> fills /root/work/commitmode_cache (parallel), runall.log
    python3 heldout_run.py score    -> results.json, report/<commit>.json
Read-only imports of commitmode_20261117/{dataset,commitmode,engines}.py; nothing is written into that directory.
"""
import json
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "commitmode_20261117"))
import commitmode as M  # noqa: E402
import dataset as DSET  # noqa: E402
import engines as E  # noqa: E402

ROOT = DSET.ROOT
MAX_EXTRA = 30
_orig_extra_of = M.extra_of


def extra_capped(c):
    """criteria 一: more than 30 out-of-scope directories -> P1/XV use the base scope only"""
    ex = _orig_extra_of(c)
    return [] if len(ex) > MAX_EXTRA else ex


M.extra_of = extra_capped          # runtime replacement; commitmode.py itself unchanged
M.HERE = HERE                      # check() writes report/ under this round's directory
COVERED = {"P1", "ORD", "WIDTH"}


def git(*a):
    return DSET.git(*a)


def build():
    adj = json.loads((HERE / "adjudication.json").read_text(encoding="utf-8"))["rows"]
    dev = json.loads((CT / "commitmode_20261117/dataset.json").read_text())
    dev_pos = {p["commit"] for p in dev["positives"]}
    dev_neg = {n["commit"] for n in dev["negatives"]}
    targets = DSET.fix_targets()
    pos = {}
    for r in adj:
        if r["final"] != "是":
            continue
        fix = M.full(r["commit"])
        msg = git("log", "-1", "--format=%B", fix)
        for t in re.findall(r"^\s*Fixes:\s*([0-9a-fA-F]{8,40})", msg, re.M):
            h = M.full(t)
            if not h or h == ROOT or h in dev_pos:
                continue
            p = pos.setdefault(h, {"commit": h, "short": h[:12], "info": git("log", "-1", "--format=%h|%cs|%s", h).strip(),
                                   "fixes": [], "categories": set(), "fix_funcs": set()})
            p["fixes"].append(fix[:12])
            p["categories"].add(r["category"] or "OTHER")
            p["fix_funcs"].update(map(tuple, DSET.touched_funcs(fix)))
    posset = {h[:8] for h in pos}
    negs = {}
    for h, p in sorted(pos.items(), key=lambda kv: kv[1]["info"]):
        fs = [f for f in DSET.files_of(h) if DSET.scanned(f)]
        p["files"] = fs
        p["neg"] = []
        if not fs:
            continue
        ct = int(git("log", "-1", "--format=%ct", h).strip())
        lines = git("log", "--no-merges", "--format=%H %ct", f"--since={ct - 365 * 86400}", f"--until={ct + 365 * 86400}", "HEAD", "--", *fs)
        cands = []
        for ln in lines.split("\n"):
            if not ln:
                continue
            c, t = ln.split()
            if c == h or c[:8] in targets or c[:8] in posset or c in negs or c in dev_pos or c in dev_neg:
                continue
            cands.append((int(t) - ct, c))
        for x in (max((x for x in cands if x[0] < 0), default=None), min((x for x in cands if x[0] > 0), default=None)):
            if x:
                negs[x[1]] = {"commit": x[1], "short": x[1][:12], "for": h[:12], "dt_days": round(x[0] / 86400, 1),
                              "info": git("log", "-1", "--format=%h|%cs|%s", x[1]).strip()}
                p["neg"].append(x[1][:12])
    out = {"positives": [dict(p, categories=sorted(p["categories"]), fix_funcs=sorted(p["fix_funcs"])) for p in pos.values()],
           "negatives": list(negs.values())}
    (HERE / "heldout_set.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print("positives", len(out["positives"]), "negatives", len(out["negatives"]))
    for p in out["positives"]:
        print(" P", p["info"][:70], p["categories"], "| scanned files", len(p["files"]), "| fix funcs", len(p["fix_funcs"]), "| neg", p["neg"])


def commits():
    s = json.loads((HERE / "heldout_set.json").read_text())
    return [p["commit"] for p in s["positives"]] + [n["commit"] for n in s["negatives"]]


def runall(maxheavy=4, maxlight=3):
    todo, seen = [], set()
    for c in commits():
        for j in M.jobs_of(c):
            if j not in seen and not E.cache_path(*j).exists():
                seen.add(j)
                todo.append(j)
    todo.sort(key=lambda j: j[0] not in M.HEAVY)
    running, t0 = [], time.time()
    log = open(HERE / "runall.log", "a")
    print(f"start {len(todo)} jobs", file=log, flush=True)
    while todo or running:
        running = [(j, pr) for j, pr in running if pr.poll() is None]
        nh = sum(1 for j, _ in running if j[0] in M.HEAVY)
        nl = len(running) - nh
        for j in list(todo):
            if (j[0] in M.HEAVY and nh < maxheavy) or (j[0] not in M.HEAVY and nl < maxlight):
                pr = subprocess.Popen([sys.executable, str(CT / "commitmode_20261117/engines.py"), j[0], j[1], *j[2]],
                                      stdout=log, stderr=subprocess.STDOUT)
                running.append((j, pr))
                todo.remove(j)
                nh += j[0] in M.HEAVY
                nl += j[0] not in M.HEAVY
        print(f"{round(time.time() - t0)}s todo={len(todo)} running={len(running)}", file=log, flush=True)
        time.sleep(10)
    print("all done", round(time.time() - t0), file=log, flush=True)


def score():
    s = json.loads((HERE / "heldout_set.json").read_text())
    rows = []
    for kind, items in (("pos", s["positives"]), ("neg", s["negatives"])):
        for it in items:
            r = M.check(it["commit"], run_missing=False)
            r["kind"] = kind
            r["capped"] = len(_orig_extra_of(it["commit"])) > MAX_EXTRA
            if kind == "pos":
                names = {fn for _, fn in it["fix_funcs"]}
                hits = [x for x in r["new"] if x["func"] in names or
                        (x["engine"] == "WT" and x["sig"].startswith("A|arg:") and x["sig"].split("|")[1][4:].split("#")[0] in names)]
                r["aligned"] = bool(hits)
                r["aligned_hits"] = [f"{x['engine']} {x['file']}:{x['line']} {x['func']} {x['sig'][:80]}" for x in hits][:10]
                r["categories"] = it["categories"]
                r["covered"] = bool(set(it["categories"]) & COVERED)
                r["scanned_files"] = len(it["files"])
            rows.append(r)
    P = [r for r in rows if r["kind"] == "pos"]
    N = [r for r in rows if r["kind"] == "neg"]
    cov = [r for r in P if r["covered"]]
    res = {"n_pos": len(P), "n_neg": len(N), "recall_all": sum(r["flag_all"] for r in P), "recall_noA": sum(r["flag_noA"] for r in P),
           "aligned": sum(r["aligned"] for r in P), "covered_pos": len(cov), "covered_aligned": sum(r["aligned"] for r in cov),
           "fp_all": sum(r["flag_all"] for r in N), "fp_noA": sum(r["flag_noA"] for r in N),
           "engine_errors": sum(1 for r in rows for e in r["engines"].values() if e["status"] == "error"), "engine_runs": len(rows) * 4,
           "capped": [r["commit"] for r in rows if r["capped"]],
           "by_category": {c: {"n": sum(1 for r in P if c in r["categories"]), "aligned": sum(1 for r in P if c in r["categories"] and r["aligned"])}
                           for c in sorted({c for r in P for c in r["categories"]})},
           "per_engine": {e: {"pos_flag": sum(1 for r in P if any(x["engine"] == e for x in r["new"])),
                              "pos_aligned": sum(1 for r in P if any(h.startswith(e + " ") for h in r.get("aligned_hits", []))),
                              "neg_flag": sum(1 for r in N if any(x["engine"] == e for x in r["new"]))} for e in M.ENGS},
           "rows": rows}
    (HERE / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"positives {len(P)}: flagged(all) {res['recall_all']} flagged(noA) {res['recall_noA']} aligned {res['aligned']} | covered {len(cov)} aligned {res['covered_aligned']}")
    print(f"negatives {len(N)}: flagged(all) {res['fp_all']} flagged(noA) {res['fp_noA']} | engine errors {res['engine_errors']}/{res['engine_runs']} capped {res['capped']}")
    print("by category", res["by_category"], "\nper engine", res["per_engine"])
    for r in P:
        print("P", "ALIGN" if r["aligned"] else ("flag " if r["flag_all"] else "-    "), r["categories"], r["info"][:60],
              {e: v.get("new", v["status"]) for e, v in r["engines"].items()})
    for r in N:
        if r["flag_all"] or any(v["status"] == "error" for v in r["engines"].values()):
            print("N", "FLAG" if r["flag_all"] else "ERR ", r["info"][:60], {e: v.get("new", v["status"]) for e, v in r["engines"].items()})


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    {"build": build, "runall": runall, "score": score}[sys.argv[1]]()
