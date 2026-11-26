"""covgap criteria 二 K1 (copy of bres g1.py: work dir, two new cases). bres criteria 三 G1: relative layering calibration (over compiled definitions) + two restored boundary edges"""
import gzip, json, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
E = json.load(gzip.open("/root/work/covgap/funcs.json.gz", "rt"))
ED = json.load(gzip.open("/root/work/covgap/edges.json.gz", "rt"))
B5 = {"riscv", "arm64", "x86_64", "arm", "powerpc"}
A = ("架构层A0", "架构层A1")
def defs(f, pat):
    return [e for e in E if e["file"] == f and re.fullmatch(pat, e["name"]) and e["builds"]]
cases = [("arch/riscv/mm/pgtable.c", "pudp_invalidate", lambda ds: all(d["label"] == "架构层A0" for d in ds)),
         ("arch/x86/kernel/amd_nb.c", "amd_get_mmconfig_range", lambda ds: all(d["label"] == "架构层A0" for d in ds)),
         ("include/linux/pgtable.h", "ptep_get", lambda ds: all(d["label"] == "架构层A1" for d in ds)),
         ("mm/huge_memory.c", "change_huge_pud", lambda ds: all(d["label"] == "公共层（部分架构）" for d in ds)),
         ("mm/mprotect.c", "change_pud_range", lambda ds: all(d["label"] == "公共层" for d in ds)),
         ("mm/memory.c", "zap_pud_range", lambda ds: all(d["label"] == "公共层" for d in ds)),
         ("mm/memory.c", "insert_page_into_pte_locked", lambda ds: all(d["label"] == "公共层" for d in ds)),
         ("fs/proc/task_mmu.c", "smaps_pmd_entry", lambda ds: all(d["label"] in ("公共层", "公共层-配置差异") for d in ds)),
         ("mm/secretmem.c", "secretmem_init", lambda ds: all(d["label"] == "公共层（部分架构）" for d in ds)),
         ("mm/migrate.c", "do_pages_move", lambda ds: all(d["label"] == "公共层（部分架构）" for d in ds)),
         ("arch/powerpc/include/asm/hugetlb.h", "hugepages_supported", lambda ds: all(d["label"] in A for d in ds)),
         ("arch/arm/include/asm/pgtable-3level.h", "pmd_mkinvalid", lambda ds: all(d["label"] in A for d in ds)),
         ("arch/arm/include/asm/pgtable.h", r"pte_swp_\w+", lambda ds: all(d["label"] in A for d in ds)),
         ("mm/zswap.c", "zswap_decompress", lambda ds: all(set(d["builds"]) == B5 for d in ds)),
         ("mm/kasan/hw_tags.c", "__kasan_unpoison_vmalloc", lambda ds: all(d["builds"] == ["arm64"] for d in ds)),
         ("include/linux/highmem-internal.h", "kmap_local_page", lambda ds: any("arm" in d["builds"] for d in ds)),
         # covgap criteria 二 K1: two new cases
         ("mm/rmap.c", "try_to_migrate_one", lambda ds: all(d["label"] == "公共层（体内架构配置）" for d in ds)),
         ("include/linux/pgtable.h", "ptep_get", lambda ds: all(d["label"] == "架构层A1" for d in ds))]
rows, ok = [], 0
for f, pat, pred in cases:
    ds = defs(f, pat)
    good = bool(ds) and bool(pred(ds))
    ok += good
    rows.append({"case": f"{f} {pat}", "got": [(d["name"], d["label"], d["builds"]) for d in ds][:4], "ok": good})
    print("G1", "OK " if good else "BAD", f, pat, [(d["label"], d["builds"]) for d in ds][:2])
def edge(f, n, callee):
    ids = {i for i, e in enumerate(E) if e["file"] == f and e["name"] == n}
    return sorted({b for kind in ("direct", "macro") for a, c, b in ED[kind] if a in ids and E[c]["name"] == callee})
e1, e2 = edge("mm/secretmem.c", "secretmem_init", "can_set_direct_map"), edge("mm/migrate.c", "do_pages_move", "get_user")
print("edge secretmem_init->can_set_direct_map", e1, "| do_pages_move->get_user", e2)
lab = {}
for e in E:
    lab[e["label"]] = lab.get(e["label"], 0) + 1
res = {"pass": ok == len(cases) and bool(e1) and bool(e2), "ok": ok, "n": len(cases), "rows": rows,
       "edges": {"secretmem_init->can_set_direct_map": e1, "do_pages_move->get_user": e2}, "labels": lab}
json.dump(res, open(HERE / "g1.json", "w"), ensure_ascii=False, indent=1)
print("G1", ok, "/", len(cases), "PASS" if res["pass"] else "FAIL", lab)
