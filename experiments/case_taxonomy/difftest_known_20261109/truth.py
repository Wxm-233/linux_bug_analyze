"""Mechanical ground truth and host-side kernel configuration (criteria sections 5 P4 and 7). Runs in WSL.

    python3 truth.py   -> truth.json

Bug X is present in kernel T iff X's introducing commit is an ancestor of T's revision and X's fix is not.
"""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
KSRC = "/root/repos/linux"
BB = "/root/work/boundary_build"
DB = "/root/work/difftest/build"
CUR = "df2908090cda"

KERNELS = {
    "cur_riscv": ("riscv", CUR, f"{BB}/riscv_defconfig/.config"),
    "cur_arm64": ("arm64", CUR, f"{BB}/arm64_defconfig/.config"),
    "cur_x86_64": ("x86_64", CUR, f"{BB}/x86_64_defconfig/.config"),
}
FIXES = {"A101": "2116988d5372", "A310": "61119394631f", "A171": "890ba5be6335", "A181": "1046791390af",
         "B467": "c625154993d0"}
for sid, c in FIXES.items():
    KERNELS[f"{sid.lower()}_pre"] = ("riscv", f"{c}^", f"{DB}/{sid}_pre/.config")
    KERNELS[f"{sid.lower()}_fix"] = ("riscv", c, f"{DB}/{sid}_fix/.config")

# introducing commit of the symptom code (criteria section 7). B467: the riscv perf drivers' first commits,
# older than every tree under test; represented by the oldest of the Fixes tags.
INTRO = {"A101": "b5b4287accd7", "A310": "52449c17bdd1", "A171": "ad5643cf2f69", "A181": "ca1a66cdd685",
         "B467": "9b3e150e310e"}

CONFIG_KEYS = ["RISCV_PMU_SBI", "RISCV_PMU_LEGACY", "ARM_PMUV3", "HW_PERF_EVENTS", "CPU_SUP_INTEL", "CPU_SUP_AMD",
               "HAVE_HW_BREAKPOINT", "PERF_EVENTS", "HAVE_EFFICIENT_UNALIGNED_ACCESS"]


def is_ancestor(a, b):
    return subprocess.run(["git", "-C", KSRC, "merge-base", "--is-ancestor", a, b]).returncode == 0


def rev_parse(r):
    return subprocess.run(["git", "-C", KSRC, "rev-parse", "--short=12", r], capture_output=True, text=True,
                          check=True).stdout.strip()


def config(path):
    vals = {}
    p = Path(path)
    if not p.exists():
        return None
    for line in p.read_text().splitlines():
        if line.startswith("CONFIG_"):
            k, _, v = line[7:].partition("=")
            if k in CONFIG_KEYS:
                vals[k] = v
    return {k: vals.get(k, "n") for k in CONFIG_KEYS}


def main():
    out = {"kernels": {}, "intro": INTRO, "fixes": FIXES, "present": {}}
    for name, (arch, rev, cfg) in KERNELS.items():
        out["kernels"][name] = {"arch": arch, "rev": rev, "commit": rev_parse(rev), "config": config(cfg)}
        if arch != "riscv":
            continue
        out["present"][name] = sorted(sid for sid in FIXES
                                      if is_ancestor(INTRO[sid], rev) and not is_ancestor(FIXES[sid], rev))
    (HERE / "truth.json").write_text(json.dumps(out, indent=1))
    for k, v in out["present"].items():
        print(k, out["kernels"][k]["commit"], v)


if __name__ == "__main__":
    main()
