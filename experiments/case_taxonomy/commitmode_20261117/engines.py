"""commitmode: one engine per check line, each a read-only import of that line's official version. WSL, no build.

    python3 engines.py <engine> <rev> [extra_dir ...]     -> /root/work/commitmode_cache/<engine>/<rev>[__extra].json

engines:
  P1   effect dependency, direct calls (reachgap_20261116 = official reachability filter)
  XV   effect dependency, horizontal domains (xvdom_20261116) + interface lifting (xvlift_20261116)
  ORD  page-size-derived order x page-cache limit (orddom_20261116)
  WT   width truncation (widthtrunc3_20261117)
Each candidate: {engine, file, func, line, sig}; sig carries no line numbers (used to match C^ against C).
"""
import hashlib
import json
import re
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
CACHE = Path("/root/work/commitmode_cache")


def norm(s):
    return re.sub(r"\s+", "", str(s))


def eng_P1(rev, extra):
    sys.path.insert(0, str(CT / "reachgap_20261116"))
    import reachgap as G
    blobs = G.R.blobs_of(rev, extra)
    fns = G.S.analyze_all(blobs)
    rows = G.candidates(fns, G.R.RESTR | G.R.OLD_NAMES, G.D.Dead(fns, blobs, rev))
    return [{"file": r["file"], "func": r["func"], "line": r["line"], "sig": f"{r['A']}|{norm(r['canon'])}"}
            for r in rows if r["filtered"] is None], len(blobs)


def eng_XV(rev, extra):
    sys.path.insert(0, str(CT / "xvlift_20261116"))
    import xvlift as L
    X, R, S, D, K, C = L.X, L.R, L.S, L.D, L.K, L.C
    for o, n in X.OLD.items():                       # renamed interfaces, as in xvdom recall()
        X.GROUP[o] = X.GROUP[n]
        X.TABLE[o] = X.TABLE[n]
        X.NAMES[X.GROUP[n]].add(o)
    blobs = R.blobs_of(rev, extra)
    mmh = [p for p in C.git("ls-tree", "-r", "--name-only", rev, "--", "mm").split("\n") if p.endswith(".h")]
    blobs.update(C.cat_files(rev, mmh))
    fns = S.analyze_all(blobs)
    dead = D.Dead(fns, blobs, rev)
    out = []
    for r in X.candidates(fns, dead):
        if r["filtered"] is None and r["horizontal"] and K.in_scope(r["file"], extra):
            out.append({"file": r["file"], "func": r["func"], "line": r["line"], "sig": f"dom|{r['A']}|{norm(r['canon'])}"})
    lifted, consumed = L.lift(fns, blobs, dead)
    for r in L.candidates(fns, lifted, consumed, dead):
        if r["A"] in L.TABLE:
            out.append({"file": r["file"], "func": r["func"], "line": r["line"], "sig": f"lift|{r['H']}@{r['arg']}|{r['A']}|{norm(r['obj'])}"})
    return out, len(blobs)


def eng_ORD(rev, extra):
    sys.path.insert(0, str(CT / "orddom_20261116"))
    import orddom as O
    blobs = O.blobs_of(rev)
    rows, _ = O.analyze(blobs)
    return [{"file": r["file"], "func": r["func"], "line": r["line"], "sig": "|".join(r["sources"])} for r in O.candidates(rows)], len(blobs)


def eng_WT(rev, extra):
    sys.path.insert(0, str(CT / "widthtrunc3_20261117"))
    import widthtrunc3 as T
    rows, _, _, _ = T.analyze3(rev)
    return [{"file": r["file"], "func": r["func"], "line": r["line"], "sig": f"{r['form']}|{r['where']}|{norm(r['text'])}"}
            for r in T.candidates(rows)], None


ENGINES = {"P1": eng_P1, "XV": eng_XV, "ORD": eng_ORD, "WT": eng_WT}


def cache_path(engine, rev, extra):
    tag = rev + ("__" + hashlib.sha1("|".join(sorted(extra)).encode()).hexdigest()[:10] if extra and engine in ("P1", "XV") else "")
    return CACHE / engine / f"{tag}.json"


def run(engine, rev, extra=()):
    p = cache_path(engine, rev, extra)
    if p.exists():
        return json.loads(p.read_text())
    t0 = time.time()
    try:
        cands, nfiles = ENGINES[engine](rev, tuple(extra))
        res = {"engine": engine, "rev": rev, "extra": list(extra), "ok": True, "n": len(cands), "files": nfiles,
               "secs": round(time.time() - t0, 1), "cands": cands}
    except Exception:
        res = {"engine": engine, "rev": rev, "extra": list(extra), "ok": False, "error": traceback.format_exc()[-2000:],
               "secs": round(time.time() - t0, 1), "cands": []}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res))
    return res


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    eng, rev, *extra = sys.argv[1:]
    r = run(eng, rev, extra)
    print(eng, rev, "ok" if r["ok"] else "ERROR", r.get("n"), "cands", r["secs"], "s", (r.get("error") or "")[-300:])
