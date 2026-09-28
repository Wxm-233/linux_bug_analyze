# Representation and lifecycle source-slice experiments

Run fixed Linux history with the same fixture tables on x86_64 little endian
and a statically compiled s390x big-endian executable under qemu-s390x user-mode
emulation. This is not a booted s390 kernel or physical hardware experiment.

```bash
python experiments/representation_lifecycle/run.py --linux-dir /root/repos/linux \
  --outdir analysis_out/representation-lifecycle-new
python experiments/representation_lifecycle/verify.py \
  --outdir analysis_out/representation-lifecycle-new
```

Needs GCC, s390x-linux-gnu-gcc, its static libc development files and qemu-s390x.
The output directory must be new. Compilation uses -O2 -Wall -Wextra -Werror;
only topology adds -Wno-sign-compare to retain the original signed loop counter
and unsigned smp_cpu_mtid. Saved files include historical source, resolved
commit IDs, generated C, build logs, binaries, commands, expected and actual
results, source/artifact hashes and a summary. No model calls or kernel checkout
changes occur. verify.py checks exact failures, ELF byte order and lifecycle
observation points. An experiment completing alone does not establish success.

## Recorded 2026-09-15 results

| Case | Inputs per version/architecture | Old x86 failures | Old s390x failures | Fixed failures on both |
|---|---:|---:|---:|---:|
| NUMA get_nodes input representation | 36 | 3 | 10 | 0 |
| perf typed union configuration | 12 | 0 | 5 | 0 |
| s390 topology notification lifecycle | 12 | 12 | 12 | 0 |

240 executions compare historical parent/fixed slices. Another 48 execute two
explicitly synthetic partial topology repairs, both of which fail all 12 input
sequences on both architectures. Total 288 executions, not 288 vulnerabilities.

## NUMA scope

Fix e130242dc351f1cfa2bbeb6766a1486ce936ef88. Execute the unchanged get_nodes
from each revision; after also includes the real get_bitmap and
compat_get_bitmap. MAX_NUMNODES=128, 64-bit kernel words and 32-bit compat words.
Inputs use 1,31,32,33,63,64 meaningful bits (get_nodes receives maxnode=bits+1),
native/compat layouts, and tight/padded/one-byte-short accessible ranges. Bits
0 and bits-1 are set; the 33-bit input has equal 32-bit halves and is a useful
big-endian negative control. Native and deliberately undersized inputs are
also controls. Bounds are enforced by uaccess test doubles over a local array;
no real user-page mapping or page fault is induced.

IMPORTANT: the old helper is deliberately fed the same raw compat layout as
the new helper. Actual historical compat syscall wrappers could first convert
the input into a temporary native bitmap. This is a direct helper-contract
comparison (also relevant to native helper entry paths), not a reconstruction
of every old compat syscall. In particular, big-endian failures here do not
establish an actual old s390 syscall regression. No copy_nodes_to_user,
odd-output-word corruption, unsupported-node checks, mbind or migration is
tested. Do not extend these results to the full commit's bug coverage.

## perf scope

Fix aa6a6a2d16c1e2e27e986936369959d70316199f. Extract the original term enum,
struct/union layout and full add_config_term constructor from each revision.
Old construction is followed by the original get_config_terms numeric
assignment; new construction passes the value to the typed constructor.
Six fields each have zero and nonzero inputs: overwrite, inherit, time,
max_stack, aux_sample_size and period. Boolean inputs are only 0 or 1.
overwrite uses the original attr.write_backward consumer statement. Other
checks read the named typed member, not a full downstream event configuration.
The real list shape and zero allocation are retained via small host helpers;
list insertion is checked. Strings and allocation failures are not tested.

Old x86 passes all 12; old s390x loses nonzero values in three bool fields,
the int field and u32 field. Full-width u64 values remain correct. New typed
construction passes both. This is actual big-endian instruction execution,
not host byte rearrangement, but it does not run the full perf parser or the
upstream backward-ring-buffer test and does not allocate perf mmap rings.
perf remains a user-space system-tool reference, not an in-kernel bug count.

## Topology scope

Fix a052096bdd6809eeab809202726634d1ac975aa1. Execute the unchanged
cpu_group_map and cpu_thread_map functions. Start/stop sequences are projections
of the real smp_start_secondary and __cpu_disable mask/update/notify operations
in their source order. cpumasks are four-bit sets, CPU0 starts prepared/online,
four CPUs are present, and group info is a synthetic single package. The full
topology discovery/update machinery, locks and scheduler are not executed.
notify_cpu_starting is a recording observer, not the scheduler notifier chain.

HW/PACKAGE/SINGLE modes cross two SMT widths and target CPU1/CPU2. Each sequence
observes first notify, online, offline, then notify after re-add. The contract
requires the target's appropriate group/thread set at notify while it is still
offline, and removal from both masks on teardown. This does not reproduce a
SCHED_CORE crash, rq->core selection or real CPU hotplug.

order_only is a controlled mutant on the fixed base: retain early update and
prepared operations but use online eligibility in the two mapping functions.
mask_only retains fixed eligibility but moves update after set_cpu_online.
They are not historical commits. Both fail the notification contract; the
former also leaves stale online results. This isolates why prepared state and
notification ordering must be repaired together. Running the slice on x86
does not imply that actual x86 topology code has this historical s390 bug.

## Development runs

The first run stopped on an unused harness helper warning; the helper became
inline. The second stopped because extraction matched get_config_terms' forward
declaration; extraction now selects its definition. The third stopped on a
signed-comparison warning in unchanged topology code; the case-specific flag
above resolves it without changing the historical algorithm. The fourth is
the complete matrix; earlier partial executions are excluded from totals.
No expected values were relaxed to make a failure disappear.
