"""linmap2 criteria 二: v1 (linmap_20261119, read-only import) + parameter propagation only. WSL, no build.

    python3 linmap2.py selftest
    python3 linmap2.py run <rev> [out.json]          -> v1 candidates + new 'param' candidates
    python3 linmap2.py dev                            -> regression on btf / zswap (criteria 三.2)
    python3 linmap2.py diag                           -> diag.json: breakpoint table on the 25 adjudicated samples (criteria 三.3)
"""
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "linmap_20261119"))
sys.path.insert(0, str(CT / "commitmode_20261117"))
import linmap as L  # noqa: E402
C = L.C
IDENT = L.IDENT
MAX_ROUNDS = 3
TYPEISH = {"char", "u8", "unsigned", "int", "void", "long", "struct", "u32", "u64", "__u8", "uint8_t", "const"}


def statics_and_params(t):
    """[(name, params[(types, pname)], lo, hi, is_static)]"""
    out = []
    for name, params, lo, hi in C.functions(t):
        j = lo - 1
        while j >= 0 and t[j][0] not in (";", "}"):
            j -= 1
        out.append((name, params, lo, hi, "static" in [x[0] for x in t[j + 1:lo]]))
    return out


class PFile:
    """memory (11-20, after two OOM runs): keep only functions that call a sink or a function of interest (or are in keep),
    each with its own token slice; the whole-file token list is not retained. Rules unchanged."""

    def __init__(self, path, src, interest=None, keep=()):
        s = C.strip(src)
        self.path = path
        t = C.tokenize(s)
        self.funcs = []
        for name, params, lo, hi, st in statics_and_params(t):
            if interest is not None and name not in keep:
                if not any(t[i][0] in interest and t[i + 1][0] == "(" for i in range(lo, hi)):
                    continue
            self.funcs.append((name, params, 0, hi - lo, st, t[lo:hi + 1]))
        self.all_defs = [(name, st) for name, params, lo, hi, st in statics_and_params(t)] if interest is not None else \
            [(f[0], f[4]) for f in self.funcs]
        self.images = set(re.findall(r"\bextern\s+(?:const\s+)?(?:char|u8|unsigned\s+char)\s+(\w+)\s*\[\s*\]", s))
        for m in re.finditer(r"\bextern\s+(?:const\s+)?char\s+([^;]+);", s):
            self.images |= set(re.findall(r"(\w+)\s*\[\s*\]", m.group(1)))
        self.sub = L.subsys(path)


