import json
SM = "/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/sample_match_v2.json"
cmp = {r["id"]: r for r in json.load(open("/root/work/archbound/kernel/sample_compare.json"))}
common = ("kernel/", "mm/", "lib/", "init/", "drivers/irqchip/", "drivers/perf/", "drivers/acpi/", "drivers/clocksource/",
          "drivers/iommu/", "drivers/cpuidle/", "drivers/firmware/", "arch/riscv/", "arch/x86/", "include/")
n_in = hit_in = ab_in = 0; out_ids = []
for s in json.load(open(SM))["samples"]:
    files = [e.get("current_file") or "" for e in s.get("resolved_entities") or []]
    inside = bool(files) and any(f.startswith(common) for f in files)
    if s["hit"] and not inside: out_ids.append(s["id"])
    if inside:
        n_in += 1; hit_in += s["hit"]; ab_in += cmp[s["id"]]["archbound_hit"]
print("samples with an entity inside archbound scope:", n_in, " ours hit:", hit_in, " archbound hit:", ab_in)
print("ours-hit samples entirely outside scope:", len(out_ids), out_ids)
