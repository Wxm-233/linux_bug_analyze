"""encrank criteria 二: generate probes, compile to LLVM IR with each arch's kernel flags, read constant results. WSL.

    python3 probe.py          -> encoding.json
"""
import json
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = "/root/work/kbuild/pristine/df2908090cda"
W = Path("/root/work/encprobe")
ARCHS = {"x86_64": "x86_64", "arm64": "arm64", "riscv": "riscv", "loongarch": "loongarch", "powerpc": "powerpc", "s390": "s390",
         "arm": "arm", "mips": "mips"}
P = "0x12345UL"

PTE_ACC = ["write", "dirty", "young", "special", "exec", "soft_dirty", "uffd", "protnone", "pfn", "present", "none", "MKOLD"]
PMD_ACC = ["leaf", "write", "dirty", "young", "special", "soft_dirty", "uffd", "protnone", "pfn", "trans_huge", "present", "MKOLD"]
PTE_KINDS = {
    "swap": ("1", f"swp_entry_to_pte(swp_entry(0, {P}))"),
    "mig_r": ("IS_ENABLED(CONFIG_MIGRATION)", f"swp_entry_to_pte(make_readable_migration_entry({P}))"),
    "mig_re": ("IS_ENABLED(CONFIG_MIGRATION)", f"swp_entry_to_pte(make_readable_exclusive_migration_entry({P}))"),
    "mig_w": ("IS_ENABLED(CONFIG_MIGRATION)", f"swp_entry_to_pte(make_writable_migration_entry({P}))"),
    "dp_r": ("IS_ENABLED(CONFIG_DEVICE_PRIVATE)", f"swp_entry_to_pte(make_readable_device_private_entry({P}))"),
    "dp_w": ("IS_ENABLED(CONFIG_DEVICE_PRIVATE)", f"swp_entry_to_pte(make_writable_device_private_entry({P}))"),
    "dexcl": ("IS_ENABLED(CONFIG_DEVICE_PRIVATE)", f"swp_entry_to_pte(make_device_exclusive_entry({P}))"),
    "marker": ("1", "make_pte_marker(PTE_MARKER_UFFD_WP)"),
}
PMD_KINDS = {k: (c, e.replace("swp_entry_to_pte", "swp_entry_to_pmd")) for k, (c, e) in PTE_KINDS.items() if k.startswith(("mig", "dp"))}
PTE_MODS = {"plain": "", "sd": "pte_swp_mksoft_dirty", "ex": "pte_swp_mkexclusive", "uf": "pte_swp_mkuffd"}
PMD_MODS = {"plain": "", "sd": "pmd_swp_mksoft_dirty", "uf": "pmd_swp_mkuffd"}
HAS_PFN = {"mig_r", "mig_re", "mig_w", "dp_r", "dp_w", "dexcl"}


def test_expr(level, acc, kind):
    if acc == "MKOLD":
        return f"({level}_val({level}_mkold(e)) != {level}_val(e))"
    if acc == "pfn":
        return f"({level}_pfn(e) == {P})" if kind in HAS_PFN else None
    return f"!!{level}_{acc}(e)"


def gen(level, acc, mod):
    kinds = PTE_KINDS if level == "pte" else PMD_KINDS
    mfun = (PTE_MODS if level == "pte" else PMD_MODS)[mod]
    lines = ["#include <linux/mm.h>", "#include <linux/swapops.h>", "#include <linux/pgtable.h>"]
    if level == "pmd":
        lines.append("#ifdef CONFIG_ARCH_HAS_PMD_SOFTLEAVES")
    n = 0
    for k, (cond, cons) in kinds.items():
        te = test_expr(level, acc, k)
        if te is None:
            continue
        built = f"{mfun}({cons})" if mfun else cons
        lines += [f"#if {cond}", f"int probe__{k}(void) {{ {level}_t e = {built}; return {te}; }}", "#endif"]
        n += 1
    if level == "pmd":
        lines.append("#endif")
    return "\n".join(lines) + "\n", n


def run_arch(arch):
    o = W / arch
    m = W / f"mod_{arch}"
    shutil.rmtree(m, ignore_errors=True)
    m.mkdir(parents=True)
    names = []
    for level, accs, mods in (("pte", PTE_ACC, PTE_MODS), ("pmd", PMD_ACC, PMD_MODS)):
        for acc in accs:
            for mod in mods:
                src, n = gen(level, acc, mod)
                if not n:
                    continue
                name = f"{level}__{acc}__{mod}"
                (m / f"{name}.c").write_text(src)
                names.append(name)
    (m / "Kbuild").write_text("obj-m := " + " ".join(f"{n}.o" for n in names) + "\nccflags-y += -Wno-missing-prototypes -Wno-error\n")
    cmd = ["make", "-C", SRC, f"O={o}", f"ARCH={ARCHS[arch]}", "LLVM=1", f"M={m}", "-k", "-j6"] + [f"{n}.ll" for n in names]
    log = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    (m / "build.log").write_text(log.stdout + log.stderr)
    res = {}
    for n in names:
        level, acc, mod = n.split("__")
        ll = m / f"{n}.ll"
        cell = res.setdefault(level, {}).setdefault(acc, {})
        if not ll.exists():
            cell[mod] = "unavailable"
            continue
        txt = ll.read_text(errors="replace")
        got = {}
        for fm in re.finditer(r"define [^@]*@probe__(\w+)\(\)[^{]*\{\n(.*?)\n\}", txt, re.S):
            # ignore debug-info intrinsics and tracing hooks (arm64 debug info, powerpc/s390 mcount/fentry)
            body = [l.strip() for l in fm.group(2).split("\n") if l.strip()
                    and not re.match(r"(tail )?call void @(llvm\.dbg\.\w+|_mcount|__fentry__|mcount)\(", l.strip())]
            mm = re.fullmatch(r"ret i32 (\d+)(, !dbg !\d+)?", body[-1]) if body else None
            got[fm.group(1)] = int(mm.group(1)) if (mm and len(body) == 2) else "unknown"
        cell[mod] = got
    return arch, res, sum(1 for n in names if not (m / f"{n}.ll").exists()), len(names)


def main():
    out = {}
    with ThreadPoolExecutor(4) as ex:
        for arch, res, fails, total in ex.map(run_arch, ARCHS):
            out[arch] = res
            print(arch, "files", total, "unavailable", fails, flush=True)
    (HERE / "encoding.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
