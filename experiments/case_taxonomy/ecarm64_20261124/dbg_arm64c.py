"""ecarm64 debug 3: __phys_to_pud_val / the PTE address mask on a symbolic phys, for several pfn widths; where do the low bits come from."""
import json, sys, shlex, subprocess, re
from pathlib import Path
sys.setrecursionlimit(100000)
CT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CT / "ecunreach_20261123"))
import ec9
ec9.patch()
import ec4
rev = sys.argv[1] if len(sys.argv) > 1 else "4dd7724f02ab"
ec4.setup("dbg", rev)
import mine as M
S, E = M.S, M.E
I = S.I
b = "arm64"
p = Path(f"/root/work/autoenc/dbgc_{rev}.c")
p.write_text(M.HDR + M.CONSTS + """
static __attribute__((used)) unsigned long AE_mask(void) { return PHYS_TO_PTE_ADDR_MASK; }
static __attribute__((used)) unsigned long AE_conv(unsigned long phys) { return __phys_to_pte_val(phys); }
static __attribute__((used)) unsigned long AE_pud(unsigned long pfn) { return pud_val(pfn_pud(pfn, PAGE_NONE)); }
""")
funcs = M.load(b, p)
cx = M.Ctx(funcs, b)
for nb in (30, 34, 40):
    S.DOM.update(tmax=None, ofree=nb, omin=0)
    pf = M.lit("o", nb, 64, 18)
    for w, a in (("AE_mask", []), ("AE_conv", [M.lit("o", nb, 64, 30)]), ("AE_pud", [pf])):
        it = M.AInterp(funcs, 64, {}); it.build = b; it.oracle = {}
        v = S.unwrap(it.call(w, a))
        c = v.const()
        print(nb, w, hex(c) if c is not None else repr(v)[:230], it.notes[:2])
# the preprocessed text of the mask and the conversion
cc = I.ccdb(I.BUILDS[b])[I.UNIT]
args = shlex.split(cc["command"]); base, skip = [], False
for a in args:
    if skip: skip = False; continue
    if a == "-o": skip = True; continue
    if a == "-c" or a.startswith("-Wp,-MMD") or a.endswith("mm/memory.c"): continue
    base.append(a)
txt = subprocess.run(base + ["-E", "-P", str(p)], cwd=cc["directory"], capture_output=True, text=True).stdout
i = txt.find("AE_mask(void)"); print(re.sub(r"\s+", " ", txt[i:i + 700]))
i = txt.find("__phys_to_pte_val(phys_addr_t phys)"); print(re.sub(r"\s+", " ", txt[i:i + 500]))