class P:
    """parameter summaries over a set of PFiles, on top of a v1 Analyzer A (sources, source functions, callbacks)"""

    def __init__(self, A, sec_images=()):
        self.A = A
        self.sec = set(sec_images)
        self.files = {}
        self.sp = defaultdict(dict)          # func -> {param index: (sink file, sink func, line, sink, via)}
        self.defs = defaultdict(set)         # func -> {(file, static)}
        self.sites = defaultdict(list)       # (g, j) -> [(file, func, line, arg_text, arg_class)]

    def add(self, path, src, keep=()):
        pf = PFile(path, src, set(L.SINKS) | set(self.sp), keep)
        self.files[path] = pf
        for name, st in pf.all_defs:
            self.defs[name].add((path, st))

    def visible(self, g, path):
        ds = self.defs.get(g, set())
        return any(not st or f == path for f, st in ds)

    def walk(self, pf, fn, collect):
        name, params, lo, hi, st, t = fn
        sub = pf.sub
        pnames = {p: i for i, (_, p) in enumerate(params)}
        ptaint = {p: (i, -1) for p, i in pnames.items()}
        taint, guards, depth, out = {}, set(), 0, []
        for j in range(lo, hi):
            if t[j][0] in L.GUARDS and t[j + 1][0] == "(":
                k = C.match_fwd(t, j + 1)
                for i in range(j + 2, k):
                    p, _ = L.path_at(t, i, k)
                    if p:
                        guards.add(p)
        local_arrays = set()
        for j in range(lo + 1, hi - 1):
            if IDENT.match(t[j][0]) and t[j + 1][0] == "[" and (t[j - 1][0] in TYPEISH or t[j - 1][0].endswith("_t") or t[j - 1][0] == "*"):
                local_arrays.add(t[j][0])
        j = lo + 1
        while j < hi:
            x = t[j][0]
            if x == "{":
                depth += 1
            elif x == "}":
                depth -= 1
            elif x == "=" and IDENT.match(t[j - 1][0]):
                k = j - 1
                while k - 2 >= lo and t[k - 1][0] in ("->", ".") and IDENT.match(t[k - 2][0]):
                    k -= 2
                if not (t[k - 1][0] in ("->", ".", "]", ")") or (t[k - 1][0] == "*" and t[k - 2][0] in (";", "{", "}", ")", ",", "("))):
                    var = C.norm(t, k, j)
                    e, d = j + 1, 0
                    while e < hi:
                        y = t[e][0]
                        if y in "([{":
                            d += 1
                        elif y in ")]}":
                            if d == 0:
                                break
                            d -= 1
                        elif y in (";", ",") and d == 0:
                            break
                        e += 1
                    src = self.A.rhs_source(t, j + 1, e, taint, sub)
                    b = L.base_ident(t, j + 1, e)
                    if src:
                        taint[var] = (src[0], src[1], var, depth)
                    elif var in taint and depth == taint[var][3]:
                        del taint[var]
                    if b in ptaint and "->" not in var and "." not in var:
                        ptaint[var] = (ptaint[b][0], depth)
                    elif var in ptaint and var not in pnames and depth == ptaint[var][1]:
                        del ptaint[var]
            elif IDENT.match(x) and j + 1 < hi and t[j + 1][0] == "(" and (j == 0 or t[j - 1][0] not in ("->", ".")):
                args, end = C.args_of(t, j + 1)
                if x in L.SINKS:
                    ai = L.SINKS[x]
                    if ai < len(args):
                        b = L.base_ident(t, *args[ai])
                        if b in ptaint and b not in guards and "->" not in b:
                            i = ptaint[b][0]
                            if i not in self.sp[name]:
                                self.sp[name][i] = (pf.path, name, t[j][1], x, [])
                                out.append(("sp", name, i))
                elif x in self.sp and self.visible(x, pf.path):
                    for gj, info in list(self.sp[x].items()):
                        if gj >= len(args):
                            continue
                        a0, a1 = args[gj]
                        b = L.base_ident(t, a0, a1)
                        lo2, hi2 = L.strip_cast(t, a0, a1)
                        b2 = t[lo2 + 1][0] if t[lo2][0] == "&" and lo2 + 1 < hi2 else b
                        if b in ptaint and b not in guards and "->" not in b:
                            i = ptaint[b][0]
                            if i not in self.sp[name]:
                                self.sp[name][i] = (info[0], info[1], info[2], info[3], [x] + info[4])
                                out.append(("sp", name, i))
                        src = self.A.rhs_source(t, a0, a1, taint, sub)
                        if src is None and b2 and (b2 in pf.images or b2 in self.sec):
                            src = ("镜像符号", [b2])
                        cls = self.arg_class(t, a0, a1, b, taint, ptaint, local_arrays, pf, src)
                        if collect:
                            self.sites[(x, gj)].append((pf.path, name, t[j][1], C.norm(t, a0, a1), cls))
                        if collect and src and not ({b, b2} & guards):
                            out.append(("cand", {"sink_file": info[0], "sink_func": info[1], "sink_line": info[2], "sink": info[3],
                                                 "via": [x] + info[4], "file": pf.path, "func": name, "line": t[j][1],
                                                 "arg": C.norm(t, a0, a1), "kind": src[0] if len(src[1]) == 1 else "经来源函数",
                                                 "chain": src[1]}))
            j += 1
        return out

    @staticmethod
    def arg_class(t, a0, a1, b, taint, ptaint, local_arrays, pf, src):
        lo, hi = L.strip_cast(t, a0, a1)
        if src:
            return "source"
        if b is None:
            c = L.call_of(t, a0, a1)
            if c:
                return f"call:{c[1]}"
            if t[lo][0] == "&":
                return "address-of"
            return "other"
        if b in ptaint:
            return "param"
        if "->" in b or "." in b:
            return "field"
        if b in local_arrays:
            return "stack-array"
        return "local-or-global"

    def summarize(self):
        for _ in range(10):
            n0 = sum(len(v) for v in self.sp.values())
            for pf in self.files.values():
                for fn in pf.funcs:
                    self.walk(pf, fn, False)
            if sum(len(v) for v in self.sp.values()) == n0:
                break

    def candidates(self):
        self.sites.clear()
        out = []
        for pf in self.files.values():
            for fn in pf.funcs:
                out += [x[1] for x in self.walk(pf, fn, True) if x[0] == "cand"]
        return out


