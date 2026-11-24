"""ecnoise criteria 二: round-3 EC = round-2 EC (ecscan_20261122/ec.py, imported, not modified) + three noise rules in the mapping
family (constant observers do not vote; PMD/PUD leaf entries go through T_mkhuge; folded levels are not compared). WSL.

    python3 ec3.py engine <rev>          -> /root/work/ec_cache/r3/<full rev>.json  (same format as every other engine)
    python3 ec3.py mine <rev> <build>    -> (internal) one build's behaviours
"""
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ecscan_20261122"))
import ec as EC2  # noqa: E402  (puts autoenc_20261122 on sys.path)

EC2.CACHE = Path("/root/work/ec_cache/r3")        # round 2's cache stays untouched
CACHE = EC2.CACHE

EXTRA = r'''
static __attribute__((used)) unsigned long AE_K_PPMD(void) { return PTRS_PER_PMD; }
static __attribute__((used)) unsigned long AE_K_PPUD(void) { return PTRS_PER_PUD; }
'''


# ---------------------------------------------------------------- mapping family with the three round-3 rules
def pt_family3(cx, R, K, out):
    import mine as M
    SBV, wname = M.SBV, M.wname
    L, PS, MPB, PHYS = cx.L, K["PAGE_SHIFT"], K["MPB"], K["PHYS"]
    prots = [n for n, t in R.get("prot", [])]
    pv = {n: cx.call(wname("prot", n, ""), []) for n in prots}
    pv = {n: p for n, p in pv.items() if not isinstance(p, tuple)}
    # rule 3: folded levels (PTRS_PER_* == 1; not a constant -> not folded)
    folded = {}
    for ct, k in (("pmd_t", "AE_K_PPMD"), ("pud_t", "AE_K_PPUD")):
        v = cx.call(k, [])
        folded[ct] = isinstance(v, SBV) and v.const() == 1
    out["PT|_levels"] = {"beh": "not-applicable", "folded": [c for c, f in folded.items() if f]}
    modl = {ct: [n for n, t in R.get("mod", []) if t == ct and "_swp_" not in n] for ct in M.T}
    mk = {ct: (ct[:3] + "_mkhuge") if (ct[:3] + "_mkhuge") in modl[ct] else None for ct in M.T}
    for cn, ct in R.get("cons", []):
        if folded.get(ct):
            out[f"PT|{cn}|folded"] = {"beh": "not-applicable", "why": f"PTRS_PER_{ct[:3].upper()} == 1"}
            continue
        huge = ct in ("pmd_t", "pud_t")
        if huge and mk[ct] is None:                  # rule 2: no T_mkhuge on this build -> no leaf entries at this level
            out[f"PT|{cn}|nohuge"] = {"beh": "not-applicable", "why": f"no {ct[:3]}_mkhuge"}
            continue
        lz = 0
        if huge:
            sh = K["PMD_SHIFT"] if ct == "pmd_t" else K["PUD_SHIFT"]
            if sh is None:
                out[f"PT|{cn}|domain"] = {"beh": "domain-unknown", "why": f"{ct[:3].upper()}_SHIFT is not a constant"}
                continue
            lz = sh - PS
        nb, dsrc = (MPB - PS, "MAX_PHYSMEM_BITS") if MPB else (PHYS - PS, "回退:phys_addr_t")
        nb = min(nb, L)
        M.S.DOM.update(tmax=None, ofree=nb, omin=0)
        pf = M.lit("o", nb, L, lz)
        params = {"pfn": ("o", nb, lz)}
        obs = [n for n, t in R.get("obs", []) if t == ct and "_swp_" not in n]
        hobs = ct[:3] + "_huge"
        mkw = wname("mod", mk[ct], ct) if mk[ct] else None
        # chains: (key constructor, apply T_mkhuge?, observers, modifiers)
        if huge:
            chains = [(f"{cn}>{mk[ct]}", True, obs, [m for m in modl[ct] if m != mk[ct]])]
        else:
            chains = [(cn, False, [o for o in obs if o != hobs], modl[ct])]
            if hobs in obs:
                if mkw:
                    chains.append((f"{cn}>{mk[ct]}", True, [hobs], [m for m in modl[ct] if m != mk[ct]]))
                else:
                    out[f"PT|{cn}|{hobs}|nohuge"] = {"beh": "not-applicable", "why": f"no {mk[ct] or ct[:3] + '_mkhuge'}"}
        for kcn, usemk, cobs, cmods in chains:
            # rule 1: observers that give a constant on a fully symbolic entry do not vote on this build
            shape = None
            for p in pv.values():
                x0 = cx.call(wname("cons", cn, ct), [pf, p])
                if not isinstance(x0, tuple):
                    shape = x0
                    break
            constobs = set()
            if shape is not None:
                for on in cobs:
                    v = cx.call(wname("obs", on, ct), [M.fresh_like(shape)])
                    if isinstance(v, SBV) and v.const() is not None:
                        constobs.add(on)
                        out[f"PT|{kcn}|{on}|constobs"] = {"beh": "not-applicable", "why": f"constant {v.const()} on a fully symbolic entry"}
            for pn, p in pv.items():
                x = cx.call(wname("cons", cn, ct), [pf, p])
                if usemk:
                    x = cx.call(mkw, [x])
                for mn in [None] + cmods:
                    xm = x if mn is None else cx.call(wname("mod", mn, ct), [x])
                    if mn is not None and M.is_stub(cx, wname("mod", mn, ct), x):
                        out[f"PT|{kcn}|{pn}|{mn}|noop"] = {"beh": "not-applicable", "why": "modifier is the identity"}
                        continue
                    for on in cobs:
                        if on in constobs:
                            continue
                        v = cx.call(wname("obs", on, ct), [xm])
                        out[f"PT|{kcn}|{pn}|{mn or '-'}|{on}"] = {"beh": M.behaviour(v, params, {}), "dom": dsrc, "nbits": nb, "lowzero": lz}


