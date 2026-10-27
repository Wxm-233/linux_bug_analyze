"""Read only the ten frozen reports and save a report-level dimension audit."""
from pathlib import Path
import hashlib
import json

stage = Path(__file__).resolve().parent.parent
root = stage.parents[2]
materials = json.loads((stage / "materials_pre.json").read_text(encoding="utf-8"))
assert len(materials["materials"]) == 10
texts = {}
hashes = {}
for item in materials["materials"]:
    path = root / item["path"]
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == item["sha256"], item["path"]
    assert len(raw) == item["bytes"], item["path"]
    texts[item["path"]] = raw.decode("utf-8").splitlines()
    hashes[item["path"]] = digest
assert sum(item["bytes"] for item in materials["materials"]) <= 512 * 1024

prefix = "experiments/case_taxonomy/"
def ref(name, start, end=None):
    name = prefix + name
    end = end or start
    lines = texts[name]
    assert 1 <= start <= end <= len(lines)
    return {"path": name, "sha256": hashes[name], "line_start": start,
            "line_end": end, "quote": "\n".join(lines[start-1:end])}

shared_time = ref("case_reviews.md", 22)
base_time = ref("final_summary_case_baseline.md", 21, 25)
rows = [
 {"work_unit": "Btrfs", "commit": "6f93e834fa7c", "cpu_architecture": "unknown",
  "trigger_platform_condition": "64K page and disk sector; max_inline exceeds temporary 4K limit",
  "subsystem": "Btrfs option parsing", "relation": "unknown",
  "provisional_relation": "conditional_vertical_mechanism_candidate",
  "relation_basis_level": "report_level_inference_not_individual_causal_card",
  "introduction_side": "unknown", "reported_check_location": "shared filesystem open_ctree / option consumption order",
  "origin_date": "unknown", "origin_effective_date": "unknown", "fix_date": "unknown",
  "evidence": [ref("interface_contract_matrix.md", 11), ref("final_summary_pattern_contracts.md", 24), base_time]},
 {"work_unit": "s390 topology", "commit": "a052096bdd68", "cpu_architecture": "s390",
  "trigger_platform_condition": "secondary CPU start/hotplug; SCHED_CORE consumer reachable",
  "subsystem": "s390 CPU topology / scheduler", "relation": "unknown",
  "provisional_relation": "conditional_vertical_mechanism_candidate",
  "relation_basis_level": "report_level_inference_not_individual_causal_card",
  "introduction_side": "unknown", "reported_check_location": "architecture mask preparation to shared scheduler notification boundary",
  "origin_date": "unknown", "origin_effective_date": "unknown", "fix_date": "unknown",
  "evidence": [ref("interface_contract_matrix.md", 12), ref("final_summary_pattern_contracts.md", 25), base_time]},
 {"work_unit": "arch_topology", "commit": "3fcbf1c77d08", "cpu_architecture": "ARM64_reported",
  "trigger_platform_condition": "cacheinfo released on offline then CPU online; shared LLC",
  "subsystem": "CPU cacheinfo/topology", "relation": "conditional_vertical_reported",
  "introduction_side": "shared topology consumption timing assumption",
  "origin_date": "2022-07-04", "origin_effective_date": "2022-07-04_reported_combined_conditions", "fix_date": "2022-07-22",
  "evidence": [ref("case_reviews.md", 7), ref("case_reviews.md", 26), ref("interface_contract_matrix.md", 13), shared_time]},
 {"work_unit": "ARM64 Hyper-V", "commit": "52ae076c3a9b", "cpu_architecture": "ARM64",
  "trigger_platform_condition": "Hyper-V vPCI IRQ-affinity redirection reachable; allocation successful",
  "subsystem": "CPU hotplug / virtual PCI", "relation": "conditional_vertical_reported",
  "introduction_side": "combined architecture registration and shared consumer timing",
  "origin_date": "2021_registration_only", "origin_effective_date": "2023-04-17/2023-04-21_reported_consumer_window", "fix_date": "2023-06-17",
  "evidence": [ref("case_reviews.md", 11), ref("case_reviews.md", 28), ref("interface_contract_matrix.md", 14), shared_time]},
 {"work_unit": "shmem", "commit": "9fd154ba926b", "cpu_architecture": "ARM64",
  "trigger_platform_condition": "64KB base page; PMD huge-page selection enabled",
  "subsystem": "shmem/xarray page cache", "relation": "conditional_vertical_reported",
  "introduction_side": "shared MM", "origin_date": "2022-01-08_Fixes_code_source",
  "origin_effective_date": "unknown", "fix_date": "2024-07-03",
  "evidence": [ref("case_reviews.md", 12), ref("case_reviews.md", 29), ref("interface_contract_matrix.md", 22), shared_time]},
 {"work_unit": "virtio input", "commit": "95c7b0ad6c69", "cpu_architecture": "unknown",
  "trigger_platform_condition": "actually non-coherent platform; DMA mapping path; cacheline sharing",
  "subsystem": "virtio input / DMA", "relation": "conditional_vertical_reported",
  "introduction_side": "shared driver layout", "origin_date": "2015-03-29_layout_source_only",
  "origin_effective_date": "unknown", "fix_date": "unknown",
  "evidence": [ref("case_reviews.md", 9), ref("case_reviews.md", 33), ref("interface_contract_matrix.md", 23), shared_time]},
 {"work_unit": "ARM SMMU range", "commit": "eb6c97647be2", "cpu_architecture": "unknown_in_ten_report_scope",
  "trigger_platform_condition": "ARM SMMUv3; range enabled; SVA or io-pgtable non-leaf invalidation",
  "subsystem": "IOMMU / TLB invalidation", "relation": "conditional_vertical_reported",
  "introduction_side": "ARM SMMU backend", "origin_date": "2023-06-08_Fixes_code_source",
  "origin_effective_date": "unknown", "fix_date": "2023-09-18",
  "evidence": [ref("case_reviews.md", 8), ref("case_reviews.md", 27), ref("interface_contract_matrix.md", 24), shared_time]},
 {"work_unit": "die sysfs", "commit": "2c4dcd7fd57b", "cpu_architecture": "s390_ARM64_reported_matrix",
  "trigger_platform_condition": "historical non-native die provider, SMP/sysfs; x86 controls separately",
  "subsystem": "CPU topology / sysfs", "relation": "horizontal_source_candidate_not_runtime_confirmed",
  "introduction_side": "shared export layer", "origin_date": "2019-05-23_shared_interface_source",
  "origin_effective_date": "unknown", "fix_date": "2021-12-03",
  "evidence": [ref("case_reviews.md", 13), ref("case_reviews.md", 30), ref("interface_contract_matrix.md", 32), ref("final_summary_authority_cards.md", 9, 16), shared_time]}
]
for row in rows:
    row.update(discovery_date="unknown", error_to_discovery_days="unknown",
               discovery_to_fix_days="unknown", source_level="saved_report_only_not_new_primary_authentication")
assert len(rows) == 8
record = {
 "date": "2026-10-11", "review_scope": "ten_frozen_reports_only",
 "status": "PASS_for_bounded_report_review_with_explicit_unknowns",
 "materials": [{"path": item["path"], "sha256": hashes[item["path"]]} for item in materials["materials"]],
 "work_unit_count": 8, "new_confirmed_cases": 0, "independent_new_positives": 0,
 "fixed_12_denominator": {"source_chains": 6, "outside": 5, "conditional": 1},
 "goal_intervals_computable": 0, "old_two_individual_causal_card_not_in_scope": True,
 "prohibited_operations_performed": [], "rows": rows,
 "counting_evidence": [ref("interface_contract_matrix.md", 3), ref("final_summary_case_baseline.md", 9, 15)],
 "method_boundary": [ref("teacher_questions_roadmap.md", 18, 22), ref("numa_authority_review_20261011/authority_card.md", 55, 59), ref("kunit_config_override_20261011/mechanism_card.md", 35, 39)]
}
destination = Path(__file__).with_name("review.json")
destination.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": record["status"], "frozen_materials_verified": 10, "rows": len(rows),
                  "goal_intervals_computable": 0, "written": str(destination)}, ensure_ascii=False))
