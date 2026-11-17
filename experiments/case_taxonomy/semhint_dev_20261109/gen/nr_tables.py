"""Syscall numbers per architecture from the cross toolchains' <asm/unistd.h> (criteria 六: raw numbers per arch).
Runs in WSL.   python3 nr_tables.py -> nr_tables.json {"riscv": {name: nr}, ...}
Names come from ../../twostage_dev_20261109/version_tables.json (union over all kernels)."""
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
VT = json.loads((HERE.parents[1] / "twostage_dev_20261109/version_tables.json").read_text())
names = sorted({n for v in VT.values() for n in v})
CC = {"riscv": "riscv64-linux-gnu-gcc", "arm64": "aarch64-linux-gnu-gcc", "x86_64": "x86_64-linux-gnu-gcc"}
src = "#include <asm/unistd.h>\n" + "\n".join(f"#ifdef __NR_{n}\nSHNR {n} __NR_{n}\n#endif" for n in names) + "\n"
out = {}
for arch, cc in CC.items():
    r = subprocess.run([cc, "-E", "-P", "-x", "c", "-"], input=src, capture_output=True, text=True, check=True)
    tab = {}
    for line in r.stdout.splitlines():
        m = re.match(r"^SHNR (\w+) (.+)$", line)
        if m:
            expr = m.group(2)
            if re.fullmatch(r"[\d\s+()]+", expr):
                tab[m.group(1)] = eval(expr)
    out[arch] = tab
    print(arch, len(tab), "of", len(names))
(HERE / "nr_tables.json").write_text(json.dumps(out, indent=0, sort_keys=True))
