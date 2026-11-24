"""pfnswap (round 5): PFN swap entries and PMD swap entries, bit-symbolic, on the 20 builds of swapsym rounds 3-4. WSL.

    python3 pfnswap.py run [builds...]      -> pfn_<build>.json
"""
import itertools
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SS = HERE.parent / "swapsym_20261121"
sys.path.insert(0, str(SS))
import swaparch as A  # noqa: E402  (registers the round-4 variants; imported, not modified)
S = A.S
E, I = S.E, S.I
SBV = S.SBV
# arm64 with LPA2: PHYS_MASK_SHIFT = lpa2_is_enabled() ? 52 : 48 -- a runtime CPU feature read through inline asm; enumerate it like the
# other runtime predicates (extends the imported pattern at run time; evalpg.py itself is not modified)
E.UNKNOWN_BOOL_CALLS = re.compile(E.UNKNOWN_BOOL_CALLS.pattern[:-2] + "|lpa2_is_enabled)$")

BASE = ["riscv64", "rv32_abi", "x86_64", "i386", "i386_pae", "arm64"]
VARS = ["ppc64le", "ppc64le_hash", "ppc64e", "ppc32s", "ppc44x", "ppc8xx", "s390", "loongarch", "mips32", "mips32xpa", "mips64", "arm",
        "arm_lpae", "hexagon"]

SRC = S.SRC + r'''
unsigned long S_pfnbits(void) { return SWP_PFN_BITS; }
unsigned long S_migtotal(void) { return SWP_MIG_TOTAL_BITS; }
unsigned long S_pfnoff(unsigned long t, unsigned long o) { return swp_offset(softleaf_from_pte(s_p(t, o))) & SWP_PFN_MASK; }
#ifdef CONFIG_MIGRATION
unsigned long T_MIGRATION_READ(void) { return SWP_MIGRATION_READ; }
unsigned long T_MIGRATION_READ_EXCLUSIVE(void) { return SWP_MIGRATION_READ_EXCLUSIVE; }
unsigned long T_MIGRATION_WRITE(void) { return SWP_MIGRATION_WRITE; }
#endif
#ifdef CONFIG_MEMORY_FAILURE
unsigned long T_HWPOISON(void) { return SWP_HWPOISON; }
#endif
#ifdef CONFIG_DEVICE_PRIVATE
unsigned long T_DEVICE_WRITE(void) { return SWP_DEVICE_WRITE; }
unsigned long T_DEVICE_READ(void) { return SWP_DEVICE_READ; }
unsigned long T_DEVICE_EXCLUSIVE(void) { return SWP_DEVICE_EXCLUSIVE; }
#endif
#ifdef CONFIG_ARCH_HAS_PMD_SOFTLEAVES
static inline pmd_t s_m(unsigned long t, unsigned long o) { return swp_entry_to_pmd(swp_entry(t, o)); }
unsigned long long M_enc(unsigned long t, unsigned long o) { return pmd_val(s_m(t, o)); }
int M_present(unsigned long t, unsigned long o) { return !!pmd_present(s_m(t, o)); }
int M_none(unsigned long t, unsigned long o) { return !!pmd_none(s_m(t, o)); }
unsigned long long M_flags(unsigned long t, unsigned long o)
{
	pmd_t m = s_m(t, o), m2 = m;
	if (pmd_swp_soft_dirty(m2))
		m2 = pmd_swp_clear_soft_dirty(m2);
	if (pmd_swp_uffd(m2))
		m2 = pmd_swp_clear_uffd(m2);
	return pmd_val(m2) ^ pmd_val(m);
}
unsigned long M_type(unsigned long t, unsigned long o) { return swp_type(softleaf_from_pmd(s_m(t, o))); }
unsigned long M_off(unsigned long t, unsigned long o) { return swp_offset(softleaf_from_pmd(s_m(t, o))); }
unsigned long M_offraw(unsigned long t, unsigned long o) { swp_entry_t a = __pmd_to_swp_entry(s_m(t, o)); return swp_offset(swp_entry(__swp_type(a), __swp_offset(a))); }
#endif
'''


def load(b, p):
    """as swapsym.load, with this round's extra function prefixes"""
    funcs = E.dump_unit(b, p, ["S_", "s_p", "T_", "M_", "s_m"])
    for _ in range(10):
        miss = sorted(x for x in S.callees(funcs) if x not in funcs and not E.UNKNOWN_BOOL_CALLS.match(x) and not x.startswith("__builtin"))
        if not miss:
            break
        funcs.update(E.dump_unit(b, p, miss))
    info = {"records": S.record_layouts(b, p), "enums": {}}
    names = S.enum_names(funcs)
    if names:
        src = p.read_text() + "".join(f"long long EN_{nm}(void) {{ return {nm}; }}\n" for nm in names)
        got = S.clang_consts(b, src, [f"EN_{nm}" for nm in names])
        info["enums"] = {nm: got[f"EN_{nm}"] for nm in names if got.get(f"EN_{nm}") is not None}
    S.BUILD_INFO[b] = info
    return funcs


