"""capguard criteria 二: capability predicates (arch-overridable, nullary). B1 silent success, B2 inconsistent guard. WSL, no build.

    python3 capguard.py selftest
    python3 capguard.py run <rev> [out.json]
    python3 capguard.py dev                  -> dev.json (criteria 三.2)
    python3 capguard.py engine <rev>         -> /root/work/commitmode_cache/CAP/<rev>.json
"""
import json
import re
import subprocess
import sys
import time
import traceback
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "p1check_20261115"))
import p1check as C  # noqa: E402  (read-only helpers)

REPO = "/root/repos/linux"
EXCL = ("arch/", "tools/", "scripts/", "samples/", "Documentation/", "usr/")
IDENT = re.compile(r"^[A-Za-z_]\w*$")
KEYW = C.KEYW | {"defined", "__builtin_expect"}


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def full(c):
    return git("rev-parse", "--verify", "-q", c + "^{commit}").strip()


def alt(names):
    return "|".join(sorted(re.escape(n) for n in names))


def common_c(p):
    return p.endswith(".c") and not p.startswith(EXCL)


# ---------------------------------------------------------------- predicate set (criteria 二.1)
def predicates(rev):
    out = git("grep", "-n", "-E", r"^[[:space:]]*#[[:space:]]*ifndef[[:space:]]+[a-z_][a-z0-9_]*[[:space:]]*$", rev, "--", "include/")
    cand = defaultdict(list)                       # X -> [(file, line)]
    for ln in out.splitlines():
        _, f, n, txt = ln.split(":", 3)
        cand[txt.split()[-1]].append((f, int(n)))
    files = sorted({f for v in cand.values() for f, _ in v})
    blobs = {}
    for i in range(0, len(files), 500):
        blobs.update(C.cat_files(rev, files[i:i + 500]))
    dflt = set()
    for x, locs in cand.items():
        for f, n in locs:
            lines = blobs.get(f, "").split("\n")[n:n + 10]
            if any(re.search(r"#\s*define\s+" + re.escape(x) + r"\b", l) or re.search(r"\binline\b.*\b" + re.escape(x) + r"\s*\(", l)
                   for l in lines):
                dflt.add(x)
                break
    if not dflt:
        return {}, {}
    pat = alt(dflt)
    archdef = defaultdict(set)
    for ln in git("grep", "-n", "-E", r"(#[[:space:]]*define[[:space:]]+(" + pat + r")\b)|(^[a-z].*\b(" + pat + r")[[:space:]]*\([^;]*$)", rev,
                  "--", "arch/").splitlines():
        parts = ln.split(":", 3)
        if len(parts) < 4:
            continue
        a = parts[1].split("/")[1]
        for m in re.finditer(r"\b(" + pat + r")\b", parts[3]):
            archdef[m.group(1)].add(a)
    used = set()
    for ln in git("grep", "-h", "-o", "-E", r"(if[[:space:]]*\(|&&|\|\|)[[:space:]]*!?[[:space:]]*(" + pat + r")[[:space:]]*\([[:space:]]*\)", rev,
                  "--", "*.c", "*.h").splitlines():
        m = re.search(r"(" + pat + r")\s*\(\s*\)$", ln)
        if m:
            used.add(m.group(1))
    preds = {x: sorted(archdef[x]) for x in dflt if archdef.get(x) and x in used}
    return preds, {"ifndef_lower": len(cand), "with_default": len(dflt), "nullary_used": len(used)}


# ---------------------------------------------------------------- lexical helpers
def calls(t, lo, hi):
    """(index, name) for call sites in t[lo:hi]"""
    out = []
    for i in range(lo, hi - 1):
        x = t[i][0]
        if t[i + 1][0] == "(" and IDENT.match(x) and x not in KEYW and (i == 0 or t[i - 1][0] not in ("->", ".")):
            out.append((i, x))
    return out


