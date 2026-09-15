# ACPI CPU usability contract prototype

This offline experiment compiles unchanged historical LAPIC/x2APIC parser
functions and, where present, `acpi_is_processor_usable()` from six fixed Linux
commits. It extracts the original MADT/FADT capability-detection statement into
a wrapper. ACPI flag constants come from each revision's `actbl2.h`.

Run in WSL from the project root (Python 3 and GCC required; no model calls):

```bash
python experiments/acpi_contracts/run.py --linux-dir /root/repos/linux \
  --outdir analysis_out/acpi-contract-new-run
```

The output directory must not already exist. The runner saves original source
snapshots, extracted slices, complete generated C, compiler logs, executables,
individual observations and expectations, a summary, and artifact SHA-256 hashes.
The source extractor is shared with `experiments/iommu_contracts/run.py`.

## Contract and cases

The fixtures specify accepted flag values independently of the historical code.
Modern ACPI accepts Enabled or Online Capable CPUs. For legacy ACPI, the chosen
2025 compatibility policy accepts disabled entries for guests but not bare metal.
The latter is a Linux compatibility policy, not a universal ACPI requirement.
The original 2025 predicate checks non-native hypervisors, not QEMU identity only.

Five version scenarios: ACPI 6.2 / MADT 4, ACPI 6.2b / MADT 45, ACPI 6.3 / MADT 5,
ACPI 6.4 / MADT 5, and a synthetic future major 7 / MADT 5. The 6.2b association
comes from upstream commit a74fabfbd1b7, not independent firmware measurement.
Each covers bare metal/guest and LAPIC/x2APIC; legacy uses flags 0/1 and modern
uses 0/1/2. Reserved-bit combinations are excluded. Total: 52 cases per revision.

The positive control requires enabled CPUs to be accepted in every revision.
Named negative controls check the LAPIC-only gap, MADT 45 misclassification,
legacy guest rejection, and excessive legacy bare-metal acceptance. These gates
must pass before the experiment reports success. Historical mismatch counts are
comparisons against this explicitly chosen policy, not numbers of vulnerabilities.

## Recorded results (2026-09-14)

| Profile | Revision | Acceptance mismatches | Capability mismatches | All fields match |
|---|---|---:|---:|---:|
| before | aa06e20f1be6 parent | 16 | 36 | 12/52 |
| lapic_only | aa06e20f1be6 | 10 | 8 | 36/52 |
| both_madt | e2869bd7af60 | 4 | 8 | 42/52 |
| both_fadt | a74fabfbd1b7 | 4 | 0 | 48/52 |
| legacy_all | fed8d8773b8e | 4 | 0 | 48/52 |
| guest_scoped | adbf61cc47cb | 0 | 0 | 52/52 |

Final artifacts: `analysis_out/acpi-contract-20260914-v2`. Acceptance and capability
mismatches can overlap and must not be added. The two 4-mismatch profiles fail
different environments, so aggregate counts alone hide the changed behavior.

## Limits

This does not boot Linux, parse binary firmware tables, hotplug CPUs, or measure
per-CPU allocation. Structures are minimal logical doubles, table-bound checks
are assumed valid, IDs are valid and unique, and logging/APIC/hypervisor calls are
substituted. Mixed LAPIC/x2APIC duplicate-ID and ordering policies are outside scope.
Each process handles one entry, not a complete MADT.

Historical `acpi_register_lapic()` executes for the first five profiles, with
processor-registration dependencies replaced. The 2025 profile uses a recording
`topology_register_apic()` double. Counts are normalized observations of accepted
enabled/disabled registrations, not actual `cpu_possible_mask` or online CPUs.
Full `prefill_possible_map()`, boot limits and topology allocation do not execute.

GCC enables `-Wall -Wextra -Werror`; only unused shared fixture functions/variables
are exempted. No extracted historical C was changed to achieve the result.
The first run's final positive-control assertion conflated capability detection
with acceptance; the runner corrected that assertion and reran all cases in a
new directory, preserving the first run. The historical parser code was unchanged.

References: [initial fix](https://github.com/torvalds/linux/commit/aa06e20f1be628186f0c2dcec09ea0009eb69778),
[version source fix](https://github.com/torvalds/linux/commit/a74fabfbd1b7013045afc8cc541e6cab3360ccb5),
[legacy compatibility](https://github.com/torvalds/linux/commit/fed8d8773b8ea68ad99d9eee8c8343bef9da2c2c),
[guest-scoped compatibility](https://github.com/torvalds/linux/commit/adbf61cc47cb72b102682e690ad323e1eda652c2).