def const(funcs, b, nm):
    r = S.sym_call(funcs, b, nm, None, None)
    return r["val"].const() if "val" in r and isinstance(r["val"], SBV) else None


def tconst(L, T):
    return SBV(L, T)


def ofree(L, n):
    return SBV.of([("o", i, False) if i < n else 0 for i in range(L)])


def first_mismatch(x, n):
    """index of the first bit i < n where x is not exactly o_i (None if all match and nothing else leaks in below n)"""
    if not isinstance(x, SBV):
        return -1
    for i in range(min(n, x.w)):
        if x.bits[i] != ("o", i, False):
            return i
    return None


def eval_once(funcs, b, L, MAX, pfnbits, types, has_pmd):
    out = {}
    # capacity of the PTE encoding (as round 4) and of the PMD encoding
    S.DOM.update(tmax=None, ofree=c_pubw(funcs, b), omin=0)
    raw = S.sym_call(funcs, b, "S_offraw", tconst(L, 0), ofree(L, S.DOM["ofree"]))
    k = first_mismatch(raw.get("val"), S.DOM["ofree"])
    out["K_enc"] = S.DOM["ofree"] if k is None else max(k, 0)
    if has_pmd:
        rawm = S.sym_call(funcs, b, "M_offraw", tconst(L, 0), ofree(L, S.DOM["ofree"]))
        km = first_mismatch(rawm.get("val"), S.DOM["ofree"])
        out["K_enc_pmd"] = S.DOM["ofree"] if km is None else max(km, 0)
    # contract A: each special type over 0 <= pfn < 2^pfnbits
    A_res = {}
    for tn, T in types.items():
        S.DOM.update(tmax=None, ofree=pfnbits, omin=0)
        t, o = tconst(L, T), ofree(L, pfnbits)
        r = {nm: S.sym_call(funcs, b, nm, t, o) for nm in ("S_enc", "S_present", "S_none", "S_flags", "S_type", "S_pfnoff")}

        def tv(nm):
            return r[nm]["val"].truth() if "val" in r[nm] else "不支持"
        pres, none, fl = tv("S_present"), tv("S_none"), tv("S_flags")
        p1 = "成立" if pres is False and none is False else ("不支持" if "不支持" in (pres, none) else "违反" if True in (pres, none) else "未知")
        p2 = "成立" if fl is False else ("不支持" if fl == "不支持" else "违反" if fl is True else "未知")
        ty = r["S_type"].get("val")
        ty_ok = isinstance(ty, SBV) and ty.const() == T
        mm = first_mismatch(r["S_pfnoff"].get("val"), pfnbits)
        p3 = "成立" if ty_ok and mm is None else ("不支持" if "unsupported" in r["S_type"] or "unsupported" in r["S_pfnoff"] else "违反" if mm not in (None, -1) else "未知")
        A_res[tn] = {"T": T, "P1": p1, "P2": p2, "P3": p3, "type_const": ty.const() if isinstance(ty, SBV) else None,
                     "first_lost_pfn_bit": mm, "enc": repr(r["S_enc"].get("val", r["S_enc"].get("unsupported"))),
                     "pfnoff": repr(r["S_pfnoff"].get("val", r["S_pfnoff"].get("unsupported"))),
                     "unsupported": {nm: x["unsupported"] for nm, x in r.items() if "unsupported" in x}}
    out["A"] = A_res
    # contract B: PMD ordinary swap entries
    if has_pmd:
        K = min(32, out["K_enc_pmd"])
        S.DOM.update(tmax=MAX - 1, ofree=K, omin=1)
        t, o = S.mk_inputs(L, K)
        r = {nm: S.sym_call(funcs, b, nm, t, o) for nm in ("M_enc", "M_present", "M_none", "M_flags", "M_type", "M_off")}

        def tvm(nm):
            return r[nm]["val"].truth() if "val" in r[nm] else "不支持"
        pres, none, fl = tvm("M_present"), tvm("M_none"), tvm("M_flags")
        o1 = "成立" if pres is False and none is False else ("不支持" if "不支持" in (pres, none) else "违反" if True in (pres, none) else "未知")
        o2 = "成立" if fl is False else ("不支持" if fl == "不支持" else "违反" if fl is True else "未知")
        o3 = "成立" if S.exact_bits(r["M_type"].get("val"), "t", 5, L) and S.exact_bits(r["M_off"].get("val"), "o", K, L) else (
            "不支持" if any("unsupported" in r[x] for x in ("M_type", "M_off")) else "未知或违反")
        out["B"] = {"K": K, "O1": o1, "O2": o2, "O3": o3, "enc": repr(r["M_enc"].get("val", r["M_enc"].get("unsupported"))),
                    "unsupported": {nm: x["unsupported"] for nm, x in r.items() if "unsupported" in x}}
    return out


