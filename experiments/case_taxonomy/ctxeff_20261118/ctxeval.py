"""ctxeff criteria 五.4: CTX engine in commit-level mode on the held-out set (run once, after the rules were frozen). WSL.

    python3 ctxeval.py engine <rev>   -> /root/work/commitmode_cache/CTX/<rev>.json
    python3 ctxeval.py runall [N]     -> all held-out revs that need it, N parallel
    python3 ctxeval.py score          -> heldout_eval.json, heldout_eval.log
Signature (hook, arch, effect); new = child signatures not in parent. Alignment: hook name in the functions touched by any
fix whose Fixes: points to the commit, or in the data set's fix_funcs (archsig_20261118.fixes_for / dataset.touched_funcs).
"""
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
for d in ("ctxeff_20261118", "archsig_20261118"):
    sys.path.insert(0, str(CT / d))
import ctxeff as X  # noqa: E402
import archsig as A  # noqa: E402

M, TL = A.M, A.TL
CACHE = Path("/root/work/commitmode_cache/CTX")


def engine(rev):
    p = CACHE / f"{rev}.json"
    if p.exists():
        return json.loads(p.read_text())
    t0 = time.time()
    try:
        if M.full(rev) != rev:
            raise ValueError(f"not a full commit id: {rev}")
        cands, info = X.run(rev)
        if len(info["archs"]) < 10:
            raise ValueError("too few architectures read")
        res = {"rev": rev, "ok": True, "n": len(cands), "secs": round(time.time() - t0, 1),
               "cands": [{"hook": c["hook"], "arch": c["arch"], "effect": c["effect"], "minority": c["minority"], "site": c["site"],
                          "witness": c["witness"]} for c in cands]}
    except Exception:
        res = {"rev": rev, "ok": False, "error": traceback.format_exc()[-2000:], "secs": round(time.time() - t0, 1)}
    CACHE.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res))
    return res


def heldout():
    return json.loads((CT / "heldout_commit_20261117" / "heldout_set.json").read_text())


def revs():
    out = []
    ho = heldout()
    for it in ho["positives"] + ho["negatives"]:
        c = M.full(it["commit"])
        if TL.touches(c):
            for r in (M.full(c + "^"), c):
                if r not in out:
                    out.append(r)
    return out


def runall(n=5):
    todo = [r for r in revs() if not (CACHE / f"{r}.json").exists()]
    log = open(HERE / "ctxeval_runall.log", "a")
    print(f"start {len(todo)} CTX jobs", file=log, flush=True)
    running, t0 = [], time.time()
    while todo or running:
        running = [pr for pr in running if pr.poll() is None]
        while todo and len(running) < n:
            running.append(subprocess.Popen([sys.executable, str(HERE / "ctxeval.py"), "engine", todo.pop(0)], stdout=log, stderr=subprocess.STDOUT))
        print(f"{round(time.time() - t0)}s todo={len(todo)} running={len(running)}", file=log, flush=True)
        time.sleep(15)
    print("all done", round(time.time() - t0), file=log, flush=True)


def key(c):
    return (c["hook"], c["arch"], c["effect"])


def score():
    ho = heldout()
    rows = []
    for kind, items in (("pos", ho["positives"]), ("neg", ho["negatives"])):
        for it in items:
            c = M.full(it["commit"])
            r = {"commit": c[:12], "kind": kind, "categories": it.get("categories"), "tainted": c[:12] in TL.TAINTED,
                 "info": M.git("log", "-1", "--format=%h|%cs|%s", c).strip()}
            if not TL.touches(c):
                r.update(status="skip", new=[])
            else:
                pr, cr = (json.loads((CACHE / f"{x}.json").read_text()) if (CACHE / f"{x}.json").exists() else None for x in (M.full(c + "^"), c))
                if not pr or not cr or not pr["ok"] or not cr["ok"]:
                    r.update(status="error", new=[])
                else:
                    pk = {key(x) for x in pr["cands"]}
                    r.update(status="ok", new=[x for x in cr["cands"] if key(x) not in pk])
            r["flag"] = bool(r["new"])
            r["flag_minority"] = any(x["minority"] for x in r["new"])
            if kind == "pos":
                names = {fn for _, fn in it.get("fix_funcs", [])}
                for f in A.fixes_for(c)[:12]:
                    names |= {fn for _, fn in A.DSET.touched_funcs(f)}
                r["aligned"] = any(x["hook"] in names for x in r["new"])
            rows.append(r)
    P = [r for r in rows if r["kind"] == "pos"]
    N = [r for r in rows if r["kind"] == "neg"]
    clean = [r for r in P if not r["tainted"]]
    s = {"pos_clean": len(clean), "recall_clean": sum(r["flag"] for r in clean), "aligned_clean": sum(r["aligned"] for r in clean),
         "neg": len(N), "fp": sum(r["flag"] for r in N), "fp_minority": sum(r["flag_minority"] for r in N),
         "errors": sum(r["status"] == "error" for r in rows), "skipped": sum(r["status"] == "skip" for r in rows),
         "p5": [{k: r[k] for k in ("commit", "info", "flag", "aligned", "status")} | {"new": r["new"][:6]} for r in P if "P5" in (r["categories"] or [])]}
    (HERE / "heldout_eval.json").write_text(json.dumps({"summary": s, "rows": rows}, indent=1, ensure_ascii=False))
    lines = [json.dumps({k: v for k, v in s.items() if k != "p5"}, ensure_ascii=False)]
    for r in s["p5"]:
        lines.append(f"P5 {r['info'][:70]} status={r['status']} flag={r['flag']} aligned={r['aligned']}")
        lines += [f"     new {x['hook']} {x['arch']} {x['effect']} {'MIN' if x['minority'] else ''} via {'->'.join(x['witness'])[:80]}" for x in r["new"]]
    for r in rows:
        if r["flag"] and "P5" not in (r["categories"] or []):
            lines.append(f"{r['kind']} {'T' if r['tainted'] else ' '} flag aligned={r.get('aligned')} {r['info'][:60]}")
            lines += [f"     new {x['hook']} {x['arch']} {x['effect']} {'MIN' if x['minority'] else ''}" for x in r["new"][:5]]
    (HERE / "heldout_eval.log").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    cmd = sys.argv[1]
    if cmd == "engine":
        r = engine(sys.argv[2])
        print("CTX", sys.argv[2][:12], "ok" if r["ok"] else "ERROR", r.get("n"), r["secs"], "s", (r.get("error") or "")[-300:], flush=True)
    elif cmd == "runall":
        runall(int(sys.argv[2]) if len(sys.argv) > 2 else 5)
    elif cmd == "score":
        score()
