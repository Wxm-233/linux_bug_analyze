"""Collect the probe values of every kernel (rtprobe criteria 三 + amendment 1). Pure Python.

    python probe_table.py -> probes.json   (and prints a table)
"""
import glob
import gzip
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
INFO_ONLY = {"mmap_default"}  # randomised; not part of the stability check


def read(f):
    d, end = {}, False
    for line in gzip.open(f, "rt", errors="replace"):
        line = line.strip()
        if line == "@@SH END":
            end = True
        if not line.startswith("{"):
            continue
        try:
            x = json.loads(line)
        except ValueError:
            continue
        if "probe" in x:
            d[x["probe"]] = x["value"]
        if "harness_error" in x:
            d["ERR_" + x.get("probe", "?")] = x.get("why")
    return d, end


def main():
    runs = {}
    for f in sorted(glob.glob(str(HERE / "runs" / "probe" / "*.log.gz"))):
        k, i = re.match(r"(.*)\.run(\d)\.log\.gz", os.path.basename(f)).groups()
        runs.setdefault(k, {})[i] = read(f)
    arch = {l.split()[0]: l.split()[1] for l in (HERE / "kernels_all.txt").read_text().splitlines() if l.strip()}
    out = {}
    for k, r in runs.items():
        (a, ea), (b, eb) = r["1"], r["2"]
        vals, unstable = {}, []
        for n in sorted(set(a) | set(b)):
            if n in INFO_ONLY:
                vals[n] = [a.get(n), b.get(n)]
            elif a.get(n) == b.get(n):
                vals[n] = a[n]
            else:
                unstable.append(n)
        out[k] = {"arch": arch[k], "complete": ea and eb, "unstable": unstable,
                  "errors": [n for n in vals if n.startswith("ERR_")], "values": vals}
    (HERE / "probes.json").write_text(json.dumps(out, indent=1))
    cols = ["uaccess_top", "uaccess_search_bits", "top_byte_ignored", "mm_top_byte_ignored", "mmap_top", "page_size"]
    for k in sorted(out, key=lambda x: (not x.startswith("cur"), x)):
        o = out[k]
        print(k.ljust(16), o["arch"].ljust(7), "ok " if o["complete"] and not o["unstable"] and not o["errors"]
              else f"PROBLEM {o['unstable']} {o['errors']}", [o["values"].get(c) for c in cols])


if __name__ == "__main__":
    main()
