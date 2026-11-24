"""swapsym criteria 一～五: bit-symbolic evaluation of ordinary swap entry encode/decode on real builds. WSL.

    python3 swapsym.py calib                 -> calib_sym.json   (8-bit exhaustive check of the symbolic ops vs clang)
    python3 swapsym.py run [builds...]       -> sym_<build>.json + conc_<build>.json
"""
import itertools
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TF = HERE.parent / "toolfix_20261121"
sys.path.insert(0, str(TF))
import evalpg as E  # noqa: E402  (imported, not modified)
I = E.I

WORK = Path("/root/work/swapsym")
VARIANTS = {"i386_pae": "/root/work/swapsym/cfg_i386_pae"}
VARIANT_BASE = {"i386_pae": "i386"}
I.BUILDS.update(VARIANTS)
E.LONGW["i386_pae"] = 32
_orig_ccdb = I.ccdb


def _ccdb(d):
    for v, path in VARIANTS.items():
        if d == path:
            base = _orig_ccdb(I.BUILDS[VARIANT_BASE[v]])
            return {f: dict(e, directory=d) for f, e in base.items()}
    return _orig_ccdb(d)


I.ccdb = _ccdb

# ---------------------------------------------------------------- bit-symbolic vectors
# a bit is 0, 1, or a literal (var, idx, neg); var is 't', 'o', or ('?', uid) for an anonymous unknown
_UID = [0]
DOM = {"tmax": None, "ofree": 0, "omin": 1}   # t <= tmax; o >= 1; t bits 0..4 free, o bits 0..ofree-1 free (other bits are constant 0 in the inputs)


def anon():
    _UID[0] += 1
    return (("?", _UID[0]), 0, False)


def neg(b):
    if b in (0, 1):
        return 1 - b
    return (b[0], b[1], not b[2])


class SBV:
    __slots__ = ("bits", "src")

    def __init__(self, w, v=0, k=None, src=None):
        m = (1 << w) - 1
        k = m if k is None else k & m
        self.bits = [((v >> i) & 1) if (k >> i) & 1 else anon() for i in range(w)]
        self.src = src

    @classmethod
    def of(cls, bits):
        x = cls.__new__(cls)
        x.bits, x.src = list(bits), None
        return x

    @property
    def w(self):
        return len(self.bits)

    @property
    def k(self):
        return sum(1 << i for i, b in enumerate(self.bits) if b in (0, 1))

    @property
    def v(self):
        return sum(1 << i for i, b in enumerate(self.bits) if b == 1)

    @staticmethod
    def unk(w, ident=False):
        return SBV(w, 0, 0)

    def const(self):
        return self.v if all(b in (0, 1) for b in self.bits) else None

    def resize(self, w, signed=False):
        if w == self.w:
            return self
        if w < self.w:
            return SBV.of(self.bits[:w])
        if self.w == 1:
            signed = False
        fill = self.bits[-1] if signed else 0
        return SBV.of(self.bits + [fill] * (w - self.w))

    def truth(self):
        if not all_zero(self.bits)[0]:
            return True
        if not nonzero(self.bits)[0]:
            return False
        return None

    def __repr__(self):
        return "SBV(" + ",".join(fmt(b) for b in reversed(self.bits)) + ")"


def fmt(b):
    if b in (0, 1):
        return str(b)
    v = b[0] if isinstance(b[0], str) else "?"
    return ("~" if b[2] else "") + f"{v}{b[1]}"


def feasible(forced):
    """forced: {(var, idx): 0/1}. Can the remaining free bits satisfy o >= 1 and t <= tmax?"""
    if DOM["omin"] and not any(var == "o" and val for (var, _), val in forced.items()):
        if not any(("o", i) not in forced for i in range(DOM["ofree"])):
            return False
    tmin = sum(val << i for (var, i), val in forced.items() if var == "t")
    return DOM["tmax"] is None or tmin <= DOM["tmax"]


def all_zero(bits):
    """(satisfiable, assignment) for 'every bit is 0'"""
    forced = {}
    for b in bits:
        if b == 1:
            return False, None
        if b == 0:
            continue
        var, i, ng = b
        req = 1 if ng else 0
        key = (var, i)
        if forced.get(key, req) != req:
            return False, None
        forced[key] = req
    real = {k: v for k, v in forced.items() if isinstance(k[0], str)}
    if not feasible(real):
        return False, None
    return True, complete(real)


