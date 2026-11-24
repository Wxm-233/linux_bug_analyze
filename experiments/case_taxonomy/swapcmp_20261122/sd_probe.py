"""swapcmp: is pte_swap_soft_dirty_tests active on each build? (clang-folded pgtable_supports_soft_dirty()). WSL."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "swapsym_20261121"))
import swaparch as A
S = A.S
B = ["riscv64", "rv32_abi", "x86_64", "i386", "i386_pae", "arm64", "ppc64le", "ppc64le_hash", "ppc64e", "ppc32s", "ppc44x", "ppc8xx",
     "s390", "loongarch", "mips32", "mips32xpa", "mips64", "arm", "arm_lpae", "hexagon"]
src = "#include <linux/mm.h>\n#include <linux/pgtable.h>\nunsigned long SD_supp(void) { return pgtable_supports_soft_dirty(); }\n"
out = {}
for b in B:
    if b in A.ARCHES or b == "ppc64le_hash":
        A.register(b)
    try:
        out[b] = S.clang_consts(b, src, ["SD_supp"])["SD_supp"]
    except Exception as ex:
        out[b] = "error: " + str(ex)[:200]
    print(b, out[b], flush=True)
(HERE / "sd_probe.json").write_text(json.dumps(out, indent=1))