def grep_names(rev, names):
    """files (in v1 scope) mentioning any of `names` as a whole word. 11-20: an ERE alternation of ~4000 names made
    `git grep` itself use ~9.3 GB; fixed-string word matching (-F -w -f) finds a superset of the same files with little
    memory. Later parsing only keeps real calls, so results are unchanged."""
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".pat", delete=False) as f:
        f.write("\n".join(sorted(names)) + "\n")
        pat = f.name
    try:
        out = L.git("grep", "-l", "-w", "-F", "-f", pat, rev, "--", "*.c", "*.h")
    finally:
        Path(pat).unlink(missing_ok=True)
    return sorted({ln.split(":", 1)[1] for ln in out.splitlines() if ":" in ln and L.in_scope(ln.split(":", 1)[1])})


def run(rev, extra_files=(), keep_funcs=()):
    """v1 run (unchanged) + parameter propagation over sink files and up to MAX_ROUNDS levels of callers"""
    t0 = time.time()
    v1, info, A = L.run(rev)
    # memory only (rules unchanged): parameter propagation needs A.src_funcs / A.cb, not v1's per-file token facts.
    # 11-20: six parallel diag runs at ~4 GB each were OOM-killed; dropping these saves ~1 GB per process.
    A.facts = {}
    import gc
    gc.collect()
    sec = set()
    for m in re.finditer(r"\bextern\s+(?:const\s+)?char\s+([^;]+);", C.strip(C.cat_files(rev, ["include/asm-generic/sections.h"]).get(
            "include/asm-generic/sections.h", ""))):
        sec |= set(re.findall(r"(\w+)\s*\[\s*\]", m.group(1)))
    Pp = P(A, sec)
    sink_files = [p for p in L.grep_files(rev, r"\b(" + L.alt(L.SINKS) + r")\s*\(") if p.endswith(".c")]
    want = sorted(set(sink_files) | {f for f in extra_files if f.endswith(".c")})
    for i in range(0, len(want), 500):
        for p, src in C.cat_files(rev, want[i:i + 500]).items():
            Pp.add(p, src, keep=keep_funcs)
    Pp.summarize()
    rounds, done = [], set()
    for r in range(MAX_ROUNDS):
        new = set(Pp.sp) - done                     # (re)read files calling newly summarized functions, so that their
        done |= new                                 # newly relevant functions are retained (memory change, 11-20)
        files = [p for p in grep_names(rev, new) if p.endswith(".c")] if new else []
        for i in range(0, len(files), 500):
            for p, src in C.cat_files(rev, files[i:i + 500]).items():
                Pp.add(p, src, keep=keep_funcs)
        Pp.summarize()
        rounds.append({"read_files": len(files), "funcs_with_param_summary": len(Pp.sp)})
        if not files:
            break
    cands = Pp.candidates()
    ai = L.arch_info(rev)
    for c in cands:
        c["archs"] = ai.get(L.base_kind(c["chain"][-1]) or ("image" if c["kind"] == "镜像符号" else c["kind"]), [])
    info2 = {"v1": {k: v for k, v in info.items() if k != "arch"}, "rounds": rounds, "files": len(Pp.files),
             "param_summaries": sum(len(v) for v in Pp.sp.values()), "secs": round(time.time() - t0, 1)}
    return v1, cands, info2, Pp


