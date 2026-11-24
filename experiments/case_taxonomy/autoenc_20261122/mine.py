"""autoenc criteria 二.3-二.4 (+ amendments 1-3): compose the classified interfaces and evaluate their behaviour bit-symbolically. WSL.

    python3 mine.py [builds...]      -> beh_<build>.json  ({law key: {"beh": ..., "dom": ..., ...}})
No hand lists: interfaces come from sigs_<build>.json (classify.py), parameter names from names.json (discover.py), domains from the
generic rules (criteria 一.1 + amendment 1), compositions from the generic templates (criteria 二.3 + amendment 2).
"""
import itertools
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "swapsym_20261121"))
import swaparch as A  # noqa: E402
S = A.S
E, SBV = S.E, S.SBV
# arm64 LPA2: PHYS_MASK_SHIFT = lpa2_is_enabled() ? 52 : 48 is a runtime CPU feature (same run-time extension as pfnswap round 5)
if "lpa2_is_enabled" not in E.UNKNOWN_BOOL_CALLS.pattern:
    E.UNKNOWN_BOOL_CALLS = re.compile(E.UNKNOWN_BOOL_CALLS.pattern[:-2] + "|lpa2_is_enabled)$")
BUILDS = ["riscv64", "rv32_abi", "x86_64", "i386", "i386_pae", "arm64", "ppc64le", "ppc64le_hash", "ppc64e", "ppc32s", "ppc44x", "ppc8xx",
          "s390", "loongarch", "mips32", "mips32xpa", "mips64", "arm", "arm_lpae", "hexagon"]
T = ["pte_t", "pmd_t", "pud_t"]
HDR = "#include <linux/mm.h>\n#include <linux/pgtable.h>\n#include <linux/swapops.h>\n#include <linux/leafops.h>\n"
CONSTS = r'''
static __attribute__((used)) unsigned long AE_K_MAX(void) { return MAX_SWAPFILES; }
static __attribute__((used)) unsigned long AE_K_PAGE_SHIFT(void) { return PAGE_SHIFT; }
static __attribute__((used)) unsigned long AE_K_PMD_SHIFT(void) { return PMD_SHIFT; }
static __attribute__((used)) unsigned long AE_K_PUD_SHIFT(void) { return PUD_SHIFT; }
static __attribute__((used)) unsigned long AE_K_PHYS(void) { return sizeof(phys_addr_t) * 8; }
static __attribute__((used)) unsigned long AE_K_MPB(void)
{
#ifdef MAX_PHYSMEM_BITS
	return MAX_PHYSMEM_BITS;
#else
	return 0;
#endif
}
'''


# ---------------------------------------------------------------- interfaces of one build
def level_of(name):
    m = re.search(r"(pte|pmd|pud)", name)
    return (m.group(1) + "_t") if m else None


def level_filter(sigs):
    out = {}
    for nm, ts in sigs.items():
        lv = level_of(nm)
        keep = [t for t in ts if not (lv and re.findall(r"(pte_t|pmd_t|pud_t)", t.partition(":")[2]) and
                                      re.findall(r"(pte_t|pmd_t|pud_t)", t.partition(":")[2])[-1] != lv)]
        if keep:
            out[nm] = keep
    return out


def is_weak(sigs):
    """amendment 4.1: most interfaces that pass the modifier template also pass the observer template"""
    mods = [nm for nm, ts in sigs.items() if any(t.startswith("mod:") for t in ts)]
    both = [nm for nm in mods if any(t.startswith("obs:") for t in sigs[nm])]
    return bool(mods) and len(both) * 2 > len(mods)


def consensus():
    """amendment 4.2: {(name, template): share of strong builds (where the name has any signature) that pass it}"""
    from collections import Counter
    have, ok = Counter(), Counter()
    for b in BUILDS:
        p = HERE / f"sigs_{b}.json"
        if not p.exists():
            continue
        sg = level_filter(json.loads(p.read_text(encoding="utf-8")))
        if is_weak(sg):
            continue
        for nm, ts in sg.items():
            have[nm] += 1
            for t in ts:
                ok[(nm, t)] += 1
    return {k: v / have[k[0]] for k, v in ok.items()}


