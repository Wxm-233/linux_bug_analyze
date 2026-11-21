"""E-ZERO effect-dependency implementation-consistency check (effzero criteria 一). Lexical, any revision, no build. WSL.

    python3 effzero.py facts <rev>            -> /root/work/effzero/facts_<rev12>.pkl.gz  (phase 1, parallel)
    python3 effzero.py run <rev> [out.json]   -> candidates (phase 2; runs phase 1 if needed)
    python3 effzero.py selftest
"""
import gzip
import json
import os
import pickle
import re
import resource
import subprocess
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "p1check_20261115"))
import p1check as C  # noqa: E402  (read-only: strip, tokenize, functions, match_fwd, match_back, P)

REPO = "/root/repos/linux"
WORK = "/root/work/effzero"
EXCL = ("tools/", "scripts/", "samples/", "Documentation/", "usr/")
CAP = 512
IDENT = re.compile(r"^[A-Za-z_]\w*$")
REQBIT = re.compile(r"^_*[A-Z0-9_]*(ZERO[A-Z0-9_]*|_INIT|INIT_ON[A-Z0-9_]*)$")  # amendment 2.1
ZALLOC = {"kzalloc", "kvzalloc", "vzalloc", "kcalloc", "kvcalloc", "vcalloc", "get_zeroed_page", "dma_alloc_coherent",
          "dma_zalloc_coherent", "kzalloc_node", "kvzalloc_node", "vzalloc_node", "kcalloc_node", "kvcalloc_node", "devm_kzalloc",
          "devm_kcalloc", "kmem_cache_zalloc", "dmam_alloc_coherent", "kzalloc_obj", "kzalloc_objs", "vzalloc_noprof",
          "kzalloc_noprof", "kvzalloc_noprof", "kcalloc_noprof", "kvcalloc_noprof"}
ZALLOC |= {x + "_noprof" for x in list(ZALLOC)}
RAW = {"kmalloc", "kmalloc_array", "kmalloc_node", "kmalloc_array_node", "kvmalloc", "kvmalloc_node", "kvmalloc_array", "vmalloc",
       "vmalloc_node", "vmalloc_user", "vmalloc_32", "__vmalloc", "__vmalloc_node", "__vmalloc_node_range", "vmalloc_huge",
       "alloc_pages", "alloc_page", "__alloc_pages", "alloc_pages_node", "__alloc_pages_node", "alloc_pages_exact",
       "alloc_pages_exact_nid", "alloc_pages_vma", "__get_free_pages", "__get_free_page", "folio_alloc", "__folio_alloc",
       "kmem_cache_alloc", "kmem_cache_alloc_node", "dma_alloc_from_contiguous", "cma_alloc", "gen_pool_alloc",
       "gen_pool_alloc_algo", "gen_pool_dma_alloc", "gen_pool_dma_alloc_align", "memblock_alloc_raw", "dma_common_contiguous_remap",
       "dma_common_pages_remap", "vmap", "alloc_pages_mpol", "alloc_frozen_pages", "folio_alloc_mpol", "vma_alloc_folio",
       "alloc_page_vma", "dma_alloc_contiguous", "__dma_alloc_from_coherent", "alloc_pages_exact_node"}
RAW |= {x + "_noprof" for x in list(RAW)}
ZERO_OPS = {"memset", "memzero_explicit", "clear_page", "clear_highpage", "clear_user_highpage", "clear_highpage_kasan_tagged",
            "zero_user", "zero_user_segment", "zero_user_segments", "folio_zero_range", "memzero_page", "clear_user_page"}
CONV = {"page_address", "page_to_virt", "phys_to_virt", "virt_to_page", "lowmem_page_address", "folio_address", "__va",
        "kasan_reset_tag", "untagged_addr", "page_folio", "folio_page", "pfn_to_page", "virt_to_phys", "__pa", "page_to_phys",
        "phys_to_page", "virt_to_folio", "pfn_to_virt", "virt_to_pfn", "page_to_pfn", "pfn_to_kaddr", "kmap", "kmap_local_page",
        "kmap_atomic"}
NULLISH = {"NULL", "0", "false", "ZERO_SIZE_PTR"}
ERRF = {"ERR_PTR", "ERR_CAST", "IOMEM_ERR_PTR"}
WRITE_FUNCS = {"memcpy", "memcpy_fromio", "memmove", "strscpy", "strcpy", "strncpy", "sprintf", "snprintf", "scnprintf",
               "copy_from_user", "sg_init_table", "sg_alloc_table", "memcpy_toio", "strlcpy", "sg_set_page", "sg_init_one",
               "__copy_from_user", "copy_from_kernel_nofault"}
CAPWORD = re.compile(r"(has_|supports|_enabled|_supported|can_|_capable|is_)")


def reqbit_in(t, lo, hi):
    """request bit = all-caps identifier with INIT/ZERO that is not a macro call (devlog 1)"""
    return any(REQBIT.match(t[i][0]) and not (i + 1 < len(t) and t[i + 1][0] == "(") for i in range(lo, hi))


ZSET = {"__GFP_ZERO"}   # + object-like macros expanding to __GFP_ZERO (devlog 3), set by facts()


def _init_worker(zs):
    global ZSET
    ZSET = set(zs)