def mine3(rev, b):
    import mine as M
    if "AE_K_PPMD" not in M.CONSTS:
        M.CONSTS = M.CONSTS + EXTRA
    M.pt_family = pt_family3
    EC2.mine_build(rev, b)                         # round 2: HERE -> cache dir, "other" -> imprecise / transform, then run_build


# ---------------------------------------------------------------- reproduction and blame with the T_mkhuge chain in the key
_c_expr2, _blame2 = EC2.c_expr, EC2.blame


def c_expr3(key, arg, names):
    p = key.split("|")
    if p[0] == "PT" and ">" in p[1]:
        cons, mkh = p[1].split(">")
        x = f"{mkh}({cons}({arg}UL, {p[2]}))"
        if p[3] != "-":
            x = f"{p[3]}({x})"
        return f"(unsigned long long){p[4]}({x})"
    return _c_expr2(key, arg, names)


def blame3(dv, names):
    p = dv["key"].split("|")
    if p[0] == "PT" and ">" in p[1]:
        p[1] = p[1].split(">")[0]
        dv = dict(dv, key="|".join(p))
    return _blame2(dv, names)


EC2.c_expr, EC2.blame = c_expr3, blame3


# ---------------------------------------------------------------- engine entry (same steps as round 2, mining through mine3)
def engine(rev):
    fr = EC2.full(rev)
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"{fr}.json"
    if fr[:12] not in EC2.SUPPORTED:
        out.write_text(json.dumps({"ok": False, "error": "该版本的构建变体未生成", "rev": fr}, ensure_ascii=False))
        print("EC3", fr[:12], "unsupported")
        return
    t0 = time.time()
    d = EC2.wdir(rev)
    import discover as D
    import classify as C
    D.HERE = d
    D.main(fr[:12])
    names_all = json.loads((d / "names.json").read_text(encoding="utf-8"))["names"]
    names = sorted(names_all)
    for b in EC2.BUILDS:
        if b in C.A.ARCHES or b == "ppc64le_hash":
            C.A.register(b)
        sigs, _, _ = C.classify(b, names)
        (d / f"sigs_{b}.json").write_text(json.dumps(sigs, indent=1, ensure_ascii=False), encoding="utf-8")
    procs, todo = [], list(EC2.BUILDS)
    while todo or procs:
        while todo and len(procs) < 5:
            b = todo.pop(0)
            procs.append((b, subprocess.Popen([sys.executable, str(Path(__file__)), "mine", fr[:12], b], stdout=subprocess.PIPE,
                                              stderr=subprocess.STDOUT, text=True)))
        time.sleep(2)
        for b, p in list(procs):
            if p.poll() is not None:
                txt = p.stdout.read().strip().splitlines() if p.stdout else []
                print(txt[-1][:200] if txt else b, flush=True)
                procs.remove((b, p))
    laws, devs = EC2.vote(rev)
    EC2.repro(rev, devs)
    (d / "deviations.json").write_text(json.dumps(devs, indent=1, ensure_ascii=False), encoding="utf-8")
    cands = EC2.group(devs, names_all)
    res = {"ok": True, "rev": fr, "secs": int(time.time() - t0), "laws": len(laws), "deviations": len(devs),
           "laws_by_family": dict(Counter(k.split("|")[0] for k in laws)), "deviations_by_family": dict(Counter(x["key"].split("|")[0] for x in devs)),
           "repro": dict(Counter(x.get("repro") for x in devs if x.get("repro"))), "cands": cands}
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print("EC3", fr[:12], json.dumps({k: v for k, v in res.items() if k != "cands"}, ensure_ascii=False), "rows", len(cands))


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    if sys.argv[1] == "engine":
        engine(sys.argv[2])
    elif sys.argv[1] == "mine":
        mine3(sys.argv[2], sys.argv[3])
