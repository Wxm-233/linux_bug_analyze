"""swapsym amendment 1: run swapsym.py (unchanged) on the extra architecture variants made by mkarch.sh. WSL.

    python3 swaparch.py run [names...]      -> sym_<name>.json (same format as swapsym.py)
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import swapsym as S  # noqa: E402
E, I = S.E, S.I

ARCHES = ["ppc64le", "ppc64e", "ppc32s", "ppc44x", "ppc8xx", "s390", "loongarch", "mips32", "mips32xpa", "mips64", "arm", "arm_lpae",
          "hexagon", "um", "sparc64"]
_VAR = {}
_prev_ccdb = I.ccdb


def _ccdb(d):
    return _VAR[d] if d in _VAR else _prev_ccdb(d)


I.ccdb = _ccdb


def register(name):
    d = f"/root/work/swapsym/cfg_{name}"
    cmdf = Path(d) / "mm" / ".memory.o.cmd"
    if not cmdf.exists():
        return f"构建不可用：没有 {cmdf}"
    m = re.search(r"^savedcmd_mm/memory\.o := (.*)$", cmdf.read_text(errors="replace"), re.M)
    if not m:
        return "构建不可用：.memory.o.cmd 里没有 savedcmd"
    cmd = m.group(1).split(";")[0].strip()
    cfg = (Path(d) / ".config").read_text(errors="replace")
    I.BUILDS[name] = d
    E.LONGW[name] = 64 if re.search(r"^CONFIG_64BIT=y", cfg, re.M) else 32
    _VAR[d] = {I.UNIT: {"command": cmd, "directory": d}}
    return None


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    names = sys.argv[2:] or ARCHES
    ok, skipped = [], {}
    for n in names:
        why = register(n)
        if why:
            skipped[n] = why
        else:
            ok.append(n)
    print("skipped", json.dumps(skipped, ensure_ascii=False), flush=True)
    print(json.dumps(S.run(ok), ensure_ascii=False, indent=1))
