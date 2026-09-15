# NUMA entry-chain boundary experiment

Execute the actual historical native/compat set_mempolicy entry bodies,
kernel_set_mempolicy, sanitize_mpol_flags, get_nodes and compat bitmap helper.
The policy sink records the accepted node mask. It does not modify real task
policy. Macros turn syscall definitions into ordinary C functions; this is not
a booted historical kernel, system-call dispatcher or actual compat process.

Input is placed at the end of a readable mmap page followed by a PROT_NONE page.
Uaccess doubles copy bytes and recover SIGSEGV/SIGBUS to EFAULT; they do not
pre-reject based on a synthetic accessible-length comparison. Short-input
controls verify that the physical page boundary and signal recovery work.
Temporary user-stack allocation is a host buffer, and configured capacity is
64 nodes. This is a deeper selected entry conversion chain than the earlier
get_nodes-only slice, but still a userspace harness with explicit doubles.

```bash
python experiments/numa_entry/run.py --linux-dir /root/repos/linux \
  --outdir analysis_out/numa-entry-new
python experiments/numa_entry/verify.py --outdir analysis_out/numa-entry-new
```

32 fixtures/version: nine meaningful bit counts, native/compat, zero or nonzero
unsupported tail where applicable, plus four short-input controls. Expected
results were frozen before execution. Three source profiles:

- before: e130242dc351 parent, including the old compat conversion wrapper.
- unified: e130242dc351, full selected input conversion chain.
- followup: keep unified entry chain, replay only get_nodes from 000eca5d044d.
  The code asserts it differs by the exact single historical index correction.
  This is a controlled backport, not the complete 2022 kernel; its compat wrapper
  had already been removed. Original and entry-base sources are both saved.

2026-09-15 results: before 27/32 pass (five ignored unsupported compat tails),
unified 20/32 pass (12 boundary mismatches), followup 28/32 pass (four unresolved
partial-compat-word boundary mismatches). All small <=64-bit ordinary entry cases
pass even in before, because its wrapper converts the representation. This
corrects any inference that earlier direct-helper results applied to every
historical compat syscall.

Do not infer a new real-kernel defect from the four unresolved cases. The chosen
oracle expects only ABI-rounded declared storage. Further review of actual
entry contracts, access rules, supported node configurations and current kernel
behavior is required. Keep these mismatches visible rather than changing the
oracle to force a pass. No copy-out or migration test is included.

First development run stopped at the later kernel's removed compat wrapper.
The final run explicitly fixes the entry baseline as described above. The
follow-up historical fix was discovered during development, not blind holdout
evidence. No paid model calls are needed.
