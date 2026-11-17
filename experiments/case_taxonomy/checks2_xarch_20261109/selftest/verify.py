"""Self-test for archbound_ext collect + xcmp.py (criteria.md section 6: the expected flag set must match exactly).

    python3 selftest/verify.py        (run in WSL from the round directory)

Fixture families (src/):
  arch_hook       riscv uses the generic constant stub (static inline in include/linux/gen.h), x86 has a real one -> stub
  arch_set_state  x86 writes task.state; riscv only writes task.flags through a static helper  -> write-missing task.state
                  (arm64 writes task.flags directly: covered by riscv's transitive writes -> nothing)
  arch_flush      x86 calls cpumask_clear_all (common, writes g_mask), riscv does not          -> call-missing
                  (arm64 calls log_only, which writes nothing -> nothing)
  arch_reset2     arm64 calls common_reset directly, riscv two hops away through a helper     -> nothing
  arch_alloc      common_alloc(4096, 0) on riscv vs common_alloc(4096, 8) on x86              -> arg-diff at position 1
  arch_map_event  riscv returns -2, x86 returns -95                                          -> errno-diff
  arch_get_reg    x86 checks idx before regs[idx], riscv does not                            -> param-check param#0:index
  arch_dir        riscv calls common_reset, x86 is empty (wrong direction)                    -> nothing
  arch_multi      two riscv static inline definitions in two headers, one writes task.state  -> nothing (merged)
  arch_private    riscv definition is static in a .c file (not an implementation)            -> nothing
  not_candidate   not in the candidate pools                                                  -> nothing
"""
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent
SRC = HERE / "src"
WORK = Path("/root/work/checks2/selftest")
BIN = "/root/work/checks2/archbound_ext/archbound"
sys.path.insert(0, str(ROUND))
import xcmp  # noqa: E402

# (type, family, detail, counterpart), written from the fixture before the first run
EXPECTED = {
    ("stub", "arch_hook", "const", "x86"),
    ("write-missing", "arch_set_state", "task.state", "x86"),
    ("call-missing", "arch_flush", "cpumask_clear_all", "x86"),
    ("arg-diff", "arch_alloc", "common_alloc#1:['0']vs['8']", "x86"),
    ("errno-diff", "arch_map_event", "-95", "x86"),
    ("param-check", "arch_get_reg", "param#0:index", "x86"),
    ("arg-diff", "arch_flush", "log_only#0:['1']vs['3']", "arm64"),  # corrected: required by criteria 3.3 (see expected_corrections.md)
}
CANDIDATES = ["arch_hook", "arch_set_state", "arch_flush", "arch_reset2", "arch_alloc", "arch_map_event",
              "arch_get_reg", "arch_dir", "arch_multi", "arch_private"]
UNITS = {"riscv": ["common/lib.c", "arch/riscv/a.c", "arch/riscv/b.c"],
         "x86": ["common/lib.c", "arch/x86/x.c"],
         "arm64": ["common/lib.c", "arch/arm64/y.c"]}


def main():
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    reduced = {}
    for arch, units in UNITS.items():
        bdir = WORK / arch
        bdir.mkdir()
        # absolute "file", as in the kernel's compile_commands.json (a relative one is resolved against the cwd)
        rows = [{"directory": str(SRC), "file": str(SRC / u),
                 "arguments": ["clang", "-c", "-std=gnu11", "-I", "include", "-I", f"arch/{arch}/include",
                               "-o", str(bdir / (u.replace("/", "_") + ".o")), u]} for u in units]
        (bdir / "compile_commands.json").write_text(json.dumps(rows))
        facts = bdir / "facts.json"
        subprocess.run([BIN, "collect", "-p", str(bdir / "compile_commands.json"), "--root", str(SRC), "--arch", arch,
                        "-j", "2", "--out", str(facts)], check=True)
        xcmp.reduce_facts(str(facts), str(bdir / "facts.json.gz"))
        reduced[arch] = xcmp.load(str(bdir / "facts.json.gz"))
    # candidate pools in the format of boundary_audit's symbols_runtime_<arch>.json; one macro provider for the count
    pool = WORK / "pool.json"
    pool.write_text(json.dumps([{"direction": "public_to_arch", "kind": "function", "name": n} for n in CANDIDATES] +
                               [{"direction": "public_to_arch", "kind": "macro", "name": "ARCH_HAS_HOOK"}]))
    flags, summary = xcmp.compare(reduced["riscv"], [("x86", reduced["x86"]), ("arm64", reduced["arm64"])], [str(pool)])
    got = {(f["type"], f["family"], f["detail"], tag) for f in flags for tag in f["counterparts"]}
    units_clean = all(f["units"] == len(UNITS[a]) for a, f in reduced.items())
    # guard: a facts file with one failed unit must be refused by reduce (criteria section 2)
    raw = json.loads((WORK / "riscv" / "facts.json").read_text())
    bad = copy.deepcopy(raw)
    bad["units"][0]["status"] = 1
    (WORK / "bad.json").write_text(json.dumps(bad))
    try:
        xcmp.reduce_facts(str(WORK / "bad.json"), str(WORK / "bad.json.gz"))
        guard_ok = False
    except SystemExit:
        guard_ok = True
    # the extension fields are present
    ext_ok = (any(c.get("argConsts") for c in raw["calls"]) and any(d.get("retConsts") for d in raw["defs"])
              and all(u["status"] == 0 for u in raw["units"]))
    ok = got == EXPECTED and units_clean and guard_ok and ext_ok
    result = {"passed": ok, "units_clean": units_clean, "guard_refuses_failed_unit": guard_ok, "ext_fields": ext_ok,
              "missing": sorted(EXPECTED - got), "unexpected": sorted(got - EXPECTED), "summary": summary,
              "flags": flags}
    (HERE / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
    print(json.dumps({k: result[k] for k in ("passed", "units_clean", "guard_refuses_failed_unit", "ext_fields",
                                              "missing", "unexpected", "summary")}, ensure_ascii=False, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
