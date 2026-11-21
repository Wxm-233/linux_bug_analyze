"""linmap criteria 二: linear-map-only interfaces applied to addresses outside the linear map (type consistency, address class).
Lexical, git objects of /root/repos/linux at any revision, no build. WSL.

    python3 linmap.py selftest
    python3 linmap.py run <rev> [out.json]
    python3 linmap.py dev                    -> dev.json   (criteria 三.2)
    python3 linmap.py engine <rev>           -> /root/work/commitmode_cache/LM/<rev>.json
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
sys.path.insert(0, str(CT / "p1check_20261115"))
import p1check as C  # noqa: E402  (read-only: strip, tokenize, functions, match_fwd, args_of, split_top, cat_files, git)

REPO = "/root/repos/linux"
SINKS = {"virt_to_phys": 0, "__pa": 0, "virt_to_page": 0, "virt_to_pfn": 0, "virt_to_folio": 0, "virt_to_head_page": 0,
         "sg_init_one": 1, "sg_set_buf": 1}
VMALLOC = {"vmalloc", "vzalloc", "vmalloc_node", "vzalloc_node", "vmalloc_user", "vmalloc_32", "vmalloc_32_user", "vmalloc_huge",
           "vmalloc_huge_node", "vmalloc_array", "vcalloc", "__vmalloc", "__vmalloc_node", "__vmalloc_node_range"}
VMALLOC |= {x + "_noprof" for x in list(VMALLOC)}
BASE = {**{x: "vmalloc" for x in VMALLOC}, "vmap": "vmap", "vm_map_ram": "vmap",
        **{x: "kmap" for x in ("kmap", "kmap_atomic", "kmap_local_page", "kmap_local_folio", "kmap_local_pfn")},
        "memremap": "ioremap"}
IOREMAP = re.compile(r"^ioremap(?:_(?:wc|wt|uc|np|cache|prot|encrypted))?$")
GUARDS = {"virt_addr_valid", "is_vmalloc_addr", "is_vmalloc_or_module_addr", "is_kmap_addr", "PageHighMem"}
EXCL = ("arch/", "tools/", "scripts/", "samples/", "Documentation/", "usr/")
IDENT = re.compile(r"^[A-Za-z_]\w*$")
TYPEWORDS = {"const", "volatile", "struct", "union", "enum", "unsigned", "signed", "char", "short", "int", "long", "void", "u8", "u16",
             "u32", "u64", "__u8", "__u32", "__u64", "uintptr_t", "phys_addr_t", "size_t", "__force", "__iomem", "__user"}


def base_kind(name):
    if name in BASE:
        return BASE[name]
    if IOREMAP.match(name):
        return "ioremap"
    return None


def subsys(path):
    d = path.rsplit("/", 1)[0] if "/" in path else ""
    return "/".join(d.split("/")[:2])


# ---------------------------------------------------------------- expression helpers
def strip_cast(t, lo, hi):
    """drop parens and leading casts like (u8 *)(void *)"""
    while lo < hi:
        lo, hi = C.strip_parens(t, lo, hi)
        if t[lo][0] == "(":
            k = C.match_fwd(t, lo)
            inner = [x[0] for x in t[lo + 1:k]]
            if k < hi - 1 and inner and all(IDENT.match(x) or x == "*" for x in inner) and \
                    (any(x in TYPEWORDS or x.endswith("_t") for x in inner) or "*" in inner):
                lo = k + 1
                continue
        break
    return lo, hi


def path_at(t, k, hi):
    """access path starting at token k: X, X->f, X.f.g (amendment 1); returns (text, next index) or (None, k)"""
    if k >= hi or not IDENT.match(t[k][0]):
        return None, k
    parts, j = [t[k][0]], k + 1
    while j + 1 < hi and t[j][0] in ("->", ".") and IDENT.match(t[j + 1][0]):
        parts += [t[j][0], t[j + 1][0]]
        j += 2
    return "".join(parts), j


def base_ident(t, lo, hi):
    """access path an argument is based on (X, X->f, X + off, (T *)X, &X[i]); None for calls, derefs, other forms"""
    lo, hi = strip_cast(t, lo, hi)
    if lo >= hi:
        return None
    if t[lo][0] == "&" and lo + 1 < hi and IDENT.match(t[lo + 1][0]) and lo + 2 < hi and t[lo + 2][0] == "[":
        return t[lo + 1][0]
    p, j = path_at(t, lo, hi)
    if p is None:
        return None
    if j < hi and t[j][0] not in ("+", "-"):
        return None
    return p


def call_of(t, lo, hi):
    """whole expression is a call: ('name', name) or ('member', member); else None"""
    lo, hi = strip_cast(t, lo, hi)
    if hi - lo >= 3 and t[hi - 1][0] == ")":
        k = C.match_back(t, hi - 1)
        if k > lo and IDENT.match(t[k - 1][0]):
            if k - 1 == lo:
                return ("name", t[lo][0])
            if t[k - 2][0] in ("->", "."):
                return ("member", t[k - 1][0])
    return None


# ---------------------------------------------------------------- per-file facts
def file_facts(path, src, keep_all=True):
    """per-function records with their own token slices. keep_all=False (summary-only files): keep only functions that
    return a pointer (only those can return a mapped address, criteria 二.3) -- saves memory, rule unchanged."""
    s = C.strip(src)
    t = C.tokenize(s)
    images = set(re.findall(r"\bextern\s+(?:const\s+)?(?:char|u8|unsigned\s+char)\s+(\w+)\s*\[\s*\]", s))
    for m in re.finditer(r"\bextern\s+(?:const\s+)?char\s+([^;]+);", s):
        images |= set(re.findall(r"(\w+)\s*\[\s*\]", m.group(1)))
    inits = re.findall(r"\.\s*(\w+)\s*=\s*&?\s*(\w+)\s*[,}\n]", s)
    recs = []
    for name, params, lo, hi in C.functions(t):
        j = lo - 1
        while j >= 0 and t[j][0] not in (";", "}"):
            j -= 1
        head = [x[0] for x in t[j + 1:lo]]
        ptr = name in head and "*" in head[:head.index(name)]
        if not (keep_all or ptr):
            continue
        body = t[lo:hi + 1]
        callees = {body[i][0] for i in range(len(body) - 1) if body[i + 1][0] == "(" and IDENT.match(body[i][0])}
        mcallees = {body[i][0] for i in range(1, len(body) - 1) if body[i + 1][0] == "(" and body[i - 1][0] in ("->", ".")}
        recs.append({"name": name, "t": body, "ptr": ptr, "callees": callees, "mcallees": mcallees})
    return {"recs": recs, "images": images, "inits": inits, "sub": subsys(path), "sinkfile": keep_all}


class Analyzer:
    def __init__(self, facts, sections_images=()):
        self.facts = facts                     # path -> file_facts
        self.sec_images = set(sections_images)
        self.src_funcs = {}                    # name -> (kind, chain)
        self.cb = {}                           # (subsys, member) -> (kind, chain)

    def rhs_source(self, t, lo, hi, taint, sub):
        c = call_of(t, lo, hi)
        if c:
            kind, name = c
            if kind == "name":
                b = base_kind(name)
                if b:
                    return (b, [name])
                if name in self.src_funcs:
                    k2, ch = self.src_funcs[name]
                    return (k2, [name] + ch)
            elif (sub, name) in self.cb:
                k2, ch = self.cb[(sub, name)]
                return (k2, ["->" + name] + ch)
            return None
        b = base_ident(t, lo, hi)
        if b and b in taint:
            return taint[b][:2]
        return None

    def walk(self, path, rec, mode):
        """mode 'summary' -> (kind, chain) if the function returns a mapped address; mode 'sinks' -> candidate list"""
        fx = self.facts[path]
        name, t, sub = rec["name"], rec["t"], fx["sub"]
        lo, hi = 0, len(t) - 1
        taint, depth, out, ret = {}, 0, [], None
        guards = set()
        for j in range(lo, hi):
            if t[j][0] in GUARDS and j + 1 < hi and t[j + 1][0] == "(":
                k = C.match_fwd(t, j + 1)
                for i in range(j + 2, k):
                    p, _ = path_at(t, i, k)
                    if p:
                        guards.add(p)            # identifiers and access paths (amendment 1)
        j = lo + 1
        while j < hi:
            x = t[j][0]
            if x == "{":
                depth += 1
            elif x == "}":
                depth -= 1
            elif x == "=" and IDENT.match(t[j - 1][0]):
                k = j - 1                        # left side: X or X->f / X.f (amendment 1)
                while k - 2 >= lo and t[k - 1][0] in ("->", ".") and IDENT.match(t[k - 2][0]):
                    k -= 2
                if t[k - 1][0] in ("->", ".", "]", ")") or \
                        (t[k - 1][0] == "*" and t[k - 2][0] in (";", "{", "}", ")", ",", "(")):   # '*p = x' is a store, 'T *p = x' a declaration
                    j += 1
                    continue
                var = C.norm(t, k, j)
                e = j + 1
                d = 0
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
                src = self.rhs_source(t, j + 1, e, taint, sub)
                if src:
                    root = taint[base_ident(t, j + 1, e)][2] if base_ident(t, j + 1, e) in taint else var
                    taint[var] = (src[0], src[1], root, depth)
                elif var in taint and depth == taint[var][3]:   # amendment 2: only a same-level reassignment untaints
                    del taint[var]
            elif x == "return" and mode == "summary":
                e = j + 1
                d = 0
                while e < hi and not (t[e][0] == ";" and d == 0):
                    d += t[e][0] in "([{"
                    d -= t[e][0] in ")]}"
                    e += 1
                src = self.rhs_source(t, j + 1, e, taint, sub)
                if src and ret is None:
                    ret = src
            elif mode == "sinks" and x in SINKS and j + 1 < hi and t[j + 1][0] == "(":
                args, end = C.args_of(t, j + 1)
                ai = SINKS[x]
                if ai < len(args):
                    a0, a1 = args[ai]
                    b = base_ident(t, a0, a1)
                    lo2, hi2 = strip_cast(t, a0, a1)
                    if t[lo2][0] == "&" and lo2 + 1 < hi2:
                        b2 = t[lo2 + 1][0]
                    else:
                        b2 = b
                    hit = None
                    if b2 and (b2 in fx["images"] or b2 in self.sec_images) and b2 not in taint:
                        hit = ("镜像符号", [b2], b2)
                    elif b and b in taint:
                        k2, ch, root, _ = taint[b]
                        hit = (k2 if len(ch) == 1 else "经来源函数", ch, root)
                    if hit and not ({b, b2, hit[2]} & guards):
                        out.append({"file": path, "func": name, "line": t[j][1], "sink": x, "arg": C.norm(t, a0, a1),
                                    "kind": hit[0], "chain": hit[1], "base": BASE_OF(hit)})
            j += 1
        return ret if mode == "summary" else out

    def relevant(self, rec, sub):
        if rec["callees"] & self.names_known or any(IOREMAP.match(c) for c in rec["callees"]):
            return True
        return any((sub, m) in self.cb for m in rec["mcallees"])

    def summarize(self, max_iter=12):
        """worklist: re-walk a pointer-returning function only if it calls a known source and the known set grew since"""
        for _ in range(max_iter):
            changed = False
            self.names_known = set(BASE) | set(self.src_funcs)
            state = (len(self.src_funcs), len(self.cb))
            for path, fx in self.facts.items():
                for rec in fx["recs"]:
                    if not rec["ptr"] or rec["name"] in self.src_funcs or base_kind(rec["name"]) or rec.get("last") == state:
                        continue
                    if not self.relevant(rec, fx["sub"]):
                        continue
                    rec["last"] = state
                    r = self.walk(path, rec, "summary")
                    if r:
                        self.src_funcs[rec["name"]] = r
                        changed = True
            for path, fx in self.facts.items():
                for member, fn in fx["inits"]:
                    if fn in self.src_funcs and (fx["sub"], member) not in self.cb:
                        k2, ch = self.src_funcs[fn]
                        self.cb[(fx["sub"], member)] = (k2, [fn] + ch)
                        changed = True
            if not changed:
                break

    def sinks(self, paths=None):
        out = []
        for path in (paths or self.facts):
            fx = self.facts[path]
            if path.endswith(".c") and fx["sinkfile"]:
                for rec in fx["recs"]:
                    out += self.walk(path, rec, "sinks")
        return out


def BASE_OF(hit):
    """underlying source class for the architecture column"""
    if hit[0] == "镜像符号":
        return "image"
    last = hit[1][-1]
    return base_kind(last) or hit[0]


# ---------------------------------------------------------------- revision driver
def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def in_scope(p):
    return p.endswith((".c", ".h")) and not p.startswith(EXCL)


def grep_files(rev, pattern):
    out = git("grep", "-l", "-E", pattern, rev, "--", "*.c", "*.h")
    return sorted({ln.split(":", 1)[1] for ln in out.splitlines() if ":" in ln and in_scope(ln.split(":", 1)[1])})


def arch_info(rev):
    pa = {ln.split(":", 1)[1].split("/")[1] for ln in git("grep", "-l", r"#define __pa_symbol", rev, "--", "arch/*/include/asm/*").splitlines() if ":" in ln}
    hm = {ln.split(":", 1)[1].split("/")[1] for ln in git("grep", "-l", "-E", r"^config HIGHMEM$", rev, "--", "arch/*/Kconfig*").splitlines() if ":" in ln}
    return {"image": sorted(pa), "kmap": sorted(hm), "vmalloc": ["全部"], "vmap": ["全部"], "ioremap": ["全部"]}


def alt(names):
    return "|".join(sorted(re.escape(n) for n in names))


def run(rev):
    t0 = time.time()
    sink_files = [p for p in grep_files(rev, r"\b(" + alt(SINKS) + r")\s*\(") if p.endswith(".c")]
    sec = C.cat_files(rev, ["include/asm-generic/sections.h"]).get("include/asm-generic/sections.h", "")
    sec_images = set()
    for m in re.finditer(r"\bextern\s+(?:const\s+)?char\s+([^;]+);", C.strip(sec)):
        sec_images |= set(re.findall(r"(\w+)\s*\[\s*\]", m.group(1)))
    facts = {}

    def load(paths, keep_all=False):
        new = [p for p in paths if p not in facts]
        for i in range(0, len(new), 500):
            for p, src in C.cat_files(rev, new[i:i + 500]).items():
                facts[p] = file_facts(p, src, keep_all)
        return len(new)

    def log(msg):
        print(f"[{round(time.time() - t0)}s] {msg}", file=sys.stderr, flush=True)

    load(sink_files, keep_all=True)
    log(f"sink files {len(sink_files)}")
    A = Analyzer(facts, sec_images)
    names, members = set(BASE), set()
    for it in range(8):
        pat = r"(\b(" + alt(names) + r")\s*\()|(\bioremap\w*\s*\()"
        if members:
            pat += r"|(->\s*(" + alt(members) + r")\s*\()"
        n_new = load(grep_files(rev, pat))
        A.summarize()
        new_names = set(A.src_funcs) - names
        new_members = {m for _, m in A.cb} - members
        if new_names:
            n_new += load(grep_files(rev, r"\.\s*\w+\s*=\s*&?\s*(" + alt(new_names) + r")\b"))
            A.summarize()
            new_members = {m for _, m in A.cb} - members
        names |= new_names
        members |= new_members
        log(f"iter {it + 1}: files {len(facts)} (+{n_new}), source funcs {len(A.src_funcs)}, callbacks {len(A.cb)}")
        if not new_names and not new_members and not n_new:
            break
    cands = A.sinks([p for p in sink_files])
    ai = arch_info(rev)
    for c in cands:
        c["archs"] = ai.get(c["base"], [])
    info = {"sink_files": len(sink_files), "files_read": len(facts), "source_funcs": len(A.src_funcs), "callbacks": len(A.cb),
            "iterations": it + 1, "arch": ai, "secs": round(time.time() - t0, 1)}
    return cands, info, A


def show(cands, n=60):
    for c in cands[:n]:
        print(f"  {c['file']}:{c['line']} {c['func']} {c['sink']}({c['arg'][:50]}) <- {c['kind']} {'>'.join(c['chain'][:6])} {c['archs'][:6]}")


def cmd_run(rev, out=None):
    cands, info, A = run(rev)
    print("info", {k: v for k, v in info.items() if k != "arch"}, "arch", info["arch"])
    from collections import Counter
    print("cands", len(cands), Counter(c["kind"] for c in cands), Counter(c["sink"] for c in cands))
    show(cands, 200)
    if out:
        Path(out).write_text(json.dumps({"rev": rev, "info": info, "cands": cands, "src_funcs": {k: v for k, v in A.src_funcs.items()},
                                         "callbacks": {f"{a}|{b}": v for (a, b), v in A.cb.items()}}, indent=1, ensure_ascii=False))


def full(c):
    return git("rev-parse", "--verify", "-q", c + "^{commit}").strip()


def cmd_dev():
    res = {}
    for name, fix, pred in (("btf", "2e2713ae1a05", lambda c: c["func"] == "btf_sysfs_vmlinux_mmap" and c["sink"] == "virt_to_phys"),
                            ("zswap", "9c500835f279", lambda c: c["func"] == "zswap_decompress" and c["sink"] == "sg_init_one")):
        for tag, rev, want in (("parent", full(fix + "^"), True), ("fix", full(fix), False)):
            cands, info, _ = run(rev)
            hit = [c for c in cands if pred(c)]
            ok = bool(hit) == want
            res[f"{name}_{tag}"] = {"rev": rev, "want": want, "hit": bool(hit), "ok": ok, "n": len(cands), "match": hit,
                                    "info": {k: v for k, v in info.items() if k != "arch"}}
            print(name, tag, rev[:12], "hit" if hit else "no-hit", "OK" if ok else "FAIL", "cands", len(cands), info["secs"], "s")
            show(hit)
    (HERE / "dev.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))


# ---------------------------------------------------------------- engine (cache shared with the other engines)
CACHE = Path("/root/work/commitmode_cache/LM")


def sigs(cands):
    out = []
    for c in cands:
        arg = re.sub(r"\s+", "", c["arg"])
        out.append({"file": c["file"], "func": c["func"], "line": c["line"], "sig": f"LM|{c['sink']}|{c['kind']}|{arg}",
                    "archs": c["archs"], "chain": c["chain"]})
    return out


def engine(rev):
    p = CACHE / f"{rev}.json"
    if p.exists():
        return json.loads(p.read_text())
    t0 = time.time()
    try:
        if full(rev) != rev:
            raise ValueError(f"not a full commit id: {rev}")
        cands, info, _ = run(rev)
        res = {"engine": "LM", "rev": rev, "ok": True, "info": info, "secs": round(time.time() - t0, 1), "cands": sigs(cands)}
        res["n"] = len(res["cands"])
    except Exception:
        res = {"engine": "LM", "rev": rev, "ok": False, "error": traceback.format_exc()[-2000:], "secs": round(time.time() - t0, 1), "cands": []}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res, ensure_ascii=False))
    return res


# ---------------------------------------------------------------- selftest (criteria 三.1)
def selftest():
    files = {
        "kernel/a.c": "extern char __start_X[], __stop_X[];\n"
                      "int img(void) { phys_addr_t a = virt_to_phys(__start_X); return a; }\n"
                      "int img_ok(void) { phys_addr_t a = __pa_symbol(__start_X); return a; }\n"
                      "int vm(void) { void *p = vmalloc(10); struct page *pg = virt_to_page(p); return 0; }\n"
                      "int vm_guard(void *x) { void *p = vmalloc(10); struct page *pg; if (is_vmalloc_addr(p)) pg = vmalloc_to_page(p); else pg = virt_to_page(p); return 0; }\n"
                      "int alias(void) { void *p = vmap(pages, 2, 0, PAGE_KERNEL); u8 *q = (u8 *)p + 4; sg_init_one(&sg, q, 4); return 0; }\n"
                      "int killed(void) { void *p = vmalloc(1); p = kmalloc(1, GFP_KERNEL); virt_to_page(p); return 0; }\n"
                      "int nested(int c) { void *s = kmap_local_page(pg); if (c) { memcpy(buf, s, 4); s = buf; } sg_init_one(&in, s, 4); return 0; }\n"
                      "int field(void) { sg_set_buf(&sg, area->buf, 4); return 0; }\n"
                      "int km(void) { void *p = kmalloc(8, GFP_KERNEL); return virt_to_phys(p); }\n"
                      "int io(void) { void __iomem *r = ioremap(0x1000, 8); return virt_to_phys((void *)r); }\n"
                      "int fld(struct a *ar) { ar->va = kmap_atomic(pg); void *q = ar->va + 8; return virt_to_phys(q); }\n"
                      "int fld_guard(struct a *ar) { ar->va = vmalloc(8); if (is_vmalloc_addr(ar->va)) return 0; return virt_to_phys(ar->va); }\n",
        "mm/zs.c": "static void *zs_map_object(int h) { void *ret; if (h) { a->va = kmap_atomic(pg); ret = a->va + 4; goto out; }\n"
                   "  ret = lin_buf(a); out: return ret; }\n"
                   "static void *zs_zmap(void *pool, int h) { return zs_map_object(h); }\n"
                   "static struct zpool_driver zs_drv = { .type = \"zs\", .map = zs_zmap, };\n",
        "mm/zpool.c": "void *zpool_map_handle(struct zpool *zp, int h) { return zp->driver->map(zp->pool, h); }\n",
        "mm/zsw.c": "void dec(struct zpool *z) { void *src = zpool_map_handle(z, 1); sg_init_one(&in, src, 4); }\n"
                    "void dec_ok(struct zpool *z) { void *src = zpool_map_handle(z, 1); if (!virt_addr_valid(src)) return; sg_init_one(&in, src, 4); }\n",
        "drivers/foo/b.c": "void other(struct thing *th) { void *p = th->ops->map(th); virt_to_page(p); }\n",
    }
    facts = {p: file_facts(p, s) for p, s in files.items()}
    A = Analyzer(facts)
    A.summarize()
    got = {(c["func"], c["kind"]) for c in A.sinks()}
    want = {("img", "镜像符号"), ("vm", "vmalloc"), ("alias", "vmap"), ("nested", "kmap"), ("io", "ioremap"), ("dec", "经来源函数"),
            ("fld", "kmap")}
    ok = got == want
    print("src_funcs", A.src_funcs)
    print("callbacks", A.cb)
    print("got ", sorted(got))
    print("want", sorted(want))
    print("selftest", "PASS" if ok else "FAIL", "missing", sorted(want - got), "extra", sorted(got - want))
    return ok


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
