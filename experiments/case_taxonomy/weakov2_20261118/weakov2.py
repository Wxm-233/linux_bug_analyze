"""weakov2 criteria 一/二/四: weakov v1 (read-only import) + non-effect list + alt marking; engine WK for commit-level mode.

    python3 weakov2.py selftest
    python3 weakov2.py run <rev> [out.json]
    python3 weakov2.py engine <rev>          -> /root/work/commitmode_cache/WK/<rev>.json
    python3 weakov2.py runall [N]            -> missing WK jobs for the commit-mode dev + held-out sets
    python3 weakov2.py score                 -> cm_results.json
"""
import json
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "weakov_20261118"))
import weakov as W  # noqa: E402

C = W.C
NONEFF2 = {"ERR_PTR", "ERR_CAST", "PTR_ERR", "IS_ERR", "IS_ERR_OR_NULL", "PTR_ERR_OR_ZERO", "static_assert"}
_v1_noneffect = W.noneffect


def noneffect(n):
    return _v1_noneffect(n) or n in NONEFF2 or n.startswith("BUILD_BUG_ON")


W.noneffect = noneffect          # criteria 一.1 (weak_effects and everything in v1 look the name up at call time)
# v1 run() writes its grep pattern file to W.HERE/.names.tmp and deletes it; parallel engine processes raced on that one
# file (first runall: 9 of 20 jobs failed). Give every process its own directory.
import tempfile  # noqa: E402
W.HERE = Path(tempfile.mkdtemp(prefix="weakov2_"))


def _ret_end(t, j, b1):
    k = j
    while k < b1 and t[k][0] != ";":
        k += 1
    return k


def missing_paths(t, b0, b1, e, void):
    """v1 missing_paths + alt (criteria 一.2)"""
    ctx = W.cond_map(t, b0, b1)
    calls = W.calls_of(t, b0, b1)
    other = [i for i in calls if t[i][0] != e and not noneffect(t[i][0])]
    occ = [i for i in calls if t[i][0] == e]
    top = [i for i in occ if ctx.get(i) == ()]
    if not top:
        c0 = ctx.get(occ[0], ())
        alt = False
        if c0:
            last = c0[-1]       # amendment 1: the sibling of an else branch "!(c)" is the if branch "c"
            sib = last[2:-1] if last.startswith("!(") and last.endswith(")") else "!(" + last + ")"
            els = c0[:-1] + (sib,)
            alt = any(ctx.get(i, ())[:len(els)] == els for i in other)
        return [{"line": t[occ[0]][1], "kind": "conditional-effect", "cond": " && ".join(c0), "ret": None, "alt": alt}]
    p = top[0]
    labels = {t[k][0]: k for k in range(b0 + 1, b1 - 1) if W.IDENT.match(t[k][0]) and t[k + 1][0] == ":" and t[k - 1][0] in (";", "{", "}")}
    out = []
    for j in range(b0 + 1, p):
        x = t[j][0]
        cj = ctx.get(j)
        if x == "return" and cj != ():
            k = _ret_end(t, j, b1)
            rv = " ".join(t[m][0] for m in range(j + 1, k))
            alt = any(ctx.get(i) == cj and i < j for i in other) or any(j < i < k for i in other)
            out.append({"line": t[j][1], "kind": "early-return", "cond": " && ".join(cj or ()), "ret": rv, "void": void, "alt": alt})
        elif x == "goto" and W.IDENT.match(t[j + 1][0]) and labels.get(t[j + 1][0], -1) > p:
            alt = any(ctx.get(i) == cj and i < j for i in other)
            out.append({"line": t[j][1], "kind": "goto-past", "cond": " && ".join(cj or ()), "ret": "goto " + t[j + 1][0], "void": void, "alt": alt})
    return out


W.missing_paths = missing_paths


def analyze(files):
    cands, info = W.analyze(files)
    for c in cands:
        c["alt"] = all(m.get("alt") for m in c["missing"])
    cands.sort(key=lambda c: (not c["ignored"], c["alt"], -c["n_generic_archs"], c["hook"], c["arch"]))
    return cands, info


def run(rev):
    W.analyze = _analyze_v1          # W.run calls W.analyze; route it through v1 then re-sort here
    try:
        cands, info = _orig_run(rev)
    finally:
        W.analyze = _analyze_v1
    for c in cands:
        c["alt"] = all(m.get("alt") for m in c["missing"])
    cands.sort(key=lambda c: (not c["ignored"], c["alt"], -c["n_generic_archs"], c["hook"], c["arch"]))
    return cands, info


_analyze_v1 = W.analyze
_orig_run = W.run


