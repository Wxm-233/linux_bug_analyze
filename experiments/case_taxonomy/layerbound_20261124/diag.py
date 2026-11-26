import gzip, json, re
from collections import Counter
E = json.load(gzip.open("/root/work/layerbound/funcs.json.gz", "rt"))
lab = Counter(e["label"] for e in E); print(lab)
un = [e for e in E if e["label"] == "未归因"]
print("unattr kinds", Counter(tuple(sorted({d[0].split(":")[0] for d in e["diffs"] if d[1] == "unattr"})) for e in un).most_common(5))
print("unattr top files", Counter(e["file"].split("/")[0] + "/" + e["file"].split("/")[1] for e in un).most_common(8))
print("unattr cond samples", Counter(d[0] for e in un for d in e["diffs"] if d[1] == "unattr" and d[0] != "file").most_common(12))
for a in ("riscv", "arm64", "x86_64"):
    c = open(f"/root/work/boundary_build/{a}_defconfig/.config").read()
    print(a, {k: bool(re.search(rf"^CONFIG_{k}=y", c, re.M)) for k in ("TRANSPARENT_HUGEPAGE", "LRU_GEN", "PNP", "NUMA", "HUGETLBFS", "RISCV_ISA_SVNAPOT", "PERF_EVENTS")})
for n in ("quirk_amd_mmconfig_area", "perf_get_pgtable_size", "pnp_fixup_device"):
    print(n, [(e["file"], e["label"], e["builds"], e["diffs"][:2]) for e in E if e["name"] == n])
