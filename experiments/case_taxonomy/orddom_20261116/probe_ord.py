"""orddom criteria 二: constant table over arch x page-size combos (LLVM IR constant folding). WSL.
    python3 probe_ord.py -> consts.json, consts.md"""
import json
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = "/root/work/kbuild/pristine/df2908090cda"
W = Path("/root/work/encprobe")
COMBOS = {  # name -> (build dir, ARCH)
    "x86_64-4k": ("x86_64", "x86_64"), "riscv-4k": ("riscv", "riscv"), "s390-4k": ("s390", "s390"), "arm-4k": ("arm", "arm"),
    "arm64-4k": ("arm64", "arm64"), "arm64-16k": ("arm64_16k", "arm64"), "arm64-64k": ("arm64_64k", "arm64"),
    "loongarch-4k": ("loongarch_4k", "loongarch"), "loongarch-16k": ("loongarch", "loongarch"), "loongarch-64k": ("loongarch_64k", "loongarch"),
    "powerpc-4k": ("powerpc_4k", "powerpc"), "powerpc-64k": ("powerpc", "powerpc"),
    "mips-4k": ("mips", "mips"), "mips-16k": ("mips_16k", "mips"), "mips-64k": ("mips_64k", "mips"),
}
CONSTS = ["PAGE_SHIFT", "PMD_ORDER", "PUD_ORDER", "HPAGE_PMD_ORDER", "MAX_PAGECACHE_ORDER", "MAX_XAS_ORDER", "XA_CHUNK_SHIFT",
          "MAX_PAGE_ORDER"]
INC = ["#include <linux/mm.h>", "#include <linux/pgtable.h>", "#include <linux/huge_mm.h>", "#include <linux/pagemap.h>",
       "#include <linux/xarray.h>", "#include <linux/mmzone.h>"]


def run_combo(name):
    bdir, arch = COMBOS[name]
    m = W / f"ord_{name}"
    shutil.rmtree(m, ignore_errors=True)
    m.mkdir(parents=True)
    for c in CONSTS:
        (m / f"c_{c}.c").write_text("\n".join(INC + [f"int probe__x(void) {{ return (int)({c}); }}"]) + "\n")
    names = [f"c_{c}" for c in CONSTS]
    (m / "Kbuild").write_text("obj-m := " + " ".join(f"{n}.o" for n in names) + "\nccflags-y += -Wno-missing-prototypes -Wno-error\n")
    cmd = ["make", "-C", SRC, f"O={W / bdir}", f"ARCH={arch}", "LLVM=1", f"M={m}", "-k", "-j6"] + [f"{n}.ll" for n in names]
    log = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    (m / "build.log").write_text(log.stdout + log.stderr)
    cfg = (W / bdir / ".config").read_text(errors="replace")
    out = {"thp": "CONFIG_TRANSPARENT_HUGEPAGE=y" in cfg}
    for c in CONSTS:
        ll = m / f"c_{c}.ll"
        if not ll.exists():
            out[c] = "unavailable"
            continue
        fm = re.search(r"define [^@]*@probe__x\(\)[^{]*\{\n(.*?)\n\}", ll.read_text(errors="replace"), re.S)
        body = [l.strip() for l in (fm.group(1).split("\n") if fm else []) if l.strip()
                and not l.strip().endswith(":") and not re.match(r"(tail )?call void @(llvm\.dbg\.\w+|_mcount|__fentry__|mcount)\(", l.strip())]
        mm = re.fullmatch(r"ret i32 (-?\d+)(, !dbg !\d+)?", body[-1]) if body else None
        out[c] = int(mm.group(1)) if (mm and len(body) == 1) else "unknown"
    return name, out


def main():
    res = {}
    with ThreadPoolExecutor(5) as ex:
        for name, out in ex.map(run_combo, COMBOS):
            res[name] = out
            print(name, out, flush=True)
    (HERE / "consts.json").write_text(json.dumps(res, indent=1))
    L = ["| 组合 | THP | " + " | ".join(CONSTS) + " |", "|---|---|" + "---|" * len(CONSTS)]
    for n, o in res.items():
        L.append(f"| {n} | {'y' if o['thp'] else 'n'} | " + " | ".join(str(o[c]) for c in CONSTS) + " |")
    (HERE / "consts.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
