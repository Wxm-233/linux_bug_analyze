"""Collect probe logs into probes.json (rtprobe criteria 三 rules, reusing its reader). Pure Python.

    python probe_table.py <logs dir> <kernels.txt> <probes.json>   (merges into an existing probes.json)
"""
import importlib.util
import glob
import json
import os
import re
import sys
from pathlib import Path

CT = Path(__file__).resolve().parent.parent
s = importlib.util.spec_from_file_location("rt_table", CT / "rtprobe_dev_20261110" / "probe_table.py")
PT = importlib.util.module_from_spec(s)
s.loader.exec_module(PT)


def main():
    logs, klist, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    arch = {l.split()[0]: l.split()[1] for l in klist.read_text().splitlines() if l.strip()}
    res = json.loads(out.read_text()) if out.exists() else {}
    runs = {}
    for f in sorted(glob.glob(str(logs / "*.log.gz"))):
        k, i = re.match(r"(.*)\.run(\d)\.log\.gz", os.path.basename(f)).groups()
        if k in arch:
            runs.setdefault(k, {})[i] = PT.read(f)
    for k, r in runs.items():
        (a, ea), (b, eb) = r["1"], r["2"]
        vals, unstable = {}, []
        for n in sorted(set(a) | set(b)):
            if n in PT.INFO_ONLY:
                vals[n] = [a.get(n), b.get(n)]
            elif a.get(n) == b.get(n):
                vals[n] = a[n]
            else:
                unstable.append(n)
        res[k] = {"arch": arch[k], "complete": ea and eb, "unstable": unstable,
                  "errors": [n for n in vals if n.startswith("ERR_")], "values": vals}
        v = res[k]["values"]
        print(k, arch[k], "ok" if res[k]["complete"] and not unstable and not res[k]["errors"] else "PROBLEM",
              {x: v.get(x) for x in ("uaccess_top", "mmap_top", "top_byte_ignored", "mm_top_byte_ignored", "page_size")})
    out.write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
