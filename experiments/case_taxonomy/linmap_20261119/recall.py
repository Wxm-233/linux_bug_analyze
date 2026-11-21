"""linmap criteria 三.4: recall on independently mined samples (adjudicated 'yes'). WSL.

    python3 recall.py runall [N]   -> runs `linmap.py engine F^` for every adjudicated fix, N parallel (cache LM)
    python3 recall.py score        -> recall.json: hit = a candidate on F^ lies in a function the fix F touches
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "commitmode_20261117"))
import dataset as DSET  # noqa: E402  (read-only: touched_funcs)
import linmap as L  # noqa: E402


def samples():
    adj = json.loads((HERE / "adjudication.json").read_text(encoding="utf-8"))
    rows = json.loads((HERE / "mined.json").read_text())["rows"]
    return [dict(rows[a["n"] - 1], n=a["n"]) for a in adj if a["final"] == "yes"]


def runall(n=4):
    todo = []
    for s in samples():
        rev = L.full(s["commit"] + "^")
        if rev and not (L.CACHE / f"{rev}.json").exists() and rev not in todo:
            todo.append(rev)
    log = open(HERE / "recall_runall.log", "a")
    print(f"start {len(todo)} LM jobs", file=log, flush=True)
    running, t0 = [], time.time()
    while todo or running:
        running = [p for p in running if p.poll() is None]
        while todo and len(running) < n:
            running.append(subprocess.Popen([sys.executable, str(HERE / "linmap.py"), "engine", todo.pop(0)], stdout=log, stderr=subprocess.STDOUT))
        print(f"{round(time.time() - t0)}s todo={len(todo)} running={len(running)}", file=log, flush=True)
        time.sleep(15)
    print("all done", round(time.time() - t0), file=log, flush=True)


def score():
    out = []
    for s in samples():
        rev = L.full(s["commit"] + "^")
        p = L.CACHE / f"{rev}.json"
        r = json.loads(p.read_text()) if p.exists() else None
        funcs = {fn for _, fn in DSET.touched_funcs(L.full(s["commit"]))}
        if r is None or not r["ok"]:
            out.append({"n": s["n"], "commit": s["commit"], "subject": s["subject"], "status": "error" if r else "missing"})
            continue
        hits = [c for c in r["cands"] if c["func"] in funcs]
        out.append({"n": s["n"], "commit": s["commit"], "subject": s["subject"], "status": "ok", "n_cands": r["n"],
                    "hit": bool(hits), "hits": [f"{c['file']}:{c['line']} {c['func']} {c['sig']}" for c in hits][:5],
                    "fix_funcs": sorted(funcs)[:8]})
    ok = [x for x in out if x["status"] == "ok"]
    res = {"n": len(out), "ok": len(ok), "hit": sum(x["hit"] for x in ok), "rows": out}
    (HERE / "recall.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(f"recall {res['hit']}/{res['ok']} (samples {res['n']})")
    for x in out:
        print(f"  {x['n']:03d} {x['commit']} {'HIT ' if x.get('hit') else ('-   ' if x['status'] == 'ok' else x['status'])} "
              f"{x['subject'][:70]} {x.get('hits', [])[:2]} cands={x.get('n_cands')}")


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    {"runall": lambda: runall(int(sys.argv[2]) if len(sys.argv) > 2 else 4), "score": score}[sys.argv[1]]()
