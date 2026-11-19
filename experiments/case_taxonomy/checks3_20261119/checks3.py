"""checks3 criteria 一-四: group the existing commit-level engines into the three checks. No rule is changed: every engine's
"new candidates" and "aligned" decisions come from that engine's own round (read-only imports, or the scoring lines copied).

    python3 checks3.py score              -> results.json, report.md, verify.json  (dev + held-out sets, cached results only)
    python3 checks3.py commit <commit>    -> grouped report for one commit (runs missing engine jobs, held-out settings)
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
for d in ("commitmode_20261117", "commitmode_tlb_20261117", "ctxeff_20261118", "weakov2_20261118", "xvatom2_20261119"):
    sys.path.insert(0, str(CT / d))
import commitmode as M  # noqa: E402
import engines as E  # noqa: E402
import cmtlb as TLB  # noqa: E402
import ctxeval as CE  # noqa: E402
import weakov2 as WK  # noqa: E402
import xvatom2 as XA2  # noqa: E402

XA = XA2.X
M.HERE = HERE                         # criteria 一: check() writes report/ here, not into the old round
CE.CACHE = Path("/root/work/commitmode_cache/CTX3")
_extra_orig = M.extra_of

GROUPS = {"类型一致性检查": ["WT", "ORD"], "实现一致性检查": ["P1", "XV", "TLB", "WK", "XA"], "调用上下文检查": ["CTX"]}
CHECK_OF = {e: g for g, es in GROUPS.items() for e in es}
ENGINES = [e for es in GROUPS.values() for e in es]
DEV, HO = CT / "commitmode_20261117", CT / "heldout_commit_20261117"


def set_variant(name):
    """held-out: more than 30 out-of-scope directories -> base scope only (heldout_run.extra_capped)"""
    if name == "heldout":
        M.extra_of = lambda c: (lambda ex: [] if len(ex) > 30 else ex)(_extra_orig(c))
    else:
        M.extra_of = _extra_orig


def cand(engine, x):
    return {"check": CHECK_OF[engine], "engine": engine, "file": x.get("file", ""), "func": x.get("func", x.get("hook", "")),
            "line": x.get("line", 0), "sig": x.get("sig") or f"{x.get('hook')}|{x.get('arch')}|{x.get('effect')}"}


# ---------------------------------------------------------------- adapters (one per engine round)
def base4(c, names, run_missing):
    """P1/XV/ORD/WT via commitmode.check(); alignment as in commitmode.score()/heldout_run.score()"""
    r = M.check(c, run_missing=run_missing)
    out = {}
    for e in M.ENGS:
        st = r["engines"][e]["status"]
        new = [x for x in r["new"] if x["engine"] == e]
        al = [x for x in new if x["func"] in names or
              (e == "WT" and x["sig"].startswith("A|arg:") and x["sig"].split("|")[1][4:].split("#")[0] in names)]
        out[e] = {"status": st, "new": [cand(e, x) for x in new], "aligned": bool(al),
                  "noA": any(not (e == "WT" and x["sig"].startswith("A|")) for x in new)}
    return out


def tlb(c, names):
    st, new = TLB.tlb_new(c)
    return {"status": st, "new": [cand("TLB", x) for x in new], "aligned": any(x["func"] in names for x in new), "noA": bool(new)}


def ctx(c, names_fix):
    """copied from ctxeff_20261118/ctxeval.py score(): key-set difference, Fixes reverse lookup for alignment"""
    c = M.full(c)
    if not CE.TL.touches(c):
        return {"status": "skip", "new": [], "aligned": False, "noA": False}
    p, q = (CE.CACHE / f"{x}.json" for x in (M.full(c + "^"), c))
    if not p.exists() or not q.exists():
        return {"status": "未评估", "new": [], "aligned": False, "noA": False}
    pr, cr = json.loads(p.read_text()), json.loads(q.read_text())
    if not pr["ok"] or not cr["ok"]:
        return {"status": "error", "new": [], "aligned": False, "noA": False}
    pk = {CE.key(x) for x in pr["cands"]}
    new = [x for x in cr["cands"] if CE.key(x) not in pk]
    names = set(names_fix or ())
    if names_fix is not None:
        for f in CE.A.fixes_for(c)[:12]:
            names |= {fn for _, fn in CE.A.DSET.touched_funcs(f)}
    return {"status": "ok", "new": [cand("CTX", x) for x in new], "aligned": any(x["hook"] in names for x in new), "noA": bool(new)}


def wk(c, names):
    st, new = WK.wk_new(c)
    return {"status": st, "new": [cand("WK", x) for x in new], "aligned": any(x["func"] in names for x in new), "noA": bool(new)}


def xa(c, names):
    c = M.full(c)
    if not XA.touches(c):
        return {"status": "skip", "new": [], "aligned": False, "noA": False}
    res = []
    for r in (M.full(c + "^"), c):
        p = XA.CACHE / f"{r}.json"
        res.append(json.loads(p.read_text()) if p.exists() else None)
    if any(x is None for x in res):
        return {"status": "未评估", "new": [], "aligned": False, "noA": False}
    if not all(x["ok"] for x in res):
        return {"status": "error", "new": [], "aligned": False, "noA": False}
    new = M.compare({"cands": res[0]["cands"]}, {"cands": res[1]["cands"]}, M.renames(c))
    return {"status": "ok", "new": [cand("XA", x) for x in new], "aligned": any(x["func"] in names for x in new), "noA": bool(new)}


def grouped(c, kind, names, run_missing=False):
    eng = base4(c, names, run_missing)
    eng["TLB"] = tlb(c, names)
    eng["CTX"] = ctx(c, names if kind == "pos" else None)
    eng["WK"] = wk(c, names)
    eng["XA"] = xa(c, names)
    checks = {}
    for g, es in GROUPS.items():
        checks[g] = {"engines": {e: {k: eng[e][k] for k in ("status", "aligned")} | {"n_new": len(eng[e]["new"])} for e in es},
                     "flag": any(eng[e]["new"] for e in es), "aligned": kind == "pos" and any(eng[e]["aligned"] for e in es),
                     "cands": [x for e in es for x in eng[e]["new"]]}
    return {"commit": M.full(c)[:12], "kind": kind, "checks": checks, "flag": any(v["flag"] for v in checks.values()),
            "flag_noA": any(eng[e]["noA"] for e in ENGINES),
            "aligned": kind == "pos" and any(v["aligned"] for v in checks.values()), "_eng": eng}


# ---------------------------------------------------------------- verification against each round's stored results (criteria 四)
def stored():
    s = {}
    for name, p in (("dev", DEV / "results.json"), ("heldout", HO / "results.json")):
        for r in json.loads(p.read_text(encoding="utf-8"))["rows"]:
            hits = {h.split(" ")[0] for h in r.get("aligned_hits", [])}
            for e in M.ENGS:
                st = r["engines"][e]["status"]
                s[(name, r["commit"][:12], e)] = {"status": st, "n_new": sum(1 for x in r["new"] if x["engine"] == e),
                                                  "aligned": e in hits if r["kind"] == "pos" else None}
    t = json.loads((CT / "commitmode_tlb_20261117/results.json").read_text(encoding="utf-8"))
    for name in ("dev", "heldout"):
        for r in t[name]["rows"]:
            s[(name, r["commit"][:12], "TLB")] = {"status": r["tlb_status"], "n_new": len(r["tlb_new"]),
                                                  "aligned": r["tlb_aligned"] if r["kind"] == "pos" else None}
    for r in json.loads((CT / "ctxeff3_20261118/heldout_eval.json").read_text(encoding="utf-8"))["rows"]:
        s[("heldout", r["commit"][:12], "CTX")] = {"status": r["status"], "n_new": len(r["new"]),
                                                   "aligned": r.get("aligned") if r["kind"] == "pos" else None}
    for eng, p in (("WK", CT / "weakov2_20261118/cm_results.json"), ("XA", CT / "xvatom2_20261119/cm_results.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        for name in ("dev", "heldout"):
            for r in d[name]["rows"]:
                s[(name, r["commit"][:12], eng)] = {"status": r["status"], "n_new": len(r["new"]),
                                                    "aligned": r.get("aligned") if (r["kind"] == "pos" and "aligned" in r) else None}
    return s


def datasets():
    return {"dev": json.loads((DEV / "dataset.json").read_text()), "heldout": json.loads((HO / "heldout_set.json").read_text())}


def summarize(rows, engines_of=None):
    P = [r for r in rows if r["kind"] == "pos"]
    N = [r for r in rows if r["kind"] == "neg"]
    out = {"all": {"pos": len(P), "neg": len(N), "pos_flag": sum(r["flag"] for r in P), "pos_aligned": sum(r["aligned"] for r in P),
                   "neg_flag": sum(r["flag"] for r in N), "neg_flag_noA": sum(r["flag_noA"] for r in N)}}
    for g, es in GROUPS.items():
        out[g] = {"pos_flag": sum(r["checks"][g]["flag"] for r in P), "pos_aligned": sum(r["checks"][g]["aligned"] for r in P),
                  "neg_flag": sum(r["checks"][g]["flag"] for r in N),
                  "engines": {e: {"pos_flag": sum(bool(r["_eng"][e]["new"]) for r in P), "pos_aligned": sum(r["_eng"][e]["aligned"] for r in P),
                                  "neg_flag": sum(bool(r["_eng"][e]["new"]) for r in N),
                                  "未评估": sum(r["_eng"][e]["status"] == "未评估" for r in P + N),
                                  "error": sum(r["_eng"][e]["status"] == "error" for r in P + N)} for e in es}}
    return out


def score():
    ref = stored()
    res, mism, compared = {}, [], 0
    for name, ds in datasets().items():
        set_variant(name)
        rows = []
        for kind, items in (("pos", ds["positives"]), ("neg", ds["negatives"])):
            for it in items:
                names = {fn for _, fn in it.get("fix_funcs", [])}
                r = grouped(it["commit"], kind, names)
                rows.append(r)
                for e in ENGINES:
                    k = (name, r["commit"], e)
                    if k not in ref:
                        continue
                    a, b = r["_eng"][e], ref[k]
                    got = {"status": a["status"], "n_new": len(a["new"]), "aligned": a["aligned"] if kind == "pos" else None}
                    compared += 1
                    for f in ("status", "n_new", "aligned"):
                        if b[f] is None or got[f] is None:
                            continue
                        if got[f] != b[f]:
                            mism.append({"set": name, "commit": r["commit"], "engine": e, "field": f, "now": got[f], "stored": b[f]})
        s = {"summary": summarize(rows), "rows": rows}
        if name == "heldout":
            clean = [r for r in rows if not (r["kind"] == "pos" and r["commit"] in TLB.TAINTED)]
            s["clean"] = summarize(clean)
        res[name] = s
    set_variant("dev")
    (HERE / "verify.json").write_text(json.dumps({"compared": compared, "mismatches": mism}, indent=1, ensure_ascii=False))
    out = {k: {kk: vv for kk, vv in v.items() if kk != "rows"} | {"rows": [{kk: vv for kk, vv in r.items() if kk != "_eng"} for r in v["rows"]]}
           for k, v in res.items()}
    (HERE / "results.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print("verify: compared", compared, "engine-commit pairs, mismatches", len(mism))
    for m in mism[:30]:
        print("  MISMATCH", m)
    for name, v in res.items():
        for part in [p for p in ("summary", "clean") if p in v]:
            s = v[part]
            a = s["all"]
            print(f"\n[{name}/{part}] pos {a['pos']} flagged {a['pos_flag']} aligned {a['pos_aligned']} | neg {a['neg']} flagged {a['neg_flag']} (noA {a['neg_flag_noA']})")
            for g in GROUPS:
                x = s[g]
                print(f"  {g}: pos flagged {x['pos_flag']} aligned {x['pos_aligned']} | neg flagged {x['neg_flag']}")
                for e, y in x["engines"].items():
                    print(f"      {e:4s} pos {y['pos_flag']}/{y['pos_aligned']}  neg {y['neg_flag']}  未评估 {y['未评估']}  error {y['error']}")
    return res, mism


# ---------------------------------------------------------------- one commit (criteria 五)
def ensure(c):
    """run missing engine jobs with each engine's own entry point"""
    c = M.full(c)
    revs = (M.full(c + "^"), c)
    for e, rev, x in M.jobs_of(c):
        if not E.cache_path(e, rev, x).exists():
            subprocess.run([sys.executable, str(DEV / "engines.py"), e, rev, *x], check=False)
    for rev in revs:
        if TLB.touches(c) and not (TLB.CACHE / f"{rev}.json").exists():
            subprocess.run([sys.executable, str(CT / "commitmode_tlb_20261117/cmtlb.py"), "engine", rev], check=False)
        if CE.TL.touches(c) and not (CE.CACHE / f"{rev}.json").exists():
            subprocess.run([sys.executable, str(CT / "ctxeff3_20261118/ctxeff3.py"), "engine", rev], check=False)
        if WK.touches(c) and not (WK.CACHE / f"{rev}.json").exists():
            subprocess.run([sys.executable, str(CT / "weakov2_20261118/weakov2.py"), "engine", rev], check=False)
        if XA.touches(c) and not (XA.CACHE / f"{rev}.json").exists():
            subprocess.run([sys.executable, str(CT / "xvatom2_20261119/xvatom2.py"), "engine", rev], check=False)


