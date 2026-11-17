# Claude 2026-11-08: C units of a build inside the checks_v1 scope (criteria section 2), with arch/<arch>/ for the build's arch.
import json, os, sys
cdb, arch, out = sys.argv[1], sys.argv[2], sys.argv[3]
root = "/root/repos/linux/"
common = ("kernel/", "mm/", "lib/", "init/", "drivers/irqchip/", "drivers/perf/", "drivers/acpi/", "drivers/clocksource/",
          "drivers/iommu/", "drivers/cpuidle/", "drivers/firmware/")
files = set()
for r in json.load(open(cdb)):
    f = os.path.normpath(os.path.join(r["directory"], r["file"]))
    if not f.startswith(root) or not f.endswith(".c"):
        continue
    rel = f[len(root):]
    if rel.startswith(f"arch/{arch}/") or rel.startswith(common):
        files.add(f)
open(out, "w").write("\n".join(sorted(files)) + "\n")
print(arch, len(files))
