# VT-d in-kernel encoding and page-table contract tests

This experiment boots an x86_64 Linux kernel in QEMU and runs a KUnit suite linked
into the real Intel IOMMU driver. It does not replace the WSL kernel, attach a host
PCI device, perform DMA, or claim to verify an IOMMU hardware enforcement boundary.

## Tested code

Base revision: `6f5dc7658094610debe2fad1b09a2034e14857b1`.
The `before` encoding comes from its parent; `after` comes from the repair commit.
That repair changes only `drivers/iommu/intel/iommu.c`.

`setup.py` moves the original attribute statements into the static helper
`intel_iommu_encode_pte_attr()`, replacing the access to `domain->use_first_level`
with a bool parameter. The production `__domain_mapping()` path and the tests both
call that helper. Constants, integer types, compiler and driver build dependencies
are real kernel code. Unlike the earlier source-slice harness, this test does not
define replacement domain structs, C library wrappers or hardware function stubs.

The current suite adds eight tests using the public mapping API, real Intel domain
operations, allocated page tables and leaf readback. A detached domain fixture
supplies 48-bit addressing, coherent page tables and 4 KiB pages; it does not probe
hardware capabilities. Real cache callbacks run with an empty target list, so no
hardware IOTLB invalidation or device reads/writes are validated.
The first-level WO case characterizes its lack of representability;
expecting RW there is not a declaration that a WO request is safely supported.

## Reproduce in WSL

Requires GCC, make, flex, bison, ELF/OpenSSL development headers, and
`qemu-system-x86` including `qboot.rom`. Commands below are run from the analysis
project. A new dedicated worktree must be clean and at the specified revision.

```bash
git -C /root/repos/linux worktree add --detach /root/lba-vtd-kunit \
  6f5dc7658094610debe2fad1b09a2034e14857b1

python experiments/vtd_kunit/setup.py --worktree /root/lba-vtd-kunit \
  --mode before --outdir analysis_out/vtd-pagetable-kunit
python experiments/vtd_kunit/run_kernel.py --worktree /root/lba-vtd-kunit \
  --build-dir /root/lba-vtd-build --mode before --outdir analysis_out/vtd-pagetable-kunit

python experiments/vtd_kunit/setup.py --worktree /root/lba-vtd-kunit \
  --mode after --outdir analysis_out/vtd-pagetable-kunit
python experiments/vtd_kunit/run_kernel.py --worktree /root/lba-vtd-kunit \
  --build-dir /root/lba-vtd-build --mode after --outdir analysis_out/vtd-pagetable-kunit
python experiments/vtd_kunit/verify.py --pagetable --outdir analysis_out/vtd-pagetable-kunit
```

The runner preserves the KUnit process return code in `*-run.json`, including
expected old-behavior failures. Its own completion does not imply test success:
inspect the boot logs and KUnit JSON. Expected outcome: old behavior fails
`second_level_write_only`, `map_second_wo`, and `map_second_wo_cross_boundary`;
repair passes all 14 cases. The two first-level WO cases characterize permissive
existing behavior, and must not be counted as exact WO support.

`setup.py` marks and hashes the three managed files. It refuses an initially dirty
worktree or later outside edits to managed files. It leaves other files alone.
Generated patches, test source, configurations, full build/boot logs, result JSON
and separate boot images are saved in the output directory. Large output artifacts
are ignored by the analysis project's Git rules. The final dedicated worktree is
left in the repaired state for inspection; there is no automatic commit or push.

## Historical encoding-only run (2026-09-12)

Both kernels booted in QEMU. Old behavior: 5 PASS, 1 FAIL, with only
`second_level_write_only` failing (actual R/W bits `0x3`, expected `0x2`).
Repaired behavior: 6 PASS. The unsupported first-level WO characterization is one
of those six tests, not an additional supported permission combination.

The first build/run took 79.81 seconds; the repaired incremental build/run took
13.85 seconds. They are not comparable performance benchmarks. Identical test-file
and Kconfig hashes and identical generated kernel configurations were verified.
Distinct images and full boot logs were preserved. `vtd-pte-contract.patch` is the
complete repaired-state test/refactoring patch against the fixed base revision;
it includes the new test file and has been reverse-apply checked against the
tested worktree. It is a local experimental patch, not an upstream submission.

## Expanded page-table run (2026-09-12)

Saved separately under `analysis_out/vtd-pagetable-kunit`: before 11 PASS / 3 FAIL,
after 14 PASS; 13.40 and 11.44 seconds respectively (not performance benchmarks).
The API returned success for second-level WO in both kernels; the old leaf had
R/W=3 instead of W=2. The boundary test maps two contiguous physical pages at
IOVA 0x1ff000 and 0x200000, checking both leaf entries across a 2 MiB boundary.
Supported RO/RW, physical-address/offset translation, unmap return sizes and
cleared mappings passed. Zero permissions were rejected with -EINVAL.

First-level WO also returned success and installed RW in both variants. This is
an explicit characterization of the remaining representation boundary, not an
additional fix. Hardware capability negotiation, DMA enforcement, device attach,
large pages, remapping and concurrency remain outside this experiment.

`verify.py --pagetable` checks the exact 14 cases, four expected old assertion
failures (two in the boundary case), no extra kernel warning/oops/panic, identical
test/configuration hashes and distinct image hashes. The old six-case artifacts
remain verifiable without `--pagetable`. `vtd-pagetable-contract.patch` records
the expanded repaired-state experiment; the original patch remains unchanged.
