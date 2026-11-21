"""capguard criteria 三.3/三.5: recall on adjudicated mined samples. WSL.

    python3 recall.py runall [N]   -> capguard.py engine F^ for each adjudicated 'yes' fix (cache CAP)
    python3 recall.py score        -> recall.json. aligned = candidate in a file the fix touches AND the fix's added lines use its predicate
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import capguard as G  # noqa: E402


def samples():
    adj = json.loads((HERE / "adjudication.json").read_text(encoding="utf-8"))
    rows = json.loads((HERE / "mined.json").read_text())["rows"]
    return [dict(rows[a["n"] - 1], n=a["n"]) for a in adj if a["final"] == "yes"]


def runall(n=4):
    todo = [G.full(s["commit"] + "^") for s in samples()]
    todo = [r for i, r in enumerate(todo) if r and r not in todo[:i] and not (G.CACHE / f"{r}.json").exists()]
    log = open(HERE / "recall_runall.log", "a")
    print(f"start {len(todo)} CAP jobs", file=log, flush=True)
    running, t0 = [], time.time()
    while todo or running:
        running = [p for p in running if p.poll() is None]
        while todo and len(running) < n:
            running.append(subprocess.Popen([sys.executable, str(HERE / "capguard.py"), "engine", todo.pop(0)], stdout=log, stderr=subprocess.STDOUT))
        time.sleep(5)
    print("all done", round(time.time() - t0), file=log, flush=True)


def added_lines(fix):
    files, cur, add = set(), None, []
    for ln in G.git("show", "--format=", "-U0", fix).split("\n"):
        if ln.startswith("+++ b/"):
            cur = ln[6:]
            files.add(cur)
        elif cur and ln.startswith("+") and not ln.startswith("+++"):
            add.append(ln[1:])
    return files, "\n".join(add)


def score():
    out = []
    for s in samples():
        fix = G.full(s["commit"])
        rev = G.full(fix + "^")
        p = G.CACHE / f"{rev}.json"
        r = json.loads(p.read_text()) if p.exists() else None
        if r is None or not r["ok"]:
            out.append({"n": s["n"], "commit": s["commit"], "subject": s["subject"], "status": "error" if r else "missing"})
            continue
        files, added = added_lines(fix)
        al = [c for c in r["cands"] if c["file"] in files and re.search(r"\b" + re.escape(c["pred"]) + r"\s*\(", added)]
        out.append({"n": s["n"], "commit": s["commit"], "subject": s["subject"], "status": "ok", "n_cands": r["n"], "hit": bool(al),
                    "hits": [f"{c['file']}:{c['line']} {c['func']} {c['sig']}" for c in al][:5], "preds_in_set": len(r["info"].get("pred_info", {}))})
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
