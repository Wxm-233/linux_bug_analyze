"""Assistant source-fidelity reference; no method, tests or outputs imported.

These already-read Linux fragments are developer material, not a new holdout.
Expected facts are manually interpreted finite queries, not architecture norms.
"""
from pathlib import Path
import hashlib
import json


ROOT = Path(__file__).resolve().parent
INNER = ROOT.parents[3]


def h(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def selector(kind, line=None, local=None, code=None, **other):
    result = {"kind": kind}
    if line is not None: result["source_line"] = line
    if local is not None: result["local_line"] = local
    if code is not None: result["code_contains"] = code
    result.update(other)
    return result


def main():
    if (ROOT / "freeze_manifest.json").exists():
        raise SystemExit("Reference frozen; do not replace expected facts")
    ROOT.mkdir(parents=True, exist_ok=True)
    inputs = [
        {"profile": "old_s390", "path": "experiments/case_taxonomy/compiler_consumer_frontend_20261018/old_s390.consumer.gimple.txt", "sha256": "63b4a4ee0e0c4b9b2021fbeeae0d10f459fc42b3d6f7ce487a02a896fbff09e9", "candidate_load": 107, "candidate_if": 108, "witness_goto": 111, "exit_label": "D.80224", "exit_label_line": 119, "skip_if": 83, "skip_targets": ["D.87292", "D.87293"], "skip_target_lines": [84, 87], "pre_def": 50, "post_use": 69, "post_load": 182, "post_compare": 183, "store": 177, "asm_count_manual_context_only": 6},
        {"profile": "old_x86", "path": "experiments/case_taxonomy/compiler_consumer_frontend_20261018/old_x86.consumer.gimple.txt", "sha256": "b5c042e3f6e9f0b649e65a306dc58274e131f06e2b9861109ab2a784a51b536c", "candidate_load": 110, "candidate_if": 111, "witness_goto": 114, "exit_label": "D.81134", "exit_label_line": 122, "skip_if": 86, "skip_targets": ["D.87105", "D.87106"], "skip_target_lines": [87, 90], "pre_def": 50, "post_use": 72, "post_load": 188, "post_compare": 189, "store": 183, "asm_count_manual_context_only": 9},
    ]
    checks = []
    def add(data, number, op, description, expected, **fields):
        checks.append({"id": f"{data['profile']}_F{number:02}", "profile": data["profile"], "op": op, "predicate_description": description, "expected": expected, "anchor_requirement": "Raw identity must match; positive/negative relation requires both unique anchors and explicit unresolved/barrier evidence. Missing anchors are insufficient. Zero counts require relevant scanner coverage, not an empty/failed event list.", **fields})
    for data in inputs:
        path = INNER / data["path"]
        assert h(path) == data["sha256"]
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        assert lines[0].startswith("void sched_core_cpu_starting") and lines[-1] == "}"
        for at, needle in [(data["candidate_load"], "rq->core"), (data["candidate_if"], "if (rq == _16)"), (data["witness_goto"], "goto <" + data["exit_label"] + ">"), (data["exit_label_line"], "<" + data["exit_label"] + ">:"), (data["pre_def"], "__ret_warn_on = (int) _6"), (data["post_use"], "_10 = __ret_warn_on != 0"), (data["post_load"], "_29 ="), (data["post_compare"], "_30 = core_rq != _29"), (data["store"], "rq->core = core_rq")]:
            assert needle in lines[at - 1], (data["profile"], at, needle)
        add(data, 1, "event_count", "Whole-section explicit arrow member loads named core; source-path/asm spellings are not member loads.", {"count": 3}, selector=selector("field_load", field="core"))
        add(data, 2, "event_count", "One displayed rq->core assignment at C5787; this count does not establish its guard dominance or runtime object identity.", {"count": 1}, selector=selector("field_store", 5787, data["store"], "rq->core", field="core"))
        add(data, 3, "event_count", "Displayed calls excluding asm: helper/result calls plus builtin_expect; call result remains unknown rather than a helper semantic summary.", {"count": 12}, selector=selector("call"), manual_context_only={"callee_multiset": {"cpu_smt_mask": 1, "sched_core_lock": 1, "cpumask_weight": 1, "cpumask_next": 2, "sched_core_unlock": 1, "__builtin_expect": 6}, "asm_spans_not_calls": data["asm_count_manual_context_only"]})
        add(data, 4, "event_count", "No explicit return statement in this void section; diagnostic asm and the final function boundary cannot manufacture a return event.", {"count": 0}, selector=selector("return"))
        add(data, 5, "dependency", "Candidate field read feeds the immediately following comparison in the same straight-line region; not global reaching-def or pointer identity.", {"relation": "supported"}, def_selector=selector("field_load", 5773, data["candidate_load"], "_16", field="core"), use_selector=selector("condition", 5773, data["candidate_if"], "rq == _16"), variable="_16")
        add(data, 6, "explicit_edge", "The goto immediately following witness assignment has the displayed search-exit label; only an explicit target edge, not first-hit correctness or general reachability.", {"target_label": data["exit_label"]}, from_selector=selector("goto", 5775, data["witness_goto"]), target_label=data["exit_label"], target_anchor={"local_line": data["exit_label_line"], "code_contains": "<" + data["exit_label"] + ">:"})
        add(data, 7, "explicit_edge", "The skip-target comparison has two distinct displayed label targets, both real labels in this section; no transitive branch/path theorem.", {"target_labels": data["skip_targets"]}, from_selector=selector("condition", 5770, data["skip_if"], "if (cpu =="), target_anchors=[{"local_line": at, "code_contains": "<" + label + ">:"} for at, label in zip(data["skip_target_lines"], data["skip_targets"])])
        add(data, 8, "dependency", "Do not attach the pre-effect warning flag definition to the later read across scope/branch/call/asm boundaries by last-text-definition; both source anchors exist.", {"relation": "unresolved", "reason_class": "barrier_or_live_in"}, def_selector=selector("assignment", 5762, data["pre_def"], "__ret_warn_on = (int) _6"), use_selector=selector("assignment", 5762, data["post_use"], "_10 = __ret_warn_on != 0"), variable="__ret_warn_on")
        add(data, 9, "dependency", "The post-update field-read temporary feeds its immediately following relation comparison; this is local value source, not store/load alias proof or pre-state forall.", {"relation": "supported"}, def_selector=selector("field_load", 5789, data["post_load"], "_29", field="core"), use_selector=selector("assignment", 5789, data["post_compare"], "_30 = core_rq != _29"), variable="_29")
        add(data, 10, "event_count", "No non-core member field events: .cache/core.c paths, assembler .section/.word spellings and D.xxx/cpu.xxx identifiers are not member syntax.", {"count": 0}, selector=selector(["field_load", "field_store"], field_not_in=["core"]))
    save(ROOT / "source_truth_checks.json", {"schema": "n212_source_fidelity_reference_v1", "actual_author": "independent assistant manual source interpretation, not human expert gold", "contact": "Both complete source sections were already read and manually reviewed in N2.11. No new method/tests/output read before reference freeze. This is source-fidelity developer evidence, not Linux holdout.", "coordinate_system": {"source_line": "GCC reported original-C locus line", "local_line": "1-based line within exact section", "identity": "source bytes SHA256; columns/UTF8 byte mapping not independently proven"}, "inputs": inputs, "checks": checks, "scope": "Only local facts/displayed edges and protocol-mandated barriers; no architecture obligation, runtime truth, global reaching-def, dominance, alias, full CFG or first-consumption proof", "manual_context_only_not_scored_unless_explicit_check": "Callee multisets, asm counts and source interpretation descriptions document review rationale; the op+selector+expected defines each finite query."})
    (ROOT / "README.md").write_text("""# N2.12 isolated finite source-fidelity reference

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
""", encoding="utf-8")
    save(ROOT / "summary.json", {"checks": len(checks), "known_configured_profiles": len(inputs), "new_Linux_cases": 0, "new_method_or_tests_read": False, "external_calls": 0, "reference_kind": "assistant manual developer source fidelity, not human expert gold", "release": "After method/scorer freeze only"})
    files = [p for p in ROOT.iterdir() if p.is_file() and p.name != "freeze_manifest.json"]
    save(ROOT / "freeze_manifest.json", {"schema": "n212_independent_reference_freeze_v1", "date": "2026-10-18", "files": {p.relative_to(ROOT).as_posix(): h(p) for p in sorted(files)}, "source_inputs": [{k: v for k, v in x.items() if k in {"profile", "path", "sha256"}} for x in inputs], "new_method_tests_or_output_read_before_freeze": False})
    print(json.dumps({"status": "reference_frozen", "checks": len(checks), "profiles": len(inputs), "manifest_sha256": h(ROOT / "freeze_manifest.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