def cmd_run(rev, out=None):
    v1, cands, info, _ = run(rev)
    print("info", info)
    print("v1", len(v1), "param", len(cands))
    for c in cands[:200]:
        print(f"  {c['sink_file']}:{c['sink_line']} {c['sink_func']} {c['sink']} <= {c['file']}:{c['line']} {c['func']}({c['arg'][:40]}) "
              f"via {'>'.join(c['via'])} <- {c['kind']} {'>'.join(c['chain'][:4])}")
    if out:
        Path(out).write_text(json.dumps({"rev": rev, "info": info, "v1": v1, "param": cands}, indent=1, ensure_ascii=False))


def cmd_dev():
    res = {}
    for name, fix, pred in (("btf", "2e2713ae1a05", lambda c: c["func"] == "btf_sysfs_vmlinux_mmap"),
                            ("zswap", "9c500835f279", lambda c: c["func"] == "zswap_decompress")):
        for tag, rev, want in (("parent", L.full(fix + "^"), True), ("fix", L.full(fix), False)):
            v1, cands, info, _ = run(rev)
            hit = [c for c in v1 if pred(c)] + [c for c in cands if pred({"func": c["sink_func"]}) or pred(c)]
            ok = bool(hit) == want
            res[f"{name}_{tag}"] = {"rev": rev, "ok": ok, "hit": bool(hit), "v1": len(v1), "param": len(cands), "info": info}
            print(name, tag, rev[:12], "hit" if hit else "no-hit", "OK" if ok else "FAIL", "v1", len(v1), "param", len(cands), info["secs"], "s")
    (HERE / "dev.json").write_text(json.dumps(res, indent=1))


def cmd_diag(only=None):
    """only=None: list sample numbers; only=n: diagnose sample n into diag/<n>.json"""
    import dataset as DSET
    adj = json.loads((CT / "linmap_20261119/adjudication.json").read_text(encoding="utf-8"))
    rows = json.loads((CT / "linmap_20261119/mined.json").read_text())["rows"]
    if only is None:
        print(" ".join(str(a["n"]) for a in adj if a["final"] == "yes"))
        return
    out = []
    for a in adj:
        if a["final"] != "yes" or a["n"] != only:
            continue
        s = rows[a["n"] - 1]
        fix = L.full(s["commit"])
        rev = L.full(fix + "^")
        ff = DSET.touched_funcs(fix)
        funcs = {fn for _, fn in ff}
        files = {f for f, _ in ff}
        v1, cands, info, Pp = run(rev, extra_files=files, keep_funcs=funcs)
        v1_hit = any(c["func"] in funcs for c in v1)
        v2_hit = any(c["sink_func"] in funcs or c["func"] in funcs for c in cands)
        sinks = []
        for p in files:
            pf = Pp.files.get(p)
            if not pf:
                continue
            for fn in pf.funcs:
                if fn[0] not in funcs:
                    continue
                name, params, lo, hi, st, t = fn
                pidx = {pn: i for i, (_, pn) in enumerate(params)}
                for j in range(lo, hi):
                    if t[j][0] in L.SINKS and t[j + 1][0] == "(":
                        args, _ = C.args_of(t, j + 1)
                        ai = L.SINKS[t[j][0]]
                        if ai >= len(args):
                            continue
                        b = L.base_ident(t, *args[ai])
                        rec = {"func": name, "line": t[j][1], "sink": t[j][0], "arg": C.norm(t, *args[ai])}
                        if b in pidx:
                            i = pidx[b]
                            rec["form"] = f"param#{i}"
                            rec["summary"] = i in Pp.sp.get(name, {})
                            st_ = Pp.sites.get((name, i), [])
                            rec["callers"] = len(st_)
                            rec["caller_arg_classes"] = sorted({x[4] for x in st_})
                            rec["caller_examples"] = [f"{x[1]}({x[3][:40]})={x[4]}" for x in st_[:4]]
                        else:
                            rec["form"] = Pp.arg_class(t, *args[ai], b, {}, {}, set(), pf, None) if b is None or "->" in (b or "") \
                                else ("field" if "->" in b or "." in b else "local-or-global")
                        sinks.append(rec)
        r = {"n": a["n"], "commit": s["commit"], "subject": s["subject"], "v1_hit": v1_hit, "v2_hit": v2_hit,
             "sinks_in_fix_funcs": sinks, "fix_funcs": sorted(funcs)[:8], "param_cands": len(cands), "info": info}
        out.append(r)
        print(f"{a['n']:03d} {s['commit']} v1={'Y' if v1_hit else '-'} v2={'Y' if v2_hit else '-'} {s['subject'][:60]}", flush=True)
        for x in sinks[:4]:
            print(f"      {x['func']}:{x['line']} {x['sink']}({x['arg'][:40]}) form={x['form']} "
                  f"{('summary=' + str(x['summary']) + ' callers=' + str(x['callers']) + ' ' + str(x['caller_arg_classes'])) if 'summary' in x else ''}",
                  flush=True)
        (HERE / "diag").mkdir(exist_ok=True)
        (HERE / "diag" / f"{only:03d}.json").write_text(json.dumps(r, indent=1, ensure_ascii=False))