def zero_macros(rev):
    """object-like macros whose expansion contains __GFP_ZERO, transitively (devlog 3)"""
    found, frontier = set(), {"__GFP_ZERO"}
    for _ in range(4):
        pat = "|".join(sorted(frontier))
        out = git("grep", "-h", "-E", r"^\s*#\s*define\s+\w+\s.*\b(" + pat + r")\b", rev, "--", "*.h", "*.c")
        new = set()
        for ln in out.split("\n"):
            m = re.match(r"^\s*#\s*define\s+(\w+)\s", ln)
            if m and m.group(1) not in found and m.group(1) != "__GFP_ZERO":
                new.add(m.group(1))
        if not new:
            break
        found |= new
        frontier = new
    return found


class Overflow(Exception):
    pass


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def tree_files(rev):
    return [p for p in git("ls-tree", "-r", "--name-only", rev).split("\n")
            if p.endswith((".c", ".h")) and not p.startswith(EXCL)]


# ------------------------------------------------------------------ expression helpers
def strip_cast(t, lo, hi):
    while lo < hi:
        lo, hi = C.strip_parens(t, lo, hi)
        if t[lo][0] == "(":
            k = C.match_fwd(t, lo)
            inner = [x[0] for x in t[lo + 1:k]]
            if k < hi - 1 and inner and all(IDENT.match(x) or x == "*" for x in inner) and \
                    ("*" in inner or any(x in ("void", "struct", "unsigned", "long", "char", "u8") or x.endswith("_t") for x in inner)):
                lo = k + 1
                continue
        break
    return lo, hi


def args_list(t, k):
    a = C.args_of(t, k)[0]
    return [] if len(a) == 1 and a[0][0] == a[0][1] else a


def call_at(t, lo, hi):
    """whole expression a call -> (kind, name, args[(lo,hi)]) kind in name/member"""
    lo, hi = strip_cast(t, lo, hi)
    if hi - lo >= 3 and t[hi - 1][0] == ")":
        k = C.match_back(t, hi - 1)
        if k > lo and IDENT.match(t[k - 1][0]):
            if k - 1 == lo:
                return ("name", t[lo][0], args_list(t, k))
            if k - 2 >= lo and t[k - 2][0] in ("->", "."):
                return ("member", t[k - 1][0], args_list(t, k))
    return None


def obj_base(t, lo, hi, depth=0):
    """object variable an expression denotes: strip casts, CONV(x), x +/- off, &x[...]; None otherwise"""
    lo, hi = strip_cast(t, lo, hi)
    if lo >= hi or depth > 4:
        return None
    c = call_at(t, lo, hi)
    if c:
        if c[0] == "name" and c[1] in CONV and c[2]:
            return obj_base(t, c[2][0][0], c[2][0][1], depth + 1)
        return None
    if t[lo][0] == "&" and lo + 1 < hi:
        lo += 1
    if not IDENT.match(t[lo][0]) or t[lo][0] in C.KEYW:
        return None
    j = lo + 1
    while j + 1 < hi and t[j][0] in ("->", ".") and IDENT.match(t[j + 1][0]):
        j += 2
    name = "".join(x[0] for x in t[lo:j])
    if j < hi and t[j][0] not in ("+", "-", "["):
        return None
    return name


def calls_in(t, lo, hi):
    """(name, member?, k_open) for every call in range"""
    out = []
    for i in range(lo, hi - 1):
        if t[i + 1][0] == "(" and IDENT.match(t[i][0]) and t[i][0] not in C.KEYW:
            out.append((t[i][0], i > lo and t[i - 1][0] in ("->", "."), i + 1))
    return out


def assigns_in(t, lo, hi):
    """(lhs_base, rhs_lo, rhs_hi) for `x = rhs` (also inside conditions)"""
    out = []
    for e in range(lo + 1, hi):
        if t[e][0] != "=":
            continue
        a = e - 1
        while a - 2 >= lo and t[a - 1][0] in ("->", ".") and IDENT.match(t[a - 2][0]):
            a -= 2
        if not IDENT.match(t[e - 1][0]):
            continue
        lhs = "".join(x[0] for x in t[a:e])
        d, r = 0, e + 1
        while r < hi:
            x = t[r][0]
            if x in "([{":
                d += 1
            elif x in ")]}":
                if d == 0:
                    break
                d -= 1
            elif x in (",", ";") and d == 0:
                break
            r += 1
        out.append((lhs, e + 1, r))
    return out