def nonzero(bits):
    """(satisfiable, assignment) for 'some bit is 1'"""
    for b in bits:
        if b == 1:
            return (True, complete({})) if feasible({}) else (False, None)
        if b == 0:
            continue
        var, i, ng = b
        if not isinstance(var, str):
            return True, None                      # an anonymous bit may be 1, but there is no concrete witness
        f = {(var, i): 0 if ng else 1}
        if feasible(f):
            return True, complete(f)
    return False, None


def complete(forced):
    """a concrete (t, o) agreeing with forced: free t bits 0; o >= 1 by setting its lowest free bit if needed"""
    t = sum(v << i for (var, i), v in forced.items() if var == "t")
    o = sum(v << i for (var, i), v in forced.items() if var == "o")
    if o == 0 and DOM["omin"]:
        i = next(i for i in range(DOM["ofree"]) if ("o", i) not in forced)
        o = 1 << i
    return {"t": t, "o": o}


def subst(x, t, o):
    if not isinstance(x, SBV):
        return None
    r = 0
    for i, b in enumerate(x.bits):
        if b in (0, 1):
            bit = b
        elif b[0] == "t":
            bit = ((t >> b[1]) & 1) ^ b[2]
        elif b[0] == "o":
            bit = ((o >> b[1]) & 1) ^ b[2]
        else:
            return None
        r |= bit << i
    return r


def unwrap(x):
    """single-field wrappers (e.g. the i386 PAE pte_t union read through .pte) are transparent; reconciliation checks it"""
    while isinstance(x, dict) and len(x) == 1:
        x = next(iter(x.values()))
    if isinstance(x, dict):
        raise E.Unsupported("multi-field struct used as a value")
    return x


def _bitop(a, b, f):
    a, b = unwrap(a), unwrap(b)
    w = max(a.w, b.w)
    a, b = a.resize(w), b.resize(w)
    return SBV.of(f(x, y) for x, y in zip(a.bits, b.bits))


def _and(x, y):
    if x == 0 or y == 0:
        return 0
    if x == 1:
        return y
    if y == 1:
        return x
    if x == y:
        return x
    if x == neg(y):
        return 0
    return anon()


def _or(x, y):
    if x == 1 or y == 1:
        return 1
    if x == 0:
        return y
    if y == 0:
        return x
    if x == y:
        return x
    if x == neg(y):
        return 1
    return anon()


def _xor(x, y):
    if x in (0, 1) and y in (0, 1):
        return x ^ y
    if x == 0:
        return y
    if y == 0:
        return x
    if x == 1:
        return neg(y)
    if y == 1:
        return neg(x)
    if x == y:
        return 0
    if x == neg(y):
        return 1
    return anon()


def b_and(a, b):
    return _bitop(a, b, _and)


def b_or(a, b):
    return _bitop(a, b, _or)


def b_xor(a, b):
    return _bitop(a, b, _xor)


def b_not(a):
    a = unwrap(a)
    return SBV.of(neg(x) for x in a.bits)


def shl(a, n):
    a = unwrap(a)
    n = min(n, a.w)
    return SBV.of([0] * n + a.bits[:a.w - n])


def shr(a, n, signed=False):
    a = unwrap(a)
    n = min(n, a.w)
    fill = a.bits[-1] if signed else 0
    return SBV.of(a.bits[n:] + [fill] * n)


def boolbv(t):
    return SBV.unk(1) if t is None else SBV(1, int(t))


def join(a, b):
    if isinstance(a, dict) or isinstance(b, dict):
        if isinstance(a, dict) and isinstance(b, dict):
            if len(a) == 1 and len(b) == 1:
                (ka, va), (kb, vb) = next(iter(a.items())), next(iter(b.items()))
                return {ka if ka != "_0" else kb: join(va, vb)}
            if set(a) != set(b):
                raise E.Unsupported("join of structs with different fields")
            return {f: join(a[f], b[f]) for f in a}
        if isinstance(a, dict) and len(a) == 1:
            return join(next(iter(a.values())), b)
        if isinstance(b, dict) and len(b) == 1:
            return join(a, next(iter(b.values())))
        raise E.Unsupported("join of different shapes")
    w = max(a.w, b.w)
    a, b = a.resize(w), b.resize(w)
    return SBV.of(x if x == y else anon() for x, y in zip(a.bits, b.bits))