def c_pubw(funcs, b):
    return const(funcs, b, "S_pubw")


def consts_for(funcs, b):
    # a non-empty neutral domain: with the module default (no free o bit but o >= 1) the domain is empty and every condition on unknown
    # bits would be "proved" vacuously -- this is what produced arm64's spurious SWP_PFN_BITS = 40 in the first runs
    S.DOM.update(tmax=None, ofree=1, omin=0)
    return {"MAX": const(funcs, b, "S_max"), "pfnbits": const(funcs, b, "S_pfnbits"), "migtotal": const(funcs, b, "S_migtotal"),
            "probe": const(funcs, b, "S_probe"), "types": {nm[2:]: const(funcs, b, nm) for nm in sorted(funcs) if nm.startswith("T_")}}


def run_build(b):
    """runtime predicates (e.g. x86_64 pgtable_l5_enabled() inside MAX_PHYSMEM_BITS) are found first; every combination gets its own
    constants and its own verdicts; an obligation holds only if it holds under every combination"""
    S.WORK.mkdir(parents=True, exist_ok=True)
    p = S.WORK / f"pfn_{b}.c"
    p.write_text(SRC)
    funcs = load(b, p)
    L = E.LONGW[b]
    cfg = (Path(I.BUILDS[b]) / ".config").read_text(errors="replace")
    has_pmd = bool(re.search(r"^CONFIG_ARCH_HAS_PMD_SOFTLEAVES=y", cfg, re.M)) and "M_enc" in funcs
    S.ORACLE.clear()
    S.RUNTIME.clear()
    consts_for(funcs, b)
    first = None
    try:
        c0 = consts_for(funcs, b)
        if None not in (c0["MAX"], c0["pfnbits"]) and None not in c0["types"].values():
            first = eval_once(funcs, b, L, c0["MAX"], c0["pfnbits"], c0["types"], has_pmd)
    except E.Unsupported:
        pass
    keys = sorted(S.RUNTIME)
    res = {"build": b, "longw": L, "has_pmd_softleaves": has_pmd}
    if len(keys) > 4:
        res["status"] = f"运行时判断过多 {keys}"
        return res, funcs
    combos = {}
    for vals in (itertools.product([False, True], repeat=len(keys)) if keys else [()]):
        S.ORACLE.clear()
        S.ORACLE.update(zip(keys, vals))
        c = consts_for(funcs, b)
        name = ", ".join(f"{k}={v}" for k, v in S.ORACLE.items())
        if None in (c["MAX"], c["pfnbits"]) or None in c["types"].values():
            combos[name] = {"consts": c, "status": "常量求不出"}
            continue
        r = eval_once(funcs, b, L, c["MAX"], c["pfnbits"], c["types"], has_pmd)
        r["consts"] = c
        r["capacity_vs_pfn"] = "够" if c["pfnbits"] <= r["K_enc"] else f"不够：SWP_PFN_BITS {c['pfnbits']} > K_enc {r['K_enc']}"
        r["ad_consistent"] = c["migtotal"] is not None and c["probe"] is not None and ((c["probe"] >= (1 << c["migtotal"])) == (c["migtotal"] <= r["K_enc"]))
        combos[name] = r
    S.ORACLE.clear()
    res["runtime"] = keys
    res["per_combo"] = combos
    if any("status" in c for c in combos.values()):
        res["status"] = "某些组合常量求不出"
        return res, funcs
    one = next(iter(combos.values()))
    res["types"] = one["consts"]["types"]
    res["MAX_SWAPFILES"] = sorted({c["consts"]["MAX"] for c in combos.values()})
    res["SWP_PFN_BITS"] = sorted({c["consts"]["pfnbits"] for c in combos.values()})
    res["K_enc"] = min(c["K_enc"] for c in combos.values())
    res["capacity_vs_pfn"] = sorted({c["capacity_vs_pfn"] for c in combos.values()})
    res["ad_consistent"] = all(c["ad_consistent"] for c in combos.values())
    res["A"] = {tn: {k: ("成立" if all(c["A"][tn][k] == "成立" for c in combos.values()) else "/".join(sorted({c["A"][tn][k] for c in combos.values()})))
                     for k in ("P1", "P2", "P3")} for tn in res["types"]}
    for tn in res["types"]:
        res["A"][tn]["first_lost_pfn_bit"] = sorted({c["A"][tn]["first_lost_pfn_bit"] for c in combos.values()}, key=lambda x: (x is None, x))
    if has_pmd:
        res["K_enc_pmd"] = min(c["K_enc_pmd"] for c in combos.values())
        res["B"] = {k: ("成立" if all(c["B"][k] == "成立" for c in combos.values()) else "/".join(sorted({c["B"][k] for c in combos.values()})))
                    for k in ("O1", "O2", "O3")}
    return res, funcs