def cond_preds(t, lo, hi, preds):
    """for a condition t[lo:hi]: (negated preds in top-level '||' segments, positive preds in top-level '&&' segments)"""
    lo, hi = C.strip_parens(t, lo, hi)
    neg, pos = set(), set()
    for a, b in C.split_top(t, lo, hi, "||"):
        a, b = C.strip_parens(t, a, b)
        s = C.norm(t, a, b)
        m = re.match(r"^!(\w+)\(\)$", s)
        if m and m.group(1) in preds:
            neg.add(m.group(1))
    for a, b in C.split_top(t, lo, hi, "&&"):
        a, b = C.strip_parens(t, a, b)
        s = C.norm(t, a, b)
        m = re.match(r"^(\w+)\(\)$", s)
        if m and m.group(1) in preds:
            pos.add(m.group(1))
    return neg, pos


def stmt_end(t, i, hi):
    """end index (exclusive) of the statement starting at i"""
    if t[i][0] == "{":
        return C.match_fwd(t, i, "{", "}") + 1
    if t[i][0] == "if":
        k = C.match_fwd(t, i + 1)
        e = stmt_end(t, k + 1, hi)
        if e < hi and t[e][0] == "else":
            e = stmt_end(t, e + 1, hi)
        return e
    d = 0
    while i < hi:
        x = t[i][0]
        if x in "([{":
            d += 1
        elif x in ")]}":
            d -= 1
        elif x == ";" and d == 0:
            return i + 1
        i += 1
    return hi


def has_return(t, lo, hi):
    return any(t[i][0] == "return" for i in range(lo, hi))


def guard_map(t, lo, hi, preds):
    """for one function body t[lo..hi] ({..}): list of (call index, name, set of preds guarding it)"""
    sites = calls(t, lo + 1, hi)
    guard = defaultdict(set)
    depth = 0
    i = lo + 1
    while i < hi:
        x = t[i][0]
        if x == "{":
            depth += 1
        elif x == "}":
            depth -= 1
        elif x == "if" and t[i + 1][0] == "(":
            k = C.match_fwd(t, i + 1)
            neg, pos = cond_preds(t, i + 2, k, preds)
            body_end = stmt_end(t, k + 1, hi)
            if neg and depth == 0 and has_return(t, k + 1, body_end):
                for j in range(body_end, hi):
                    guard[j] |= neg
            # amendment 1: positive blocks `if (X()) { ... }` are branch selection, not a guard -- not counted
        i += 1
    return [(j, n, set(guard.get(j, ()))) for j, n in sites]


# ---------------------------------------------------------------- B1 (criteria 二.2)
def silent_impls(rev, preds):
    pat = alt(preds)
    files = sorted({ln.split(":", 1)[1] for ln in git("grep", "-l", "-E", r"if[[:space:]]*\([[:space:]]*![[:space:]]*(" + pat + r")[[:space:]]*\(",
                                                        rev, "--", "arch/").splitlines() if ":" in ln})
    out = defaultdict(lambda: defaultdict(set))    # F -> X -> archs
    for p, src in C.cat_files(rev, files).items():
        t = C.tokenize(C.strip(src))
        for name, params, lo, hi in C.functions(t):
            depth, i = 0, lo + 1
            while i < hi:
                x = t[i][0]
                if x == "{":
                    depth += 1
                elif x == "}":
                    depth -= 1
                elif x == "if" and depth == 0 and t[i + 1][0] == "(":
                    k = C.match_fwd(t, i + 1)
                    s = C.norm(t, i + 2, k)
                    m = re.match(r"^!(\w+)\(\)$", s)
                    if m and m.group(1) in preds:
                        nxt = C.norm(t, k + 1, min(hi, k + 4))
                        if nxt.startswith(("return0;", "return;", "returnfalse;")):
                            out[name][m.group(1)].add(p.split("/")[1])
                i += 1
    return out


def b1(rev, preds):
    impls = silent_impls(rev, preds)
    if not impls:
        return [], {}
    files = sorted({ln.split(":", 1)[1] for ln in git("grep", "-l", "-E", r"\b(" + alt(impls) + r")[[:space:]]*\(", rev, "--", "*.c").splitlines()
                    if ":" in ln and common_c(ln.split(":", 1)[1])})
    out = []
    for p, src in C.cat_files(rev, files).items():
        s = C.strip(src)
        t = C.tokenize(s)
        words = set(re.findall(r"\w+", s))
        for name, params, lo, hi in C.functions(t):
            for j, n in calls(t, lo + 1, hi):
                if n in impls and n != name:
                    for x, archs in impls[n].items():
                        if x not in words:
                            out.append({"rule": "B1", "file": p, "func": name, "line": t[j][1], "callee": n, "pred": x, "archs": sorted(archs)})
    return out, {k: {x: sorted(a) for x, a in v.items()} for k, v in impls.items()}


