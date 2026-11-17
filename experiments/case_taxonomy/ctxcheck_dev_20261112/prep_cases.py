"""Cases from the call-context hints (ctxcheck criteria 五). Pure Python.

    python prep_cases.py hints_ctx_pre.json   -> cases/trap.txt, cases/sys_<arch>.txt, cases/manifest.json

Trap cases: 3 per trap kind that has flags and that trap_runner implements.  Syscall cases: G3g cases of
fieldhint2_dev_20261111/run/CUR (all three seeds) whose syscall is in the hints' top 20, by id, at most 2000.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CUR = HERE.parent / "fieldhint2_dev_20261111" / "run" / "CUR"
RUNNER = ["breakpoint", "illegal_insn", "misaligned_load", "misaligned_store"]
ARCHS = {"riscv": "cur_riscv", "arm64": "cur_arm64", "x86_64": "cur_x86_64"}


def main():
    h = json.loads(Path(sys.argv[1]).read_text())
    out = HERE / "cases"
    out.mkdir(exist_ok=True)
    kinds = [k for k in RUNNER if k in h["traps"]]
    not_run = sorted(set(h["traps"]) - set(RUNNER))
    lines = [f"{i + 1} {k}" for i, k in enumerate(k for k in kinds for _ in range(3))]
    (out / "trap.txt").write_text("\n".join(lines) + "\n", newline="\n")
    top = set(h["syscalls"])
    cases = {c["id"]: c for c in json.loads((CUR / "cases.json").read_text())["cases"]}
    lists = json.loads((CUR / "lists.json").read_text())
    ids = sorted({i for s in lists["G3g"].values() for i in s if cases[i]["sc"] in top})[:2000]
    keep = set(ids)
    for arch, k in ARCHS.items():
        src = (CUR / f"cases_{k}.txt").read_text().splitlines()
        sel = [l for l in src if l.split(" ", 1)[0].isdigit() and int(l.split(" ", 1)[0]) in keep]
        assert len(sel) == len(ids), (arch, len(sel), len(ids))
        (out / f"sys_{arch}.txt").write_text("\n".join(sel) + "\n", newline="\n")
    by_sc = {}
    for i in ids:
        by_sc[cases[i]["sc"]] = by_sc.get(cases[i]["sc"], 0) + 1
    man = {"trap_kinds_run": kinds, "trap_kinds_flagged_not_run": not_run, "trap_cases": len(lines),
           "sys_top20": sorted(top), "sys_cases": len(ids), "sys_cases_by_syscall": by_sc}
    (out / "manifest.json").write_text(json.dumps(man, indent=1))
    print(json.dumps(man))


if __name__ == "__main__":
    main()