def cmd_merge():
    out = [json.loads(p.read_text()) for p in sorted((HERE / "diag").glob("*.json"))]
    (HERE / "diag.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print("samples", len(out), "v1 hits", sum(r["v1_hit"] for r in out), "v2 hits", sum(r["v2_hit"] for r in out))
    for r in out:
        print(f"{r['n']:03d} {r['commit']} v1={'Y' if r['v1_hit'] else '-'} v2={'Y' if r['v2_hit'] else '-'} {r['subject'][:60]}")
        for x in r["sinks_in_fix_funcs"][:4]:
            extra = f" summary={x['summary']} callers={x['callers']} {x['caller_arg_classes']} {x['caller_examples'][:2]}" if "summary" in x else ""
            print(f"      {x['func']}:{x['line']} {x['sink']}({x['arg'][:40]}) form={x['form']}{extra}")
        if not r["sinks_in_fix_funcs"]:
            print("      (修复改动的函数里没有接收者调用)")


def selftest():
    files = {
        "fs/a.c": "static void do_crypt(struct sc *sg, void *buf, int len) { sg_init_one(sg, buf, len); }\n"
                  "static void enc(void *data) { u8 *p = (u8 *)data + 4; do_crypt(&sg, p, 8); }\n"
                  "void user1(void) { void *v = vmalloc(64); enc(v); }\n"
                  "void user2(void) { void *k = kmalloc(64, GFP_KERNEL); enc(k); }\n"
                  "static void guarded(void *buf) { if (is_vmalloc_addr(buf)) return; sg_init_one(&s, buf, 4); }\n"
                  "void user3(void) { void *v = vmalloc(64); guarded(v); }\n"
                  "static void fld(struct st *x) { virt_to_page(x->buf); }\n"
                  "void user4(struct st *x) { x->buf = vmalloc(8); fld(x); }\n"
                  "void user5(void) { void *m = kmap(pg); enc(m); }\n",
    }
    facts = {p: L.file_facts(p, s) for p, s in files.items()}
    A = L.Analyzer(facts)
    A.summarize()
    Pp = P(A)
    for _ in range(MAX_ROUNDS + 1):              # same as run(): re-read files as new summaries appear
        for p, s in files.items():
            Pp.add(p, s)
        Pp.summarize()
    got = {(c["func"], c["sink_func"], c["kind"]) for c in Pp.candidates()}
    want = {("user1", "do_crypt", "vmalloc"), ("user5", "do_crypt", "kmap")}
    ok = got == want
    print("sp", dict(Pp.sp))
    print("got ", sorted(got))
    print("want", sorted(want))
    print("selftest", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    elif cmd == "run":
        cmd_run(L.full(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == "dev":
        cmd_dev()
    elif cmd == "diag":
        cmd_diag(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    elif cmd == "merge":
        cmd_merge()
