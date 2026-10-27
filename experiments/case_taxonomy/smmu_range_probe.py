"""Run historical ARM SMMUv3 TLBI range encoding with controlled partial edits.

The real __arm_smmu_tlb_inv_range() body is compiled against recording queue
doubles. This does not issue a command to SMMU hardware or run the MMU notifier.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path


FIX = "eb6c97647be227822c7ce23655482b05e348fba5"
DRIVER = "drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.c"
PAGES = (1, 2, 31, 32, 33, 64, 65)
SHIFTS = (12, 14, 16)


def git_file(linux_dir: Path, revision: str, path: str) -> str:
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
    raise ValueError(f"unbalanced function {signature}")


SCAFFOLD = r"""
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
struct arm_smmu_device { unsigned int features; };
struct iommu_domain { unsigned long pgsize_bitmap; };
struct arm_smmu_domain {
    struct arm_smmu_device *smmu;
    struct iommu_domain domain;
};
struct arm_smmu_cmdq_ent {
    struct {
        bool leaf;
        unsigned long tg, ttl, scale, num, addr;
    } tlbi;
};
struct arm_smmu_cmdq_batch { unsigned int num; };
#define ARM_SMMU_FEAT_RANGE_INV 1U
#define CMDQ_TLBI_RANGE_NUM_MAX 31UL
#define __ffs(x) __builtin_ctzl(x)
#define ilog2(x) (63 - __builtin_clzl((unsigned long)(x)))
static struct arm_smmu_cmdq_ent recorded[128];
static unsigned int recorded_count;
static void arm_smmu_cmdq_batch_add(struct arm_smmu_device *smmu,
    struct arm_smmu_cmdq_batch *batch, struct arm_smmu_cmdq_ent *cmd)
{
    (void)smmu;
    if (recorded_count >= 128)
        abort();
    recorded[recorded_count++] = *cmd;
    batch->num++;
}
static void arm_smmu_cmdq_batch_submit(struct arm_smmu_device *smmu,
    struct arm_smmu_cmdq_batch *batch)
{
    (void)smmu; (void)batch;
}
"""


MAIN = r"""
int main(int argc, char **argv)
{
    if (argc != 5)
        return 2;
    unsigned long pages = strtoul(argv[1], NULL, 10);
    unsigned long shift = strtoul(argv[2], NULL, 10);
    bool leaf = strtoul(argv[3], NULL, 10) != 0;
    bool range = strtoul(argv[4], NULL, 10) != 0;
    struct arm_smmu_device smmu = { .features = range ? ARM_SMMU_FEAT_RANGE_INV : 0 };
    struct arm_smmu_domain domain = {
        .smmu = &smmu,
        .domain = { .pgsize_bitmap = 1UL << shift },
    };
    struct arm_smmu_cmdq_ent cmd = { .tlbi = { .leaf = leaf } };
    unsigned long granule = 1UL << shift;
    __arm_smmu_tlb_inv_range(&cmd, 0x100000UL, pages * granule,
                             granule, &domain);
    printf("%u\n", recorded_count);
    for (unsigned i = 0; i < recorded_count; i++) {
        struct arm_smmu_cmdq_ent *entry = &recorded[i];
        printf("%lu %lu %lu %lu %lu %u\n", entry->tlbi.addr,
               entry->tlbi.ttl, entry->tlbi.num, entry->tlbi.scale,
               entry->tlbi.tg, entry->tlbi.leaf);
    }
    return 0;
}
"""


def variants(old: str, fixed: str) -> dict[str, str]:
    added = "else if ((num_pages & CMDQ_TLBI_RANGE_NUM_MAX) == 1)\n\t\t\tnum_pages++;"
    if added not in fixed or added in old:
        raise AssertionError("historical range guard not found as expected")
    single_page = fixed.replace(
        "((num_pages & CMDQ_TLBI_RANGE_NUM_MAX) == 1)",
        "(num_pages == 1)",
        1,
    )
    ttl_only = fixed.replace(
        added,
        "else\n\t\t\tcmd->tlbi.ttl = 4 - ((ilog2(granule) - 3) / (tg - 3));",
        1,
    )
    return {
        "old": old,
        "single_page_only_mutant": single_page,
        "ttl_hint_only_mutant": ttl_only,
        "fixed": fixed,
    }


def assess(commands: list[dict], pages: int, shift: int, leaf: bool, range_mode: bool) -> dict:
    cursor = 0x100000
    invalid_triples = 0
    nonleaf_ttl_errors = 0
    for cmd in commands:
        if cmd["addr"] != cursor:
            raise AssertionError(f"non-contiguous issued range: {cmd}")
        if range_mode:
            if cmd["num"] > 30 or cmd["tg"] != (shift - 10) // 2:
                raise AssertionError(f"out-of-range command field: {cmd}")
            if cmd["ttl"] == cmd["num"] == cmd["scale"] == 0:
                invalid_triples += 1
            covered = (cmd["num"] + 1) << (cmd["scale"] + shift)
            if not leaf and cmd["ttl"] != 0:
                nonleaf_ttl_errors += 1
        else:
            covered = 1 << shift
        cursor += covered
    if cursor < 0x100000 + (pages << shift):
        raise AssertionError("issued commands do not cover requested range")
    return {
        "invalid_ttl_num_scale_zero": invalid_triples,
        "nonleaf_ttl_contract_errors": nonleaf_ttl_errors,
        "requested_pages": pages,
        "covered_pages": (cursor - 0x100000) >> shift,
        "command_count": len(commands),
    }


def run(linux_dir: Path) -> dict:
    before = git_file(linux_dir, FIX + "^", DRIVER)
    after = git_file(linux_dir, FIX, DRIVER)
    signature = "static void __arm_smmu_tlb_inv_range("
    old = function(before, signature)
    fixed = function(after, signature)
    header = git_file(linux_dir, FIX, "drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h")
    if not re.search(r"#define CMDQ_TLBI_RANGE_NUM_MAX\s+31\b", header):
        raise AssertionError("historical range NUM mask is not 31")
    sva = git_file(linux_dir, FIX, "drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3-sva.c")
    if not re.search(r"arm_smmu_tlb_inv_range_asid\(start, size,.*?PAGE_SIZE, false,", sva, re.S):
        raise AssertionError("SVA non-leaf caller path changed")
    if ".tlb_flush_walk = arm_smmu_tlb_inv_walk" not in after:
        raise AssertionError("io-pgtable walk caller path changed")
    for field in ("num", "scale", "ttl"):
        if f"FIELD_PREP(CMDQ_TLBI_{'1' if field == 'ttl' else '0'}_{field.upper()}" not in after:
            raise AssertionError(f"hardware command does not encode {field}")

    cases = []
    with tempfile.TemporaryDirectory(prefix="smmu-range-") as tmp:
        root = Path(tmp)
        for name, body in variants(old, fixed).items():
            program = root / f"{name}.c"
            executable = root / name
            program.write_text("\n".join((SCAFFOLD, body, MAIN)))
            subprocess.run(
                ["cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                 str(program), "-o", str(executable)],
                check=True,
            )
            for shift in SHIFTS:
                for pages in PAGES:
                    for leaf in (False, True):
                        for range_mode in (False, True):
                            output = subprocess.check_output(
                                [str(executable), str(pages), str(shift),
                                 str(int(leaf)), str(int(range_mode))],
                                text=True,
                            ).splitlines()
                            expected_count = int(output[0])
                            commands = []
                            for line in output[1:]:
                                addr, ttl, num, scale, tg, leaf_field = map(int, line.split())
                                commands.append({
                                    "addr": addr, "ttl": ttl, "num": num,
                                    "scale": scale, "tg": tg, "leaf": bool(leaf_field),
                                })
                            if expected_count != len(commands):
                                raise AssertionError("recorded command count mismatch")
                            result = assess(commands, pages, shift, leaf, range_mode)
                            cases.append({
                                "variant": name, "page_shift": shift,
                                "pages": pages, "leaf": leaf,
                                "range_feature": range_mode, **result,
                            })
    if any(
        item["invalid_ttl_num_scale_zero"] or item["nonleaf_ttl_contract_errors"]
        for item in cases if item["variant"] == "fixed"
    ):
        raise AssertionError("fixed version violates a command contract")
    by_key = {
        (item["variant"], item["page_shift"], item["pages"],
         item["leaf"], item["range_feature"]): item
        for item in cases
    }
    for shift in SHIFTS:
        for pages in PAGES:
            for leaf in (False, True):
                for range_mode in (False, True):
                    if not leaf and range_mode and pages in (1, 33, 65):
                        continue
                    old_case = by_key[("old", shift, pages, leaf, range_mode)]
                    fixed_case = by_key[("fixed", shift, pages, leaf, range_mode)]
                    for field in (
                        "invalid_ttl_num_scale_zero", "nonleaf_ttl_contract_errors",
                        "covered_pages", "command_count",
                    ):
                        if old_case[field] != fixed_case[field]:
                            raise AssertionError(f"normal control changed: {old_case}, {fixed_case}")
    return {
        "fix": FIX,
        "evidence_level": "historical SMMU range function with recording queue doubles; no device execution",
        "source_caller": "SVA MMU notifier and io-pgtable .tlb_flush_walk traced, not executed",
        "cases_total": len(cases),
        "cases": cases,
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
