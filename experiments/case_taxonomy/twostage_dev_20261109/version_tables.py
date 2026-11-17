"""Syscall names present in each kernel's syscall table at its revision (criteria: version exclusion). Runs in WSL.

    python3 version_tables.py   -> version_tables.json  {kernel: [names]}

riscv/arm64 use the generic table: scripts/syscall.tbl in newer trees, include/uapi/asm-generic/unistd.h
(__SYSCALL(__NR_x, sys_x) lines) in older ones. x86_64 uses arch/x86/entry/syscalls/syscall_64.tbl.
"""
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
KSRC = "/root/repos/linux"
FIXES = {"A101": "2116988d5372", "A310": "61119394631f", "A171": "890ba5be6335", "A181": "1046791390af",
         "B467": "c625154993d0"}
CUR = "df2908090cda"

KERNELS = {"cur_riscv": ("riscv", CUR), "cur_arm64": ("arm64", CUR), "cur_x86_64": ("x86_64", CUR)}
for sid, c in FIXES.items():
    KERNELS[f"{sid.lower()}_pre"] = ("riscv", f"{c}^")
    KERNELS[f"{sid.lower()}_fix"] = ("riscv", c)
    KERNELS[f"{sid.lower()}_ref_arm64"] = ("arm64", c)
    KERNELS[f"{sid.lower()}_ref_x86_64"] = ("x86_64", c)


def show(rev, path):
    r = subprocess.run(["git", "-C", KSRC, "show", f"{rev}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def generic(rev, abis):
    tbl = show(rev, "scripts/syscall.tbl")
    names = set()
    if tbl is not None:
        for line in tbl.splitlines():
            f = line.split()
            if len(f) >= 3 and not line.startswith("#") and f[1] in abis:
                names.add(f[2])
        if names:
            return names
    hdr = show(rev, "include/uapi/asm-generic/unistd.h") or ""
    # older trees: __SYSCALL(__NR_name, sys_name) or __SC_COMP/__SC_3264 variants
    for m in re.finditer(r"#define __NR(?:3264)?_(\w+)\s+\d+", hdr):
        names.add(m.group(1))
    names.discard("syscalls")
    return names


def x86(rev):
    tbl = show(rev, "arch/x86/entry/syscalls/syscall_64.tbl") or ""
    return {f[2] for f in (l.split() for l in tbl.splitlines() if l and not l.startswith("#"))
            if len(f) >= 3 and f[1] in ("common", "64")}


def main():
    abis = {"riscv": {"common", "64", "riscv", "rlimit", "memfd_secret", "renameat", "time64", "stat64"},
            "arm64": {"common", "64", "rlimit", "memfd_secret", "renameat", "stat64"}}
    out = {}
    for name, (arch, rev) in KERNELS.items():
        out[name] = sorted(x86(rev) if arch == "x86_64" else generic(rev, abis[arch]))
        print(name, rev, len(out[name]))
    (HERE / "version_tables.json").write_text(json.dumps(out, indent=0))


if __name__ == "__main__":
    main()