def cmd_commit(c):
    set_variant("heldout")
    ensure(c)
    r = grouped(c, "neg", set())
    print("commit", r["commit"], M.git("log", "-1", "--format=%s", M.full(c)).strip(), "| flagged" if r["flag"] else "| not flagged")
    for g, v in r["checks"].items():
        print(f"  {g}: {'报出' if v['flag'] else '无'}  " + "  ".join(f"{e}={x['status']}/{x['n_new']}" for e, x in v["engines"].items()))
        for x in v["cands"][:10]:
            print(f"      {x['engine']} {x['file']}:{x['line']} {x['func']} {x['sig'][:90]}")
    (HERE / "commits").mkdir(exist_ok=True)
    (HERE / "commits" / f"{r['commit']}.json").write_text(json.dumps({k: v for k, v in r.items() if k != "_eng"}, indent=1, ensure_ascii=False))


def ctx_dev_revs():
    """dev-set revisions CTX needs (same touch rule as ctxeval.revs(), which only covered the held-out set)"""
    out = []
    for it in datasets()["dev"]["positives"] + datasets()["dev"]["negatives"]:
        c = M.full(it["commit"])
        if CE.TL.touches(c):
            for r in (M.full(c + "^"), c):
                if r not in out:
                    out.append(r)
    return out


