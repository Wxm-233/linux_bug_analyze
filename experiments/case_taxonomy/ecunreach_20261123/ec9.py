"""ecunreach criteria 二: ecsrc's EC (ecsrc_20261123/ec8.py) + three infrastructure changes around __builtin_unreachable. Judging rules
unchanged. WSL.

  1. reaching __builtin_unreachable raises a distinct "unreachable path" (behaviour "unreachable", not "unsup");
  2. an if whose condition is unknown: a branch that reaches unreachable is dropped (only the other branch is taken);
  3. runtime-combination merge: "unreachable" combinations do not take part; all unreachable -> "not-applicable"; on builds without
     runtime combinations "unreachable" -> "not-applicable".

    python3 ec9.py df | changed | parent <hash> | recall | mine <tag> <rev> <b>     (as ec8.py, caches v9 / r9, reuse from v8)
"""
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
for p in ("autoenc_20261122", "ecscan_20261122", "ecnoise_20261122", "ecrecall_20261122", "ecprot_20261122", "ecbuild_20261122",
          "ecpud_20261123", "ecsrc_20261123"):
    sys.path.insert(0, str(CT / p))
import ec8  # noqa: E402
import ec7  # noqa: E402
import ec4  # noqa: E402

V8, V9, R9 = Path("/root/work/ec_cache/v8"), Path("/root/work/ec_cache/v9"), Path("/root/work/ec_cache/r9")
DF = ec8.DF
ec4.VCACHE = V9
ec4.HERE = HERE
ec4.__file__ = str(Path(__file__))
UNREACH = "unreachable path"


