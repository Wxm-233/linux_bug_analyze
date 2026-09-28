# Boundary contract source-slice experiments

Three additional historical cases, executed as small C programs compiled with
GCC `-O2 -Wall -Wextra -Werror`. No paid API, kernel checkout mutation, mount,
device access or architecture emulation is required. Outputs must be ignored.

```bash
python experiments/boundary_contracts/run.py --linux-dir /root/repos/linux \
  --outdir analysis_out/boundary-contracts-new
python experiments/boundary_contracts/verify.py \
  --outdir analysis_out/boundary-contracts-new
```

The output directory must not already exist. Full historical source files,
resolved commit IDs, hashes, generated harnesses, build logs, executables,
explicit fixture tables, expected/actual values and summaries are saved. The
verifier checks hashes and exact counterexample locations, not just totals.

| Case | Fixed commit prefix | Scenarios per version | Old violations | Fixed violations |
|---|---|---:|---:|---:|
| Btrfs max_inline | 6f93e834fa7c | 18 | 5 | 0 |
| fbnic page fragments | 4bd451f4c285 | 18 | 12 | 0 |
| parisc scheduler clock policy | d97180ad68bd | 14 | 10 | 0 |

Recorded 2026-09-15: 50 scenarios per version, 100 executions total. These are
three historical issues, not 100 vulnerabilities or independent samples.

## What is real and what is a double

**Btrfs:** extracts the literal default assignment from `btrfs_init_fs_info`,
the geometry assignments and parser call in their `open_ctree` source order,
and the real nonzero max_inline clamp block from `super.c`. The harness is a
data-dependency projection, not the entire mount function. It supplies parsed
numeric options and a logical superblock; allocation, option string parsing,
feature validation and real mount I/O are omitted. Cases cross 4K/64K geometry
with zero, below-boundary, at-boundary and above-boundary requests. The contract
is the historical numeric option clamp, not all current Btrfs validity rules.

**fbnic:** executes the full unchanged `fbnic_bd_prep` and original descriptor
mask macros. DMA address lookup returns a supplied aligned address; descriptor
storage is a 128-entry host array initialized with sentinels. 4K,16K,64K pages,
three page IDs and two addresses check every descriptor and untouched slots.
Expected output independently enumerates consecutive 4K chunks and unique IDs.
`cpu_to_le64` is identity on this x86 little-endian host; this does not test
big-endian code generation. Larger pages are synthetic parameter inputs, not
supported-device runtime evidence. No packet processing or ring wrap test.

**parisc:** executes the full unchanged `init_cr16_clocksource`; projects only
`setup_arch`'s call to clear_sched_clock_stable, whose presence is checked in
each revision. Topology, online enumeration, guest flag and registration are
doubles. Clearing stability is observed as a call count; actual scheduler
static-key and clocksource registration internals are not executed. Seven
topologies under two policy environments check flags, rating and clear calls.
This verifies consistency with the historical topology policy, not that clock
signals on physical CPUs are synchronized. No PA-RISC instruction execution.

The first development run stopped because the extractor incorrectly expected
the Btrfs default assignment inside open_ctree. Source inspection located it
in btrfs_init_fs_info, called by the mount path before open_ctree. Correcting
the extractor allowed the unchanged expected fixture table to run. That failed
setup is not counted as an old-kernel contract failure.

## Mechanism implications

Require geometry readiness before consuming options; enumerate device chunks
through a checked shared layout/iterator; derive capability declarations from
the same validated policy used by the underlying provider. These experiments
validate historical repair behavior, not a newly installed protection layer.
