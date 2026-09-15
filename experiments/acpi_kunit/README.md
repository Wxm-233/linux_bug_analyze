# ACPI early-boot contract experiment

This experiment boots a real x86_64 kernel once per fixture and checks its actual
`cpu_possible_mask`, `cpu_present_mask`, `cpu_online_mask`, and `cpuid_to_apicid`.
It uses real ACPI record parsers and the real topology registration/finalization
path, rather than the logical registration doubles in `acpi_contracts`.

Run only in isolated QEMU. The dedicated test worktree intentionally requires
`CONFIG_LBA_ACPI_CONTRACT_TEST`; it is not a production kernel patch.

## How the fixture works

QEMU q35 starts one CPU with eight maximum CPU slots. Its MADT must contain eight
contiguous 8-byte LAPIC records. The early fixture verifies that layout before
replacing exactly those 64 bytes. It retains all non-CPU records and total table
length and updates the MADT checksum. A failed injection fails KUnit.

The replacement is either eight LAPIC records (four valid IDs plus invalid-ID
padding), or four 16-byte x2APIC records. APIC 0 is the only enabled CPU. No test
tries to start a nonexistent secondary CPU. FADT major/minor and MADT revision
are injected before the actual capability-detection code runs.

| IDs / fixture | modern ACPI 6.3 | legacy ACPI 6.2 |
|---|---|---|
| 0 | enabled | enabled |
| 1 | online capable | disabled |
| 2 | disabled / not online capable | disabled |
| 3 | online capable | disabled |

Eight boot scenarios: modern, legacy native-policy, legacy guest-policy, legacy
MADT45 guest-policy; each uses LAPIC and x2APIC separately. Expected possible APIC
sets are `{0,1,3}`, `{0}`, `{0,1,2,3}`, `{0,1,2,3}` respectively. Present and online
sets must always contain only CPU 0. The policy's hypervisor query is the only
environment override: QEMU is never claimed to become bare-metal hardware.

## Controlled before/after comparison

Base is `adbf61cc47cb72b102682e690ad323e1eda652c2`. Before mode replaces only
`acpi_is_processor_usable()` with the original parent-revision predicate; all
other topology code stays at the fixed base. After mode uses the fixed predicate,
with its hypervisor query routed to the test environment selector. This isolates
the predicate and is **not** a comparison of complete historical kernels (the
upstream commit also changed another topology check).

Both modes use identical fixture/test/configuration files. The old predicate is
expected to retain disabled legacy native-policy entries, failing the CPU-mask
and APIC-membership tests in scenarios 2 and 3. Other scenarios should pass.

## Reproduce

Requires Python, GCC and kernel build dependencies, QEMU x86 with SeaBIOS. The
x2APIC Kconfig option needs HYPERVISOR_GUEST or IRQ_REMAP; the supplied config
selects HYPERVISOR_GUEST. Default execution uses TCG and needs no host device.

```bash
git -C /root/repos/linux worktree add --detach /root/lba-acpi-kunit \
  adbf61cc47cb72b102682e690ad323e1eda652c2
python experiments/acpi_kunit/setup.py --worktree /root/lba-acpi-kunit \
  --mode before --outdir analysis_out/acpi-kunit-new
python experiments/acpi_kunit/run.py --worktree /root/lba-acpi-kunit \
  --build-dir /root/lba-acpi-build --mode before --outdir analysis_out/acpi-kunit-new
python experiments/acpi_kunit/setup.py --worktree /root/lba-acpi-kunit \
  --mode after --outdir analysis_out/acpi-kunit-new
python experiments/acpi_kunit/run.py --worktree /root/lba-acpi-kunit \
  --build-dir /root/lba-acpi-build --mode after --outdir analysis_out/acpi-kunit-new
python experiments/acpi_kunit/verify.py --outdir analysis_out/acpi-kunit-new
```

Setup refuses an unmarked dirty worktree or externally modified managed files.
Artifacts include complete source patches, source hashes, build logs, separate
images/configurations, command lines and boot logs. The runner finishing does
not prove KUnit passed; use the verifier to check exact expected failures and
matching test/configuration hashes. Default runs cover all eight scenarios;
`--scenarios 0` is a diagnostic pilot, not the complete matrix.

## Limits

Recorded local run (2026-09-14): eight scenarios per mode, 16 boots total.
Before: 20 checks passed and four expected failures (mask and membership in
both legacy native-policy entry paths). After: all 24 checks passed. Artifact
hashes and exact failure positions passed `verify.py`. Only CPU 0 was present
and online in every boot. This compares isolated predicates on the fixed base,
not complete historical kernels. Runtime artifacts are ignored by Git.

The firmware data and policy environment are synthetic. This does not validate a
vendor BIOS, physically hotplug CPUs, compare actual native and guest hardware,
or validate malformed/duplicate/mixed-order table handling. It exercises the
LAPIC and x2APIC entry paths in separate boots, not both within one mixed table.
It validates real possible/present/online sets, not per-CPU memory usage. The
host WSL kernel and main Linux checkout remain unchanged.