def roles(sigs):
    """{role: [(name, T or E pair)]} after amendment 3 (level by name) and amendment 4 (weak builds use the strong-build majority)"""
    out = {}
    sigs = level_filter(sigs)
    if is_weak(sigs):
        cons = consensus()
        sigs = {nm: [t for t in ts if cons.get((nm, t), 0) >= 0.5] for nm, ts in sigs.items()}
    for nm, ts in sigs.items():
        lv = level_of(nm)
        for t in ts:
            role, _, ty = t.partition(":")
            tys = re.findall(r"(pte_t|pmd_t|pud_t)", ty)
            if lv and tys and tys[-1] != lv:
                continue
            out.setdefault(role, []).append((nm, ty))
    return out


def wname(role, nm, ty):
    return "AE_" + re.sub(r"\W", "_", f"{role}__{nm}__{ty}")


def wrapper(role, nm, ty):
    w = wname(role, nm, ty)
    if role == "prot":
        return f"static __attribute__((used)) pgprot_t {w}(void) {{ return {nm}; }}"
    if role in ("mod", "obs", "cons"):
        t = ty
        return {"mod": f"static __attribute__((used)) {t} {w}({t} x) {{ return {nm}(x); }}",
                "obs": f"static __attribute__((used)) unsigned long long {w}({t} x) {{ return {nm}(x); }}",
                "cons": f"static __attribute__((used)) {t} {w}(unsigned long a, pgprot_t p) {{ return {nm}(a, p); }}"}[role]
    if role in ("enc", "dec"):
        a, b = ty.split(">")
        return f"static __attribute__((used)) {b} {w}({a} x) {{ return {nm}(x); }}"
    e = ty
    return {"scons1": f"static __attribute__((used)) {e} {w}(unsigned long a) {{ return {nm}(a); }}",
            "scons2": f"static __attribute__((used)) {e} {w}(unsigned long a, unsigned long b) {{ return {nm}(a, b); }}",
            "sobs": f"static __attribute__((used)) unsigned long long {w}({e} e) {{ return {nm}(e); }}",
            "smod": f"static __attribute__((used)) {e} {w}({e} e) {{ return {nm}(e); }}"}[role]


def union_names(b, p):
    """records whose top-level fields all sit at offset 0 (unions; clang prints typedef'd unions without the 'union' prefix)"""
    import subprocess
    args, cwd = S.base_args(b)
    r = subprocess.run(args + ["-fsyntax-only", "-w", "-Xclang", "-fdump-record-layouts", str(p)], cwd=cwd, capture_output=True, text=True,
                       errors="replace")
    out = set()
    for blk in r.stdout.split("*** Dumping AST Record Layout")[1:]:
        lines = [ln for ln in blk.splitlines() if "|" in ln]
        if not lines:
            continue
        name = re.sub(r"^(struct|union) ", "", lines[0].split("|", 1)[1].strip())
        offs = []
        for ln in lines[1:]:
            off, body = ln.split("|", 1)
            if body.startswith("   ") and not body.startswith("    ") and not body.strip().startswith("["):
                offs.append(off.strip())
        if len(offs) > 1 and len(set(offs)) == 1:
            out.add(name)
    return sorted(out)


def load(b, p):
    funcs = E.dump_unit(b, p, ["AE_"])
    for _ in range(12):
        miss = sorted(x for x in S.callees(funcs) if x not in funcs and not E.UNKNOWN_BOOL_CALLS.match(x) and not x.startswith("__builtin"))
        if not miss:
            break
        funcs.update(E.dump_unit(b, p, miss))
    info = {"records": S.record_layouts(b, p), "enums": {}, "unions": union_names(b, p)}
    names = S.enum_names(funcs)
    if names:
        src = p.read_text() + "".join(f"long long EN_{nm}(void) {{ return {nm}; }}\n" for nm in names)
        got = S.clang_consts(b, src, [f"EN_{nm}" for nm in names])
        info["enums"] = {nm: got[f"EN_{nm}"] for nm in names if got.get(f"EN_{nm}") is not None}
    S.BUILD_INFO[b] = info
    return funcs


