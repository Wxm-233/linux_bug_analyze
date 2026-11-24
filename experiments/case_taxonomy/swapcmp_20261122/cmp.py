"""swapcmp (round 7): frozen swap checks vs nine engines, frozen basic tests and the native debug_vm_pgtable swap tests. WSL.

    python3 cmp.py native     -> native_<build>.json (clang-folded native assertions on the native vector)
    python3 cmp.py table      -> cells.json, cells.md, violations.md (reads frozen results + native_*.json; runs anywhere with python3)
"""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
BUILDS = ["riscv64", "rv32_abi", "x86_64", "i386", "i386_pae", "arm64", "ppc64le", "ppc64le_hash", "ppc64e", "ppc32s", "ppc44x", "ppc8xx",
          "s390", "loongarch", "mips32", "mips32xpa", "mips64", "arm", "arm_lpae", "hexagon"]
ROUND3 = ["riscv64", "rv32_abi", "x86_64", "i386", "i386_pae", "arm64"]


def check_frozen():
    for ln in (HERE / "frozen_sha256.txt").read_text().splitlines():
        h, name = ln.split(" ", 1)
        name = name.lstrip("*")
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == h, f"frozen file changed: {name}"


NATIVE_SRC = r'''
#include <linux/mm.h>
#include <linux/pgtable.h>
#include <linux/swapops.h>
#include <linux/leafops.h>
/* mm/debug_vm_pgtable.c:1228-1231: the one ordinary swap entry every native swap test uses */
static inline swp_entry_t n_entry(void)
{
	unsigned long mso = swp_offset(softleaf_from_pte(softleaf_to_pte(swp_entry(0, ~0UL))));
	return swp_entry(MAX_SWAPFILES - 1, mso);
}
unsigned long N_vec_type(void) { return swp_type(n_entry()); }
unsigned long N_vec_offset(void) { return swp_offset(n_entry()); }
/* pte_swap_tests (:805-820): softleaf_is_swap + PTE -> arch entry -> PTE byte equality */
unsigned long N_pte_isswap(void) { return softleaf_is_swap(softleaf_from_pte(swp_entry_to_pte(n_entry()))); }
unsigned long N_pte_bytes(void)
{
	pte_t p1 = swp_entry_to_pte(n_entry());
	swp_entry_t a = __pte_to_swp_entry(p1);
	pte_t p2 = __swp_entry_to_pte(a);
	return pte_val(p1) == pte_val(p2);
}
/* pte_swap_exclusive_tests (:773-803): exclusive bit clear after encoding; decoded entry equals the input, with and without the bit */
unsigned long N_excl_clear(void) { return !pte_swp_exclusive(swp_entry_to_pte(n_entry())); }
unsigned long N_roundtrip(void) { swp_entry_t e = n_entry(); return softleaf_from_pte(swp_entry_to_pte(e)).val == e.val; }
unsigned long N_excl_roundtrip(void)
{
	swp_entry_t e = n_entry();
	pte_t p = pte_swp_mkexclusive(swp_entry_to_pte(e));
	return pte_swp_exclusive(p) && !pte_swp_soft_dirty(p) && softleaf_from_pte(p).val == e.val &&
	       softleaf_from_pte(pte_swp_clear_exclusive(p)).val == e.val;
}
/* pte_swap_soft_dirty_tests (:715-730) */
unsigned long N_sd(void)
{
	pte_t p = swp_entry_to_pte(n_entry());
	return pte_swp_soft_dirty(pte_swp_mksoft_dirty(p)) && !pte_swp_soft_dirty(pte_swp_clear_soft_dirty(p));
}
#ifdef CONFIG_ARCH_HAS_PMD_SOFTLEAVES
/* pmd_softleaf_tests / pmd_leaf_soft_dirty_tests (:822-840, :749-768): leaf_entry = make_writable_migration_entry(~0UL) */
unsigned long N_pmd_valid(void) { return pmd_is_valid_softleaf(softleaf_to_pmd(make_writable_migration_entry(~0UL))); }
unsigned long N_pmd_bytes(void)
{
	pmd_t m1 = softleaf_to_pmd(make_writable_migration_entry(~0UL));
	pmd_t m2 = __swp_entry_to_pmd(__pmd_to_swp_entry(m1));
	return pmd_val(m1) == pmd_val(m2);
}
#endif
'''
NAT = ["N_vec_type", "N_vec_offset", "N_pte_isswap", "N_pte_bytes", "N_excl_clear", "N_roundtrip", "N_excl_roundtrip", "N_sd", "N_pmd_valid",
       "N_pmd_bytes"]


