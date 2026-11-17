"""Generate the dev groups with B cases per seed (budget criteria 二). Pure Python (Windows, like the dev rounds).

    python gen_budget.py <B> <group>...   -> ws/... (generator workspace), run/<group>/{cases.json, lists.json,
                                              cases_<kernel>.txt}, prefix_check.json
The generator files are imported from their frozen locations; only generate_x.B and path variables are set.
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "diverse_dev_20261110" / "gen"))
sys.path.insert(0, str(CT / "merge_dev_20261111" / "gen"))
import calib  # noqa: E402
import generate_x  # noqa: E402
import generate_c  # noqa: E402

DG = CT / "diverse_dev_20261110" / "gen"


def kernels(g):
    if g == "CUR":
        return {"cur_riscv": "riscv", "cur_arm64": "arm64", "cur_x86_64": "x86_64"}
    p = g.lower()
    return {f"{p}_pre": "riscv", f"{p}_fix": "riscv", f"{p}_ref_arm64": "arm64", f"{p}_ref_x86_64": "x86_64"}


def key(c):
    return json.dumps({k: v for k, v in c.items() if k != "id"}, sort_keys=True)


def main():
    B, groups = int(sys.argv[1]), sys.argv[2:]
    ws = HERE / "ws"
    xg, cg = ws / "diverse_dev_20261110" / "gen", ws / "merge_dev_20261111" / "gen"
    for d in (xg, cg, ws / "rankprune_dev_20261110" / "gen", ws / "twostage_dev_20261109", ws / "rtprobe_dev_20261110",
              ws / "anyarch_dev_20261110" / "gen"):
        d.mkdir(parents=True, exist_ok=True)
    for f in ("nr_tables.json", "bases.json"):
        shutil.copy(DG / f, xg / f)
    shutil.copy(CT / "twostage_dev_20261109" / "version_tables.json", ws / "twostage_dev_20261109")
    shutil.copy(CT / "rtprobe_dev_20261110" / "probes.json", ws / "rtprobe_dev_20261110")
    shutil.copy(CT / "anyarch_dev_20261110" / "gen" / "confirmed.json", ws / "anyarch_dev_20261110" / "gen")
    generate_x.B = B
    generate_x.HERE = calib.HERE = generate_c.DG = xg
    generate_c.CT, generate_c.HERE = ws, cg
    check = {}
    for g in groups:
        for f in (f"vocab_{g}.json", f"layouts_{g}.json"):
            shutil.copy(DG / f, xg / f)
        shutil.copy(CT / "rankprune_dev_20261110" / "gen" / f"hints_{g}.json", ws / "rankprune_dev_20261110" / "gen")
        sys.argv = ["generate_x.py", g]
        generate_x.main()
        sys.argv = ["generate_c.py", g]
        generate_c.main()
        # prefix check: the first 1000 cases of every seed equal the diverse round's lists, by content
        old = {c["id"]: c for c in json.loads((DG / f"cases_{g}.json").read_text())["cases"]}
        oldl = json.loads((DG / f"lists_{g}.json").read_text())
        xm = json.loads((xg / f"cases_{g}.json").read_text())
        new = {c["id"]: c for c in xm["cases"]}
        xl = json.loads((xg / f"lists_{g}.json").read_text())
        check[g] = {G: all(key(new[a]) == key(old[b]) for s in oldl[G] for a, b in zip(xl[G][s][:1000], oldl[G][s]))
                    for G in oldl}
        # combine: generate_x's per-arch list + generate_c's new lines per kernel
        cm = json.loads((cg / f"cases_{g}.json").read_text())
        xids = {c["id"] for c in xm["cases"]}
        extra = [c for c in cm["cases"] if c["id"] not in xids]
        out = HERE / "run" / g
        out.mkdir(parents=True, exist_ok=True)
        meta = {k: v for k, v in xm.items() if k != "cases"}
        meta.update({"cases": xm["cases"] + extra})
        (out / "cases.json").write_text(json.dumps(meta, indent=0))
        cl = json.loads((cg / f"lists_{g}.json").read_text())
        (out / "lists.json").write_text(json.dumps({"G0d": xl["G0d"], "G2d": xl["G2d"], "G3d": xl["G3d"],
                                                    "G3c": cl["G3c"]}))
        newids = {str(c["id"]) for c in extra}
        for k, a in kernels(g).items():
            base = (xg / f"cases_{g}_{a}.txt").read_text().splitlines()
            add = [l for l in (cg / f"cases_{g}_{k}.txt").read_text().splitlines() if l.split(" ", 1)[0] in newids]
            (out / f"cases_{k}.txt").write_text("\n".join(base + add) + "\n")
        print(g, "cases", len(meta["cases"]), "prefix", check[g])
    (HERE / "prefix_check.json").write_text(json.dumps(check, indent=1))


if __name__ == "__main__":
    main()
