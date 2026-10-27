"""Seal finite independent audit from saved evidence; do not execute case code."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent


def read(name):
    return json.loads((STAGE / name).read_text(encoding="utf-8"))


execution = read("audit_final/execution_review.json")
locked = read("audit_final/locked_review_checks.json")
assert execution["status"] == locked["status"] == "pass"
checks = execution["checks"] | locked["checks"] | {
    "SMB_cast_warning_distinguished_from_unchanged_API_endian_format": True,
    "SMB_fixed_scalar_sizeof_references_are_not_value_reads": True,
    "SMB_normal_expression_unrelated_to_target_and_not_whole_function_verdict": True,
    "ath12k_selected_read_target_distinguished_from_producer_scope": True,
    "ath12k_parent_u64_and_fixed_le64_not_used_as_external_parent_format_proof": True,
    "ath12k_other_file_writes_manual_only_no_input_replacement_or_rule_rerun": True,
    "ath12k_actual_status_ring_swap_mode_runtime_and_external_authority_unknown": True,
    "source_quotes_machine_facts_and_post_unseal_manual_inference_distinguished": True,
    "zero_target_pairs_zero_confirmed_cases_no_true_negative_or_accuracy_upgrade": True,
    "root_summary_synthesis_and_checkpoint_within_supported_scope": True,
}
names = list(execution["final_inputs_sha256"]) + [
    "audit_final/review_criteria.md", "audit_final/execution_review.json", "audit_final/check_locked_reviews.py",
    "audit_final/locked_review_checks.json", "audit_final/seal_final_audit.py", "source_manifest.json",
    "consumer/raw/parent.json", "consumer/raw/fixed.json", "consumer/patch_unsealed.txt",
    "producer/raw/parent.json", "producer/raw/fixed.json", "producer/patch_unsealed.txt",
    "consumer/manual_review/review.json", "consumer/manual_review/review.md",
    "consumer/manual_review/artifact_manifest.json", "consumer/manual_review/source_manifest_extra.json",
    "consumer/manual_review/commands_extra.json", "producer/manual_review/review.json",
    "producer/manual_review/review.md", "producer/manual_review/locked_manifest.json",
    "producer/manual_review/source_manifest_extra.json", "producer/manual_review/commands_extra.json",
    "review_summary.json", "synthesis.md", "checkpoint.md",
]
result = {
    "date": "2026-10-03", "stage": "bounded_interface_holdout_20261003", "status": "pass",
    "audit_kind": "independent_read_only_execution_identity_quote_and_method_review",
    "checks": checks, "blockers_found": [], "counts": locked["counts"],
    "final_inputs_sha256": {n: hashlib.sha256((STAGE / n).read_bytes()).hexdigest() for n in sorted(set(names))},
    "case_conclusions": {
        "SMB": "Frozen consumer has 0 candidate / 1 local normal / 2 insufficient in both revisions. Target is an output-pointer cast for a reported warning; UTF16_LITTLE_ENDIAN and local put_utf16/LE consumer relation are unchanged. Two sizeof scalar references do not evaluate field values, and normal belongs to another expression. Target is outside this rule, not a machine-normal or true-negative result.",
        "ath12k": "Frozen dp_rx producer has 0/0/5 in both revisions; five unrelated assignments are insufficient. Actual selected target reads tl into tag/switch. Parent tl is u64 and fix is __le64; three hal_rx writes are manual explanation only. Internal helper relations are conditional evidence, while actual status-ring swap flags, external hardware format and supported BE execution remain unknown."
    },
    "limits": [
        "64 title/message-informed metadata entries produced two purposeful fixed inputs; local SHA non-match is not complete human non-exposure, and post-unseal manual judgments are not pre-frozen expert gold.",
        "Original runner must be entered through the sealed supplemental gate. Locks/markers prove the saved sequence and successful one-shot calls, not detection semantics or kernel execution.",
        "Old rules remain text-based and narrow; condition-wide/prefix matching, unsupported expressions, direction and missing endian annotations limit coverage. No rule changes or reruns occurred.",
        "SMB diagnostic compiler/checker/options were not reproduced; API semantic evidence is local source, not independent external SMB normative certification.",
        "ath12k post-fix __le64, nearby LE payloads, nonzero enum names and commit Tested-on do not establish historical remote format, returned bytes, real status-ring swap mode or BE platform support.",
        "Extra evidence stops at four sources per case per revision. Full preprocessing, configuration solving, target compilation/layout, network/DMA/MMIO or device execution was not performed.",
        "No independent target candidate-to-fixed-normal pair, zero newly confirmed defects; no true-negative, accuracy, overall frequency or speedup inference. First discovery/introduction dates and requested intervals remain unknown.",
        "Earlier-stage recursive locks are verified by root closeout; this auditor only checked current-stage direct evidence and preserved audit_pre."
    ],
    "audit_operations": ["read locked saved source/patch/quotes and claims", "recompute SHA and Git blob identity",
                         "compare raw/source/summary identity and execution chronology", "write audit_final only"],
    "rule_execution_compile_model_or_Git_called_by_auditor": False
}
(HERE / "final_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": result["status"], "checks": len(checks), "blockers_found": [], "inputs": len(result["final_inputs_sha256"])}))
