# Cross-architecture defect mechanisms (catalog given to the model in method RL)

Each mechanism describes how a requirement that holds for common code or another architecture can fail in the
RISC-V implementation. Use it as a checklist; a bug claim must still name a concrete violated requirement and cite
lines.

- M1 Default assumption mismatch: a generic/default implementation or helper assumes a representation that this
  architecture does not use (e.g. one page-table entry per huge page while RISC-V uses a contiguous NAPOT group;
  generic size or level assumptions).
- M2 Entry state vs. information source: size, grouping, pfn or attributes are decoded from an entry's content
  although on this path the entry may be non-present (none, swap, migration, hwpoison, marker) and then carries no
  such information.
- M3 Update protocol for live or multi-entry mappings: required order such as clear-then-flush (break-before-make),
  updating a whole contiguous group, TLB or instruction-cache maintenance after changing mappings or code.
- M4 Atomicity and ordering: read-modify-write that must be atomic (xchg/cmpxchg), fences required by the RISC-V
  weak memory model before publishing data, ordering between memory and I/O.
- M5 Execution context: code that runs with interrupts disabled, in NMI-like or exception entry, in single-step or
  probe windows, with preemption disabled, or that must guard against recursion; no sleeping in atomic context.
- M6 Lifetime and error paths: missing release or reference drop, double free, use after free, missing cleanup or
  unwinding on failure paths, leaked temporary mappings.
- M7 Bounds, widths and alignment: off-by-one, integer width, sign or overflow, address or size alignment, limits
  that depend on configuration (page size, virtual address bits, XLEN).
- M8 Common-code contract change: the common interface changed its parameters or semantics (new argument, new
  entry type, new caller), and the architecture implementation was not updated to match.
- M9 Feature and configuration conditions: code that assumes an ISA extension, firmware feature or Kconfig
  combination is present or absent, wrong alternative patching or capability check.
