"""Run the frozen case generator on a data workspace (criteria 三.1). Pure Python (Windows, like the dev rounds).

    python gen_adapter.py <workspace> <group> <S hex,...> [--slot-name NAME]

The generator files are imported from their frozen locations and are not modified.  Only module-level path variables,
the group -> kernels table and the TASK_SIZE_MAX values S are set.  The workspace mirrors the dev tree:

  WS/diverse_dev_20261110/gen/   vocab_<g>.json  layouts_<g>.json  nr_tables.json  bases.json      (inputs)
                                 cases_<g>.json  lists_<g>.json  cases_<g>_<slot>.txt                (generate_x output)
  WS/rankprune_dev_20261110/gen/ hints_<g>.json
  WS/twostage_dev_20261109/      version_tables.json
  WS/rtprobe_dev_20261110/       probes.json
  WS/anyarch_dev_20261110/gen/   confirmed.json
  WS/merge_dev_20261111/gen/     cases_<g>.json  lists_<g>.json  cases_<g>_<kernel>.txt              (generate_c output)

The target architecture occupies the generator's slot "riscv" (layouts, syscall numbers, version tables and the
NR_syscalls of the hints are put under that key by the data preparation).  --slot-name only renames output files
whose name contains the slot (e.g. cases_CUR_riscv.txt -> cases_CUR_loongarch.txt, cur_riscv -> cur_loongarch).
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "diverse_dev_20261110" / "gen"))
sys.path.insert(0, str(CT / "merge_dev_20261111" / "gen"))
import calib  # noqa: E402
import generate_x  # noqa: E402
import generate_c  # noqa: E402

BG = generate_x.ML.BG


def kernels_of(g):
    if g == "CUR":
        return ["cur_riscv", "cur_arm64", "cur_x86_64"]
    p = g.lower()
    return [f"{p}_pre", f"{p}_fix", f"{p}_ref_arm64", f"{p}_ref_x86_64"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ws")
    ap.add_argument("group")
    ap.add_argument("S", help="comma separated hex values of TASK_SIZE_MAX known for this group")
    ap.add_argument("--slot-name", default=None)
    a = ap.parse_args()
    ws = Path(a.ws).resolve()
    xdir = ws / "diverse_dev_20261110" / "gen"
    cdir = ws / "merge_dev_20261111" / "gen"
    cdir.mkdir(parents=True, exist_ok=True)
    # --- module variables (paths, group table, S); no function is replaced
    generate_x.HERE = xdir
    calib.HERE = xdir
    BG.KERNELS[a.group] = kernels_of(a.group)
    generate_c.DG = xdir
    generate_c.CT = ws
    generate_c.HERE = cdir
    generate_c.S[a.group] = [int(x, 16) for x in a.S.split(",") if x]
    sys.argv = ["generate_x.py", a.group]
    generate_x.main()
    sys.argv = ["generate_c.py", a.group]
    generate_c.main()
    if a.slot_name:
        for d in (xdir, cdir):
            for f in sorted(d.glob(f"cases_{a.group}_*riscv*.txt")):
                f.rename(f.with_name(f.name.replace("riscv", a.slot_name)))
        print("renamed slot riscv ->", a.slot_name)


if __name__ == "__main__":
    main()