# ---------------------------------------------------------------- B2 (criteria 二.3)
def b2_file(path, src, preds):
    t = C.tokenize(C.strip(src))
    funcs = list(C.functions(t))
    defined = {f[0] for f in funcs}
    static = set()
    for name, params, lo, hi in funcs:
        j = lo - 1
        while j >= 0 and t[j][0] not in (";", "}"):
            j -= 1
        if "static" in [x[0] for x in t[j + 1:lo]]:
            static.add(name)
    gm = {f[0]: guard_map(t, f[2], f[3], preds) for f in funcs}
    full_g = {}                                    # function -> preds guarding every in-file call of it
    for _ in range(10):
        changed = False
        sites_of = defaultdict(list)
        for g, sites in gm.items():
            for j, n, gs in sites:
                if n in defined and n != g:
                    sites_of[n].append(gs | full_g.get(g, set()))
        for f in static:
            if sites_of.get(f):
                common = set.intersection(*sites_of[f])
                if common and common != full_g.get(f):
                    full_g[f] = common
                    changed = True
        if not changed:
            break
    out = []
    for X in preds:
        guarded, unguarded = defaultdict(list), defaultdict(list)
        for g, sites in gm.items():
            for j, n, gs in sites:
                if n in defined and n != g:
                    (guarded if X in (gs | full_g.get(g, set())) else unguarded)[n].append((g, t[j][1]))
        for G in guarded:
            for g, line in unguarded.get(G, []):
                out.append({"rule": "B2", "file": path, "func": g, "line": line, "callee": G, "pred": X, "archs": preds[X],
                            "guarded_example": f"{guarded[G][0][0]}:{guarded[G][0][1]}"})
    return out


def b2(rev, preds):
    pat = alt(preds)
    files = sorted({ln.split(":", 1)[1] for ln in git("grep", "-l", "-E", r"\b(" + pat + r")[[:space:]]*\([[:space:]]*\)", rev, "--", "*.c").splitlines()
                    if ":" in ln and common_c(ln.split(":", 1)[1])})
    out = []
    for p, src in C.cat_files(rev, files).items():
        if re.search(r"\b(" + pat + r")\s*\(\s*\)", src):
            out += b2_file(p, src, preds)
    return out, len(files)


def run(rev):
    t0 = time.time()
    preds, pinfo = predicates(rev)
    c1, impls = b1(rev, preds)
    c2, nf = b2(rev, preds)
    info = {"predicates": len(preds), "pred_info": pinfo, "silent_impls": len(impls), "b2_files": nf, "secs": round(time.time() - t0, 1)}
    return c1 + c2, info, preds, impls


def show(cands, n=200):
    for c in cands[:n]:
        extra = c.get("guarded_example", "")
        print(f"  {c['rule']} {c['file']}:{c['line']} {c['func']} -> {c['callee']} [{c['pred']}] {c['archs'][:6]} {extra}")


def cmd_run(rev, out=None):
    cands, info, preds, impls = run(rev)
    print("info", info)
    print("cands", len(cands), {r: sum(c["rule"] == r for c in cands) for r in ("B1", "B2")})
    show(cands)
    if out:
        Path(out).write_text(json.dumps({"rev": rev, "info": info, "preds": preds, "silent_impls": impls, "cands": cands}, indent=1))


def cmd_dev():
    res = {}
    for name, fix, pred in (("secretmem", "532b53cebe58", lambda c: c["file"] == "mm/secretmem.c" and c["rule"] == "B1" and c["pred"] == "can_set_direct_map"),
                            ("hugetlb", "b02019169284", lambda c: c["file"] == "mm/hugetlb.c" and c["rule"] == "B2" and c["pred"] == "hugepages_supported")):
        for tag, rev, want in (("parent", full(fix + "^"), True), ("fix", full(fix), False)):
            cands, info, preds, impls = run(rev)
            hit = [c for c in cands if pred(c)]
            ok = bool(hit) == want
            res[f"{name}_{tag}"] = {"rev": rev, "want": want, "hit": bool(hit), "ok": ok, "n": len(cands), "match": hit, "info": info,
                                    "pred_in_set": {"can_set_direct_map": "can_set_direct_map" in preds, "hugepages_supported": "hugepages_supported" in preds}}
            print(name, tag, rev[:12], "hit" if hit else "no-hit", "OK" if ok else "FAIL", "cands", len(cands), info["secs"], "s",
                  res[f"{name}_{tag}"]["pred_in_set"])
            show(hit)
    (HERE / "dev.json").write_text(json.dumps(res, indent=1))


