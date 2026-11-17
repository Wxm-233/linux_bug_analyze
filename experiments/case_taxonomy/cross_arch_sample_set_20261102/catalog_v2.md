# Cross-architecture defect mechanisms, version 2

Changes from version 1 (`mixed_sample_llm_assist_20261101/catalog.md`): M8 rewritten after the case studies
(`mech_case_studies_20261102/`); M10 added after the catalog validation (`mech_catalog_validation_20261102/`); M6 and
M7 marked as general defect classes. M1-M5 and M9 are unchanged.

Each mechanism describes how a requirement that holds for common code or another architecture can fail in the
RISC-V implementation. A label must name the concrete violated requirement.

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
- M6 Lifetime and error paths (general defect class): missing release or reference drop, double free, use after
  free, missing cleanup or unwinding on failure paths, leaked temporary mappings.
- M7 Bounds, widths and alignment (general defect class): off-by-one, integer width, sign or overflow, address or
  size alignment, limits that depend on configuration (page size, virtual address bits, XLEN).
- M8 Lagging behind the reference's evolution: the RISC-V implementation was derived from an older version of a
  reference (another architecture's code or a common-code contract), and later fixes or changes of approach in the
  reference were not carried over. A common-interface change that the architecture did not follow is one case of
  this.
- M9 Feature and configuration conditions: code that assumes an ISA extension, firmware feature or Kconfig
  combination is present or absent, wrong alternative patching or capability check.
- M10 Same contract, separate implementations, different condition or order: a common contract (system call ABI,
  KVM interface, signal semantics, a hook called by common code) is implemented separately by each architecture;
  the common interface did not change, but the RISC-V implementation differs from the other architectures in a
  condition it checks or in the order of its steps.

Labels outside the catalog:

- X1 RISC-V's own logic: an error only against RISC-V's own specifications, protocols or features (SBI return
  codes, AIA register semantics, instruction decoding), with no counterpart borne by other architectures or common
  code.
- X2 Other: typos, log levels, annotations, pure refactoring, or a "fix" that does not change behaviour.