# ---------------------------------------------------------------- switch statements (softleaf_type etc.); the frozen interpreter is subclassed, not edited
class _Break(Exception):
    pass


class AInterp(S.SInterp):
    def stmt(self, n, env, depth):
        k = n.get("kind")
        if k == "BreakStmt":
            raise _Break()
        if k == "SwitchStmt":
            kids = n.get("inner") or []
            cond, body = kids[-2], kids[-1]
            c = S.unwrap(self.expr(cond, env, depth))
            cv = c.const() if isinstance(c, SBV) else None
            if cv is None:
                raise E.Unsupported("switch on a non-constant")
            w = c.w
            items = []                                   # flattened: ("case", value) / ("default",) / ("stmt", node)

            def flat(x):
                kk = x.get("kind")
                if kk == "CaseStmt":
                    v = S.unwrap(self.expr(x["inner"][0], env, depth))
                    items.append(("case", (v.const() if isinstance(v, SBV) else None)))
                    flat(x["inner"][-1])
                elif kk == "DefaultStmt":
                    items.append(("default",))
                    flat(x["inner"][-1])
                else:
                    items.append(("stmt", x))
            for x in (body.get("inner") or []) if body.get("kind") == "CompoundStmt" else [body]:
                flat(x)
            m = (1 << w) - 1
            start = next((i for i, it in enumerate(items) if it[0] == "case" and it[1] is not None and (it[1] & m) == cv), None)
            if start is None:
                start = next((i for i, it in enumerate(items) if it[0] == "default"), None)
            if start is None:
                return None
            try:
                for it in items[start:]:
                    if it[0] == "stmt":
                        r = self.stmt(it[1], env, depth)
                        if r is not None:
                            return r
            except _Break:
                return None
            return None
        if k == "DoStmt":                               # do { ... } while (0), e.g. BUILD_BUG_ON
            body, cond = n["inner"][0], n["inner"][1]
            try:
                r = self.stmt(body, env, depth)
            except _Break:
                return None
            if r is not None:
                return r
            c = S.unwrap(self.expr(cond, env, depth))
            if not (isinstance(c, SBV) and c.const() == 0):
                raise E.Unsupported("do-while with a non-zero condition")
            return None
        return super().stmt(n, env, depth)

    def rec_fields(self, member):
        """field list of the record a MemberExpr reads from (clang record layout), or None"""
        base = member["inner"][0]
        t = base.get("type") or {}
        info = S.BUILD_INFO.get(self.build, {})
        recs, unions = info.get("records", {}), set(info.get("unions", []))
        for q in (t.get("qualType"), t.get("desugaredQualType")):
            if q:
                q = re.sub(r"^(struct|union) ", "", q.strip())
                if q in unions:
                    return None                         # a union is one storage, not several fields
                if q in recs:
                    return recs[q]
        return None

    @staticmethod
    def strip(n):
        while n.get("kind") in ("ParenExpr", "ImplicitCastExpr") and n.get("inner"):
            n = n["inner"][0]
        return n

    def expr(self, n, env, depth):
        k = n.get("kind")
        if k == "CompoundAssignOperator" or (k == "BinaryOperator" and n.get("opcode") == "="):
            lhs = self.strip(n["inner"][0])
            fields = self.rec_fields(lhs) if lhs.get("kind") == "MemberExpr" else None
            try:
                i, f = self.lval_id(n["inner"][0])
            except E.Unsupported:
                i, f = None, None
            if f is not None and fields and len(fields) > 1:
                # amendment 6.2: multi-field record -- write one field, keep the others
                cur = env.get(i)
                st = dict(cur) if isinstance(cur, dict) else {}
                w, sg = self.width(n["inner"][0])
                if k == "CompoundAssignOperator":
                    old = st.get(f)
                    old = old if isinstance(old, SBV) else SBV.unk(w or self.longw)
                    rhs = self.expr(n["inner"][1], env, depth)
                    v = self.binop(n.get("opcode")[:-1], old, rhs, w, sg)
                else:
                    v = self.expr(n["inner"][1], env, depth)
                while isinstance(v, dict) and len(v) == 1:
                    v = next(iter(v.values()))
                if isinstance(v, SBV) and w:
                    v = v.resize(w)
                st[f] = v
                env[i] = st
                return v
            if f is not None and isinstance(env.get(i), SBV) and not (fields and len(fields) > 1):
                env[i] = {f: env[i]}                    # a single-field struct that was kept unwrapped: re-wrap before a field write
        if k == "MemberExpr":
            fields = self.rec_fields(n)
            if fields and len(fields) > 1:
                base = self.expr(n["inner"][0], env, depth)
                if isinstance(base, dict):
                    if n.get("name") in base:
                        return base[n["name"]]
                    w, _ = self.width(n)
                    return SBV.unk(w or self.longw)    # amendment 6.2: an unwritten field is unknown, not another field
        return super().expr(n, env, depth)

    def binop(self, op, a, b, w, s):
        """relational operators on symbolic values: sound interval bounds from the bits and the input domain (DOM)"""
        if op in ("<", "<=", ">", ">="):
            a, b = S.unwrap(a), S.unwrap(b)
            nonneg = isinstance(a, SBV) and isinstance(b, SBV) and a.bits[-1] == 0 and b.bits[-1] == 0   # signed == unsigned when both >= 0
            if isinstance(a, SBV) and isinstance(b, SBV) and (not s or nonneg) and (a.const() is None or b.const() is None):
                ra, rb = bounds(a), bounds(b)
                if ra and rb:
                    (alo, ahi), (blo, bhi) = ra, rb
                    t = {"<": (ahi < blo, alo >= bhi), "<=": (ahi <= blo, alo > bhi), ">": (alo > bhi, ahi <= blo), ">=": (alo >= bhi, ahi < blo)}[op]
                    if t[0]:
                        return SBV(1, 1)
                    if t[1]:
                        return SBV(1, 0)
        return super().binop(op, a, b, w, s)