# ---------------------------------------------------------------- engine
CACHE = Path("/root/work/commitmode_cache/CAP")


def engine(rev):
    p = CACHE / f"{rev}.json"
    if p.exists():
        return json.loads(p.read_text())
    t0 = time.time()
    try:
        if full(rev) != rev:
            raise ValueError(f"not a full commit id: {rev}")
        cands, info, _, _ = run(rev)
        res = {"engine": "CAP", "rev": rev, "ok": True, "info": info, "secs": round(time.time() - t0, 1),
               "cands": [{"file": c["file"], "func": c["func"], "line": c["line"], "sig": f"CAP|{c['rule']}|{c['callee']}|{c['pred']}",
                          "archs": c["archs"], "pred": c["pred"], "rule": c["rule"]} for c in cands]}
        res["n"] = len(res["cands"])
    except Exception:
        res = {"engine": "CAP", "rev": rev, "ok": False, "error": traceback.format_exc()[-2000:], "secs": round(time.time() - t0, 1), "cands": []}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res))
    return res


# ---------------------------------------------------------------- selftest (criteria 三.1)
def selftest():
    preds = {"can_set_dm": ["arm64"], "hp_supported": ["powerpc"]}
    src = """
static int alloc_pages_h(struct hstate *h) { return grab(h); }
static void init_hstates(void) { alloc_pages_h(h); }
static int __init h_init(void)
{
	if (!hp_supported()) {
		pr_info("disabled");
		return 0;
	}
	init_hstates();
	return 0;
}
void bootmem_alloc(void) { alloc_pages_h(h); }
void report(void) { if (hp_supported()) { show_h(h); } }
void other(void) { show_h(h); pte_young(x); }
static int helper(void) { return 1; }
void a(void) { if (!pte_young(p)) return; helper(); }
void b(void) { helper(); }
"""
    got = {(c["func"], c["callee"], c["pred"]) for c in b2_file("mm/x.c", src, preds)}
    want = {("bootmem_alloc", "alloc_pages_h", "hp_supported")}
    ok2 = got == want
    print("B2 got", sorted(got), "want", sorted(want), "PASS" if ok2 else "FAIL")
    # B1 core on token level: silent pattern detection
    t = C.tokenize(C.strip("int set_dm_invalid(struct page *p) { struct d x = {0}; if (!can_set_dm()) return 0; return apply(p); }\n"
                           "int set_dm_err(struct page *p) { if (!can_set_dm()) return -EINVAL; return apply(p); }\n"
                           "int set_dm_inner(struct page *p) { if (p) { if (!can_set_dm()) return 0; } return apply(p); }\n"))
    found = set()
    for name, params, lo, hi in C.functions(t):
        depth, i = 0, lo + 1
        while i < hi:
            x = t[i][0]
            depth += x == "{"
            depth -= x == "}"
            if x == "if" and depth == 0 and t[i + 1][0] == "(":
                k = C.match_fwd(t, i + 1)
                m = re.match(r"^!(\w+)\(\)$", C.norm(t, i + 2, k))
                if m and m.group(1) in preds and C.norm(t, k + 1, min(hi, k + 4)).startswith(("return0;", "return;", "returnfalse;")):
                    found.add(name)
            i += 1
    ok1 = found == {"set_dm_invalid"}
    print("B1 found", sorted(found), "PASS" if ok1 else "FAIL")
    print("selftest", "PASS" if ok1 and ok2 else "FAIL")
    return ok1 and ok2


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    elif cmd == "run":
        cmd_run(full(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == "dev":
        cmd_dev()
    elif cmd == "engine":
        print(json.dumps({k: v for k, v in engine(sys.argv[2]).items() if k != "cands"}))
