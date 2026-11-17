"""C units of a build inside the scope of criteria section 2 (plus optional extra directories), one path per line.

    python3 scope_list.py <compile_commands.json> <arch dir name> <out.txt> [extra_dir/ ...]
"""
import json, os, sys
cdb, arch, out, extra = sys.argv[1], sys.argv[2], sys.argv[3], tuple(sys.argv[4:])
common = ("kernel/", "mm/", "lib/", "init/", "drivers/irqchip/", "drivers/perf/", "drivers/acpi/", "drivers/clocksource/",
          "drivers/iommu/", "drivers/cpuidle/", "drivers/firmware/")
rows = json.load(open(cdb))
src_root = os.environ.get("KROOT", "/root/repos/linux").rstrip("/") + "/"
files = set()
for r in rows:
    f = os.path.normpath(os.path.join(r["directory"], r["file"]))
    if not f.startswith(src_root) or not f.endswith(".c"):
        continue
    rel = f[len(src_root):]
    if rel.startswith(f"arch/{arch}/") or rel.startswith(common) or (extra and rel.startswith(extra)):
        files.add(f)
open(out, "w").write("\n".join(sorted(files)) + "\n")
print(arch, len(files), "units in scope")