def bounds(x):
    """(lo, hi) of an unsigned bit vector under DOM; None if it cannot be bounded"""
    lo = sum(1 << i for i, b in enumerate(x.bits) if b == 1)
    hi = sum(1 << i for i, b in enumerate(x.bits) if b != 0)
    for var, lim_key, min_key in (("t", "tmax", None), ("o", None, "omin")):
        want = [(var, i, False) for i in range(x.w)]
        n = sum(1 for b in x.bits if b != 0)
        if n and all(b == want[i] or b == 0 for i, b in enumerate(x.bits)) and all(b == (var, i, False) for i, b in enumerate(x.bits) if b != 0)                 and set(i for i, b in enumerate(x.bits) if b != 0) == set(range(n)):
            if lim_key and S.DOM.get(lim_key) is not None:
                hi = min(hi, S.DOM[lim_key])
            if min_key and S.DOM.get(min_key):
                lo = max(lo, S.DOM[min_key])
    return lo, hi


# ---------------------------------------------------------------- behaviour of one observed value
class Ctx:
    def __init__(self, funcs, b):
        self.funcs, self.b, self.L = funcs, b, E.LONGW[b]
        self.cache, self.keep = {}, []

    def call(self, w, args):
        key = (w, tuple(id(a) for a in args))
        if key in self.cache:
            return self.cache[key]
        self.keep.append(args)            # keep the argument objects alive so their ids are never reused
        bad = next((a for a in args if isinstance(a, tuple)), None)
        if bad is not None:
            self.cache[key] = bad             # an argument is already "unsupported": propagate it
            return bad
        it = AInterp(self.funcs, self.L, {})
        it.build = self.b
        it.oracle = dict(S.ORACLE)
        try:
            r = it.call(w, args)
            if isinstance(r, dict) and len(r) == 1:
                r = next(iter(r.values()))
        except E.Unsupported as ex:
            r = ("unsup", str(ex)[:80])
        except RecursionError:
            r = ("unsup", "recursion")
        S.RUNTIME.update(it.runtime)
        self.cache[key] = r
        return r