def run_build9(b):
    """ecbuild_20261122/ec6.py run_build6 with change 3 (unreachable combinations do not merge)"""
    import mine as M
    A, S = M.A, M.S
    if b in A.ARCHES or b == "ppc64le_hash":
        A.register(b)
    sigs = json.loads((M.HERE / f"sigs_{b}.json").read_text(encoding="utf-8"))
    R = M.roles(sigs)
    weak = M.is_weak(M.level_filter(sigs))
    S.WORK.mkdir(parents=True, exist_ok=True)
    p = Path("/root/work/autoenc") / f"mine_{b}.c"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join([M.HDR, M.CONSTS] + [M.wrapper(r, n, t) + "\n" for r, xs in R.items() for n, t in xs]))
    funcs = M.load(b, p)
    res = {"build": b, "weak_types": weak, "roles": {r: len(xs) for r, xs in R.items()}}
    S.ORACLE.clear()
    S.RUNTIME.clear()

    def once():
        cx = M.Ctx(funcs, b)
        S.DOM.update(tmax=None, ofree=1, omin=0)
        K = {}
        for k in ("MAX", "PAGE_SHIFT", "PMD_SHIFT", "PUD_SHIFT", "PHYS", "MPB"):
            v = cx.call(f"AE_K_{k}", [])
            K[k] = v.const() if isinstance(v, M.SBV) else None
        out = {}
        if None in (K["MAX"], K["PAGE_SHIFT"], K["PHYS"], K["MPB"]):
            return K, {"_error": {"beh": "constants unknown", "K": K}}
        M.sw_family(cx, R, K, out)
        M.pt_family(cx, R, K, out)
        return K, out

    def na(v):
        return dict(v, beh="not-applicable", why="unreachable in every mode") if v.get("beh") == "unreachable" else v
    K0, out0 = once()
    keys = sorted(S.RUNTIME)
    if keys and len(keys) <= 4:
        per = {}
        for vals in itertools.product([False, True], repeat=len(keys)):
            S.ORACLE.clear()
            S.ORACLE.update(zip(keys, vals))
            per[vals] = once()
        S.ORACLE.clear()
        good = {v: ko for v, ko in per.items() if "_error" not in ko[1]}
        use = good or per
        allk = set().union(*[set(o) for _, o in use.values()])
        merged = {}
        for k in allk:
            behs = {v: o.get(k, {}).get("beh") for v, (_, o) in use.items()}
            live = {v: x for v, x in behs.items() if x != "unreachable"}          # change 3
            if not live or all(x is None for x in live.values()):               # amendment 1.1: only in unreachable combos
                one = next(o[k] for _, o in use.values() if k in o)
                merged[k] = dict(one, beh="not-applicable", why="unreachable in every mode", per_combo=None)
                continue
            bs = set(live.values())
            one = next(use[v][1][k] for v in live if k in use[v][1])
            merged[k] = dict(one, beh=bs.pop() if len(bs) == 1 else "runtime-dependent",
                             per_combo=sorted(str(x) for x in set(live.values())) if len(set(live.values())) > 1 else None,
                             unreachable_combos=sorted(str(v) for v in behs if v not in live) or None)
        res.update(runtime=keys, K={str(v): kk for v, (kk, _) in per.items()}, laws=merged,
                   dropped_combos=[str(v) for v in per if v not in good] if good else [])
    else:
        res.update(runtime=keys, K=K0, laws={k: na(v) for k, v in out0.items()})
    (M.HERE / f"beh_{b}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    c = Counter(v["beh"].split(":")[0] for v in res["laws"].values())
    nu = sum(1 for v in res["laws"].values() if v.get("unreachable_combos") or v.get("why") == "unreachable in every mode")
    print(b, "laws", len(res["laws"]), dict(c), "runtime", keys, "dropped", res.get("dropped_combos"), "unreachable_keys", nu, flush=True)


def patch_unreach():
    import mine as M
    S, E = M.S, M.E

    class Unreachable(E.Unsupported):
        pass
    M.Unreachable = Unreachable
    call0 = S.SInterp.call

    def call(self, name, args, depth=0):
        if name == "__builtin_unreachable":                  # change 1
            raise Unreachable(UNREACH)
        return call0(self, name, args, depth)
    S.SInterp.call = call
    stmt0 = M.AInterp.stmt

    def stmt(self, n, env, depth):
        if n.get("kind") != "IfStmt":
            return stmt0(self, n, env, depth)
        cond = self.expr(n["inner"][0], env, depth)            # as evalpg Interp.stmt, plus change 2
        t = cond.truth() if isinstance(cond, S.SBV) else None
        then = n["inner"][1]
        els = n["inner"][2] if len(n["inner"]) > 2 else None
        if t is True:
            return self.stmt(then, env, depth)
        if t is False:
            return self.stmt(els, env, depth) if els else None
        e1, e2 = dict(env), dict(env)
        u1 = u2 = False
        try:
            r1 = self.stmt(then, e1, depth)
        except Unreachable:
            u1, r1 = True, None
        try:
            r2 = self.stmt(els, e2, depth) if els else None
        except Unreachable:
            u2, r2 = True, None
        if u1 and u2:
            raise Unreachable(UNREACH)
        if u1 or u2:
            env.clear()
            env.update(e2 if u1 else e1)
            return r2 if u1 else r1
        self.notes.append("未知条件：两个分支分别求值后合并")
        for key in set(e1) | set(e2):
            if key in e1 and key in e2:
                env[key] = E.join(e1[key], e2[key])
        if r1 is not None and r2 is not None:
            return ("ret", E.join(r1[1], r2[1]))
        if r1 is None and r2 is None:
            return None
        raise E.Unsupported("one-armed return under unknown condition")
    M.AInterp.stmt = stmt
    beh0 = M.behaviour

    def behaviour(v, params, consts):
        if isinstance(v, tuple) and len(v) > 1 and UNREACH in str(v[1]):
            return "unreachable"
        return beh0(v, params, consts)
    M.behaviour = behaviour


def patch():
    ec8.patch()
    import mine as M
    M.run_build = run_build9
    patch_unreach()


def df_run():
    import ec5
    res = ec4.pipeline(DF, DF, None, reuse_from=V8 / DF / DF)
    ec5.R5 = R9
    return ec5.revote(V9 / DF / DF, "df", DF, df=True), res


def df_part(builds):
    """amendment 1: re-mine <builds> at df; the first run is kept in v9/df_run1, the stale behaviour files of <builds> are removed from
    the reuse copy so that a crash shows up as a missing file"""
    import ec5
    import shutil
    bak = V9 / "df_run1"
    if not bak.exists():
        shutil.copytree(V9 / DF, bak)
    reuse = V9 / "df_reuse"
    shutil.rmtree(reuse, ignore_errors=True)
    shutil.copytree(bak / DF, reuse)
    for b in builds:
        (reuse / f"beh_{b}.json").unlink(missing_ok=True)
        (V9 / DF / DF / f"beh_{b}.json").unlink(missing_ok=True)
    res = ec4.pipeline(DF, DF, builds, reuse_from=reuse)
    missing = [b for b in builds if not (V9 / DF / DF / f"beh_{b}.json").exists()]
    print("DFPART missing", missing, flush=True)
    ec5.R5 = R9
    return ec5.revote(V9 / DF / DF, "df", DF, df=True), res


def changed():
    out = {}
    for f in sorted((V9 / DF / DF).glob("beh_*.json")):
        o = V8 / DF / DF / f.name
        A = json.loads(f.read_text())["laws"]
        B = json.loads(o.read_text())["laws"] if o.exists() else {}
        diff = [k for k in set(A) | set(B) if (A.get(k) or {}).get("beh") != (B.get(k) or {}).get("beh")]
        unr = [k for k, v in A.items() if v.get("unreachable_combos") or v.get("why") == "unreachable in every mode"]
        from collections import Counter
        out[f.stem[4:]] = {"changed": len(diff), "unreachable_keys": len(unr),
                           "transitions": dict(Counter(f"{(B.get(k) or {}).get('beh', '-').split(':')[0]}->{(A.get(k) or {}).get('beh', '-').split(':')[0]}"
                                                       for k in diff).most_common(6)),
                           "unreachable_examples": sorted(unr)[:4]}
        print(f.stem[4:], out[f.stem[4:]]["changed"], out[f.stem[4:]]["unreachable_keys"], out[f.stem[4:]]["transitions"])
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "changed_df.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


def parent(h):
    par = ec4.git("rev-parse", "--short=12", f"{h}^")
    ch = json.loads((HERE / "results" / "changed_df.json").read_text(encoding="utf-8"))
    rem = [b for b, v in ch.items() if v["changed"]]
    ok = [b for b in rem if (ec4.VER / par / f"cfg_{b}" / "mm" / ".memory.o.cmd").exists()]
    (V9 / par).mkdir(parents=True, exist_ok=True)
    import shutil                                    # amendment 1.2: no stale behaviour file for the builds being re-mined
    reuse = V9 / f"{par}_reuse"
    shutil.rmtree(reuse, ignore_errors=True)
    shutil.copytree(V8 / par / par, reuse)
    for b in ok:
        (reuse / f"beh_{b}.json").unlink(missing_ok=True)
        (V9 / par / par / f"beh_{b}.json").unlink(missing_ok=True)
    ec4.pipeline(par, par, ok, reuse_from=reuse)
    print("PARENT missing", [b for b in ok if not (V9 / par / par / f"beh_{b}.json").exists()], flush=True)
    ec4.fixed(h)


def recall9():
    ec7.V7, ec7.R7 = V9, R9
    ec7.HERE = HERE
    ec7.recall7()


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    cmd = sys.argv[1]
    patch()
    if cmd == "df":
        df_run()
    elif cmd == "dfpart":
        df_part(sys.argv[2:])
    elif cmd == "changed":
        changed()
    elif cmd == "parent":
        parent(sys.argv[2])
    elif cmd == "mine":
        ec4.mine_one(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "recall":
        recall9()
