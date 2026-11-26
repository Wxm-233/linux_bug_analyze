"""bres criteria 一: relative layering = layer_r.py (round-9 layer_n.py with the classification/label sections changed) on the
five builds. Reads /root/work/layerbound5 (line maps, config symbols) through links in /root/work/bres. WSL.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
WB = Path("/root/work/bres")
L5 = Path("/root/work/layerbound5")
WB.mkdir(exist_ok=True)
for b in ("riscv", "arm64", "x86_64", "arm", "powerpc"):
    for n in (f"lines_{b}.pkl.gz", f"cc_{b}.json"):
        if not (WB / n).exists():
            os.symlink(L5 / n, WB / n)
if not (WB / "config_symbols.json").exists():
    os.symlink(L5 / "config_symbols.json", WB / "config_symbols.json")
import layer_r as Lm  # noqa: E402
Lm.W, Lm.HERE, Lm.BUILDS = WB, HERE / "layer_r_out", ("riscv", "arm64", "x86_64", "arm", "powerpc")
Lm.HERE.mkdir(exist_ok=True)
Lm.main()