def sigs(cands, include_alt=False):
    """criteria 二: one signature per missing path"""
    out = []
    for c in cands:
        for m in c["missing"]:
            if m.get("alt") and not include_alt:
                continue
            out.append({"file": c["override"].rsplit(":", 1)[0], "func": c["hook"], "line": m["line"],
                        "sig": f"WK|{c['hook']}|{c['arch']}|{c['effect']}|{m['kind']}|{re.sub(r'\s+', '', m['cond'])}",
                        "alt": bool(m.get("alt"))})
    return out


def cmd_run(rev, out=None):
    cands, info = run(rev)
    print("info", info, "cands", len(cands), "non-alt", sum(not c["alt"] for c in cands))
    for c in cands:
        print(f"  {'ALT ' if c['alt'] else '    '}{c['hook']} [{c['arch']}] effect={c['effect']} ign={c['ignored']} {c['override']}")
        for m in c["missing"]:
            print(f"      L{m['line']} {m['kind']}{' alt' if m.get('alt') else ''} if ({m['cond'][:90]}) {m['ret'] or ''}")
    if out:
        Path(out).write_text(json.dumps({"rev": rev, "info": info, "cands": cands}, indent=1))


# ---------------------------------------------------------------- commit-level mode (criteria 二)
sys.path.insert(0, str(CT / "commitmode_20261117"))
CACHE = Path("/root/work/commitmode_cache/WK")
DEV = CT / "commitmode_20261117"
HO = CT / "heldout_commit_20261117"


def _M():
    import commitmode as M
    return M


def engine(rev):
    p = CACHE / f"{rev}.json"
    if p.exists():
        return json.loads(p.read_text())
    M = _M()
    t0 = time.time()
    try:
        if M.full(rev) != rev:
            raise ValueError(f"not a full commit id: {rev}")
        cands, info = run(rev)
        if info["weak_with_effect"] < 50:
            raise ValueError(f"only {info['weak_with_effect']} weak functions with effects")
        res = {"engine": "WK", "rev": rev, "ok": True, "info": info, "secs": round(time.time() - t0, 1),
               "cands": sigs(cands), "cands_alt": [s for s in sigs(cands, True) if s["alt"]]}
        res["n"] = len(res["cands"])
    except Exception:
        res = {"engine": "WK", "rev": rev, "ok": False, "error": traceback.format_exc()[-2000:], "secs": round(time.time() - t0, 1),
               "cands": [], "cands_alt": []}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res))
    return res


def touches(c):
    M = _M()
    for f in M.git("diff", "--name-only", f"{c}^", c).split("\n"):
        if re.match(r"arch/[^/]+/.*\.c$", f):
            return True
        if f.endswith(".c") and not f.startswith("arch/") and "__weak" in M.git("show", f"{c}:{f}"):
            return True
    return False


def datasets():
    return {"dev": json.loads((DEV / "dataset.json").read_text()), "heldout": json.loads((HO / "heldout_set.json").read_text())}


def jobs():
    M = _M()
    out = []
    for ds in datasets().values():
        for it in ds["positives"] + ds["negatives"]:
            c = M.full(it["commit"])
            if touches(c):
                for rev in (M.full(c + "^"), c):
                    if rev not in out:
                        out.append(rev)
    return out


def runall(n=4):
    todo = [r for r in jobs() if not (CACHE / f"{r}.json").exists()]
    log = open(HERE / "runall.log", "a")
    print(f"start {len(todo)} WK jobs", file=log, flush=True)
    running, t0 = [], time.time()
    while todo or running:
        running = [pr for pr in running if pr.poll() is None]
        while todo and len(running) < n:
            r = todo.pop(0)
            running.append(subprocess.Popen([sys.executable, str(HERE / "weakov2.py"), "engine", r], stdout=log, stderr=subprocess.STDOUT))
        print(f"{round(time.time() - t0)}s todo={len(todo)} running={len(running)}", file=log, flush=True)
        time.sleep(15)
    print("all done", round(time.time() - t0), file=log, flush=True)


def wk_new(c, key="cands"):
    M = _M()
    c = M.full(c)
    if not touches(c):
        return "skip", []
    res = []
    for rev in (M.full(c + "^"), c):
        p = CACHE / f"{rev}.json"
        res.append(json.loads(p.read_text()) if p.exists() else None)
    if any(r is None or not r["ok"] for r in res):
        return "error", []
    a, b = {"cands": res[0][key]}, {"cands": res[1][key]}
    return "ok", M.compare(a, b, M.renames(c))


