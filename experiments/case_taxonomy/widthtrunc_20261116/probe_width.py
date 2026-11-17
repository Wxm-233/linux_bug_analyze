"""widthtrunc criteria 二: bit widths of arch-dependent types (LLVM IR constant folding). WSL.
    python3 probe_width.py -> widths.json, widths.md"""
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
    "x86_64": ("x86_64", "x86_64"), "arm64": ("arm64", "arm64"), "riscv64": ("riscv", "riscv"), "loongarch64": ("loongarch", "loongarch"),
    "powerpc64": ("powerpc", "powerpc"), "s390": ("s390", "s390"), "mips64": ("mips", "mips"),
    "arm32": ("arm", "arm"), "i386": ("i386", "x86"), "riscv32": ("riscv32", "riscv"), "mips32": ("mips32", "mips"),
}
CONSTS = ["int", "long", "unsigned long", "size_t", "ssize_t", "pgoff_t", "uintptr_t", "phys_addr_t", "dma_addr_t", "resource_size_t",
          "loff_t", "u64", "sector_t", "blkcnt_t", "time64_t", "ktime_t"]
INC = ["#include <linux/types.h>", "#include <linux/time64.h>", "#include <linux/ktime.h>", "#include <linux/fs.h>"]


def fn(c):
    return c.replace(" ", "_")


def run_combo(name):
    bdir, arch = COMBOS[name]
    m = W / f"wid_{name}"
    shutil.rmtree(m, ignore_errors=True)
    m.mkdir(parents=True)
    for c in CONSTS:
        (m / f"c_{fn(c)}.c").write_text("\n".join(INC + [f"int probe__x(void) {{ return (int)(sizeof({c}) * 8); }}"]) + "\n")
    names = [f"c_{fn(c)}" for c in CONSTS]
    (m / "Kbuild").write_text("obj-m := " + " ".join(f"{n}.o" for n in names) + "\nccflags-y += -Wno-missing-prototypes -Wno-error\n")
    cmd = ["make", "-C", SRC, f"O={W / bdir}", f"ARCH={arch}", "LLVM=1", f"M={m}", "-k", "-j6"] + [f"{n}.ll" for n in names]
    log = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    (m / "build.log").write_text(log.stdout + log.stderr)
    cfg = (W / bdir / ".config").read_text(errors="replace")
    out = {"64bit": "CONFIG_64BIT=y" in cfg}
    for c in CONSTS:
        ll = m / f"c_{fn(c)}.ll"
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
    (HERE / "widths.json").write_text(json.dumps(res, indent=1))
    L = ["| 组合 | 64BIT | " + " | ".join(CONSTS) + " |", "|---|---|" + "---|" * len(CONSTS)]
    for n, o in res.items():
        L.append(f"| {n} | {'y' if o['64bit'] else 'n'} | " + " | ".join(str(o[c]) for c in CONSTS) + " |")
    (HERE / "widths.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
