"""Static candidate -> rule mapping (proprules criteria 三). WSL (reads effdep5 out/*.json written on D:)."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
E5 = HERE.parent / "effdep5_dev_20261113" / "out"
NAMES = {"page", "folio", "pte", "vmf", "vma", "addr"}


def rule(c):
    cats = set(c["skipped_cats"])
    res = set(c.get("shared_resources") or c.get("resources") or [])
    user = bool(res & NAMES)
    if "mem" in cats and user:
        return "R1"
    if cats & {"tlb", "pgtable"} and user:
        return "R2"
    if "cache" in cats:
        return "R3"
    return "内核内部（需要 ACTOR 或调试内核）"


out = {}
for tree in ("CUR_riscv", "X1"):
    d = json.loads((E5 / f"{tree}.json").read_text(encoding="utf-8"))
    rows = [{"fn": c["fn"], "interface": c["interface"], "cats": c["skipped_cats"], "resources": c["resources"],
             "rule": rule(c)} for c in d["candidates_list"]]
    cnt = {}
    for r in rows:
        cnt[r["rule"]] = cnt.get(r["rule"], 0) + 1
    out[tree] = {"candidates": len(rows), "by_rule": cnt, "rows": rows}
    print(tree, len(rows), cnt)
    for r in rows:
        if r["rule"] != "内核内部（需要 ACTOR 或调试内核）":
            print("  ", r["rule"], r["fn"], r["interface"], r["cats"], r["resources"])
(HERE / "mapping.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
