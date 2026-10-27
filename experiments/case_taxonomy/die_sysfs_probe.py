"""Audit die-topology sysfs guards in two historical trees.

The result is a source/preprocessor condition matrix, not a boot test.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


FIX = "2c4dcd7fd57b20a21b65da04d89c38a7217d79cf"
PERF_FIX = "a6e62743621ea29bea461774c0bcc68e5de59068"
PERF_TEST_FIX = "6c481031c9f71e2b0ff9c49d21116a38ca671746"
DRIVER = "drivers/base/topology.c"
TARGETS = (
    "static DEVICE_ATTR_RO(die_id);",
    "static BIN_ATTR_RO(die_cpus, 0);",
    "static BIN_ATTR_RO(die_cpus_list, 0);",
    "&dev_attr_die_id.attr,",
    "&bin_attr_die_cpus,",
    "&bin_attr_die_cpus_list,",
)


def git_file(linux_dir: Path, revision: str, path: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(linux_dir), "show", f"{revision}:{path}"],
        text=True,
    )


def die_guards(source: str) -> dict[str, bool]:
    stack: list[str] = []
    result: dict[str, bool] = {}
    for line in source.splitlines():
        stripped = line.strip()
        if re.match(r"^#\s*(if|ifdef|ifndef)\b", stripped):
            stack.append(stripped)
        elif re.match(r"^#\s*endif\b", stripped):
            if not stack:
                raise ValueError("unmatched #endif")
            stack.pop()
        for target in TARGETS:
            if stripped == target:
                if target in result:
                    raise ValueError(f"duplicate {target}")
                result[target] = "#ifdef TOPOLOGY_DIE_SYSFS" in stack
    if set(result) != set(TARGETS):
        raise ValueError(f"missing die sysfs lines: {set(TARGETS) - set(result)}")
    return result


def arch_supports_die(linux_dir: Path, revision: str, arch: str, smp: bool) -> bool:
    source = git_file(linux_dir, revision, f"arch/{arch}/include/asm/topology.h")
    visible: set[str] = set()
    stack: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        if re.match(r"^#\s*(if|ifdef|ifndef)\b", stripped):
            if stripped == "#ifdef CONFIG_SMP":
                stack.append("smp")
            elif stripped == "#ifndef CONFIG_SMP":
                stack.append("not_smp")
            else:
                stack.append("other")
        elif re.match(r"^#\s*else\b", stripped) and stack:
            if stack[-1] == "smp":
                stack[-1] = "not_smp"
            elif stack[-1] == "not_smp":
                stack[-1] = "smp"
        elif re.match(r"^#\s*endif\b", stripped):
            stack.pop()
        match = re.match(r"^#\s*define\s+(topology_die_id|topology_die_cpumask)\s*\(", stripped)
        if match and ("smp" not in stack or smp) and ("not_smp" not in stack or not smp):
            visible.add(match.group(1))
    return visible == {"topology_die_id", "topology_die_cpumask"}


def run(linux_dir: Path) -> dict:
    before = die_guards(git_file(linux_dir, FIX + "^", DRIVER))
    after = die_guards(git_file(linux_dir, FIX, DRIVER))
    if any(before.values()) or not all(after.values()):
        raise AssertionError("unexpected topology.c die sysfs guard layout")
    header = git_file(linux_dir, FIX, "include/linux/topology.h")
    marker = "#if defined(topology_die_id) && defined(topology_die_cpumask)"
    fallback = "#ifndef topology_die_id"
    if marker not in header or header.index(marker) > header.index(fallback):
        raise AssertionError("capability guard is not before the generic fallback")

    matrix = []
    for arch, smp in (("x86", True), ("x86", False), ("s390", True), ("arm64", True)):
        supported = arch_supports_die(linux_dir, FIX, arch, smp)
        matrix.append(
            {
                "arch": arch,
                "config_smp": smp,
                "defines_both_die_macros": supported,
                "before_exported_attrs": 3,
                "after_exported_attrs": 3 if supported else 0,
            }
        )
    if matrix[0]["after_exported_attrs"] != 3 or any(
        item["after_exported_attrs"] for item in matrix[1:]
    ):
        raise AssertionError("unexpected arch capability matrix")

    perf_driver = git_file(linux_dir, PERF_FIX, DRIVER)
    perf_guards = die_guards(perf_driver)
    perf_arch_support = arch_supports_die(linux_dir, PERF_FIX, "s390", True)
    perf_source = git_file(linux_dir, PERF_FIX, "tools/perf/util/cputopo.c")
    has_die_start = perf_source.index("static bool has_die_topology(void)")
    has_die_end = perf_source.index("struct cpu_topology *cpu_topology__new", has_die_start)
    has_die = perf_source[has_die_start:has_die_end]
    if "s390x" not in has_die or "access(filename, F_OK)" not in has_die:
        raise AssertionError("unexpected perf has_die_topology() predicate")
    if not all(perf_guards.values()):
        raise AssertionError("perf-fix tree no longer guards die attributes")
    subprocess.run(
        ["git", "-C", str(linux_dir), "merge-base", "--is-ancestor",
         PERF_TEST_FIX, PERF_FIX],
        check=True,
    )
    perf_test = git_file(linux_dir, PERF_FIX + "^", "tools/perf/tests/expr.c")
    if "if (num_dies) // Some platforms do not have CPU die support, for example s390" not in perf_test:
        raise AssertionError("s390 no-die test exception missing before perf whitelist fix")

    return {
        "fix": FIX,
        "perf_fix": PERF_FIX,
        "perf_test_fix_already_merged": PERF_TEST_FIX,
        "evidence_level": "source/preprocessor guard audit; no kernel boot",
        "die_attribute_targets_checked": len(TARGETS),
        "matrix": matrix,
        "perf_fix_tree": {
            "s390_machine_string_allowed": True,
            "s390_in_tree_die_macro_pair": perf_arch_support,
            "perf_requires_die_cpus_list_file": True,
            "generic_die_cpus_list_exported_on_s390": perf_arch_support,
            "in_tree_predicate_can_be_true_on_s390": perf_arch_support,
            "test_accepts_absent_die_before_whitelist_fix": True,
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--linux-dir", type=Path, default=Path("/root/repos/linux"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    encoded = json.dumps(run(args.linux_dir), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end="")
