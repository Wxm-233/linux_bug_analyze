# N2.12 isolated finite source-fidelity reference

This reference was manually written by an independent assistant, not by a human
expert. Both real GIMPLE sections were already read in N2.11; the role was kept
isolated from the new method/tests/output until the reference was frozen. This
is developer source-fidelity review, not blind Linux detection or a gold set.

The twenty query checks have original-source and exact local coordinates.
They test displayed member events, calls/returns, same-region local scalar
dependencies, explicit label targets, and required unknowns across barriers.
Source identities are mandatory. No missing anchor may count as an expected
unresolved relation, and no failed/empty parser may pass an absence query.
Relevant opaque spans may force insufficient. Human source interpretations and
manual-context callee/asm counts are not automatically-scored extra properties.

The method never receives this reference as analysis input. The root adapter
may only compare a frozen method's output, and may not fill machine facts or
normalize unknowns from the expected answers. Partial support, insufficient and
false support remain separate. No frozen method/source/reference repairs may
chase these checks. Query counts are not Linux cases or defects.
