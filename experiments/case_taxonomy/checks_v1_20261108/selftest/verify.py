"""Self-test for ctx_extract.py + ctx_analyze.py (criteria.md section 6: the expected set must match exactly).

    python3 selftest/verify.py        (run in WSL from the round directory)
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent
SRC = HERE / "src"
WORK = Path("/root/work/checks_v1/selftest")

# (kind, caller, callee, line) written from the fixture before the first run
EXPECTED = {
    ("S", "s_local", "mutex_lock", 7),
    ("S", "s_branch", "mutex_lock", 8),
    ("S", "s_goto", "msleep", 15),
    ("R", "r_raw", "takes_spin", 21),
    ("R", "takes_spin", "spin_lock", 20),  # corrected: required by criteria 3.4(c)+3.5 (see expected_corrections.md)
    ("S", "cb", "mutex_lock", 22),
    ("I", "i_irq", "on_each_cpu", 23),
    ("S", "alloc", "kmalloc", 28),
    ("S", "sw", "msleep", 42),          # corrected: line miscount (see expected_corrections.md)
    ("S", "do_trap_x", "helper_user", 6),
    ("S", "helper_user", "copy_from_user", 5),
}


def main():
    if WORK.exists():
        shutil.rmtree(WORK)
    build = WORK / "build"
    build.mkdir(parents=True)
    rows = []
    # amendment 3: kernel/opaque.c checks that NO_DESCEND / primitive bodies are not expanded; it adds no flag
    for c in ("kernel/a.c", "arch/riscv/kernel/traps.c", "kernel/opaque.c"):
        rows.append({"directory": str(SRC), "file": c,
                     # amendment 2, item 3: relative include path, as in the kernel's compile_commands.json
                     "arguments": ["clang", "-c", "-std=gnu11", "-I", "include", "-o",
                                   str(build / (c.replace("/", "_") + ".o")), c]})
    (build / "compile_commands.json").write_text(json.dumps(rows))
    subprocess.run([sys.executable, str(ROUND / "ctx_extract.py"), str(build), str(WORK / "cache"),
                    "--jobs", "2", "--source", str(SRC)], check=True)
    out = WORK / "flags.json"
    subprocess.run([sys.executable, str(ROUND / "ctx_analyze.py"), str(WORK / "cache"),
                    str(SRC / "arch/riscv/kernel/entry.S"), str(out)], check=True)
    data = json.loads(out.read_text())
    got = {(f["kind"], f["caller"], f["callee"], f["site"][1]) for f in data["flags"]}
    trap = set(data["summary"]["trap_entries"])
    # amendment 2, item 3: every unit must parse without a fatal diagnostic, and the node counter must count
    sys.path.insert(0, str(ROUND))
    from ctx_analyze import count
    from collections import defaultdict
    kinds = defaultdict(int)
    count(["seq", [["icall", "f", 1], ["asm", "f", 2], ["seq", [["icall", "f", 3]]]]], kinds)
    clean = data["summary"]["unit_status"] == {"ok": 3}
    counter_ok = kinds["icall"] == 2 and kinds["asm"] == 1
    ok = got == EXPECTED and trap == {"do_trap_x", "do_trap_y"} and clean and counter_ok
    result = {"passed": ok, "unit_status_clean": clean, "counter_ok": counter_ok,
              "missing": sorted(EXPECTED - got), "unexpected": sorted(got - EXPECTED),
              "trap_entries": sorted(trap), "summary": data["summary"],
              "origins": sorted((f["caller"], f["callee"], f["origin"], json.dumps(f.get("origin_chain", [])))
                                for f in data["flags"])}
    (HERE / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
    print(json.dumps(result, ensure_ascii=False, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