def lit(var, n, L, low_zero=0):
    return SBV.of([0 if i < low_zero else (var, i, False) if i < n else 0 for i in range(L)])


def exact_low(x, var, n):
    """number of low bits of x that are exactly var's bits (up to n)"""
    if not isinstance(x, SBV):
        return -1
    k = 0
    for i in range(min(n, x.w)):
        if x.bits[i] == (var, i, False):
            k += 1
        else:
            break
    return k


def behaviour(v, params, consts):
    """params: {name: (var, nbits, low_zero)}; consts: {label: value}"""
    if isinstance(v, tuple):
        return "unsup"
    if isinstance(v, dict):
        return "unsup"
    c = v.const()
    if c is not None:
        for lab, val in consts.items():
            if c == val and c not in (0, 1):
                return f"eq:{lab}"
        return f"const:{c}" if c in (0, 1) else "const:other"
    for pn, (var, n, lz) in params.items():
        if n <= 0:
            continue
        want = [0 if i < lz else (var, i, False) if i < n else 0 for i in range(v.w)]
        if v.bits == want[:v.w]:
            return f"id:{pn}"
    for pn, (var, n, lz) in params.items():
        if lz:
            continue
        k = exact_low(v, var, n)
        if 0 < k < n:
            bk = v.bits[k]
            if bk in (0, 1) or isinstance(bk[0], str):    # amendment 5.1: bit k is a definite other value
                return f"idlow:{pn}:{k}"
            return "imprecise"
    t = v.truth()
    if t is True:
        return "truthy"
    if t is False:
        return "const:0"
    return "other"


def fresh_like(x, tag="z"):
    """a value of the same shape with every bit a fresh free input bit"""
    if isinstance(x, SBV):
        return SBV.of([(tag, i, False) for i in range(x.w)])
    if isinstance(x, dict):
        return {f: fresh_like(v, f"{tag}{j}") for j, (f, v) in enumerate(x.items())}
    return x


def is_stub(cx, w, like):
    """amendment 6.1: the modifier returns ANY input unchanged (checked on a fully symbolic input of the same shape)"""
    z = fresh_like(like)
    if z is like:
        return False
    return noop(cx.call(w, [z]), z)


def noop(a, b):
    """amendment 6.1: the modifier returned its input unchanged, bit for bit"""
    def one(x):
        while isinstance(x, dict) and len(x) == 1:
            x = next(iter(x.values()))
        return x
    a, b = one(a), one(b)
    if isinstance(a, SBV) and isinstance(b, SBV):
        return a.w == b.w and a.bits == b.bits
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(isinstance(a[f], SBV) and isinstance(b[f], SBV) and a[f].bits == b[f].bits for f in a)
    return False


