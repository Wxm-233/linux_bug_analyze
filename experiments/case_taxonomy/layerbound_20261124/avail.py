"""layerbound criteria 三.1 + G1 (config part): arch-related vs common config symbols from three allyesconfigs. WSL."""
import json, re
from pathlib import Path
W = Path("/root/work/layerbound")
HERE = Path(__file__).resolve().parent
ARCHS = ("riscv", "arm64", "x86_64")
avail = {}
for a in ARCHS:
    s = set()
    for l in (W / f"avail_{a}" / ".config").read_text().splitlines():
        m = re.match(r"(?:# )?CONFIG_(\w+)(?:=| is not set)", l)
        if m:
            s.add(m.group(1))
    avail[a] = s
allsym = set().union(*avail.values())
arch_rel = {x: sorted(a for a in ARCHS if x in avail[a]) for x in allsym if sum(x in avail[a] for a in ARCHS) < 3}
common = sorted(x for x in allsym if x not in arch_rel)
json.dump({"arch_related": arch_rel, "common": common}, open(W / "config_symbols.json", "w"))
print("symbols", len(allsym), "arch-related", len(arch_rel), "common", len(common))
exp = {"RISCV_ISA_SVNAPOT": True, "ARM64_64K_PAGES": True, "HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD": True, "ARCH_SUPPORTS_PUD_PFNMAP": True,
       "TRANSPARENT_HUGEPAGE": False, "SWAP": False, "SMP": False, "MMU": False}
ok = 0
res = {}
for k, v in exp.items():
    got = k in arch_rel
    res[k] = {"expected_arch": v, "got_arch": got, "archs": arch_rel.get(k, "all three" if k in allsym else "none")}
    ok += got == v
    print(f"  {k:40s} expected {'arch' if v else 'common'} got {'arch' if got else ('common' if k in allsym else 'absent')} {arch_rel.get(k, '')}")
print("G1 config", ok, "/", len(exp))
json.dump(res, open(HERE / "g1_config.json", "w"), indent=1)
