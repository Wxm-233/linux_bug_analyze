"""Final read-only root-product review; never execute historical programs."""
from pathlib import Path
import hashlib
import json

stage = Path(__file__).resolve().parent.parent
root = stage.parents[2]
frozen = json.loads((stage / "materials_pre.json").read_text(encoding="utf-8"))
raw_reports = {}
for item in frozen["materials"]:
    raw = (root / item["path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == item["sha256"]
    assert len(raw) == item["bytes"]
    raw_reports[item["path"]] = raw

files = ["coverage.md", "coverage.json", "source_quotes.json", "checkpoint.md"]
products = {name: (stage / name).read_bytes() for name in files}
product_hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in products.items()}
coverage = json.loads(products["coverage.json"])
quotes = json.loads(products["source_quotes.json"])["quotes"]
assert len(quotes) == 38
ids = set()
for quote in quotes:
    assert quote["id"] not in ids
    ids.add(quote["id"])
    assert quote["source"] in raw_reports
    raw = raw_reports[quote["source"]]
    assert hashlib.sha256(raw).hexdigest() == quote["source_sha256"]
    lines = raw.decode("utf-8").splitlines()
    start, end = quote["line_start"], quote["line_end"]
    assert 1 <= start <= end <= len(lines)
    assert "\n".join(lines[start-1:end]) == quote["quote"]

rows = coverage["rows"]
assert len(rows) == 8
by_id = {row["id"]: row for row in rows}
assert set(by_id) == {"btrfs", "s390_topology", "arch_topology", "hyperv", "shmem", "virtio_input", "smmu_range", "die_sysfs"}
for key in ("btrfs", "s390_topology"):
    dimensions = by_id[key]["five_dimensions"]
    assert dimensions["formal_report_relation"] == "unknown"
    assert dimensions["provisional_relation"] == "vertical_candidate_from_manual_provider_consumer_inference"
    assert dimensions["origin_side_report"].startswith("unknown_first_introduction_side;")
    assert "old_two_dimensions_originals_not_in_package" in dimensions["time_missing_reason"]
for key in ("arch_topology", "hyperv", "shmem", "virtio_input", "smmu_range"):
    assert by_id[key]["five_dimensions"]["formal_report_relation"] == "vertical"
assert by_id["die_sysfs"]["five_dimensions"]["formal_report_relation"] == "horizontal_source_candidate"
assert "CPU_unknown" in by_id["btrfs"]["five_dimensions"]["trigger_arch_platform"]
assert "CPU_unknown" in by_id["virtio_input"]["five_dimensions"]["trigger_arch_platform"]
assert "CPU_model_not_fixed_by_device_name" in by_id["smmu_range"]["five_dimensions"]["trigger_arch_platform"]
metadata_notes = []
for row in rows:
    dimensions = row["five_dimensions"]
    for field in ("first_actual_discovery_date", "fault_to_discovery_days", "discovery_to_fix_days"):
        assert dimensions[field] is None
    if row["id"] not in ("btrfs", "s390_topology") and "old_two_dimensions_originals_not_in_package" in dimensions["time_missing_reason"]:
        metadata_notes.append({"row": row["id"], "field": "time_missing_reason", "note": "old-two-only reason repeated on new row; numeric conclusion unchanged"})
    assert row["new_test_execution"] is False
    assert row["contract"]["authority_recertified_this_round"] is False
    assert row["contract"]["whole_reachable_chain_automatically_extracted_this_round"] is False
    assert all(item in ids for item in row["source_quote_ids"])
assert all(item in ids for item in coverage["supplementary_quote_ids"])
assert coverage["coverage_counts"]["actual_discovery_dates_available"] == 0
assert coverage["coverage_counts"]["fault_to_discovery_intervals_available"] == 0
assert coverage["coverage_counts"]["discovery_to_fix_intervals_available"] == 0
assert coverage["new_confirmed_cases"] == 0
assert coverage["independent_positive_cases"] == 0
assert coverage["fixed12_denominator"] == "6_source_chains_5_outside_1_conditional"
assert coverage["primary_source_recertification"] is False
assert coverage["C1_C4_D2_D3_D4_overall_complete"] is False

def product_quote(name, start, end=None):
    end = end or start
    lines = products[name].decode("utf-8").splitlines()
    return {"path": name, "sha256": product_hashes[name], "line_start": start, "line_end": end,
            "quote": "\n".join(lines[start-1:end])}

status = "PASS_for_bounded_report_level_five_dimensions_and_scope"
if metadata_notes:
    status = "PASS_with_minor_time_reason_metadata_notes_not_counting_errors"
record = {
    "date": "2026-10-11", "status": status,
    "reviewed_root_files_sha256": product_hashes,
    "fixed_material_identity_verified": 10,
    "source_quote_count_verified": len(quotes),
    "row_count_verified": len(rows),
    "formal_relations": {"vertical_reported": 5, "horizontal_source_candidate": 1, "unknown_old_units": 2},
    "fault_to_discovery_computable": 0,
    "discovery_to_fix_computable": 0,
    "unknowns_preserved": ["Btrfs/s390 formal relation and introduction side", "CPU tags for Btrfs/virtio/SMMU", "all actual discovery dates and both target intervals"],
    "new_confirmed_cases": 0, "independent_new_positives": 0,
    "fixed12": "6/5/1 unchanged", "scope": "root_saved_reports_only_not_primary_authentication",
    "old_review_unchanged_by_this_script": True,
    "metadata_notes": metadata_notes,
    "root_evidence": [product_quote("coverage.md", 9, 24), product_quote("checkpoint.md", 3, 11)],
    "operations": {"new_primary_retrievals": 0, "old_program_execution": 0, "new_experiments": 0}
}
destination = Path(__file__).with_name("final_review.json")
destination.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
md = ["# 原八项覆盖整理：五维与范围最终只读审核", "", "2026-10-11。复核根产物 coverage.md、coverage.json、source_quotes.json、checkpoint.md；十份冻结报告身份一致，38段引文逐段与固定来源原文/行号/哈希相符。本轮未打开引用原物、执行旧程序或检索。", "", "结论：" + status + "。", "", "- Btrfs/s390正式关系字段为unknown，另列报告层纵向推定；首次引入侧未知，当前位置不冒充历史形成侧。", "- 六条新样本为五条报告纵向、一条横向源码候选；不是七纵一横的已确认缺陷统计。", "- Btrfs/virtio CPU标签未知；SMMU以设备/模式记录，没有推成CPU架构。", "- 八项发现日期及两目标间隔均null，可计算量分别0/8；辅助来源→修复跨度单列。", "- 八机制工作单元不扩充固定十二条6/5/1；新增确认0、独立阳性0，整体D2/D3/D4未完成。", "- 下一项Btrfs单接口已读开发补证须另冻结小范围原物；不作为独立阳性验证。", "", "## 被审阅根文件SHA-256", ""]
md += ["- `" + name + "`：`" + digest + "`" for name, digest in product_hashes.items()]
if metadata_notes:
    md += ["", "非计数问题：六条新行的time_missing_reason仍重复旧两项原物未纳入这一原因；建议分栏整理。实际日期和0/8结论正确，不升级任何未知。"]
Path(__file__).with_name("final_review.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print(json.dumps({"status": status, "root_files_hashed": 4, "source_quotes_verified": len(quotes), "metadata_note_count": len(metadata_notes)}, ensure_ascii=False))
