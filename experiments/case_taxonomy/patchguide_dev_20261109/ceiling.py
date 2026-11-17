"""Ceiling of the fix-patch source on the dev set (descriptive, after iteration 2).

For each evaluated sample: do the riscv fix's added elements (in its fix functions) appear among the added elements of
any counterpart fix patch committed before the cutoff?
  any_hunk        in any hunk at all (upper bound with a perfect function mapping)
  same_name_hunk  in a hunk whose function has the same name as one of the riscv fix functions
"""
import gzip
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
S = json.loads((HERE / "runs" / "iter2" / "samples.json").read_text(encoding="utf-8"))
with gzip.open("/root/work/pgdev/patches_x86_arm64.json.gz", "rt") as fh:
    P = json.load(fh)["commits"]
out = []
for r in S:
    if r.get("status") != "ok":
        continue
    fe = {k: set(v) for k, v in r["fix_elements"].items()}
    if not any(fe.values()):
        out.append({"id": r["id"], "fix_elements": 0})
        continue
    anyh, same = set(), set()
    for p in P:
        if p["cdate"] >= r["cutoff"]:
            continue
        for h in p["hunks"]:
            for k, es in h["added"].items():
                common = fe[k] & set(es)
                for e in common:
                    anyh.add((k, e, p["commit"][:12]))
                    if h["func"] in r["fix_functions"]:
                        same.add((k, e, p["commit"][:12], h["func"]))
    out.append({"id": r["id"], "fix_elements": sum(len(v) for v in fe.values()), "any_hunk": len({x[:2] for x in anyh}),
                "same_name_hunk": sorted(same)[:5]})
(HERE / "runs" / "iter2" / "ceiling.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
withel = [o for o in out if o["fix_elements"]]
print("evaluated", len(out), "with fix elements", len(withel),
      "| any_hunk>0:", sum(1 for o in withel if o["any_hunk"]), "| same_name_hunk>0:", sum(1 for o in withel if o["same_name_hunk"]))
for o in withel:
    if o["same_name_hunk"]: print("  same-name:", o["id"], o["same_name_hunk"])