def ctx_dev_runall(n=4):
    """user: 补跑 CTX. Runs ctxeff3.py engine (CTX v3, cache CTX3) for missing dev revisions."""
    import time
    todo = [r for r in ctx_dev_revs() if not (CE.CACHE / f"{r}.json").exists()]
    log = open(HERE / "ctx_dev_runall.log", "a")
    print(f"start {len(todo)} CTX3 dev jobs", file=log, flush=True)
    running, t0 = [], time.time()
    while todo or running:
        running = [pr for pr in running if pr.poll() is None]
        while todo and len(running) < n:
            running.append(subprocess.Popen([sys.executable, str(CT / "ctxeff3_20261118/ctxeff3.py"), "engine", todo.pop(0)],
                                            stdout=log, stderr=subprocess.STDOUT))
        print(f"{round(time.time() - t0)}s todo={len(todo)} running={len(running)}", file=log, flush=True)
        time.sleep(15)
    print("all done", round(time.time() - t0), file=log, flush=True)


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    cmd = sys.argv[1]
    if cmd == "score":
        score()
    elif cmd == "ctxdev":
        revs = ctx_dev_revs()
        print(len(revs), "dev revisions,", sum(not (CE.CACHE / f"{r}.json").exists() for r in revs), "missing")
    elif cmd == "ctxdev_runall":
        ctx_dev_runall(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    elif cmd == "commit":
        cmd_commit(sys.argv[2])
