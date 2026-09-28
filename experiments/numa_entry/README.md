# NUMA entry-chain boundary experiment

## 2026-09-21 boundary review and real syscall follow-up

The previous four unresolved slice results are **not four confirmed kernel
defects**. `boundary_review.py` varies only allocated storage while preserving
the historical followup code and previous outputs. The harness passes
`maxnode=bits+1`, but originally allocated by `bits`. For bits=96 the actual
maxnode is 97, requiring 16 bytes in a 32-bit ABI, not 12. Both 96-bit cases
match the expected outcome once this is corrected. For bits=65/maxnode=66,
12 bytes are sufficient under ABI rounding, yet the slice still returns EFAULT;
providing 16 bytes removes it. The 12 controlled executions distinguish these
two situations. Original results remain historical development evidence.

`syscall_probe.c` and `compat_probe.c` then exercise the real host kernel.
The former uses native x86-64 calls and x86 compat dispatch through int 0x80;
the latter is a genuine static i386 ELF using `compat_start.S`, without libc.
Both place inputs against a PROT_NONE page, read back the real policy, and on
success fault in a newly mapped page and query its actual NUMA node.

Observed host: WSL 6.18.33.2-microsoft-standard-WSL2, NUMA=y,
NODES_SHIFT=10 (capacity 1024), IA32_EMULATION=y, allowed node0. This shifts
the capacity-boundary experiment from 65 to 1025 effective bits.

- Final x86-64/native-or-compat-dispatch matrix: 64 observations, 55 successful
  policy and page-node readbacks, seven EINVAL and two EFAULT results.
- Genuine i386 matrix: 16 observations, 11 successful policy/page readbacks,
  three EINVAL and two EFAULT results.
- In i386, maxnode=1026 with 132 readable bytes returns EFAULT for both zero and
  nonzero unsupported tails. With 136 bytes, zero tail succeeds and nonzero
  tail returns EINVAL. maxnode=1057 requires 136 bytes already; with that
  allocation its zero/nonzero controls behave as expected.
- Failed calls leave the previously reset policy at MPOL_DEFAULT; successful
  controls read back MPOL_BIND and node0, including the freshly allocated page.

These are measured behavior on the current host, **not a historical full-kernel
before/after test**, nor physical multi-node or big-endian validation. The
remaining width discrepancy merits ABI/maintainer review; no new defect claim
or kernel fix is made. `verify_syscall.py` checks this recorded observation
profile, rather than declaring all API behavior correct. The public manual
describes storage rounded to unsigned-long units:
https://man7.org/linux/man-pages/man2/set_mempolicy.2.html

Reproduction (Linux x86-64 with IA32 support; run in a fresh output directory):

```bash
python experiments/numa_entry/boundary_review.py \
  --source-run analysis_out/numa-entry-20260915-v2 --outdir analysis_out/numa-boundary-new
mkdir -p analysis_out/numa-syscall-new
gcc -O2 -Wall -Wextra -Werror -static experiments/numa_entry/syscall_probe.c \
  -o analysis_out/numa-syscall-new/probe
gcc -m32 -nostdlib -static -fno-builtin -fno-pie -no-pie -fno-stack-protector \
  -O2 -Wall -Wextra -Werror experiments/numa_entry/compat_probe.c \
  experiments/numa_entry/compat_start.S -o analysis_out/numa-syscall-new/probe32
analysis_out/numa-syscall-new/probe > analysis_out/numa-syscall-new/native-final.log
analysis_out/numa-syscall-new/probe32 > analysis_out/numa-syscall-new/compat32-final.log
python experiments/numa_entry/verify_syscall.py --outdir analysis_out/numa-syscall-new
```

The verifier intentionally assumes the recorded 1024-node capacity/node0 host;
other configurations need separately frozen expected observations. The probe
modifies only its own thread policy and resets it between cases. Early host
logs used an oversized get_mempolicy buffer declaration, then effective-bit
allocation; only `*-final.log` is the corrected final matrix.

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
