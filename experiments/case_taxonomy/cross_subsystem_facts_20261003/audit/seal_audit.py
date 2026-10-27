"""Seal independent artifact/semantic review without executing analyzed code."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
receipt = json.loads((HERE / "mechanical_checks.json").read_text(encoding="utf-8"))
assert receipt["status"] == "pass" and not receipt["failures"]
paths = ["protocol_pre.md", "synthesis.md", "checkpoint.md",
         "audit/review_criteria.md", "audit/baseline_inputs.json",
         "audit/verify_locked_inputs.py", "audit/mechanical_checks.json", "audit/seal_audit.py"]
for case in ("ocfs2", "pwm"):
    paths += [f"{case}/{name}" for name in ("facts.json", "review.md", "artifact_manifest.json", "source_manifest.json")]
paths += ["ocfs2/lock.json", "ocfs2/runner.py", "ocfs2/build_facts.py", "ocfs2/commands.json",
          "ocfs2/tool_before.json", "ocfs2/tool_after_prepare.json", "ocfs2/tool_before_replay.json",
          "ocfs2/tool_after_replay.json", "ocfs2/final_tool_state.json", "ocfs2/raw/parent.json", "ocfs2/raw/fix.json",
          "pwm/run_pwm.py", "pwm/source_extension_manifest.json", "pwm/type_contract_manifest.json",
          "pwm/commands_prepare.json", "pwm/commands_replay.json", "pwm/commands_source_extension.json",
          "pwm/commands_type_contract.json", "pwm/replay_hashes_before.json", "pwm/replay_hashes_after.json",
          "pwm/raw/parent.json", "pwm/raw/fixed.json",
          "../endian_consumer_single_revision.py", "../endian_producer_single_revision.py"]
checks = receipt["checks"] | {
    "current_ocfs2_access_occurrences_and_complete_normal_expressions_reviewed": True,
    "ocfs2_filecheck_validation_readonly_journal_valid_and_inode_cache_conditions_preserved": True,
    "pwm_only_visible_get_caller_zero_and_byte_invariance_preserved": True,
    "machine_facts_and_manual_contract_consumption_evidence_distinguished": True,
    "local_disk_contract_transport_and_external_normative_authority_distinguished": True,
    "type_names_not_used_as_host_value_or_physical_reachability_proof": True,
    "no_runtime_generalization_or_whole_function_correctness_upgrade": True,
    "original_cli_execution_evidence_without_getter_adapter_reviewed": True,
    "audit_did_not_replay_rules_compile_or_add_inputs": True,
    "synthesis_and_checkpoint_claims_within_saved_scope": True,
}
result = {
    "date": "2026-10-03", "stage": "cross_subsystem_facts_20261003", "status": "pass",
    "audit_kind": "independent_read_only_artifact_and_method_review_of_already_read_development_interfaces",
    "checks": checks, "blockers_found": [], "counts": receipt["counts"],
    "final_inputs_sha256": {p: hashlib.sha256((STAGE / p).read_bytes()).hexdigest() for p in paths},
    "complete_case_input_receipt": "audit/mechanical_checks.json:final_inputs_sha256",
    "case_conclusions": {
        "ocfs2": "One i_flags primary: candidate to local normal. Same-version disk declaration, integer mask and conditional filecheck consumer support the local representation contract. Current zero/nonzero and same-domain boolean controls are valid locally; no actual BE build, mount, I/O reachability or corruption was proved.",
        "pwm": "One get_property reg primary: candidate to local normal. The unique source-visible static-helper caller passes reg=0; byte exchange preserves zero, so this assignment does not establish a current request-byte error. Local payload memcpy and mailbox chain are reviewed; remote firmware contract, BE device support and runtime failure remain unproved."
    },
    "limits": [
        "Both interfaces were already read; zero new cases and no blind/generalization result. Site counts are not defect counts or accuracy.",
        "Consumer conversion matching is condition-wide; mask/zero tests use partial-expression prefixes. Current simple occurrences were manually bound, general grammar soundness is not certified.",
        "Producer u32 annotation and later object call do not automatically prove actual host-value provenance, dataflow or reachability; chains and value domains here are manual source review.",
        "Kernel disk declaration, local consumer/transport implementation and an external normative specification have different authority. No independent external disk or firmware specification was reviewed.",
        "No full preprocessing/config solving, target layout compilation, sparse rerun, kernel/device/DMA/MMIO execution or real I/O observation.",
        "Consumer dependency receipts cover direct imported module origins, not a recursive materialized runtime closure. PWM freezes producer plus consumer dependency.",
        "ocfs2 prepare receipts lack protocol fields; common tool/import fields match all receipts, protocol SHA matches replay before/after/final. Final builder SHA=8f169a70d3c03b68ae50e2851c0c211678b9faa5574a9b00efb2d4c0840b9922 matches locked facts; earlier assembly stdout remains historical.",
        "Ten unavailable PWM guessed source paths are retained as unavailable, not negative tests or configuration evidence. Root closeout verifier is outside this audit lock."
    ],
    "auditor_actions": ["read saved sources and claims", "recompute saved SHA and Git blob identity",
                        "check all saved quote bindings and raw/summary identities", "write only audit subdirectory"],
    "general_expression_soundness_or_runtime_validation_claimed": False
}
(HERE / "final_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": result["status"], "checks": len(checks), "blockers_found": [], "direct_inputs": len(paths)}))