# ---------------------------------------------------------------- families
def sw_family(cx, R, K, out):
    L = cx.L
    MAX, PS, MPB, PHYS = K["MAX"], K["PAGE_SHIFT"], K["MPB"], K["PHYS"]
    for layer in ("public", "arch"):
        inl = (lambda n: n.startswith("__")) if layer == "arch" else (lambda n: not n.startswith("__"))
        cons = [(r, n, t) for r in ("scons2", "scons1") for n, t in R.get(r, []) if inl(n)]
        sobs = [(n, t) for n, t in R.get("sobs", []) if inl(n)]
        typeobs = [n for n, t in sobs if n.endswith("_type")]
        offobs = [n for n, t in sobs if n.endswith("_offset")]
        if not typeobs or not offobs:
            continue
        # the layer's type / offset field observers are chosen by behaviour, not by a hand-written name: among the observers named
        # *_type / *_offset, the one that reads back the type / offset argument of the layer's two-argument constructor
        two = [(n, t) for n, t in R.get("scons2", []) if inl(n) and len(NAMES.get(n, {}).get("params") or []) == 2]
        tob = oob = None
        if two:
            S.DOM.update(tmax=None, ofree=L, omin=0)
            e2 = cx.call(wname("scons2", two[0][0], two[0][1]), [lit("t", 5, L), lit("o", L, L)])
            for n in typeobs:
                if behaviour(cx.call(wname("sobs", n, two[0][1]), [e2]), {"type": ("t", 5, 0)}, {}) == "id:type":
                    tob = n
                    break
            for n in offobs:
                if exact_low(cx.call(wname("sobs", n, two[0][1]), [e2]), "o", L) > 0:
                    oob = n
                    break
        if tob is None or oob is None:
            out[f"SW|{layer}|field-observers"] = {"beh": "domain-unknown", "why": f"type={typeobs} offset={offobs}"}
            continue
        hasp = [n for n, t in sobs if n.endswith("has_pfn")]
        encs = [(n, t) for n, t in R.get("enc", []) if inl(n)]
        decs = [(n, t) for n, t in R.get("dec", []) if inl(n)]
        for role, cn, ety in cons:
            cw = wname(role, cn, ety)
            pnames = (NAMES.get(cn, {}).get("params") or [])
            S.DOM.update(tmax=None, ofree=L, omin=0)
            tF, oF = lit("t", 5, L), lit("o", L, L)
            if role == "scons2":
                if len(pnames) != 2 or "type" not in pnames[0]:
                    continue
                e0 = cx.call(cw, [tF, oF])
                ty_b = behaviour(cx.call(wname("sobs", tob, ety), [e0]), {"type": ("t", 5, 0)}, {})
                if ty_b != "id:type":
                    out[f"SW|{layer}|{cn}|kind"] = {"beh": "domain-unknown", "why": f"type observer gives {ty_b}"}
                    continue
                kind, tconst = "ordinary", None
            else:
                e0 = cx.call(cw, [oF])
                tv = cx.call(wname("sobs", tob, ety), [e0])
                tconst = tv.const() if isinstance(tv, SBV) else None
                hp = cx.call(wname("sobs", hasp[0], ety), [e0]) if hasp else None
                hpt = hp.truth() if isinstance(hp, SBV) else None
                if tconst is None or tconst < MAX or hpt is not True:
                    out[f"SW|{layer}|{cn}|kind"] = {"beh": "domain-unknown", "why": f"type={tconst} has_pfn={hpt}"}
                    continue
                kind = "pfn"
            # public width of the offset field (amendment 2.3)
            pubw = exact_low(cx.call(wname("sobs", oob, ety), [e0]), "o", L)
            for en, et in encs:
                tlv = et.split(">")[1]
                for dn, dt in decs:
                    if dt.split(">")[0] != tlv:
                        continue
                    ew, dw = wname("enc", en, et), wname("dec", dn, dt)
                    # amendment 5.2: is this encoder/decoder pair usable on this build (type field read back from the 2-arg constructor)?
                    S.DOM.update(tmax=MAX - 1, ofree=1, omin=1)
                    e2a = cx.call(wname("scons2", two[0][0], two[0][1]), [lit("t", 5, L), lit("o", 1, L)])
                    tb = cx.call(wname("sobs", tob, ety), [cx.call(dw, [cx.call(ew, [e2a])])])
                    if isinstance(tb, SBV) and tb.const() == 0:
                        out[f"SW|{layer}|{cn}|{en}|{dn}|avail"] = {"beh": "not-applicable", "why": "type field not read back"}
                        continue
                    # encoding capacity (amendment 2.4): raw round trip through the arch decode, no present/none filter
                    kenc = None
                    if layer == "arch":
                        kenc = exact_low(cx.call(wname("sobs", oob, ety), [cx.call(dw, [cx.call(ew, [e0])])]), "o", pubw)
                    else:
                        archd = [n for n, t in R.get("dec", []) if n.startswith("__") and t == dt]
                        archo = [n for n, t in R.get("sobs", []) if n.startswith("__") and n.endswith("_offset")]
                        archt = [n for n, t in R.get("sobs", []) if n.startswith("__") and n.endswith("_type")]
                        if archd and archo and archt:
                            raw = cx.call(wname("dec", archd[0], dt), [cx.call(ew, [e0])])
                            # public re-pack of the arch fields is what the public decoder does after its present/none filter
                            kenc = exact_low(cx.call(wname("sobs", archo[0], ety), [raw]), "o", pubw)
                    if not kenc:
                        kenc = pubw
                    if kind == "ordinary":
                        nb, dsrc, omin, tmax = min(32, kenc, pubw), "交换偏移", 1, MAX - 1
                    else:
                        if MPB:
                            nb, dsrc = min(MPB - PS, pubw), "MAX_PHYSMEM_BITS"
                        else:
                            nb, dsrc = min(PHYS - PS, pubw), "回退:phys_addr_t"
                        omin, tmax = 0, None
                    S.DOM.update(tmax=tmax, ofree=nb, omin=omin)
                    tD, oD = lit("t", 5, L), lit("o", nb, L)
                    e = cx.call(cw, [tD, oD] if role == "scons2" else [oD])
                    x = cx.call(ew, [e])
                    params = {"offset": ("o", nb, 0)} if kind == "pfn" else {"type": ("t", 5, 0), "offset": ("o", nb, 0)}
                    consts = {"type": tconst} if tconst is not None else {}
                    meta = {"dom": dsrc, "nbits": nb, "kenc": kenc, "pubw": pubw, "kind": kind}
                    tmods = [None] + [n for n, t in R.get("mod", []) if t == tlv and "_swp_" in n]
                    tobs = [n for n, t in R.get("obs", []) if t == tlv and ("_swp_" in n or n in (tlv[:3] + "_present", tlv[:3] + "_none"))]
                    for mn in tmods:
                        xm = x if mn is None else cx.call(wname("mod", mn, tlv), [x])
                        tag = mn or "-"
                        if mn is not None and is_stub(cx, wname("mod", mn, tlv), x):
                            out[f"SW|{layer}|{cn}|{en}|{tag}|noop"] = {"beh": "not-applicable", "why": "modifier is the identity"}
                            continue
                        for on in tobs:
                            v = cx.call(wname("obs", on, tlv), [xm])
                            out[f"SW|{layer}|{cn}|{en}|{tag}|{on}"] = dict(meta, beh=behaviour(v, params, consts))
                        ed = cx.call(dw, [xm])
                        for on, ot in sobs:
                            if "pfn" in on and kind != "pfn":
                                continue                        # amendment 5.3
                            v = cx.call(wname("sobs", on, ot), [ed])
                            out[f"SW|{layer}|{cn}|{en}|{tag}|{dn}>{on}"] = dict(meta, beh=behaviour(v, params, consts))


