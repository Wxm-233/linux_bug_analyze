"""Run historical perf has_die_topology() on x86_64 and qemu-s390x.

Uses temporary sysfs-shaped fixtures; it does not build perf or boot s390 Linux.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path


FIX = "a6e62743621ea29bea461774c0bcc68e5de59068"
PATH = "tools/perf/util/cputopo.c"


def git_file(linux_dir: Path, revision: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(linux_dir), "show", f"{revision}:{PATH}"],
        text=True,
    )


def function(source: str) -> str:
    start = source.index("static bool has_die_topology(void)")
    opening = source.index("{", start)
    depth = 0
    for pos in range(opening, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start : pos + 1]
    raise ValueError("unbalanced has_die_topology")


def die_path_macro(source: str) -> str:
    lines = source.splitlines()
    for pos, line in enumerate(lines):
        if line.startswith("#define DIE_CPUS_FMT"):
            return line + "\n" + lines[pos + 1]
    raise ValueError("DIE_CPUS_FMT missing")


HEADER = r"""
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/utsname.h>
#include <sys/param.h>
static const char *fixture_root;
static const char *sysfs__mountpoint(void) { return fixture_root; }
#define scnprintf snprintf
"""


MAIN = r"""
int main(int argc, char **argv)
{
    struct utsname uts;
    if (argc != 2 || uname(&uts))
        return 2;
    fixture_root = argv[1];
    printf("%s %d\n", uts.machine, has_die_topology());
    return 0;
}
"""


def run(linux_dir: Path) -> dict:
    old_source = git_file(linux_dir, FIX + "^")
    fixed_source = git_file(linux_dir, FIX)
    old = function(old_source)
    fixed = function(fixed_source)
    if "s390x" in old or "s390x" not in fixed:
        raise AssertionError("unexpected historical architecture predicate")
    results = []
    with tempfile.TemporaryDirectory(prefix="perf-die-predicate-") as tmp:
        root = Path(tmp)
        absent = root / "absent"
        present = root / "present"
        absent.mkdir()
        die_file = present / "devices/system/cpu/cpu0/topology/die_cpus_list"
        die_file.parent.mkdir(parents=True)
        die_file.write_text("0-1\n")

        for version, source in (("old", old), ("fixed", fixed)):
            program = root / f"{version}.c"
            program.write_text(
                "\n".join((HEADER, die_path_macro(fixed_source), source, MAIN))
            )
            for arch, compiler, runner in (
                ("x86_64", "cc", []),
                ("s390x", "s390x-linux-gnu-gcc", ["qemu-s390x"]),
            ):
                executable = root / f"{version}-{arch}"
                subprocess.run(
                    [compiler, "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                     "-static", str(program), "-o", str(executable)],
                    check=True,
                )
                for fixture_name, fixture in (("absent", absent), ("present", present)):
                    output = subprocess.check_output(
                        [*runner, str(executable), str(fixture)], text=True
                    ).split()
                    machine, decision = output[0], bool(int(output[1]))
                    expected = fixture_name == "present" and (
                        version == "fixed" or machine.startswith("x86_64")
                    )
                    if machine != arch or decision != expected:
                        raise AssertionError(
                            f"unexpected {version}/{arch}/{fixture_name}: {output}"
                        )
                    results.append(
                        {
                            "version": version,
                            "emulated_machine": machine,
                            "die_sysfs_fixture": fixture_name,
                            "has_die_topology": decision,
                        }
                    )
    return {
        "fix": FIX,
        "evidence_level": "historical perf function on native x86_64 and qemu-s390x user mode, synthetic sysfs",
        "cases_total": len(results),
        "cases": results,
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
