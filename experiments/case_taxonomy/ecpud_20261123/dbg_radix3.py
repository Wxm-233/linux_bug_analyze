"""ecpud debug 3: preprocessed text of radix_enabled / mmu_has_feature on a build, and sub-results under the trial guard."""
import re, shlex, subprocess, sys
from pathlib import Path
sys.setrecursionlimit(100000)
import ec7
ec7.patch()
import ec4
ec4.setup("dbg", ec7.DF)
import mine as M
S, E = M.S, M.E
I = S.I
b = sys.argv[1]
p = Path(f"/root/work/autoenc/dbg_{b}.c")
cc = I.ccdb(I.BUILDS[b])[I.UNIT]
args = shlex.split(cc["command"])
base, skip = [], False
for a in args:
    if skip: skip = False; continue
    if a == "-o": skip = True; continue
    if a == "-c" or a.startswith("-Wp,-MMD") or a.endswith("mm/memory.c"): continue
    base.append(a)
txt = subprocess.run(base + ["-E", "-P", str(p)], cwd=cc["directory"], capture_output=True, text=True).stdout
for fn in ("bool mmu_has_feature", "bool early_mmu_has_feature", "bool radix_enabled"):
    i = txt.find(fn)
    print("----", fn, "\n", re.sub(r"\s+", " ", txt[i:i + 900]) if i >= 0 else "not found")
funcs = M.load(b, p)
it = M.AInterp(funcs, E.LONGW[b], {})
it.build = b; it.oracle = {}; it._pred_guard = {"x"}
for nm, a in (("early_mmu_has_feature", [S.SBV(64, 0x40)]), ("mmu_has_feature", [S.SBV(64, 0x40)])):
    try:
        v = S.unwrap(it.call(nm, a)); print(nm, "->", v.const(), it.notes[-5:])
    except Exception as ex:
        print(nm, "raised", ex)