def score():
    out = {}
    for name, ds in datasets().items():
        rows = []
        for kind, items in (("pos", ds["positives"]), ("neg", ds["negatives"])):
            for it in items:
                st, new = wk_new(it["commit"])
                _, new_alt = wk_new(it["commit"], "cands_alt") if st == "ok" else (st, [])
                names = {fn for _, fn in it.get("fix_funcs", [])}
                rows.append({"commit": it["commit"][:12], "kind": kind, "status": st,
                             "new": [f"{x['file']}:{x['line']} {x['func']} {x['sig'][:100]}" for x in new],
                             "new_alt": [f"{x['file']}:{x['line']} {x['func']} {x['sig'][:100]}" for x in new_alt],
                             "aligned": kind == "pos" and any(x["func"] in names for x in new)})
        P = [r for r in rows if r["kind"] == "pos"]
        N = [r for r in rows if r["kind"] == "neg"]
        out[name] = {"pos": len(P), "neg": len(N), "pos_flag": sum(bool(r["new"]) for r in P), "pos_aligned": sum(r["aligned"] for r in P),
                     "neg_flag": sum(bool(r["new"]) for r in N), "neg_flag_with_alt": sum(bool(r["new"] or r["new_alt"]) for r in N),
                     "errors": sum(r["status"] == "error" for r in rows), "skipped": sum(r["status"] == "skip" for r in rows), "rows": rows}
        s = out[name]
        print(f"{name}: pos {s['pos']} flagged {s['pos_flag']} aligned {s['pos_aligned']} | neg {s['neg']} flagged {s['neg_flag']} "
              f"(with alt {s['neg_flag_with_alt']}) | errors {s['errors']} skipped {s['skipped']}")
        for r in rows:
            for x in r["new"] + [("ALT " + y) for y in r["new_alt"]]:
                print("   ", name, r["kind"], r["commit"], x)
    (HERE / "cm_results.json").write_text(json.dumps(out, indent=1))


# ---------------------------------------------------------------- selftest (criteria 四)
def selftest():
    ok = W.selftest()
    base = {"drivers/base/w.c": """
void *__weak arch_alloc_x(int n)
{
	return ERR_PTR(-ENOTSUPP);
}
void __weak hook_r(int x)
{
	release_it(x);
}
void __weak hook_s(int x)
{
	do_s(x);
}
void __weak hook_t(int x)
{
	do_t(x);
}
""", "drivers/base/u.c": """
void user(int x)
{
	void *p = arch_alloc_x(x);
	if (IS_ERR(p))
		return;
	hook_r(x);
	hook_s(x);
	hook_t(x);
}
"""}
    arch = """
void *arch_alloc_x(int n)
{
	void *p = vmalloc(n);
	if (!p)
		return ERR_PTR(-ENOMEM);
	return p;
}
void hook_r(int x)
{
	if (x > 3) {
		other_release(x);
		return;
	}
	release_it(x);
}
void hook_s(int x)
{
	if (x)
		return alt_s(x);
	do_s(x);
}
void hook_t(int x)
{
	if (x)
		do_t(x);
	else
		alt_t(x);
}
void hook_s2(int x)
{
	if (x)
		alt_s(x);
	else
		do_s(x);
}
"""
    cands, _ = analyze({**base, "arch/riscv/kernel/a.c": arch})
    got = sorted((c["hook"], c["alt"]) for c in cands)
    arch2 = arch.replace("void hook_s(int x)", "void hook_s_unused(int x)").replace("void hook_s2(int x)", "void hook_s(int x)")
    c2, _ = analyze({**base, "arch/riscv/kernel/b.c": arch2})
    good = [(c["hook"], c["alt"]) for c in c2 if c["hook"] == "hook_s"] == [("hook_s", True)]
    ok &= good
    print("PASS" if good else "FAIL", "effect in the else branch, alternative in the if branch (amendment 1)")
    want = [("hook_r", True), ("hook_s", True), ("hook_t", True)]
    good = got == want
    ok &= good
    print("PASS" if good else "FAIL", "ERR_PTR not an effect; three alt forms", got)
    old = {"drivers/base/cpu.c": W.W, "drivers/acpi/p.c": W.COM, "arch/arm64/kernel/smp.c": W.OLD}
    cands, _ = analyze(old)
    a = [c for c in cands if c["hook"] == "arch_unregister_cpu"]
    good = len(a) == 1 and not a[0]["alt"] and len(a[0]["missing"]) == 3 and not any(m["alt"] for m in a[0]["missing"])
    ok &= good
    print("PASS" if good else "FAIL", "old arm64 still reported, not alt")
    print("ALL PASS (v2)" if ok else "SOME FAIL (v2)")
    return ok


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "selftest"
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    elif cmd == "run":
        cmd_run(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == "engine":
        r = engine(sys.argv[2])
        print("WK", sys.argv[2][:12], "ok" if r["ok"] else "ERROR", r.get("n"), r["secs"], "s", (r.get("error") or "")[-300:], flush=True)
    elif cmd == "runall":
        runall(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    elif cmd == "jobs":
        print(len(jobs()))
    elif cmd == "score":
        score()
