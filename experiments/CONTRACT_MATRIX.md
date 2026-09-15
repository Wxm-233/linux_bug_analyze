# Exploratory contract matrix

Status: 2026-09-15. Nine historical cases have prototypes. This is a research
index, not a set of deployed kernel protections or a vulnerability count.

Follow-up status: NUMA now also has a 32-input native/compat entry-conversion
chain experiment with real mmap protection (96 executions over three profiles).
It reveals limits beyond the earlier small-input matrix: five old compat-tail
misses, twelve unified-profile mismatches, four remaining after a controlled
historical index backport. See numa_entry/README.md; no real old kernel syscall
is claimed. The eight-commit local holdout pilot adds one small explicit-context
transfer experiment (old 4/8 mismatch, fixed 0/8). It is separate from the nine
primary case prototypes. After explicit user approval, the eight new samples
also completed model screening: nine requests, 78,505 tokens; one contract-related
case retained, six controls excluded by the model (one restored to review due
to truncation), and the scope-uncertain case excluded. This is not a statistical
accuracy claim. Original frozen inputs and the local-only audit remain preserved.

| Case / repair | Boundary and invariant | Check location | Positive/negative controls | Current evidence | Missing evidence |
|---|---|---|---|---|---|
| Btrfs 6f93e834fa7c | Geometry must be ready before max_inline consumes it | Option parsing after superblock geometry initialization | 4K/64K, zero/above-limit values | Source-order projection, 18 cases/version | Full mount and disk validation |
| fbnic 4bd451f4c285 | Each system page maps to all unique device fragments | Descriptor construction and neighboring slots | 4K/16K/64K, IDs and aligned addresses | Whole preparation function, 18 cases/version | Supported configuration and device execution |
| parisc d97180ad68bd | Scheduler stability declaration agrees with clocksource policy | Initialization and capability reporting | 7 topologies, native/guest policy | Whole initializer plus setup-call projection, 14 cases/version | Physical clock measurements, scheduler implementation |
| VT-d 6f5dc7658094 | Supported paging mode preserves requested R/W permissions | Public mapping call to actual leaf PTE | Paging modes and permission combinations | QEMU kernel page-table checks, 14 cases/version | Device DMA, hardware IOTLB; unsupported requests need negotiation |
| ARM SMMU 8c73c32c83ce | Domain transition never violates permitted intermediate access | Each table-write transition and failure path | Attach/release/failure/direct-map policies | Real function with state/hardware doubles, 14 cases/version | Device-visible ordering, concurrency and actual DMA |
| ACPI adbf61cc47cb + history | Resource acceptance follows authoritative capability/version and scoped compatibility | LAPIC/x2APIC parsing to final CPU sets | Modern/legacy/native-policy/guest-policy | 6 historical source profiles; 8 kernel boots per predicate mode | Physical hotplug, mixed records and malformed firmware |
| NUMA e130242dc351 | User ABI width, accessible span and node meaning are preserved | Bitmap conversion and get_nodes | Native/compat, six bit counts, three buffer bounds | 36 helper cases/version/endianness | Full historical syscall wrappers, actual protected pages and unsupported bits |
| perf aa6a6a2d16c1 | Tag, written union member and consumer type agree | Constructor to typed member/write_backward | Six fields, zero/nonzero, LE/BE | 12 cases/version/endianness, s390x user emulation | Full parser, backward ring buffer, allocation failures; user-space scope |
| s390 topology a052096bdd68 | Prepared topology exists at notify, before online; teardown removes it | Start/stop to notifier observation | 12 sequences/endianness and 2 partial-repair mutants | Whole mask functions, lifecycle projection, LE/BE execution | Real kernel notifier chain, rq->core and concurrent hotplug |

## Common record and acceptance rules

Each experiment must identify provider, consumer, value representation, capability
source, applicability conditions, intermediate states, failure behavior, equivalent
entry points and observed output. Record exact source revisions and test doubles.

1. Preserve legitimate behavior on ordinary supported configurations.
2. Reject or flag a request that cannot be represented under the stated contract.
3. Check the state at consumption, not merely after the operation finishes.
4. Require an old counterexample and fixed behavior on the same independent oracle.
5. Include partial repairs where feasible; distinguish mutants from history.
6. Count distinct historical cases separately from input combinations and executions.

## Evaluation protocol frozen before the next input expansion

NUMA phase 2 will execute native and compat set_mempolicy entry wrappers through
the real kernel_set_mempolicy/get_nodes chain, ending at a recording policy sink.
Protected mmap pages will expose overreads, with signal recovery only in uaccess
doubles. This is the complete selected conversion entry chain, not a real old
kernel syscall. A current-host syscall check can separately test environment
availability without pretending to run the old kernels.

Frozen oracle: low supported bits survive; set bits inside the declared extent
but beyond the configured node capacity must be rejected; zero extension inside
that extent must be accepted; bits outside the declared extent must not affect
the decision; access must not exceed the ABI-aligned declared bitmap storage.
Invalid/short input may fail, but must not reach the policy sink. Test the same
rules on new bit-count boundaries without tuning acceptance after seeing output.

Follow-up historical fixes found during development are discovery evidence,
not an independent blind validation set. Holdout examples must be selected and
recorded before labeling, exclude prior reviewed commits, retain normal controls,
and report model versus deterministic guard outputs separately. No broad accuracy
claim is warranted until sufficient independent review exists.