# install into the imported interpreter (module-level names are looked up at call time)
E.BV, E.b_and, E.b_or, E.b_xor, E.b_not, E.shl, E.shr, E.boolbv, E.join = SBV, b_and, b_or, b_xor, b_not, shl, shr, boolbv, join


BUILD_INFO = {}      # amendment 1 (v2): per build {"enums": {name: value}, "records": {type name: [field, ...]}}


class SInterp(E.Interp):
    build = None

    # v2: __builtin_bswap* (powerpc book3s64 keeps PTEs big-endian) is an exact bit permutation
    def call(self, name, args, depth=0):
        m = re.fullmatch(r"__builtin_bswap(16|32|64)", name or "")
        if m:
            w = int(m.group(1))
            x = unwrap(args[0]).resize(w)
            bits = []
            for byte in reversed(range(w // 8)):
                bits += x.bits[byte * 8:(byte + 1) * 8]
            return SBV.of(bits)
        return super().call(name, args, depth)

    def expr(self, n, env, depth):
        k = n.get("kind")
        if k == "ImplicitValueInitExpr":                 # v2: omitted initializer fields are zero
            w, _ = self.width(n)
            if w:
                return SBV(w, 0)
            raise E.Unsupported("implicit zero init of an aggregate")
        if k == "DeclRefExpr" and (n.get("referencedDecl") or {}).get("kind") == "EnumConstantDecl":
            nm = n["referencedDecl"].get("name")
            v = BUILD_INFO.get(self.build, {}).get("enums", {}).get(nm)   # v2: value folded by clang beforehand
            if v is None:
                raise E.Unsupported(f"enum constant {nm}")
            w, _ = self.width(n)
            return SBV(w or 32, v)
        if k in ("ImplicitCastExpr", "CStyleCastExpr") and n.get("castKind") in ("IntegralCast", "IntegralToBoolean", "BooleanToSignedIntegral"):
            v = unwrap(self.expr(n["inner"][0], env, depth))   # v2: single-field wrappers used as integers
            if n["castKind"] == "IntegralToBoolean":
                return boolbv(v.truth())
            w, _ = self.width(n)
            _, ss = self.width(n["inner"][0])
            return v.resize(w, bool(ss)) if w else v
        return super().expr(n, env, depth)

    def struct_fields(self, n):                          # v2: field order from clang's record layout dump
        recs = BUILD_INFO.get(self.build, {}).get("records", {})
        t = n.get("type") or {}
        for q in (t.get("qualType"), t.get("desugaredQualType")):
            if q:
                q = re.sub(r"^(struct|union) ", "", q.strip())
                if q in recs:
                    return recs[q]
        return None

    def binop(self, op, a, b, w, s):
        a, b = unwrap(a), unwrap(b)
        if op in ("&", "|", "^"):
            return {"&": b_and, "|": b_or, "^": b_xor}[op](a, b).resize(w)
        if op in ("<<", ">>"):
            c = b.const()
            if c is None:
                raise E.Unsupported("variable shift")
            return shl(a.resize(w), c) if op == "<<" else shr(a.resize(w), c, bool(s))
        if op in ("==", "!="):
            ww = max(a.w, b.w)
            nz = b_xor(a.resize(ww), b.resize(ww)).truth()
            return boolbv(None if nz is None else (nz if op == "!=" else not nz))
        ca, cb = a.const(), b.const()
        if ca is not None and cb is not None:
            m = (1 << w) - 1
            if s:      # signed comparison / arithmetic on constants
                def sg(x, ww):
                    return x - (1 << ww) if x >> (ww - 1) & 1 else x
                ca, cb = sg(ca, a.w), sg(cb, b.w)
            r = {"+": ca + cb, "-": ca - cb, "*": ca * cb, "<": int(ca < cb), ">": int(ca > cb), "<=": int(ca <= cb), ">=": int(ca >= cb),
                 "/": int(ca / cb) if cb else 0, "%": ca % cb if cb else 0}.get(op)
            if r is not None:
                return SBV(w, r & m)
        if op == "+" and (b.const() == 0 or a.const() == 0):
            return (a if b.const() == 0 else b).resize(w)
        if op == "-" and b.const() == 0:
            return a.resize(w)
        if op in ("<", ">", "<=", ">="):
            return SBV.unk(1)
        return SBV.unk(w)


# ---------------------------------------------------------------- synthetic unit
SRC = r'''
#include <linux/mm.h>
#include <linux/pgtable.h>
#include <linux/swapops.h>
#include <linux/leafops.h>
static inline pte_t s_p(unsigned long t, unsigned long o) { return swp_entry_to_pte(swp_entry(t, o)); }
unsigned long long S_enc(unsigned long t, unsigned long o) { return pte_val(s_p(t, o)); }
int S_present(unsigned long t, unsigned long o) { return !!pte_present(s_p(t, o)); }
int S_none(unsigned long t, unsigned long o) { return !!pte_none(s_p(t, o)); }
unsigned long long S_flags(unsigned long t, unsigned long o) { pte_t p = s_p(t, o); return pte_val(pte_swp_clear_flags(p)) ^ pte_val(p); }
unsigned long S_type(unsigned long t, unsigned long o) { return swp_type(softleaf_from_pte(s_p(t, o))); }
unsigned long S_off(unsigned long t, unsigned long o) { return swp_offset(softleaf_from_pte(s_p(t, o))); }
unsigned long S_typeraw(unsigned long t, unsigned long o) { swp_entry_t a = __pte_to_swp_entry(s_p(t, o)); return swp_type(swp_entry(__swp_type(a), __swp_offset(a))); }
unsigned long S_offraw(unsigned long t, unsigned long o) { swp_entry_t a = __pte_to_swp_entry(s_p(t, o)); return swp_offset(swp_entry(__swp_type(a), __swp_offset(a))); }
unsigned long S_max(void) { return MAX_SWAPFILES; }
unsigned long S_pubw(void) { return SWP_TYPE_SHIFT; }
unsigned long S_probe(void)
{   /* body of generic_max_swapfile_size(), mm/swapfile.c:3449-3462 */
	swp_entry_t entry = swp_entry(0, ~0UL);
	const pte_t pte = softleaf_to_pte(entry);
	entry = __pte_to_swp_entry(pte);
	entry = swp_entry(__swp_type(entry), __swp_offset(entry));
	return swp_offset(entry) + 1;
}
unsigned long S_dbg(void) { return swp_offset(softleaf_from_pte(softleaf_to_pte(swp_entry(0, ~0UL)))); }   /* mm/debug_vm_pgtable.c:1229 */
'''
SYM = ["S_enc", "S_present", "S_none", "S_flags", "S_type", "S_off", "S_typeraw", "S_offraw"]
CONSTS = ["S_max", "S_pubw", "S_probe", "S_dbg"]


def callees(funcs):
    need = set()

    def walk(n):
        if isinstance(n, dict):
            if n.get("kind") == "CallExpr":
                c = n["inner"][0]
                while c.get("kind") in ("ImplicitCastExpr", "ParenExpr") and c.get("inner"):
                    c = c["inner"][0]
                x = (c.get("referencedDecl") or {}).get("name")
                if x:
                    need.add(x)
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(list(funcs.values()))
    return need


def enum_names(funcs):
    out = set()

    def walk(n):
        if isinstance(n, dict):
            if n.get("kind") == "DeclRefExpr" and (n.get("referencedDecl") or {}).get("kind") == "EnumConstantDecl":
                out.add(n["referencedDecl"]["name"])
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(list(funcs.values()))
    return sorted(out)


def record_layouts(b, p):
    """{record or typedef name: [top-level field names in order]} from -fdump-record-layouts"""
    args, cwd = base_args(b)
    r = subprocess.run(args + ["-fsyntax-only", "-w", "-Xclang", "-fdump-record-layouts", str(p)], cwd=cwd, capture_output=True, text=True,
                       errors="replace")
    recs = {}
    for blk in r.stdout.split("*** Dumping AST Record Layout")[1:]:
        lines = [ln for ln in blk.splitlines() if "|" in ln]
        if not lines:
            continue
        head = lines[0].split("|", 1)[1].strip()
        name = re.sub(r"^(struct|union) ", "", head)
        if head.startswith("union ") or "(unnamed" in name:
            continue
        fields = []
        for ln in lines[1:]:
            body = ln.split("|", 1)[1]
            if body.startswith("   ") and not body.startswith("    ") and not body.strip().startswith("["):
                fields.append(re.split(r"[\s*]+", body.strip())[-1])
        recs.setdefault(name, fields)
    return recs


def load(b, p):
    funcs = E.dump_unit(b, p, ["S_", "s_p"])
    for _ in range(10):
        miss = sorted(x for x in callees(funcs) if x not in funcs and not E.UNKNOWN_BOOL_CALLS.match(x) and not x.startswith("__builtin"))
        if not miss:
            break
        funcs.update(E.dump_unit(b, p, miss))
    info = {"records": record_layouts(b, p), "enums": {}}
    names = enum_names(funcs)
    if names:
        src = p.read_text() + "".join(f"long long EN_{nm}(void) {{ return {nm}; }}\n" for nm in names)
        got = clang_consts(b, src, [f"EN_{nm}" for nm in names])
        info["enums"] = {nm: got[f"EN_{nm}"] for nm in names if got.get(f"EN_{nm}") is not None}
    BUILD_INFO[b] = info
    return funcs


def base_args(b):
    cc = I.ccdb(I.BUILDS[b])
    e = cc[I.UNIT]
    args = e.get("arguments") or shlex.split(e["command"])
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a == "-o":
            skip = True
            continue
        if a == "-c" or a.startswith("-Wp,-MMD") or a.endswith("mm/memory.c"):
            continue
        out.append(a)
    return out, e["directory"]


def clang_consts(b, src, names):
    """compile with the build's flags at -O2 to LLVM IR and read each function's folded return constant"""
    p = WORK / f"conc_{b}.c"
    p.write_text(src)
    args, cwd = base_args(b)
    args = [a for a in args if not re.match(r"^-O[0-3s]$", a)]
    r = subprocess.run(args + ["-O2", "-w", "-S", "-emit-llvm", "-o", "-", str(p)], cwd=cwd, capture_output=True, text=True, errors="replace")
    if r.returncode:
        raise RuntimeError(r.stderr[-1500:])
    out = {}
    for nm in names:
        m = re.search(r"define [^\n]*@" + re.escape(nm) + r"\(\)[^\n]*\{\n(.*?)\n\}", r.stdout, re.S)
        if not m:
            out[nm] = None
            continue
        body = m.group(1).strip().splitlines()
        body = [ln for ln in body if ln.strip() and not ln.strip().startswith((";", "#dbg_", "call void @llvm.dbg", "call void @_mcount", "call void @__fentry__"))]   # debug-info / ftrace lines
        rm = re.fullmatch(r"\s*ret i(\d+) (-?\d+|true|false)(, !dbg !\d+)?", body[-1]) if len(body) == 1 else None
        if rm:
            v = {"true": 1, "false": 0}.get(rm.group(2))
            v = int(rm.group(2)) if v is None else v
            out[nm] = v & ((1 << int(rm.group(1))) - 1)
        else:
            out[nm] = None
    return out


def mk_inputs(longw, ofree):
    t = SBV.of([("t", i, False) for i in range(5)] + [0] * (longw - 5))
    o = SBV.of([("o", i, False) if i < ofree else 0 for i in range(longw)])
    return t, o


ORACLE, RUNTIME = {}, set()     # v2: runtime predicates (e.g. powerpc radix_enabled) are enumerated by run_build


def sym_call(funcs, b, nm, t, o):
    it = SInterp(funcs, E.LONGW[b], {})
    it.build = b
    it.oracle = dict(ORACLE)
    try:
        r = it.call(nm, [t, o] if t is not None else [])
    except E.Unsupported as ex:
        RUNTIME.update(it.runtime)
        return {"unsupported": str(ex)}
    RUNTIME.update(it.runtime)
    if isinstance(r, dict) and len(r) == 1:
        r = next(iter(r.values()))
    return {"val": r, "notes": sorted(set(it.notes))[:6]}


def exact_bits(x, var, n, w):
    """does x equal var's own bits 0..n-1, constant 0 above?"""
    if not isinstance(x, SBV):
        return False
    want = [(var, i, False) if i < n else 0 for i in range(x.w)]
    return x.bits == want[:x.w]


def run_build(b):
    """v2: evaluate once; if runtime predicates were met, evaluate every true/false combination (at most 4 predicates) and
    accept an obligation only if it holds under every combination"""
    WORK.mkdir(parents=True, exist_ok=True)
    p = WORK / f"sym_{b}.c"
    p.write_text(SRC)
    funcs = load(b, p)
    ORACLE.clear()
    RUNTIME.clear()
    res0 = run_once(b, funcs)
    keys = sorted(RUNTIME)
    if not keys:
        return res0, funcs
    if len(keys) > 4:
        res0["status"] = f"运行时判断过多：{keys}"
        return res0, funcs
    combos = {}
    for vals in itertools.product([False, True], repeat=len(keys)):
        ORACLE.clear()
        ORACLE.update(zip(keys, vals))
        RUNTIME.clear()
        r = run_once(b, funcs)
        extra = sorted(RUNTIME - set(keys))
        combos[", ".join(f"{k}={v}" for k, v in ORACLE.items())] = r if not extra else dict(r, status=f"组合外还有运行时判断 {extra}")
    ORACLE.clear()
    first = next(iter(combos.values()))
    res = dict(first)
    res["runtime"] = keys
    res["per_combo"] = {c: {"obligations": {k: v.get("status") for k, v in r.get("obligations", {}).items()}, "consts": r.get("consts"),
                            "K_enc": r.get("capacity", {}).get("K_enc"), "status": r.get("status"), "symbolic": r.get("symbolic")}
                        for c, r in combos.items()}
    if any(r.get("status") or "obligations" not in r for r in combos.values()):
        res["status"] = "某些运行时组合求不出"
        res.pop("obligations", None)
        return res, funcs
    ob = {}
    for k in first["obligations"]:
        sts = {r["obligations"][k]["status"] for r in combos.values()}
        ob[k] = dict(first["obligations"][k], status="成立" if sts == {"成立"} else "/".join(sorted(sts)), per_combo_status=sorted(sts))
    res["obligations"] = ob
    res["K"] = min(r["K"] for r in combos.values())
    return res, funcs


def run_once(b, funcs):
    L = E.LONGW[b]
    res = {"build": b, "longw": L}
    DOM["tmax"], DOM["ofree"] = None, 1
    c = {}
    for nm in CONSTS:
        r = sym_call(funcs, b, nm, None, None)
        c[nm] = r["val"].const() if "val" in r and isinstance(r["val"], SBV) else None
    res["consts"] = c
    MAX, PUBW = c["S_max"], c["S_pubw"]
    if MAX is None or PUBW is None:
        res["status"] = "不支持：MAX_SWAPFILES 或公共偏移位宽求不出"
        return res
    # capacity of the arch encoding (no present/none filter), o over the full public width, t unconstrained except tmax
    DOM["tmax"], DOM["ofree"] = MAX - 1, PUBW
    t, o = mk_inputs(L, PUBW)
    raw = sym_call(funcs, b, "S_offraw", t, o)
    rawt = sym_call(funcs, b, "S_typeraw", t, o)
    kenc = 0
    if "val" in raw:
        for i, bit in enumerate(raw["val"].bits):
            if bit == ("o", i, False):
                kenc += 1
            else:
                break
    res["capacity"] = {"K_enc": kenc, "offraw": repr(raw.get("val", raw.get("unsupported"))),
                       "typeraw_exact": exact_bits(rawt.get("val"), "t", 5, L)}
    K = min(32, kenc, L)
    res["K"] = K
    DOM["tmax"], DOM["ofree"] = MAX - 1, K
    t, o = mk_inputs(L, K)
    out = {nm: sym_call(funcs, b, nm, t, o) for nm in SYM}
    res["symbolic"] = {nm: repr(r.get("val", r.get("unsupported"))) for nm, r in out.items()}
    res["notes"] = {nm: r.get("notes") for nm, r in out.items() if r.get("notes")}

    def tv(nm):
        r = out[nm]
        return r["val"].truth() if "val" in r else "不支持"
    ob = {}
    pres, none = tv("S_present"), tv("S_none")
    o1 = "成立" if (pres is False and none is False) else ("不支持" if "不支持" in (pres, none) else "违反" if True in (pres, none) else "未知")
    wit = None
    if o1 != "成立" and "val" in out["S_enc"]:
        ok, a = all_zero(out["S_enc"]["val"].bits)          # an all-zero PTE is none on every architecture
        if ok and a:
            wit = dict(a, via="S_enc == 0")
    ob["O1"] = {"status": o1, "present": pres, "none": none, "witness": wit}
    fl = tv("S_flags")
    ob["O2"] = {"status": "成立" if fl is False else ("不支持" if fl == "不支持" else "违反" if fl is True else "未知"), "flags_truth": fl}
    ty_ok = exact_bits(out["S_type"].get("val"), "t", 5, L)
    of_ok = exact_bits(out["S_off"].get("val"), "o", K, L)
    o3 = "成立" if ty_ok and of_ok else ("不支持" if any("unsupported" in out[x] for x in ("S_type", "S_off")) else "未知或违反")
    ob["O3"] = {"status": o3, "type_exact": ty_ok, "offset_exact": of_ok}
    probe = c["S_probe"]
    ob["probe"] = {"S_probe": probe, "2^K_enc": 1 << kenc, "status": "成立" if probe is not None and probe <= (1 << kenc) else "违反或未知",
                   "S_dbg": c["S_dbg"], "dbg_is_max": c["S_dbg"] == (probe - 1 if probe else None)}
    res["obligations"] = ob
    res["domain"] = {"t": f"0..{MAX - 1}", "o": f"1..2^{K}-1"}
    return res


def concrete(b, res):
    MAX, K = res["consts"]["S_max"], res["K"]
    m = (1 << K) - 1
    cases = [(0, 1), (1, 2), (MAX - 1, 1), (MAX - 1, m), (MAX // 2, 1 << (K - 1)), (3, 0x2345 & m)]
    w = res["obligations"]["O1"].get("witness")
    if w:
        cases.append((w["t"], w["o"]))
    lines = [SRC]
    names = []
    for j, (t, o) in enumerate(cases):
        for nm in ("S_enc", "S_present", "S_none", "S_type", "S_off"):
            f = f"C{j}_{nm}"
            rt = "unsigned long long" if nm == "S_enc" else "unsigned long"
            lines.append(f"{rt} {f}(void) {{ return {nm}({t}UL, {o}UL); }}")
            names.append((f, j, nm))
    for nm in ("S_probe", "S_dbg", "S_max"):
        lines.append(f"unsigned long C_{nm}(void) {{ return {nm}(); }}")
        names.append((f"C_{nm}", None, nm))
    got = clang_consts(b, "\n".join(lines) + "\n", [n for n, _, _ in names])
    return cases, names, got


def run(builds):
    summary = {}
    for b in builds:
        try:
            res, funcs = run_build(b)
        except Exception as ex:          # parse failure etc.: record and continue
            summary[b] = {"status": f"失败：{type(ex).__name__}: {str(ex)[:300]}"}
            print(b, summary[b], flush=True)
            continue
        if "obligations" in res and res.get("K", 0) >= 1:
            cases, names, got = concrete(b, res)
            L, K, MAX = res["longw"], res["K"], res["consts"]["S_max"]
            DOM["tmax"], DOM["ofree"] = MAX - 1, K
            t, o = mk_inputs(L, K)
            combos = [dict(zip(res["runtime"], v)) for v in itertools.product([False, True], repeat=len(res["runtime"]))]                 if res.get("runtime") else [{}]
            symc = []
            for orc in combos:                      # v2: one prediction per runtime combination
                ORACLE.clear()
                ORACLE.update(orc)
                symc.append({nm: sym_call(funcs, b, nm, t, o).get("val") for nm in ("S_enc", "S_present", "S_none", "S_type", "S_off")})
            ORACLE.clear()
            rows, agree, dis, nof = [], 0, 0, 0
            per_case_ok = {}
            for f, j, nm in names:
                cv = got.get(f)
                if j is None:
                    pv = res["consts"][nm]
                    tt, oo = None, None
                else:
                    tt, oo = cases[j]
                    pvs = set()
                    for symv in symc:
                        x = subst(symv[nm], tt, oo)
                        if nm in ("S_present", "S_none") and x is not None:
                            x = int(x != 0)
                        pvs.add(x)
                    pv = pvs.pop() if len(pvs) == 1 else None   # combinations disagree or unsupported -> cannot reconcile
                if cv is None or pv is None:
                    st = "无法对账"
                    nof += 1
                elif cv == pv:
                    st = "一致"
                    agree += 1
                else:
                    st = "不一致"
                    dis += 1
                if j is not None:
                    per_case_ok.setdefault(j, []).append(st)
                rows.append({"func": f, "t": tt, "o": oo, "what": nm, "clang": cv, "symbolic": pv, "status": st})
            full = sum(1 for j, sts in per_case_ok.items() if all(s == "一致" for s in sts) and j < 6)
            res["concrete"] = {"agree": agree, "disagree": dis, "no_fold": nof, "cases_fully_agreeing": full, "rows": rows}
        (HERE / f"sym_{b}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str))
        ob = res.get("obligations", {})
        summary[b] = {k: v.get("status") for k, v in ob.items()}
        summary[b]["K_enc"] = res.get("capacity", {}).get("K_enc")
        summary[b]["concrete"] = {k: res.get("concrete", {}).get(k) for k in ("agree", "disagree", "no_fold", "cases_fully_agreeing")}
        print(b, json.dumps(summary[b], ensure_ascii=False), flush=True)
    return summary


# ---------------------------------------------------------------- calibration of the symbolic ops (8-bit exhaustive, as in toolfix)
CAL = ["x & 0x0f", "x | 0xa0", "x ^ 0x5a", "(unsigned char)~x", "(unsigned char)(x << 3)", "x >> 2", "(unsigned char)((signed char)x >> 3)",
       "(unsigned short)(int)(signed char)x", "(unsigned char)((unsigned char)~x << 2 >> 1)", "(unsigned char)(x ^ (x >> 4))",
       "(unsigned char)((x & 0xf0) | (~x & 0x0f))", "!x", "x == 0x40", "x != 3", "(x & 1) && (x & 2)", "(unsigned char)(x + 0)",
       "(unsigned char)(~(unsigned long)x << 9 >> 5)", "(unsigned int)(~(unsigned long long)x << 14 >> 5 >> 9)"]


def calib():
    WORK.mkdir(parents=True, exist_ok=True)
    body = "".join(f"unsigned int E{i}(unsigned char x) {{ return (unsigned int)({e}); }}\n" for i, e in enumerate(CAL))
    (WORK / "cal.c").write_text(body)
    main = '#include <stdio.h>\n#include "cal.c"\nint main(void){for(int x=0;x<256;x++){' + "".join(
        f'printf("%u ", E{i}((unsigned char)x));' for i in range(len(CAL))) + 'printf("\\n");}return 0;}\n'
    (WORK / "cal_main.c").write_text(main)
    subprocess.run(["clang", "-O0", "-w", "-o", str(WORK / "cal_main"), str(WORK / "cal_main.c")], check=True, cwd=WORK)
    conc = [list(map(int, ln.split())) for ln in subprocess.run([str(WORK / "cal_main")], capture_output=True, text=True).stdout.splitlines()]
    funcs = E.dump_unit("x86_64", WORK / "cal.c", ["E"])
    bad, rows = 0, []
    for i, e in enumerate(CAL):
        DOM["tmax"], DOM["ofree"], DOM["omin"] = None, 8, 0
        x = SBV.of([("o", j, False) for j in range(8)])
        it = SInterp(funcs, 64, {})
        try:
            out = it.call(f"E{i}", [x])
        except E.Unsupported as ex:
            rows.append({"expr": e, "status": f"不支持 {ex}"})
            continue
        nb, nexact = 0, 0
        for v in range(256):
            pv = subst(out, 0, v)
            if pv is None:                       # anonymous bits: check only the determined ones
                known = [(j, b) for j, b in enumerate(out.bits) if b in (0, 1) or isinstance(b[0], str)]
                for j, bb in known:
                    bit = bb if bb in (0, 1) else ((v >> bb[1]) & 1) ^ bb[2]
                    if ((conc[v][i] >> j) & 1) != bit:
                        nb += 1
            else:
                nexact += 1
                if pv != conc[v][i]:
                    nb += 1
        bad += nb
        rows.append({"expr": e, "exact_inputs": nexact, "contradictions": nb, "symbolic": repr(out)})
        print(f"{e:60s} exact {nexact:3d} contradictions {nb}  {out!r}", flush=True)
    (HERE / "calib_sym.json").write_text(json.dumps({"total_contradictions": bad, "rows": rows}, indent=1, ensure_ascii=False))
    DOM["omin"] = 1
    print("TOTAL contradictions", bad)


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    if sys.argv[1] == "calib":
        calib()
    elif sys.argv[1] == "run":
        print(json.dumps(run(sys.argv[2:] or ["riscv64", "rv32_abi", "x86_64", "i386", "arm64", "i386_pae"]), ensure_ascii=False, indent=1))
