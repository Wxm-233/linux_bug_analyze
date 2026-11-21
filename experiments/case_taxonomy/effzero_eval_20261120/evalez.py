"""effzero_eval criteria 二/三: frozen E-ZERO as 9th engine on the heldout2 evaluation set. WSL.

    python3 evalez.py run     -> runs/ (analysis), sealed/ (sealed set, never printed), summary.json, analysis_rows.json
Sealed set: only counts are printed or written outside sealed/.
"""
import hashlib
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
EZ = CT / "effzero_20261120"
H2 = CT / "heldout2_20261119"
sys.path.insert(0, str(CT / "scan3_20261119"))
EXTRA_USED = {"6c2f761dad78"}   # criteria 三: K1, E-ZERO calibration example (analysis set)


def check_ez_frozen():
    for ln in (EZ / "frozen_sha256.txt").read_text().splitlines():
        h, name = ln.split(" ", 1)
        name = name.lstrip(" *")
        if name == "effzero.py" and hashlib.sha256((EZ / name).read_bytes()).hexdigest() != h:
            raise SystemExit("effzero frozen code changed")


def main():
    t0 = time.time()
    check_ez_frozen()
    import scan3 as S
    S.check_frozen()
    sets = {n: json.loads((H2 / f"set_{n}.json").read_text(encoding="utf-8")) for n in ("analysis", "sealed")}
    jobs = []
    for n, s in sets.items():
        for i, it in enumerate(s["positives"]):
            for k, f in enumerate(it["fixes"]):
                v = S.M.full(f + "^")
                out = (HERE / "runs" / f"{v[:12]}.json") if n == "analysis" else (HERE / "sealed" / f"p{i}_{k}.json")
                jobs.append((n, i, k, v, out))
    (HERE / "runs").mkdir(exist_ok=True)
    (HERE / "sealed").mkdir(exist_ok=True)
    log = open(HERE / "sealed/effzero_runs.log", "a")
    todo = [j for j in jobs if not j[4].exists()]
    print("versions", len(jobs), "to run", len(todo), flush=True)
    running, done = [], 0
    while todo or running:
        still = []
        for pr in running:
            if pr.poll() is None:
                still.append(pr)
            else:
                done += 1
                print(f"  finished {done}/{len(todo) + done + len(still)} rc {pr.returncode} {round(time.time() - t0)}s", flush=True)
        running = still
        while todo and len(running) < 4:
            n, i, k, v, out = todo.pop(0)
            running.append(subprocess.Popen([sys.executable, str(EZ / "effzero.py"), "run", v, str(out)], stdout=log,
                                            stderr=subprocess.STDOUT))
        time.sleep(5)
    # score
    ref = json.loads((CT / "scan3_20261119/eval_summary.json").read_text(encoding="utf-8"))
    summ, arows = {}, []
    for n, s in sets.items():
        per, sizes = [], []
        for i, it in enumerate(s["positives"]):
            names = {fn for _, fn in it.get("fix_funcs", [])}
            used = bool(it.get("used"))
            used_ez = used or any(f[:12] in EXTRA_USED for f in it["fixes"])
            r = {"base": False, "ez": False, "used": used, "used_ez": used_ez}
            ezh = []
            for k, f in enumerate(it["fixes"]):
                v = S.M.full(f + "^")
                rows, st = S.rows_of(v)
                if any(x["func"] in names for x in rows):
                    r["base"] = True
                out = (HERE / "runs" / f"{v[:12]}.json") if n == "analysis" else (HERE / "sealed" / f"p{i}_{k}.json")
                ez = json.loads(out.read_text())["cands"]
                sizes.append(len(ez))
                h = [c for c in ez if c["func"] in names or (c.get("origin") and c["origin"] in names)]
                if h:
                    r["ez"] = True
                    ezh += h
            if n == "analysis":
                arows.append({"commit": it["commit"][:12], "short": it.get("short"), "used": used, "used_ez": used_ez,
                              "base": r["base"], "ez": r["ez"],
                              "ez_hits": [f"{c['form']} {c['file']}:{c['line']} {c['func']} origin={c.get('origin')} rank={c['rank']}" for c in ezh[:5]]})
            per.append(r)

        def cnt(rs, key):
            return sum(1 for r in rs if (r["base"] if key == "base" else r["ez"] if key == "ez" else (r["base"] or r["ez"])))
        all_, clean_b = per, [r for r in per if not r["used"]]
        clean_e = [r for r in per if not r["used_ez"]]
        summ[n] = {"pos": len(per),
                   "all": {"base": cnt(all_, "base"), "ez": cnt(all_, "ez"), "union": cnt(all_, "union")},
                   "clean_baseline_def": {"pos": len(clean_b), "base": cnt(clean_b, "base")},
                   "clean_ez_def": {"pos": len(clean_e), "base": cnt(clean_e, "base"), "ez": cnt(clean_e, "ez"),
                                    "union": cnt(clean_e, "union")},
                   "ez_cands_median": statistics.median(sizes) if sizes else None, "ez_cands_max": max(sizes) if sizes else None,
                   "baseline_matches_scan3": cnt(all_, "base") == ref[n]["all"]["hit"] and cnt(clean_b, "base") == ref[n]["clean"]["hit"]}
    summ["secs"] = round(time.time() - t0)
    (HERE / "summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False))
    (HERE / "analysis_rows.json").write_text(json.dumps(arows, indent=1, ensure_ascii=False))
    print(json.dumps(summ, indent=1, ensure_ascii=False))
    print("analysis rows with any hit:")
    for r in arows:
        if r["base"] or r["ez"]:
            print(" ", r)


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    if sys.argv[1] == "run":
        main()
