"""Base-case candidates for the calibration run on the current-version kernels (mutate criteria 二).

    python calib.py -> cases_calib.json, cases_calib_<arch>.txt
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mutate_lib as ML  # noqa: E402

BG, GM = ML.BG, ML.GM


def universe(group, h, nrt):
    vt = json.loads((HERE.parents[1] / "twostage_dev_20261109/version_tables.json").read_text())
    common = set.intersection(*[set(vt[k]) for k in BG.KERNELS[group]])
    return sorted(sc for sc in common if sc not in BG.BLACK_EXACT and sc in h["entries"]
                  and all(sc in nrt[a] for a in ML.ARCHS))


def main():
    h = json.loads((HERE.parents[1] / "rankprune_dev_20261110/gen/hints_CUR.json").read_text())
    vocab = json.loads((HERE / "vocab_CUR.json").read_text())["vocab"]
    lay = json.loads((HERE / "layouts_CUR.json").read_text())
    nrt = json.loads((HERE / "nr_tables.json").read_text())
    U = universe("CUR", h, nrt)
    cases = []
    for sc in U:
        rng = random.Random(f"calib/{sc}")
        for j, c in enumerate(ML.candidates(sc, h["entries"][sc], vocab, lay, rng)):
            c["cand"] = j
            c["id"] = len(cases) + 1
            cases.append(c)
    NR = {a: h["NR_syscalls"][a] for a in ML.ARCHS}
    for a, ls in ML.lines(cases, lay, nrt, NR).items():
        (HERE / f"cases_calib_{a}.txt").write_text("\n".join(ls) + "\n")
    (HERE / "cases_calib.json").write_text(json.dumps({"U": U, "params": {sc: h["entries"][sc] for sc in U},
                                                       "cases": cases}, indent=0))
    print("U", len(U), "candidates", len(cases), "structured", sum(1 for c in cases if c.get("structs")))


if __name__ == "__main__":
    main()
