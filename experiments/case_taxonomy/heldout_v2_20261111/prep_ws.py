"""Build the generator workspace of one group from the static outputs (criteria 三.1). Pure Python.

    python prep_ws.py <group>  -> ws/<group>/...   prints the S argument for gen_adapter.py

The target architecture (loongarch) is put into the generator's slot "riscv": layouts, syscall numbers and the
NR_syscalls of the hints.  For CUR the kernel name cur_riscv in version tables and probes stands for cur_loongarch.
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
T = "loongarch"


def main():
    g = sys.argv[1]
    st = HERE / "static" / g
    ws = HERE / "ws" / g
    if ws.exists():
        shutil.rmtree(ws)
    xg = ws / "diverse_dev_20261110" / "gen"
    for d in (xg, ws / "rankprune_dev_20261110" / "gen", ws / "twostage_dev_20261109", ws / "rtprobe_dev_20261110",
              ws / "anyarch_dev_20261110" / "gen"):
        d.mkdir(parents=True)
    # vocab: architecture independent
    shutil.copy(st / "vocab.json", xg / f"vocab_{g}.json")
    # layouts: loongarch -> slot riscv
    lay = json.loads((st / "layouts.json").read_text())
    lay["riscv"], lay["riscv_errors"] = lay.pop(T), lay.pop(f"{T}_errors")
    (xg / f"layouts_{g}.json").write_text(json.dumps(lay))
    # syscall numbers
    nr = json.loads((HERE / "data" / "nr_tables.json").read_text())
    nr["riscv"] = nr.pop(T)
    (xg / "nr_tables.json").write_text(json.dumps(nr))
    shutil.copy(CT / "diverse_dev_20261110" / "gen" / "bases.json", xg / "bases.json")
    # hints: NR_syscalls loongarch -> slot riscv
    h = json.loads((st / f"hints_{g}.json").read_text())
    h["NR_syscalls"]["riscv"] = h["NR_syscalls"].pop(T)
    (ws / "rankprune_dev_20261110" / "gen" / f"hints_{g}.json").write_text(json.dumps(h, indent=0))
    # version tables and probes, by kernel name
    vt = json.loads((HERE / "data" / "version_tables.json").read_text())
    pr = json.loads((HERE / "data" / "probes.json").read_text())
    if g == "CUR":
        vt["cur_riscv"] = vt["cur_loongarch"]
        dev = json.loads((CT / "rtprobe_dev_20261110" / "probes.json").read_text())
        pr = {"cur_riscv": pr["cur_loongarch"], "cur_arm64": dev["cur_arm64"], "cur_x86_64": dev["cur_x86_64"]}
    (ws / "twostage_dev_20261109" / "version_tables.json").write_text(json.dumps(vt))
    (ws / "rtprobe_dev_20261110" / "probes.json").write_text(json.dumps(pr, indent=1))
    shutil.copy(CT / "anyarch_dev_20261110" / "gen" / "confirmed.json", ws / "anyarch_dev_20261110" / "gen")
    # S = integer values of TASK_SIZE_MAX known for this group (criteria 三.3)
    vals = json.loads((st / "values.json").read_text())
    S = sorted({vals[a].get("TASK_SIZE_MAX") for a in (T, "arm64", "x86_64")
                if isinstance(vals.get(a, {}).get("TASK_SIZE_MAX"), int)})
    (ws / "S.txt").write_text(",".join(format(s, "x") for s in S))
    print(g, "S", [hex(s) for s in S], "layout roots", len(lay["roots"]), "hints T", len(h["T"]),
          "TASK_SIZE_MAX", {a: vals[a].get("TASK_SIZE_MAX") for a in (T, "arm64", "x86_64")})


if __name__ == "__main__":
    main()
