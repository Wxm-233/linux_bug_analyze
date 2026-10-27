"""Run the old and fixed shmem_is_huge() bodies against page-order profiles.

This compiles the functions extracted from the historical kernel commit with
small doubles for their surrounding kernel types/macros. It does not build or
boot either historical kernel or exercise xarray splitting.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path


FIX = "9fd154ba926b34c833b7bfc4c14ee2e931b3d743"
SOURCE = "mm/shmem.c"


def git_file(linux_dir: Path, revision: str, path: str = SOURCE) -> str:
    return subprocess.check_output(
        ["git", "-C", str(linux_dir), "show", f"{revision}:{path}"],
        text=True,
    )


def function(source: str, signature: str) -> str:
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 0
    for pos in range(opening, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start : pos + 1]
    raise ValueError(f"unbalanced function: {signature}")


SCAFFOLD = r"""
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/stat.h>
typedef unsigned long pgoff_t;
typedef long long loff_t;
struct shmem_sb_info { int huge; };
struct super_block { struct shmem_sb_info info; };
struct inode { unsigned int i_mode; struct super_block *i_sb; long long size; };
struct mm_struct { unsigned long flags; };
#define SHMEM_SB(sb) (&(sb)->info)
#define SHMEM_HUGE_NEVER 0
#define SHMEM_HUGE_ALWAYS 1
#define SHMEM_HUGE_WITHIN_SIZE 2
#define SHMEM_HUGE_ADVISE 3
#define SHMEM_HUGE_DENY 4
#define SHMEM_HUGE_FORCE 5
#define VM_NOHUGEPAGE 1UL
#define VM_HUGEPAGE 2UL
#define MMF_DISABLE_THP 0
#define test_bit(n,p) (((*(p)) >> (n)) & 1UL)
#define i_size_read(inode) ((inode)->size)
#define round_up(x,y) ((((x) + (y) - 1) / (y)) * (y))
#define fallthrough __attribute__((fallthrough))
#define PAGE_SIZE (1UL << PAGE_SHIFT)
#define HPAGE_PMD_ORDER (HPAGE_PMD_SHIFT - PAGE_SHIFT)
#define HPAGE_PMD_NR (1UL << HPAGE_PMD_ORDER)
#define min(a,b) ((a) < (b) ? (a) : (b))
#define MAX_XAS_ORDER (XA_CHUNK_SHIFT * 2 - 1)
#define PREFERRED_MAX_PAGECACHE_ORDER HPAGE_PMD_ORDER
#define MAX_PAGECACHE_ORDER min(MAX_XAS_ORDER, PREFERRED_MAX_PAGECACHE_ORDER)
static int shmem_huge = SHMEM_HUGE_NEVER;
"""


MAIN = r"""
int main(void)
{
    struct super_block sb = { .info = { .huge = SHMEM_HUGE_ALWAYS } };
    struct inode inode = { .i_mode = S_IFREG, .i_sb = &sb, .size = 1LL << 30 };
    struct mm_struct mm = { .flags = 0 };
    struct {
        const char *name;
        int policy;
        bool force;
        unsigned long vm_flags;
        bool expect_old;
    } cases[] = {
        {"always", SHMEM_HUGE_ALWAYS, false, 0, true},
        {"force", SHMEM_HUGE_NEVER, true, 0, true},
        {"advise", SHMEM_HUGE_ADVISE, false, VM_HUGEPAGE, true},
        {"never", SHMEM_HUGE_NEVER, false, 0, false},
        {"nohugepage", SHMEM_HUGE_ALWAYS, false, VM_NOHUGEPAGE, false},
    };
    int failed = 0;
    for (unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        sb.info.huge = cases[i].policy;
        bool old_result = old_shmem_is_huge(&inode, 0, cases[i].force,
                                            &mm, cases[i].vm_flags);
        bool fixed_result = shmem_is_huge(&inode, 0, cases[i].force,
                                          &mm, cases[i].vm_flags);
        bool expected_fixed = (HPAGE_PMD_ORDER <= MAX_PAGECACHE_ORDER) &&
                              cases[i].expect_old;
        if (old_result != cases[i].expect_old ||
            fixed_result != expected_fixed)
            failed++;
        printf("%s %d %d %d\n", cases[i].name, old_result,
               fixed_result, expected_fixed);
    }
    return failed ? 1 : 0;
}
"""


PROFILES = (
    ("4k_normal", 12, 21, 6),
    ("64k_normal", 16, 29, 6),
    ("4k_base_small", 12, 21, 4),
    ("64k_base_small", 16, 29, 4),
)


def run(linux_dir: Path) -> dict:
    pagemap = git_file(linux_dir, FIX, "include/linux/pagemap.h")
    xarray = git_file(linux_dir, FIX, "include/linux/xarray.h")
    for definition in (
        "#define MAX_XAS_ORDER\t\t(XA_CHUNK_SHIFT * 2 - 1)",
        "#define MAX_PAGECACHE_ORDER\tmin(MAX_XAS_ORDER, PREFERRED_MAX_PAGECACHE_ORDER)",
    ):
        if definition not in pagemap:
            raise AssertionError(f"historical pagecache macro changed: {definition}")
    if "(IS_ENABLED(CONFIG_BASE_SMALL) ? 4 : 6)" not in xarray:
        raise AssertionError("historical xarray chunk rule changed")
    old = function(git_file(linux_dir, FIX + "^"), "bool shmem_is_huge(")
    fixed_source = git_file(linux_dir, FIX)
    fixed_helper = function(fixed_source, "static bool __shmem_is_huge(")
    fixed_wrapper = function(fixed_source, "bool shmem_is_huge(")
    old = old.replace("bool shmem_is_huge(", "bool old_shmem_is_huge(", 1)
    source = "\n".join((SCAFFOLD, old, fixed_helper, fixed_wrapper, MAIN))

    results = []
    with tempfile.TemporaryDirectory(prefix="shmem-pagecache-") as tmp:
        root = Path(tmp)
        program = root / "probe.c"
        program.write_text(source)
        for name, page_shift, pmd_shift, chunk_shift in PROFILES:
            executable = root / name
            subprocess.run(
                [
                    "cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                    "-Wno-sign-compare",
                    f"-DPAGE_SHIFT={page_shift}",
                    f"-DHPAGE_PMD_SHIFT={pmd_shift}",
                    f"-DXA_CHUNK_SHIFT={chunk_shift}",
                    str(program), "-o", str(executable),
                ],
                check=True,
            )
            output = subprocess.check_output([str(executable)], text=True)
            cases = []
            for line in output.splitlines():
                label, old_value, fixed_value, expected_value = line.split()
                cases.append(
                    {
                        "condition": label,
                        "old_selects_pmd": bool(int(old_value)),
                        "fixed_selects_pmd": bool(int(fixed_value)),
                        "expected_fixed": bool(int(expected_value)),
                    }
                )
            pmd_order = pmd_shift - page_shift
            max_order = min(chunk_shift * 2 - 1, pmd_order)
            results.append(
                {
                    "profile": name,
                    "page_shift": page_shift,
                    "pmd_order": pmd_order,
                    "max_pagecache_order": max_order,
                    "cases": cases,
                }
            )
    return {
        "fix": FIX,
        "source": SOURCE,
        "evidence_level": "historical function bodies with kernel-environment doubles",
        "cases_total": sum(len(item["cases"]) for item in results),
        "profiles": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--linux-dir", type=Path, default=Path("/root/repos/linux"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(args.linux_dir)
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end="")
