"""One case set per kernel with all four groups G0d, G2d, G3d (generate_x) and G3c (generate_c). Pure Python.

    python combine.py <group> <kernel>:<arch>...   -> ws/<group>/run/{cases.json, lists.json, cases_<kernel>.txt}

The G3d cases in generate_c's per-kernel lists are byte-identical to generate_x's lines (asserted there), so the union
is: generate_x's list for the kernel's architecture + the lines of generate_c's per-kernel list with new ids.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    g = sys.argv[1]
    ks = [x.split(":") for x in sys.argv[2:]]
    ws = HERE / "ws" / g
    xg, cg, out = ws / "diverse_dev_20261110" / "gen", ws / "merge_dev_20261111" / "gen", ws / "run"
    out.mkdir(exist_ok=True)
    xm = json.loads((xg / f"cases_{g}.json").read_text())
    cm = json.loads((cg / f"cases_{g}.json").read_text())
    xids = {c["id"] for c in xm["cases"]}
    new = [c for c in cm["cases"] if c["id"] not in xids]
    meta = {k: v for k, v in xm.items() if k != "cases"}
    meta.update({"cases": xm["cases"] + new, "merge": cm.get("merge")})
    (out / "cases.json").write_text(json.dumps(meta, indent=0))
    xl, cl = json.loads((xg / f"lists_{g}.json").read_text()), json.loads((cg / f"lists_{g}.json").read_text())
    (out / "lists.json").write_text(json.dumps({"G0d": xl["G0d"], "G2d": xl["G2d"], "G3d": xl["G3d"], "G3c": cl["G3c"]}))
    newids = {str(c["id"]) for c in new}
    for k, a in ks:
        base = (xg / f"cases_{g}_{a}.txt").read_text().splitlines()
        extra = [l for l in (cg / f"cases_{g}_{k}.txt").read_text().splitlines() if l.split(" ", 1)[0] in newids]
        (out / f"cases_{k}.txt").write_text("\n".join(base + extra) + "\n", newline="\r\n")
        print(g, k, a, "lines", len(base), "+", len(extra))


if __name__ == "__main__":
    main()