def pt_family(cx, R, K, out):
    L, PS, MPB, PHYS = cx.L, K["PAGE_SHIFT"], K["MPB"], K["PHYS"]
    prots = [n for n, t in R.get("prot", [])]
    pv = {n: cx.call(wname("prot", n, ""), []) for n in prots}
    for cn, ct in R.get("cons", []):
        lz = 0
        if ct in ("pmd_t", "pud_t"):
            sh = K["PMD_SHIFT"] if ct == "pmd_t" else K["PUD_SHIFT"]
            if sh is None:
                out[f"PT|{cn}|domain"] = {"beh": "domain-unknown", "why": f"{ct[:3].upper()}_SHIFT is not a constant"}
                continue
            lz = sh - PS
        if MPB:
            nb, dsrc = MPB - PS, "MAX_PHYSMEM_BITS"
        else:
            nb, dsrc = PHYS - PS, "回退:phys_addr_t"
        nb = min(nb, L)
        S.DOM.update(tmax=None, ofree=nb, omin=0)
        pf = lit("o", nb, L, lz)
        params = {"pfn": ("o", nb, lz)}
        mods = [None] + [n for n, t in R.get("mod", []) if t == ct and "_swp_" not in n]
        obs = [n for n, t in R.get("obs", []) if t == ct and "_swp_" not in n]
        for pn, p in pv.items():
            if isinstance(p, tuple):
                continue
            x = cx.call(wname("cons", cn, ct), [pf, p])
            for mn in mods:
                xm = x if mn is None else cx.call(wname("mod", mn, ct), [x])
                if mn is not None and is_stub(cx, wname("mod", mn, ct), x):
                    out[f"PT|{cn}|{pn}|{mn}|noop"] = {"beh": "not-applicable", "why": "modifier is the identity"}
                    continue
                for on in obs:
                    v = cx.call(wname("obs", on, ct), [xm])
                    out[f"PT|{cn}|{pn}|{mn or '-'}|{on}"] = {"beh": behaviour(v, params, {}), "dom": dsrc, "nbits": nb, "lowzero": lz}