def concrete(b, res, funcs):
    L, K = res["longw"], res["K_enc"]
    pfnbits, pfnmax = min(res["SWP_PFN_BITS"]), max(res["SWP_PFN_BITS"])
    m = (1 << pfnbits) - 1
    pfns = sorted({0, 1, 0x12345 & m, (1 << min(K, pfnbits)) - 1, m, (1 << K) if K < pfnbits else m >> 1, ((1 << K) | 5) & m})
    lines, names = [SRC], []
    for tn, T in res["types"].items():
        for pfn in pfns:
            for nm in ("S_enc", "S_present", "S_none", "S_type", "S_pfnoff"):
                f = f"C_{tn}_{pfn:x}_{nm}"
                rt = "unsigned long long" if nm == "S_enc" else "unsigned long"
                lines.append(f"{rt} {f}(void) {{ return {nm}({T}UL, {pfn}UL); }}")
                names.append((f, T, pfn, nm))
    got = S.clang_consts(b, "\n".join(lines) + "\n", [n for n, *_ in names])
    combos = [dict(zip(res["runtime"], v)) for v in itertools.product([False, True], repeat=len(res["runtime"]))] if res.get("runtime") else [{}]
    rows, agree, nof, dis = [], 0, 0, 0
    S.DOM.update(tmax=None, ofree=pfnmax, omin=0)
    syms = []
    for orc in combos:
        S.ORACLE.clear()
        S.ORACLE.update(orc)
        per_t = {}
        for tn, T in res["types"].items():
            per_t[T] = {nm: S.sym_call(funcs, b, nm, tconst(L, T), ofree(L, pfnmax)).get("val")
                        for nm in ("S_enc", "S_present", "S_none", "S_type", "S_pfnoff")}
        syms.append(per_t)
    S.ORACLE.clear()
    for f, T, pfn, nm in names:
        pvs = set()
        for per_t in syms:
            x = S.subst(per_t[T][nm], 0, pfn)
            if nm in ("S_present", "S_none") and x is not None:
                x = int(x != 0)
            pvs.add(x)
        pv = pvs.pop() if len(pvs) == 1 else None
        cv = got.get(f)
        st = "无法对账" if cv is None or pv is None else ("一致" if cv == pv else "不一致")
        agree += st == "一致"
        nof += st == "无法对账"
        dis += st == "不一致"
        rows.append({"func": f, "T": T, "pfn": pfn, "what": nm, "clang": cv, "symbolic": pv, "status": st})
    res["concrete"] = {"pfns": pfns, "agree": agree, "no_fold": nof, "disagree": dis, "rows": rows}


def run(builds):
    summary = {}
    for b in builds:
        if b in VARS:
            why = A.register(b)
            if why:
                summary[b] = {"status": why}
                continue
        try:
            res, funcs = run_build(b)
            if "status" not in res:
                concrete(b, res, funcs)
        except Exception as ex:
            summary[b] = {"status": f"失败：{type(ex).__name__}: {str(ex)[:300]}"}
            print(b, json.dumps(summary[b], ensure_ascii=False), flush=True)
            continue
        (HERE / f"pfn_{b}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str))
        summary[b] = {"PFN_BITS": res.get("SWP_PFN_BITS"), "K_enc": res.get("K_enc"), "cap": res.get("capacity_vs_pfn"),
                      "A": res.get("A"), "B": res.get("B"), "ad_ok": res.get("ad_consistent"),
                      "conc": {k: res.get("concrete", {}).get(k) for k in ("agree", "no_fold", "disagree")}, "status": res.get("status")}
        print(b, json.dumps(summary[b], ensure_ascii=False), flush=True)
    return summary


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    if sys.argv[1] == "run":
        run(sys.argv[2:] or BASE + VARS)
