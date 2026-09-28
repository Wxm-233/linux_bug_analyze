# IOMMU source-slice contract experiment

This is an offline executable analysis, not a kernel module, a hardware simulator,
an exploit, or an installed runtime defense. It makes no API calls and changes no
Linux repository files. Run in WSL with Python 3 and GCC:

```bash
python experiments/iommu_contracts/run.py \
  --linux-dir /root/repos/linux \
  --outdir analysis_out/contract-prototype
```

The revisions are intentionally fixed in `run.py`. Each parent and repaired
revision is compiled separately with `-Wall -Wextra -Werror`. Full source snapshots,
resolved commit IDs and hashes are recorded alongside generated C and results.

## What actually executes

- VT-d: the original public-to-driver permission conversion and attribute encoding
  statements, with constants taken from that revision's headers. Domain fields and
  the calling wrapper are test scaffolding. Allocation, page-table insertion,
  invalidation and actual device permissions are not executed.
- SMMUv3: the complete original `arm_smmu_detach_dev`, `arm_smmu_attach_dev`, and
  `arm_smmu_release_device` functions. Locks, lists, allocations, ATS, context writes,
  frees and hardware operations use test doubles. STE installation records a logical
  state; it does not model partial writes, command completion, TLBs or concurrency.

SMMU state 0 means inaccessible (including an empty translated blocking domain),
1 means bypass and 2 means target translated domain. State 0 must not be read as
proof that the core's blocking fallback has a literal ABORT STE. The direct-mapping
test assumes the target translated domain has its required identity mappings; this
experiment does not construct or verify them.

## Oracles and scope

VT-d checks exact R/W preservation for supported combinations. First-level WO is
reported as unsupported, never as a pass. Explicit rejection or negotiation is a
proposed API policy, not implemented here or asserted to be current Linux behavior.

SMMU tests seven scenarios with `disable_bypass` false/true: isolated→S2,
identity→DMA-with-direct, S1 allocation failure, S1 context-write failure, SVA
preflight rejection, release without/with required direct mappings. Faults are
injected through test doubles. The original control flow handles their return
values. Tests check prefixes as well as final state and return code.

The whole IOMMU group rollback path is not executed. Public core code already
documents old/new-domain confinement during transition and can attempt reattachment
after failure. Thus failed-attach observations here are driver-local, not proof of
an indefinitely exposed device after full core recovery. Direct-map continuity is
an additional resource-specific condition, not a universal no-DMA-loss contract.

Results observed on 2026-09-12: VT-d old 1/5 supported combinations mismatched,
fixed 0/5; one unsupported combination per revision was reported separately.
SMMU old 5/14 scenarios violated the tested conditions, fixed 0/14. These are finite
scenario counts, not vulnerability counts or proof of complete safety.

`tests/test_iommu_contracts.py` includes negative controls for lost write permission,
transient bypass, interrupted direct mappings, missing final state and invalid
traces. It also tests extraction through comments and strings. The full test suite
can be run with `python -m unittest discover -s tests -q`.