def native():
    check_frozen()
    sys.path.insert(0, str(CT / "swapsym_20261121"))
    import swaparch as A
    S = A.S
    S.WORK.mkdir(parents=True, exist_ok=True)
    for b in BUILDS:
        if b in A.ARCHES or b == "ppc64le_hash":
            A.register(b)
        src = NATIVE_SRC + "".join(f"unsigned long long F_{n}(void) {{ return {n}(); }}\n" for n in NAT if True)
        # PMD functions exist only with ARCH_HAS_PMD_SOFTLEAVES: compile them guarded
        src = NATIVE_SRC + "".join(
            (f"#ifdef CONFIG_ARCH_HAS_PMD_SOFTLEAVES\n" if n.startswith("N_pmd") else "") + f"unsigned long long F_{n}(void) {{ return {n}(); }}\n" +
            ("#endif\n" if n.startswith("N_pmd") else "") for n in NAT)
        try:
            got = S.clang_consts(b, src, [f"F_{n}" for n in NAT])
            res = {"build": b, "native": {n: got.get(f"F_{n}") for n in NAT}}
        except Exception as ex:
            res = {"build": b, "error": str(ex)[:500]}
        (HERE / f"native_{b}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
        print(b, json.dumps(res, ensure_ascii=False), flush=True)
    check_frozen()


# ---------------------------------------------------------------- nine engines / basic tests: object match, then the reason
OBJ_FILES = re.compile(r"^(arch/[^/]+/include/asm/.*pgtable.*\.h|include/linux/swapops\.h|include/linux/leafops\.h|mm/debug_vm_pgtable\.c)$")
OBJ_FUNCS = re.compile(r"(^__?swp_|swp_entry|swp_type|swp_offset|softleaf_from_p|softleaf_to_p|softleaf_to_pfn|softleaf_has_pfn|pte_swp_clear_flags|"
                       r"^pte_swap_|^pmd_softleaf|^pmd_leaf_soft_dirty|^swap_migration_tests|^init_args$)")


def nine_rows():
    rows = json.loads((CT / "scan3_20261119/tables/df2908090cda.json").read_text(encoding="utf-8"))["rows"]
    ez = json.loads((CT / "effzero_20261120/cur/effzero.json").read_text(encoding="utf-8"))["cands"]
    allr = [dict(r, engine=r.get("engine")) for r in rows] + [dict(r, engine="EZ") for r in ez if isinstance(r, dict)]
    hits = [r for r in allr if OBJ_FILES.match(str(r.get("file", ""))) and OBJ_FUNCS.search(str(r.get("func", "")))]
    return len(rows), len(ez), hits


def basic_rows():
    inv = json.loads((CT / "pgassert_20261121/inventory.json").read_text(encoding="utf-8"))
    pat = re.compile(r"swp|swap|softleaf|migration_entry")
    return len(inv["assertions"]), [a for a in inv["assertions"] if pat.search(a["expr"]) or any(pat.search(h) for h in a.get("helpers", []))]


def table():
    check_frozen()
    sym = {b: json.loads((CT / f"swapsym_20261121/sym_{b}.json").read_text(encoding="utf-8")) for b in BUILDS}
    pfn = {b: json.loads((CT / f"pfnswap_20261121/pfn_{b}.json").read_text(encoding="utf-8")) for b in BUILDS}
    nat = {b: json.loads((HERE / f"native_{b}.json").read_text(encoding="utf-8")) for b in BUILDS}
    cells = []
    for b in BUILDS:
        s, p, n = sym[b], pfn[b], nat[b].get("native", {})
        ob = s["obligations"]
        nv = {k: n.get(k) for k in n}
        # ordinary PTE swap entries
        native_ord = {"O1": nv.get("N_pte_isswap"), "O2": nv.get("N_excl_clear"), "O3": nv.get("N_roundtrip")}
        for k in ("O1", "O2", "O3"):
            cells.append({"build": b, "family": "普通交换项", "type": "-", "prop": k, "ours_full": ob[k]["status"],
                          "native_vec": None if native_ord[k] is None else ("通过" if native_ord[k] == 1 else "报错"),
                          "native_note": {"O1": "softleaf_is_swap", "O2": "仅独占位（exclusive_tests）", "O3": "memcmp（exclusive_tests）"}[k],
                          "round": "三" if b in ROUND3 else "四"})
        for tn, v in (p.get("A") or {}).items():
            for k in ("P1", "P2", "P3"):
                cells.append({"build": b, "family": "PFN 交换项", "type": tn, "prop": k, "ours_full": v[k], "native_vec": None,
                              "native_note": "swap_migration_tests 只在公共格式上检查，不经过架构编码", "round": "五"})
        if p.get("B"):
            for k in ("O1", "O2", "O3"):
                cells.append({"build": b, "family": "PMD 交换项", "type": "-", "prop": k, "ours_full": p["B"][k], "native_vec": None,
                              "native_note": "原生 PMD 测试的输入是迁移项，不是普通交换项（单列在 native_only）", "round": "五"})
    sd = json.loads((HERE / "sd_probe.json").read_text())
    native_only = []
    for b in BUILDS:
        n = nat[b].get("native", {})
        if n.get("N_pmd_valid") is not None:
            native_only.append({"build": b, "test": "pmd_softleaf_tests: pmd_is_valid_softleaf(softleaf_to_pmd(make_writable_migration_entry(~0UL)))",
                                "result": "通过" if n["N_pmd_valid"] == 1 else "报错（WARN）", "pmd_bytes": n.get("N_pmd_bytes")})
        native_only.append({"build": b, "test": "pte_swap_soft_dirty_tests", "result": "不运行（pgtable_supports_soft_dirty()=0）" if sd.get(b) == 0
                            else ("通过" if n.get("N_sd") == 1 else f"报错或无法折叠（{n.get('N_sd')}）")})
    nrows, nez, nine_hits = nine_rows()
    nbasic, basic_hits = basic_rows()
    out = {"cells": cells, "native_only": native_only, "nine": {"scan3_rows": nrows, "ez_rows": nez, "object_hits": nine_hits}, "basic": {"assertions": nbasic, "hits": basic_hits},
           "native": nat}
    (HERE / "cells.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    # summary
    def cnt(pred):
        return sum(1 for c in cells if pred(c))
    r3 = [c for c in cells if c["round"] == "三"]
    summ = {
        "cells_total": len(cells), "cells_round3": len(r3),
        "ours_adjudicated": cnt(lambda c: c["ours_full"] in ("成立", "违反")), "ours_unsupported": cnt(lambda c: c["ours_full"] not in ("成立", "违反")),
        "ours_violations": cnt(lambda c: c["ours_full"] == "违反"),
        "native_adjudicated_vec": cnt(lambda c: c["native_vec"] is not None), "native_reports": cnt(lambda c: c["native_vec"] == "报错"),
        "round3_ours": sum(1 for c in r3 if c["ours_full"] in ("成立", "违反")), "round3_native": sum(1 for c in r3 if c["native_vec"] is not None),
        "nine_object_hits": len(nine_hits), "basic_hits": len(basic_hits),
        "native_only_reports": [x for x in native_only if x["result"].startswith("报错")],
    }
    (HERE / "summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summ, ensure_ascii=False, indent=1), encoding="utf-8")
    for h in nine_hits:
        print("nine object hit:", h.get("engine"), h.get("file"), h.get("line"), h.get("func"), h.get("sig"))
    for b in BUILDS:
        print(b, json.dumps(nat[b].get("native", nat[b].get("error")), ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    {"native": native, "table": table}[sys.argv[1]]()