def run_build(b):
    if b in A.ARCHES or b == "ppc64le_hash":
        A.register(b)
    sigs = json.loads((HERE / f"sigs_{b}.json").read_text(encoding="utf-8"))
    R = roles(sigs)
    weak = is_weak(level_filter(sigs))
    S.WORK.mkdir(parents=True, exist_ok=True)
    p = Path("/root/work/autoenc") / f"mine_{b}.c"
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [HDR, CONSTS] + [wrapper(r, n, t) + "\n" for r, xs in R.items() for n, t in xs]
    p.write_text("".join(lines))
    funcs = load(b, p)
    res = {"build": b, "weak_types": weak, "roles": {r: len(xs) for r, xs in R.items()}}
    S.ORACLE.clear()
    S.RUNTIME.clear()

    def once():
        cx = Ctx(funcs, b)
        S.DOM.update(tmax=None, ofree=1, omin=0)
        K = {}
        for k in ("MAX", "PAGE_SHIFT", "PMD_SHIFT", "PUD_SHIFT", "PHYS", "MPB"):
            v = cx.call(f"AE_K_{k}", [])
            K[k] = v.const() if isinstance(v, SBV) else None
        out = {}
        if None in (K["MAX"], K["PAGE_SHIFT"], K["PHYS"], K["MPB"]):
            return K, {"_error": {"beh": "constants unknown", "K": K}}
        sw_family(cx, R, K, out)
        pt_family(cx, R, K, out)
        return K, out
    K0, out0 = once()
    keys = sorted(S.RUNTIME)
    if keys and len(keys) <= 4:
        per = {}
        for vals in itertools.product([False, True], repeat=len(keys)):
            S.ORACLE.clear()
            S.ORACLE.update(zip(keys, vals))
            per[vals] = once()
        S.ORACLE.clear()
        allk = set().union(*[set(o) for _, o in per.values()])
        merged = {}
        for k in allk:
            bs = {o.get(k, {}).get("beh") for _, o in per.values()}
            one = next(o[k] for _, o in per.values() if k in o)
            merged[k] = dict(one, beh=bs.pop() if len(bs) == 1 else "runtime-dependent", per_combo=sorted(str(x) for x in bs) if len(bs) > 1 else None)
        res.update(runtime=keys, K={str(v): kk for v, (kk, _) in per.items()}, laws=merged)
    else:
        res.update(runtime=keys, K=K0, laws=out0)
    (HERE / f"beh_{b}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    c = Counter(v["beh"].split(":")[0] for v in res["laws"].values())
    print(b, "laws", len(res["laws"]), dict(c), "runtime", keys, flush=True)


NAMES = json.loads((HERE / "names.json").read_text(encoding="utf-8"))["names"]

if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    for b in (sys.argv[1:] or BUILDS):
        try:
            run_build(b)
        except Exception as ex:
            import traceback
            traceback.print_exc()
            print(b, "FAILED", type(ex).__name__, str(ex)[:300], flush=True)
