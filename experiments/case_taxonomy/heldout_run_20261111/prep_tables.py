"""Syscall-number and per-revision syscall tables for LoongArch (criteria 三.4). Runs in WSL (reads git objects only).

    python3 prep_tables.py [<group> <parent> <fix>]...   -> data/nr_tables.json, data/version_tables.json,
                                                             data/kernel_keys.json
Revisions are commit ids; nothing but the syscall table files is read from them.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "twostage_dev_20261109"))
import version_tables as VT  # noqa: E402  (show / generic / x86 helpers, read-only reuse)

CUR = "df2908090cda"
ABIS_LA = {"common", "64", "memfd_secret"}  # arch/loongarch/kernel/Makefile.syscalls
ABIS_ARM64 = {"common", "64", "rlimit", "memfd_secret", "renameat", "stat64"}  # as in version_tables.py


def la_numbers(rev):
    out = {}
    for line in (VT.show(rev, "scripts/syscall.tbl") or "").splitlines():
        f = line.split()
        if len(f) >= 3 and not line.startswith("#") and f[1] in ABIS_LA:
            out[f[2]] = int(f[0])
    return out


def main():
    d = HERE / "data"
    d.mkdir(exist_ok=True)
    old_nr = json.loads((CT / "diverse_dev_20261110/gen/nr_tables.json").read_text())
    la = la_numbers(CUR)
    shared = [n for n in la if n in old_nr["riscv"]]
    diff = [n for n in shared if la[n] != old_nr["riscv"][n]]
    print("loongarch syscalls", len(la), "shared with riscv", len(shared), "numbers differing", diff[:10])
    nr = {"loongarch": la, "arm64": old_nr["arm64"], "x86_64": old_nr["x86_64"]}
    (d / "nr_tables.json").write_text(json.dumps(nr, indent=0))
    vtp = d / "version_tables.json"
    vt = json.loads(vtp.read_text()) if vtp.exists() else \
        json.loads((CT / "twostage_dev_20261109/version_tables.json").read_text())
    kkp = d / "kernel_keys.json"
    kk = json.loads(kkp.read_text()) if kkp.exists() else {}
    vt["cur_loongarch"] = sorted(VT.generic(CUR, ABIS_LA))
    a = sys.argv[1:]
    for i in range(0, len(a), 3):
        g, parent, fix = a[i:i + 3]
        p = g.lower()
        vt[f"{p}_pre"] = sorted(VT.generic(parent, ABIS_LA))
        vt[f"{p}_fix"] = sorted(VT.generic(fix, ABIS_LA))
        vt[f"{p}_ref_arm64"] = sorted(VT.generic(parent, ABIS_ARM64))
        vt[f"{p}_ref_x86_64"] = sorted(VT.x86(parent))
        kk[g] = [f"{p}_pre", f"{p}_fix", f"{p}_ref_arm64", f"{p}_ref_x86_64"]
        print(g, {k: len(vt[k]) for k in kk[g]})
    vtp.write_text(json.dumps(vt, indent=0))
    kkp.write_text(json.dumps(kk, indent=1))
    print("cur_loongarch", len(vt["cur_loongarch"]))


if __name__ == "__main__":
    main()
