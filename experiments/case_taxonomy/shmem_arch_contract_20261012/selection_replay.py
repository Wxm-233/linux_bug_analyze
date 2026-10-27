"""Replay historical selection bodies with certified geometry and kernel doubles.

The independent expectation uses the unchanged xarray consumer observation,
not the repair's MAX_PAGECACHE_ORDER comparison. This is a partial-chain test,
not a historical kernel execution or a real folio allocation.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import shmem_pagecache_probe as base

MAIN = r"""
int main(void) {
    struct super_block sb = { .info = { .huge = SHMEM_HUGE_ALWAYS } };
    struct inode inode = { .i_mode = S_IFREG, .i_sb = &sb, .size = 1LL << 30 };
    struct mm_struct mm = { .flags = 0 };
    struct { const char *name; int policy; bool force; unsigned long flags; } cases[] = {
        {"always", SHMEM_HUGE_ALWAYS, false, 0},
        {"force_argument", SHMEM_HUGE_NEVER, true, 0},
        {"advise", SHMEM_HUGE_ADVISE, false, VM_HUGEPAGE},
        {"never", SHMEM_HUGE_NEVER, false, 0},
        {"nohugepage", SHMEM_HUGE_ALWAYS, false, VM_NOHUGEPAGE},
    };
    for (unsigned int i=0; i<sizeof(cases)/sizeof(cases[0]); i++) {
        sb.info.huge = cases[i].policy;
        printf("%s %d %d\n", cases[i].name,
            old_shmem_is_huge(&inode, 0, cases[i].force, &mm, cases[i].flags),
            shmem_is_huge(&inode, 0, cases[i].force, &mm, cases[i].flags));
    }
    return 0;
}
"""


def main() -> None:
    profiles_path = HERE / "profiles/results.json"
    consumer_path = HERE / "consumer/consumer_result.json"
    profiles = json.loads(profiles_path.read_text())
    names = [item["profile"] for item in profiles]
    if len(names) != 3 or set(names) != {"x86_64_4k", "arm64_4k", "arm64_64k"}:
        raise RuntimeError("expected three unique certified profiles")
    consumer = json.loads(consumer_path.read_text())
    if consumer["geometry_sha256"] != hashlib.sha256(profiles_path.read_bytes()).hexdigest():
        raise RuntimeError("consumer did not use the current geometry artifact")
    if not consumer["passed"]:
        raise RuntimeError("consumer observations not validated")
    observed = {item["profile"]: item["observed"] for item in consumer["results"]}
    if len(consumer["results"]) != 3 or set(observed) != set(names):
        raise RuntimeError("consumer profiles incomplete or duplicated")
    for profile in profiles:
        item = observed[profile["profile"]]
        if (item["order"] != profile["geometry"]["HPAGE_PMD_ORDER"] or
                item["new_order"] != 0 or item["xa_shift"] != 0 or item["xa_chunk_shift"] != 6):
            raise RuntimeError("consumer input differs from the certified split target")
    repo = Path("/root/repos/linux")
    old = base.function(base.git_file(repo, base.FIX + "^"), "bool shmem_is_huge(")
    old = old.replace("bool shmem_is_huge(", "bool old_shmem_is_huge(", 1)
    fixed_source = base.git_file(repo, base.FIX)
    helper = base.function(fixed_source, "static bool __shmem_is_huge(")
    wrapper = base.function(fixed_source, "bool shmem_is_huge(")
    scaffold = base.SCAFFOLD.replace("#define SHMEM_HUGE_DENY 4", "#define SHMEM_HUGE_DENY -1")
    scaffold = scaffold.replace("#define SHMEM_HUGE_FORCE 5", "#define SHMEM_HUGE_FORCE -2")
    # MAX_PAGECACHE_ORDER is the header probe's evaluated value, not a duplicate formula.
    scaffold = scaffold.replace(
        "#define MAX_PAGECACHE_ORDER min(MAX_XAS_ORDER, PREFERRED_MAX_PAGECACHE_ORDER)",
        "#define MAX_PAGECACHE_ORDER CERTIFIED_MAX_PAGECACHE_ORDER")
    dest = HERE / "selection"
    dest.mkdir(exist_ok=True)
    program = dest / "selection.c"
    program.write_text("\n".join((scaffold, old, helper, wrapper, MAIN)))
    results = []
    commands = []
    for profile in profiles:
        name = profile["profile"]
        geometry = profile["geometry"]
        arm = profile["arch"] == "arm64"
        binary = dest / name
        command = ["aarch64-linux-gnu-gcc" if arm else "gcc", "-std=gnu11",
                   "-Wall", "-Wextra", "-Werror", "-Wno-sign-compare",
                   f'-DPAGE_SHIFT={geometry["PAGE_SHIFT"]}',
                   f'-DHPAGE_PMD_SHIFT={geometry["HPAGE_PMD_SHIFT"]}',
                   f'-DXA_CHUNK_SHIFT={geometry["XA_CHUNK_SHIFT"]}',
                   f'-DCERTIFIED_MAX_PAGECACHE_ORDER={geometry["MAX_PAGECACHE_ORDER"]}',
                   str(program), "-o", str(binary)]
        build = subprocess.run(command, capture_output=True, text=True)
        (dest / f"{name}.compile.log").write_text(build.stdout + build.stderr)
        commands.append({"argv": command, "exit_code": build.returncode})
        if build.returncode:
            raise RuntimeError(f"{name}: compilation failed")
        execution = (["qemu-aarch64", "-L", "/usr/aarch64-linux-gnu"] if arm else []) + [str(binary)]
        output = subprocess.run(execution, capture_output=True, text=True, check=True)
        (dest / f"{name}.stdout").write_text(output.stdout)
        commands.append({"argv": execution, "exit_code": output.returncode})
        preallocation_succeeds = observed[name]["xas_error"] == 0
        cases = []
        for line in output.stdout.splitlines():
            label, old_value, fixed_value = line.split()
            intended = label in {"always", "force_argument", "advise"}
            expected_fixed = intended and preallocation_succeeds
            cases.append({"condition": label, "old_selects_pmd": bool(int(old_value)),
                          "fixed_selects_pmd": bool(int(fixed_value)),
                          "policy_intends_pmd": intended,
                          "consumer_split_preallocation_succeeds": preallocation_succeeds,
                          "expected_fixed": expected_fixed,
                          "passed": bool(int(old_value)) == intended and
                                    bool(int(fixed_value)) == expected_fixed})
        if len(cases) != 5 or {case["condition"] for case in cases} != {
                "always", "force_argument", "advise", "never", "nohugepage"}:
            raise RuntimeError(f"{name}: selection conditions incomplete or duplicated")
        results.append({"profile": name, "execution": profile["execution"],
                        "geometry": geometry, "cases": cases})
    report = {"fix": base.FIX, "parent": consumer["parent"],
              "geometry_sha256": consumer["geometry_sha256"],
              "evidence_level": "historical selection bodies with kernel doubles; target binaries",
              "expectation": "three fixed geometries: original policy and independently executed xas_split_alloc preallocation result",
              "cases_total": sum(len(item["cases"]) for item in results),
              "results": results, "commands": commands,
              "passed": all(case["passed"] for item in results for case in item["cases"]),
              "limits": ["no historical kernel boot or actual shmem allocation",
                         "selection and consumer are separate executables; source review supplies intervening path",
                         "not a universal equivalence of pagecache policy and all xarray operations",
                         "known development case, not an independent defect detection"]}
    (dest / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"cases": report["cases_total"], "passed": report["passed"]}))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