# ------------------------------------------------------------------ per-function analysis
class Fn:
    def __init__(self, t, lo, hi, params, rk):
        self.t, self.lo, self.hi, self.params, self.rk = t, lo, hi, params, rk
        self.uf = {}
        self.cache_src = {}
        for lhs, a, b in assigns_in(t, lo, hi):
            c = call_at(t, a, b)
            if c and c[0] == "name" and c[1] in CONV and c[2]:
                rb = obj_base(t, c[2][0][0], c[2][0][1])
            else:
                rb = obj_base(t, a, b) if not c else None
            if rb:
                self.union(lhs, rb)

    def find(self, x):
        while self.uf.get(x, x) != x:
            x = self.uf[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.uf[ra] = rb

    def cls(self, name):
        return self.find(name) if name else None

    def source(self, t, a, b):
        c = call_at(t, a, b)
        if not c:
            lo, hi = strip_cast(t, a, b)
            if hi - lo == 1 and t[lo][0] in NULLISH:
                return "U"
            return None  # alias or other: no new source
        kind, name, args = c
        if kind == "member":
            return "U"
        if name in CONV:
            return None
        toks = {x[0] for x in t[a:b]}
        if name in ZALLOC or toks & ZSET:
            return "Z"
        if name in RAW:
            if any(x.startswith(("GFP_", "__GFP_")) for x in toks):
                return "R"
            pn = set(self.params)
            if any(x in pn for x in toks):
                return "G"
            return "R"
        return ("C", name)

    def apply(self, st, lo, hi):
        obj, pend, consumed = st
        obj, pend = dict(obj), dict(pend)
        t = self.t
        if not consumed and reqbit_in(t, lo, hi):
            consumed = True
        for lhs, a, b in assigns_in(t, lo, hi):
            s = self.source(t, a, b)
            if s is not None:
                k = self.cls(lhs)
                obj[k] = s
                pend.pop(k, None)
        for e in range(lo + 1, hi):  # amendment 1.2: writes into the object
            if t[e][0] != "=":
                continue
            b = None
            if t[e - 1][0] == "]":
                kk = C.match_back(t, e - 1, "[", "]")
                if kk > lo and IDENT.match(t[kk - 1][0]):
                    j = kk - 1
                    while j - 2 >= lo and t[j - 1][0] in ("->", ".") and IDENT.match(t[j - 2][0]):
                        j -= 2
                    b = t[j][0]
            elif IDENT.match(t[e - 1][0]) and e - 2 >= lo and t[e - 2][0] in ("->", "."):
                j = e - 1
                while j - 2 >= lo and t[j - 1][0] in ("->", ".") and IDENT.match(t[j - 2][0]):
                    j -= 2
                b = t[j][0]
            if b:
                kk = self.cls(b)
                if obj.get(kk) != "Z":
                    obj[kk] = "W"
        for name, mem, k in calls_in(t, lo, hi):
            if mem:
                continue
            args = args_list(t, k)
            if name in WRITE_FUNCS and args:
                ob = obj_base(t, *args[0])
                if ob and obj.get(self.cls(ob)) != "Z":
                    obj[self.cls(ob)] = "W"
                continue
            if name in ZERO_OPS and args:
                if name == "memset" and (len(args) < 2 or [x[0] for x in t[args[1][0]:args[1][1]]] != ["0"]):
                    continue
                ob = obj_base(t, *args[0])
                if ob:
                    obj[self.cls(ob)] = "Z"
                continue
            for j, (x, y) in enumerate(args[:6]):
                ob = obj_base(t, x, y)
                if ob:
                    kk = self.cls(ob)
                    pend[kk] = tuple(sorted(set(pend.get(kk, ())) | {(name, j)}))
        return (tuple(sorted(obj.items(), key=str)), tuple(sorted(pend.items(), key=str)), consumed)

    # walk returns list of (state, kind, info, conds)
    def seq(self, stmts, st, conds):
        states = [(st, conds)]
        out = []
        for s in stmts:
            new, seen = [], set()
            for x, cd in states:
                for y, kind, info, cd2 in self.stmt(s, x, cd):
                    if kind == "fall":
                        if y not in seen:
                            seen.add(y)
                            new.append((y, cd2))
                    else:
                        out.append((y, kind, info, cd2))
            states = new
            if len(states) + len(out) > CAP:
                raise Overflow
        return out + [(x, "fall", None, cd) for x, cd in states]

    def ctext(self, lo, hi, neg):
        s = " ".join(x[0] for x in self.t[lo:hi])[:80]
        return ("!(" + s + ")") if neg else s

    def stmt(self, s, st, cd):
        if s is None:
            return [(st, "fall", None, cd)]
        k = s[0]
        if k == "block":
            return self.seq(s[1], st, cd)
        if k == "expr":
            return [(self.apply(st, *s[1]), "fall", None, cd)]
        if k == "if":
            st = self.apply(st, *s[1])
            nv, br = self.null_test(*s[1])
            sa, sb = st, st
            if nv:
                kk = self.cls(nv)
                ob = dict(st[0])
                ob[kk] = "NULL"
                stn = (tuple(sorted(ob.items(), key=str)), st[1], st[2])
                sa, sb = (stn, st) if br == "then" else (st, stn)
            a = self.stmt(s[2], sa, (cd + (self.ctext(*s[1], False),))[-3:])
            b = self.stmt(s[3], sb, (cd + (self.ctext(*s[1], True),))[-3:])
            return a + b
        if k == "loop":
            for r in s[3]:
                st = self.apply(st, *r)
            if s[1]:
                st = self.apply(st, *s[1])
            out = []
            for y, kind, info, cd2 in self.stmt(s[2], st, cd):
                out.append((y, "fall" if kind in ("break", "continue", "fall") else kind, info, cd2))
            return out
        if k == "switch":
            st = self.apply(st, *s[1])
            out = [(st, "fall", None, cd)]
            for y, kind, info, cd2 in self.stmt(s[2], st, cd):
                out.append((y, "fall" if kind in ("break", "fall") else kind, info, cd2))
            return out
        if k == "jump":
            st = self.apply(st, *s[2])
            return [(st, s[1], s[2], cd)]
        return [(st, "fall", None, cd)]

    def null_test(self, lo, hi):
        """devlog 3: (var, branch-where-var-is-null) for !x, x == NULL, NULL == x, x, x != NULL, IS_ERR(x)"""
        t = self.t
        lo, hi = C.strip_parens(t, lo, hi)
        w = [x[0] for x in t[lo:hi]]
        if len(w) >= 2 and w[0] == "!":
            b = obj_base(t, lo + 1, hi)
            if b and "(" not in w:
                return b, "then"
        if len(w) == 3 and w[1] == "==" and "NULL" in (w[0], w[2]):
            return (w[0] if w[2] == "NULL" else w[2]), "then"
        if len(w) == 3 and w[1] == "!=" and "NULL" in (w[0], w[2]):
            return (w[0] if w[2] == "NULL" else w[2]), "else"
        if len(w) >= 4 and w[0] in ("IS_ERR", "IS_ERR_OR_NULL") and w[1] == "(" and w[-1] == ")":
            b = obj_base(t, lo + 2, hi - 1)
            if b:
                return b, "then"
        if len(w) == 1 and IDENT.match(w[0]):
            return w[0], "else"
        return None, None

    def run(self):
        tree = C.P(self.t, self.lo, self.hi + 1).block()
        st0 = ((), (), False)
        return self.stmt(tree, st0, ())

    def ret_info(self, info):
        """success-return classification of `return E` -> (is_success, src) for pointer functions"""
        t = self.t
        lo, hi = info
        lo, hi = strip_cast(t, lo, hi)
        if lo >= hi:
            return False, None
        if hi - lo == 1 and t[lo][0] in NULLISH:
            return False, None
        if t[lo][0] in ERRF or (t[lo][0] == "-" and hi - lo <= 2):
            return False, None
        return True, (lo, hi)

    def is_error_ret(self, info):
        t = self.t
        lo, hi = strip_cast(t, *info)
        if lo >= hi:
            return False
        return t[lo][0] == "-" or t[lo][0] in ERRF or (hi - lo == 1 and t[lo][0] in ("NULL", "false"))


def head_of(t, lo):
    j = lo - 1
    depth = 0
    while j >= 0:
        x = t[j][0]
        if x == ")":
            depth += 1
        elif x == "(":
            depth -= 1
        elif x in (";", "}") and depth == 0:
            break
        j -= 1
    return j + 1


def params_of(t, name_i, lo):
    k = name_i + 1
    end = C.match_fwd(t, k)
    segs, seg, d = [], [], 0
    for x in t[k + 1:end]:
        if x[0] == "," and d == 0:
            segs.append(seg)
            seg = []
            continue
        if x[0] in "([":
            d += 1
        elif x[0] in ")]":
            d -= 1
        seg.append(x[0])
    if seg:
        segs.append(seg)
    out = []
    for sg in segs:
        ids = [x for x in sg if IDENT.match(x) and x not in ("const", "struct", "volatile", "__user", "__iomem", "__force")]
        out.append(ids[-1] if ids else "?")
    return out


def file_facts(path, src):
    s = C.strip(src)
    t = C.tokenize(s)
    is_h = path.endswith(".h")
    fns = []
    for name, _p, lo, hi in C.functions(t):
        h0 = head_of(t, lo)
        head = [x[0] for x in t[h0:lo]]
        if name not in head:
            continue
        ni = h0 + head.index(name)
        pre = head[:head.index(name)]
        static = "static" in pre
        rk = "ptr" if "*" in pre else ("void" if "void" in pre else "other")
        try:
            params = params_of(t, ni, lo)
        except Exception:
            params = []
        rec = {"n": name, "f": path, "l": t[lo][1], "le": t[hi][1], "st": static and not is_h, "h": is_h, "rk": rk,
               "params": params, "unknown": False, "rets": [], "pz": [], "req": [], "e2": [], "e3": [], "ca": [], "fw": []}
        pset = set(params)
        fw = set()  # amendment 2.3: callees that receive one of our parameters unchanged
        for nm, mem, k in calls_in(t, lo, hi):
            if mem or nm in C.KEYW:
                continue
            try:
                if any(hi2 - lo2 == 1 and t[lo2][0] in pset for lo2, hi2 in args_list(t, k)):
                    fw.add(nm)
            except Exception:
                pass
        rec["fw"] = sorted(fw)[:20]
        try:
            F = Fn(t, lo, hi, params, rk)
            outs = F.run()
        except (Overflow, RecursionError, IndexError, ValueError):
            rec["unknown"] = True
            fns.append(rec)
            continue
        pcls = [F.cls(p) for p in params[:6]]
        rets, pz, req = set(), set(), set()
        for (obj, pend, consumed), kind, info, cd in outs:
            if kind == "goto":
                continue
            od, pd = dict(obj), dict(pend)
            line = t[info[0]][1] if (kind == "return" and info and info[0] < len(t)) else t[hi][1]
            if kind == "return" and rk == "ptr":
                ok, rng = F.ret_info(info)
                if not ok:
                    continue
                c = call_at(t, *rng)
                if c and not (c[0] == "name" and c[1] in CONV):
                    src = F.source(t, *rng) or "U"
                    pd_ = ()
                else:
                    ob = obj_base(t, *rng)
                    k = F.cls(ob) if ob else None
                    src = od.get(k, "U") if k else "U"
                    pd_ = pd.get(k, ()) if k else ()
                    if src == "NULL":
                        continue
                rets.add((src if isinstance(src, str) else tuple(src), pd_, cd, line))
            if kind == "return" and rk == "other" and info and F.is_error_ret(info):
                continue
            pz.add(tuple(("Z" if od.get(k) == "Z" else pd.get(k, ())) for k in pcls))
            req.add((consumed, any(v == "Z" for v in od.values()), cd, line))  # (bit used, zeroed: amendment 2.4 R1)
        # keep distinct by semantic part
        rec["rets"] = list({(r[0], r[1]): r for r in sorted(rets, key=str)}.values())[:64]
        rec["pz"] = sorted(pz, key=str)[:64]
        rec["req"] = list({(r[0], r[1]): r for r in sorted(req, key=str)}.values()) if req else []
        rec["req_all"] = [r for r in sorted(req, key=str) if not r[0] and not r[1]][:8]
        # devlog 4: parameters that appear next to a request bit (tested or passed on together)
        rp = set()
        for i in range(lo, hi):
            if t[i][0] in pset and reqbit_in(t, max(lo, i - 6), min(hi, i + 7)):
                rp.add(params.index(t[i][0]))
        rec["reqp"] = sorted(rp)
        # E2 / E3 caller signals, call-assign facts (R2)
        try:
            tree = C.P(t, lo, hi + 1).block()
            caller_signals(F, tree, rec)
        except Exception:
            pass
        fns.append(rec)
    ops = []
    for m in re.finditer(r"\bstruct\s+(\w+)\s+(?:const\s+)?(\w+)\s*(?:\[[^\]]*\])?\s*=\s*\{", s):
        T = m.group(1)
        i = m.end() - 1
        d, j = 0, i
        while j < len(s):
            if s[j] == "{":
                d += 1
            elif s[j] == "}":
                d -= 1
                if d == 0:
                    break
            j += 1
        for mm in re.finditer(r"\.\s*(\w+)\s*=\s*&?\s*(\w+)\s*[,}\n]", s[i:j + 1]):
            ops.append((T, mm.group(1), mm.group(2), s.count("\n", 0, i + mm.start()) + 1))
    return {"fns": fns, "ops": ops}


def zero_ops_in(F, stmt):
    """callee names and direct zero ops inside a statement subtree"""
    names = set()

    def rec(s):
        if s is None:
            return
        k = s[0]
        if k == "block":
            for x in s[1]:
                rec(x)
        elif k == "expr":
            names.update(n for n, mem, _ in calls_in(F.t, *s[1]) if not mem)
        elif k == "if":
            names.update(n for n, mem, _ in calls_in(F.t, *s[1]) if not mem)
            rec(s[2])
            rec(s[3])
        elif k == "loop":
            rec(s[2])
        elif k == "switch":
            rec(s[2])
        elif k == "jump":
            names.update(n for n, mem, _ in calls_in(F.t, *s[2]) if not mem)
    rec(stmt)
    return names


def caller_signals(F, tree, rec):
    t = F.t
    allstmts = []

    def flat(s):
        if s is None:
            return
        if s[0] == "block":
            for x in s[1]:
                flat(x)
            allstmts.append(s)
        elif s[0] == "if":
            flat(s[2])
            flat(s[3])
        elif s[0] in ("loop", "switch"):
            flat(s[2])
    flat(tree)
    # guards: if (v ...) <zeroing-ish>
    guards = defaultdict(set)

    def gwalk(s):
        if s is None:
            return
        if s[0] == "block":
            for x in s[1]:
                gwalk(x)
        elif s[0] == "if":
            ids = {x[0] for x in t[s[1][0]:s[1][1]] if IDENT.match(x[0])}
            for v in ids:
                guards[v] |= zero_ops_in(F, s[2])
            gwalk(s[2])
            gwalk(s[3])
        elif s[0] in ("loop", "switch"):
            gwalk(s[2])
    gwalk(tree)
    fn_toks = {x[0] for x in t[F.lo:F.hi]}
    strips_zero = any(t[i][0] == "~" and any(x[0] == "__GFP_ZERO" for x in t[i:i + 12]) for i in range(F.lo, F.hi)) or \
        "__GFP_SKIP_ZERO" in fn_toks
    has_zero = bool(fn_toks & ZERO_OPS)
    reqvars = {lhs for lhs, a, b in assigns_in(t, F.lo, F.hi) if reqbit_in(t, a, b)}
    for i in range(F.lo, F.hi - 1):  # `v |= REQBIT`
        if t[i + 1][0] == "|=" and IDENT.match(t[i][0]) and reqbit_in(t, i + 2, min(i + 8, F.hi)):
            reqvars.add(t[i][0])
    for blk in allstmts:
        st = blk[1]
        for idx, s in enumerate(st):
            ranges = []
            if s is None:
                continue
            if s[0] == "expr":
                ranges = [s[1]]
            elif s[0] == "loop":
                ranges = [(F.lo, F.lo)]
            cands = set()
            if s[0] == "expr":
                for name, mem, k in calls_in(t, *s[1]):
                    cands.add((name, mem, k))
            elif s[0] == "loop" and s[2] is not None:
                sub = s[2]
                subs = sub[1] if sub[0] == "block" else [sub]
                for x in subs:
                    if x is not None and x[0] == "expr":
                        for name, mem, k in calls_in(t, *x[1]):
                            cands.add((name, mem, k))
            for name, mem, k in cands:
                if name in CONV or name in C.KEYW:
                    continue
                args = args_list(t, k)
                # E2: next direct statements (<=3) contain `v = false|0;` with v guarding zeroing-ish callees
                for s2 in st[idx + 1:idx + 4]:
                    if s2 is None or s2[0] != "expr":
                        continue
                    lo2, hi2 = s2[1]
                    w = [x[0] for x in t[lo2:hi2]]
                    if len(w) == 3 and w[1] == "=" and w[2] in ("false", "0") and IDENT.match(w[0]) and guards.get(w[0]):
                        argk = next((j for j, (x, y) in enumerate(args) if obj_base(t, x, y)), None)
                        rec["e2"].append((name, mem, argk, t[k][1], w[0], sorted(guards[w[0]])))
                # E3: request bit passed + caller does not zero itself
                jbit = next((j for j, (a, b) in enumerate(args) if reqbit_in(t, a, b) or
                             any(x[0] in reqvars for x in t[a:b])), None)
                if jbit is not None and (strips_zero or not has_zero):
                    rec["e3"].append((name, mem, t[k][1], strips_zero, jbit))
    # R2 facts: x = g(...) and whether x's class is zeroed anywhere in the function
    zeroed = set()
    for name, mem, k in calls_in(t, F.lo, F.hi):
        if name in ZERO_OPS and not mem:
            args = args_list(t, k)
            if args:
                ob = obj_base(t, *args[0])
                if ob:
                    zeroed.add(F.cls(ob))
    for lhs, a, b in assigns_in(t, F.lo, F.hi):
        c = call_at(t, a, b)
        if c and c[0] == "name":
            rec["ca"].append((c[1], F.cls(lhs) in zeroed))


# ------------------------------------------------------------------ phase 1 driver
def _work(args):
    rev, paths = args
    blobs = C.cat_files(rev, paths)
    out = []
    for p, src in blobs.items():
        if len(src) > 2_000_000:
            continue
        try:
            out.append((p, file_facts(p, src)))
        except Exception as e:  # noqa: BLE001
            out.append((p, {"fns": [], "ops": [], "err": repr(e)[:200]}))
    return out


def facts(rev, nproc=4):
    rev = git("rev-parse", rev).strip()
    os.makedirs(WORK, exist_ok=True)
    fn = f"{WORK}/facts_{rev[:12]}.pkl.gz"
    if os.path.exists(fn):
        return pickle.load(gzip.open(fn))
    t0 = time.time()
    files = tree_files(rev)
    chunks = [(rev, files[i:i + 400]) for i in range(0, len(files), 400)]
    res = {}
    zs = zero_macros(rev)
    print("  zero macros:", len(zs), flush=True)
    with Pool(nproc, initializer=_init_worker, initargs=(sorted(zs),)) as pool:
        for k, part in enumerate(pool.imap_unordered(_work, chunks)):
            for p, f in part:
                res[p] = f
            if k % 20 == 0:
                print(f"  facts {rev[:12]} {k + 1}/{len(chunks)} {round(time.time() - t0)}s", flush=True)
    data = {"rev": rev, "files": res, "secs": round(time.time() - t0)}
    pickle.dump(data, gzip.open(fn, "wb"))
    return data


# ------------------------------------------------------------------ phase 2
class Index:
    """definition lookup: a call from file F to name N resolves to N's definition in F if there is one (static or not),
    otherwise to all non-static definitions of N (devlog 3)"""

    def __init__(self, files):
        self.by_nf = defaultdict(list)
        self.glob = defaultdict(list)
        for p, f in files.items():
            for d in f["fns"]:
                d["id"] = (d["f"], d["n"], d["l"])
                self.by_nf[(d["n"], d["f"])].append(d)
                if not d["st"]:
                    self.glob[d["n"]].append(d)

    def resolve(self, name, file):
        return self.by_nf.get((name, file)) or self.glob.get(name, [])


def summaries(files, ix):
    """fixpoint per definition: ret[id] in Z/R/M/U, pz[id] = param indexes zeroed on every normal exit"""
    ret, pzs = {}, {}

    def callee_ret(name, file):
        ds = ix.resolve(name, file)
        vals = {ret.get(d["id"], "U") for d in ds}
        return vals.pop() if len(vals) == 1 else "U"

    def callee_pz(name, file, j):
        ds = ix.resolve(name, file)
        return bool(ds) and all(j in pzs.get(d["id"], ()) for d in ds)

    def path_zero(src, pend, file):
        if src == "Z":
            return "Z"
        if any(callee_pz(n, file, j) for n, j in pend):
            return "Z"
        if src in ("R", "G"):
            return src
        if isinstance(src, tuple) and src[0] == "C":
            v = callee_ret(src[1], file)
            return {"Z": "Z", "R": "R", "M": "M"}.get(v, "U")
        return "U"
    alld = [d for f in files.values() for d in f["fns"]]
    for _ in range(12):
        changed = False
        for d in alld:
            if d["unknown"]:
                continue
            if d["rk"] == "ptr" and d["rets"]:
                ps = {path_zero(r[0], r[1], d["f"]) for r in d["rets"]}
                if ps == {"Z"}:
                    v = "Z"
                elif ps <= {"R", "G"}:
                    v = "R"
                elif "U" not in ps and ps & {"R", "G", "M"}:
                    v = "M"
                else:
                    v = "U"
                if ret.get(d["id"], "U") != v:
                    ret[d["id"]] = v
                    changed = True
            if d["pz"]:
                n = min(len(ex) for ex in d["pz"])
                ok = set()
                for k in range(n):
                    if all(ex[k] == "Z" or (ex[k] != "Z" and any(callee_pz(nm, d["f"], j) for nm, j in ex[k])) for ex in d["pz"]):
                        ok.add(k)
                if ok and pzs.get(d["id"]) != ok:
                    pzs[d["id"]] = ok
                    changed = True
        if not changed:
            break
    return ret, pzs, path_zero, callee_pz


def impl_status(d, path_zero):
    if d["unknown"] or d["rk"] != "ptr" or not d["rets"]:
        return "U", []
    st = [(path_zero(r[0], r[1], d["f"]), r) for r in d["rets"]]
    bad = [r for s, r in st if s in ("R", "G", "M")]
    if bad:
        return "N", bad
    if all(s == "Z" for s, _ in st):
        return "Z", []
    return "U", []


def origin_of(d, bad, ix, path_zero, depth=0):
    """amendment 2.2: follow ('C', g) sources into same-file definitions that themselves have non-zero paths"""
    for r in bad:
        if isinstance(r[0], tuple) and r[0][0] == "C":
            ds = [x for x in ix.resolve(r[0][1], d["f"]) if x["f"] == d["f"]]
            for x in ds:
                s, b2 = impl_status(x, path_zero)
                if s == "N":
                    if depth < 2:
                        deeper = origin_of(x, b2, ix, path_zero, depth + 1)
                        if deeper:
                            return deeper
                    return x["n"]
    return None


def analyse(data, compiled=None):
    files = data["files"]
    ix = Index(files)
    ret, pzs, path_zero, callee_pz = summaries(files, ix)
    defs = defaultdict(list)
    for p, f in files.items():
        for d in f["fns"]:
            defs[d["n"]].append(d)
    groups = {}
    for name, ds in defs.items():
        el = [d for d in ds if not d["st"]]
        if len({d["f"] for d in el}) >= 2:
            groups[("name", name)] = el
    opsm = defaultdict(list)
    for p, f in files.items():
        for T, m, fn, line in f["ops"]:
            opsm[(T, m)].append((p, fn))
    for (T, m), lst in opsm.items():
        if len({p for p, _ in lst}) < 2:
            continue
        el, seen = [], set()
        for p, fn in lst:
            for d in ix.resolve(fn, p):
                if d["id"] not in seen:
                    seen.add(d["id"])
                    el.append(d)
        if len({d["f"] for d in el}) >= 2:
            groups[("ops", T, m)] = el
    callz = defaultdict(list)
    for p, f in files.items():
        for d in f["fns"]:
            for g, z in d["ca"]:
                callz[g].append(z)
    cands = []
    # E1
    for gk, el in groups.items():
        st = [(impl_status(d, path_zero), d) for d in el if d["rk"] == "ptr"]
        nz = [d for (s, _), d in st if s == "Z"]
        nn = [((s, bad), d) for (s, bad), d in st if s == "N"]
        if len(nz) >= 2 and len(nz) > len(nn):
            for (s, bad), d in nn:
                if gk[0] == "name" and callz.get(d["n"]) and all(callz[d["n"]]):
                    continue  # R2
                archev = d["f"].startswith("arch/") or any(x["f"].startswith("arch/") for x in el)
                cands.append({"form": "E1", "group": "/".join(gk), "file": d["f"], "line": d["l"], "func": d["n"],
                              "origin": origin_of(d, bad, ix, path_zero),
                              "paths": [{"src": str(r[0]), "conds": list(r[2]), "line": r[3]} for r in bad[:3]],
                              "n_zero": len(nz), "n_nonzero": len(nn), "n_unknown": len(st) - len(nz) - len(nn),
                              "zero_impls": sorted({(x["f"], x["n"]) for x in nz})[:6], "arch": archev})
    # E2 / E3 interface lookup (amendment 1.1 member uniqueness, amendment 2.3 wrappers)
    gby_name = {k[1]: v for k, v in groups.items() if k[0] == "name"}
    gby_member, mtypes = {}, defaultdict(set)
    for k, v in groups.items():
        if k[0] == "ops":
            mtypes[k[2]].add(k[1])
    for k, v in groups.items():
        if k[0] == "ops" and len(mtypes[k[2]]) == 1:
            gby_member[k[2]] = v

    def iface(name, mem, file):
        if mem:
            return gby_member.get(name), name
        if name in gby_name:
            return gby_name[name], name
        frontier, seen = [(name, file)], {name}
        for _ in range(2):
            nxt = []
            for nm, fl in frontier:
                for d in ix.resolve(nm, fl):
                    for g in d.get("fw", []):
                        if g in seen:
                            continue
                        seen.add(g)
                        if g in gby_name:
                            return gby_name[g], g
                        nxt.append((g, d["f"]))
            frontier = nxt
        return None, None

    def zeroes_param(x, k):
        if x["unknown"] or not x["pz"]:
            return None
        res = []
        for ex in x["pz"]:
            e = ex[k] if k < len(ex) else ()
            res.append(e == "Z" or (e != "Z" and any(callee_pz(nm, x["f"], j) for nm, j in e)))
        return res
    for p, f in files.items():
        for d in f["fns"]:
            for name, mem, argk, line, var, gcallees in d["e2"]:
                if argk is None:
                    continue
                el, gname = iface(name, mem, d["f"])
                if not el:
                    continue
                guard_zero = any(c in ZERO_OPS or any(pzs.get(x["id"]) for x in ix.resolve(c, d["f"])) for c in gcallees)
                if not guard_zero:
                    continue
                zs, ns = [], []
                for x in el:
                    ok = zeroes_param(x, argk)
                    if ok is None:
                        continue
                    if any(ok):  # amendment 1.3
                        zs.append(x)
                    else:
                        ns.append(x)
                if zs and ns:
                    archev = d["f"].startswith("arch/") or any(x["f"].startswith("arch/") for x in el)
                    cands.append({"form": "E2", "group": ("ops/" if mem else "name/") + gname, "file": d["f"], "line": line,
                                  "func": d["n"], "skip_var": var, "zero_impls": sorted({(x["f"], x["n"]) for x in zs})[:6],
                                  "nonzero_impls": sorted({(x["f"], x["n"]) for x in ns})[:6], "arch": archev})
            for name, mem, line, strips, jbit in d["e3"]:
                el, gname = iface(name, mem, d["f"])
                if not el:
                    continue
                users = [x for x in el if jbit in x.get("reqp", []) and any(r[0] for r in x.get("req", []))]
                if not users:
                    continue
                for x in el:
                    early = x.get("req_all", [])
                    if x["unknown"] or not early or jbit not in x.get("reqp", []):
                        continue
                    archev = x["f"].startswith("arch/") or any(y["f"].startswith("arch/") for y in el)
                    cands.append({"form": "E3", "group": ("ops/" if mem else "name/") + gname, "file": x["f"], "line": x["l"],
                                  "func": x["n"], "caller": [d["f"], d["n"], line], "caller_strips_zero": strips,
                                  "early_paths": [{"conds": list(r[2]), "line": r[3]} for r in early[:3]], "arch": archev})
    out, seen = [], set()
    for c in cands:
        k = (c["form"], c["file"], c["func"]) if c["form"] != "E3" else ("E3", c["file"], c["func"], c["group"])
        if k in seen:
            continue
        seen.add(k)
        if compiled:
            c["compiled"] = {a: (c["file"] in s) for a, s in compiled.items()}
        out.append(c)

    def rk(c):
        margin = (c.get("n_zero", 0) - c.get("n_nonzero", 0)) if c["form"] == "E1" else 0
        return (not c["arch"], c["form"] == "E1", -margin, c["file"], c["line"])
    out.sort(key=rk)
    for i, c in enumerate(out, 1):
        c["rank"] = i
    stats = {"functions": sum(len(f["fns"]) for f in files.values()), "unknown_fns": sum(d["unknown"] for f in files.values() for d in f["fns"]),
             "groups": len(groups), "ret_summ": Counter(ret.values()), "pz_summ": len(pzs),
             "file_errors": sum(1 for f in files.values() if f.get("err")), "forms": Counter(c["form"] for c in out)}
    return out, stats


def run(rev, outp=None, compiled=None):
    t0 = time.time()
    data = facts(rev)
    cands, stats = analyse(data, compiled)
    stats["secs_phase1"] = data.get("secs")
    stats["secs_total"] = round(time.time() - t0)
    stats["maxrss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
    res = {"rev": data["rev"], "stats": {k: (dict(v) if isinstance(v, Counter) else v) for k, v in stats.items()}, "cands": cands}
    if outp:
        Path(outp).write_text(json.dumps(res, indent=1, ensure_ascii=False))
    return res


SELF = r'''
void *a_alloc(struct device *dev, size_t size, gfp_t gfp)
{
	void *p = alloc_pages_exact(size, gfp);
	if (!p)
		return NULL;
	if (gfp & __GFP_ZERO)
		memset(p, 0, size);
	return p;
}
void *b_alloc(size_t size)
{
	struct page *page = alloc_pages(GFP_KERNEL, 2);
	void *ret;
	if (!page)
		return NULL;
	ret = page_address(page);
	memset(ret, 0, size);
	return ret;
}
void zero_it(struct page *page)
{
	clear_highpage(page);
}
void *c_alloc(size_t size)
{
	void *ret = (void *)__get_free_pages(GFP_KERNEL, 2);
	if (ret)
		memset(ret, 0, size);
	return ret;
}
void hook(struct page *page, gfp_t gfp)
{
	bool init = want_init(gfp);
	int i;
	if (zero_tags) {
		for (i = 0; i < 4; i++)
			tag_clear(page + i);
		init = false;
	}
	if (init)
		kernel_init_pages(page, 4);
}
'''


def selftest():
    f = file_facts("x.c", SELF)
    by = {d["n"]: d for d in f["fns"]}
    a, b, z, h = by["a_alloc"], by["b_alloc"], by["zero_it"], by["hook"]
    ok = True
    srcs_a = sorted(str(r[0]) for r in a["rets"])
    print("a_alloc rets", srcs_a)
    ok &= srcs_a == ["G", "Z"]
    print("b_alloc rets", [str(r[0]) for r in b["rets"]])
    ok &= [str(r[0]) for r in b["rets"]] == ["Z"]
    print("zero_it pz", z["pz"])
    ok &= z["pz"] == [("Z",)]
    print("c_alloc rets", [str(r[0]) for r in by["c_alloc"]["rets"]])
    ok &= [str(r[0]) for r in by["c_alloc"]["rets"]] == ["Z"]
    print("hook e2", h["e2"])
    ok &= bool(h["e2"]) and h["e2"][0][0] == "tag_clear" and h["e2"][0][4] == "init"
    print("SELFTEST", "OK" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    elif cmd == "facts":
        d = facts(sys.argv[2])
        print("files", len(d["files"]), "secs", d["secs"])
    elif cmd == "run":
        r = run(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        print(json.dumps(r["stats"], ensure_ascii=False))
        for c in r["cands"][:30]:
            print(c["rank"], c["form"], c["file"], c["line"], c["func"], c["group"])
