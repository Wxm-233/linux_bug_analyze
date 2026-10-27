"""Assemble post-unseal human review from saved sources; no detector invocation."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[1]
BASE = "drivers/net/wireless/ath/ath12k/"
REVISIONS = {"parent": "ea58aae8458480d6391c404e62f1a4b30462b9c3",
             "fixed": "1cfa6d4e5bd9bfb15d165d8d843163363929ba1b"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


sources = read_json(STAGE / "source_manifest.json") + read_json(HERE / "source_manifest_extra.json")
lookup = {(item["revision"], item["source_path"]): item for item in sources if item["role"] == "producer"}
quotes = []


def quote(label, identity, path, first, last):
    revision = REVISIONS[label]
    item = lookup[(revision, path)]
    raw = (STAGE / item["saved_path"]).read_bytes()
    assert sha(raw) == item["sha256"]
    assert hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest() == item["blob_sha1"]
    lines = raw.decode("utf-8").splitlines()
    assert 1 <= first <= last <= len(lines)
    quotes.append({"id": label + ":" + identity, "revision": revision,
                   "source_path": path, "saved_path": item["saved_path"],
                   "start_line": first, "end_line": last,
                   "text": "\n".join(lines[first-1:last]),
                   "sha256": item["sha256"], "blob_sha1": item["blob_sha1"]})


for label in REVISIONS:
    quote(label, "selected_complete_read_function", BASE + "dp_rx.c", 3896, 3973)
    quote(label, "tlv_64_field_and_layout", BASE + "hal_desc.h", 575, 586)
    quote(label, "tag_masks", BASE + "hal.h", 617, 618)
    quote(label, "command_and_status_tag_enums", BASE + "hal_desc.h", 356, 363)
    quote(label, "update_command_tag_enum", BASE + "hal_desc.h", 412, 412)
    quote(label, "update_status_tag_enum", BASE + "hal_desc.h", 247, 247)
    quote(label, "ring_flags", BASE + "hal.h", 605, 615)
    quote(label, "ring_memory_fields", BASE + "hal.h", 621, 641)
    quote(label, "queue_stats_layout_and_producer_consumer_comment", BASE + "hal_desc.h", 1165, 1175)
    quote(label, "queue_stats_write", BASE + "hal_rx.c", 24, 46)
    quote(label, "flush_cache_write", BASE + "hal_rx.c", 48, 93)
    quote(label, "update_queue_write_prefix", BASE + "hal_rx.c", 95, 110)
    quote(label, "command_ring_write_dispatch", BASE + "hal_rx.c", 220, 263)
    quote(label, "status_payload_read", BASE + "hal_rx.c", 462, 473)
    quote(label, "destination_ring_get_next", BASE + "hal.c", 1994, 2010)
    quote(label, "source_ring_get_next", BASE + "hal.c", 2057, 2087)
    quote(label, "ring_access_begin", BASE + "hal.c", 2127, 2136)
    quote(label, "ring_access_end", BASE + "hal.c", 2141, 2175)
    quote(label, "ring_parameter_binding", BASE + "hal.c", 2302, 2313)
    quote(label, "hardware_destination_swap_controls", BASE + "hal.c", 1713, 1723)
    quote(label, "hardware_source_swap_controls", BASE + "hal.c", 1801, 1818)
    quote(label, "bitfield_type_helper_definitions", "include/linux/bitfield.h", 174, 204)
    quote(label, "kconfig_platform_conditions", BASE + "Kconfig", 1, 17)
    quote(label, "unrelated_undecap_write", BASE + "dp_rx.c", 2118, 2127)
    quote(label, "unrelated_reinject_writes", BASE + "dp_rx.c", 3098, 3116)

reports = {label: read_json(STAGE / "producer" / "raw" / (label + ".json")) for label in REVISIONS}
assert all(report["counts"] == {"candidate": 0, "normal": 0, "insufficient": 5} for report in reports.values())
assert reports["parent"]["findings"] == reports["fixed"]["findings"]
assert all(item["field"] != "tl" for report in reports.values() for item in report["findings"])
patch = STAGE / "producer" / "patch_unsealed.txt"
review = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "stage": "bounded_interface_holdout_20261003", "role": "producer",
    "selected_fix_revision": REVISIONS["fixed"], "selected_parent_revision": REVISIONS["parent"],
    "selected_source": BASE + "dp_rx.c", "selected_source_unchanged": True,
    "review_phase": "post-unseal manual source review after both parents locked",
    "classification": "selected primary is read-side target outside producer direction; target not covered, not a true-negative result",
    "count_unit": "5 unrelated assignment sites per version, not 5 defects or independent tests",
    "new_confirmed_defect_count": 0,
    "first_discovery_date": None,
    "raw_outputs": {label: {"path": f"producer/raw/{label}.json", "sha256": sha((STAGE / "producer" / "raw" / (label + ".json")).read_bytes()),
                             "counts": report["counts"], "findings": report["findings"]} for label, report in reports.items()},
    "patch": {"path": patch.relative_to(STAGE).as_posix(), "sha256": sha(patch.read_bytes()),
              "author_date": "2024-11-19", "committer_date": "2024-11-21",
              "claimed_tested_on": "QCN9274 hw2.0 PCI WLAN.WBE.1.3.1-00173-QCAHKSWPL_SILICONZ-1",
              "claim_status": "commit text only; this study did not run it and text does not identify BE host",
              "fixes_trailer_present": False, "role": "post-unseal target locator and maintainer claim, not runtime truth"},
    "actual_patch_targets": [
        {"source_path": BASE + "dp_rx.c", "direction": "consumer read",
         "function": "ath12k_dp_rx_process_reo_status", "line": 3915,
         "field": "hdr->tl", "parent_expression": "u64_get_bits(hdr->tl, HAL_SRNG_TLV_HDR_TAG)",
         "fixed_expression": "le64_get_bits(hdr->tl, HAL_SRNG_TLV_HDR_TAG)",
         "value_consumer": "host u16 tag drives switch dispatch, then status parser and matching command callback",
         "producer_rule_target": False, "in_original_findings": False},
        {"source_path": BASE + "hal_desc.h", "direction": "format/type declaration",
         "struct": "hal_tlv_64_hdr", "field": "tl", "line": 584,
         "parent_type": "u64", "fixed_type": "__le64", "layout": "one 64-bit field followed by u8 flexible array, __packed",
         "parent_declares_endian_requirement": False, "fixed_type_alone_certifies_parent_external_format": False},
        {"source_path": BASE + "hal_rx.c", "direction": "producer writes, outside selected file",
         "functions": ["ath12k_hal_reo_cmd_queue_stats", "ath12k_hal_reo_cmd_flush_cache", "ath12k_hal_reo_cmd_update_rx_queue"],
         "lines": [29, 62, 100], "field": "tlv->tl",
         "parent_expression_shape": "OR of two u32_encode_bits calls assigned to host u64 field",
         "fixed_expression_shape": "OR of two le64_encode_bits calls assigned to __le64 field",
         "manual_only": True, "detector_rerun_on_this_file": False}
    ],
    "rule_coverage_explanation": {
        "selected_primary": "read/extract in assignment and switch, while producer examines field writes only",
        "parent_type_gap": "selected header was already in original source_tree, but tl was declared u64; no endian-marked tl contract was available to this rule on the parent",
        "fixed_still_no_write": "fixed tl is __le64, but selected primary remains a field read and never enters the producer write-site list",
        "other_file": "hal_rx.c actual producer fixes were not the frozen input; no extra CLI run or replacement source was used",
        "consumer_rule_observation": "the existing consumer rule is limited to direct if-condition reads; primary get_bits assignment/switch also lies outside that shape. This is scope analysis only, not another tool run",
        "five_insufficient": "snap_type source declaration/type not established; nested conversion and encode_bits expressions not supported by simple expression_type classifier. All five unchanged findings are unrelated to tl and patch",
        "no_automated_true_negative_claim": True, "no_hit_rate_or_accuracy_inference": True},
    "manual_field_source_and_consumption": {
        "status_pointer": "dp_rx selects dp->reo_status_ring; destination get_next returns ring_base_vaddr+tp when cached_hp differs and advances tp, without descriptor byte conversion",
        "tag_mask": "HAL_SRNG_TLV_HDR_TAG=GENMASK(9,1)",
        "expected_status_symbols": "case labels include nonzero tags e.g. GET_QUEUE_STATS_STATUS=285; these are source expected dispatch values, not observed device values",
        "status_dispatch": "switch default warns Unknown reo status type and continues; recognized tags parse tlv->value, then match cmd_num and call saved command handler",
        "command_header_values": "writer tag enums include GET_QUEUE_STATS=281, FLUSH_CACHE=283, UPDATE_RX_REO_QUEUE=339; combined with sizeof(payload). This is source-derived expression content, not an added input grid",
        "command_pointer": "ath12k_hal_reo_cmd_send gets source-ring descriptor, calls selected writer, then access_end updates head/tail toward HW/shared memory",
        "command_source_comment": "hal_reo_get_queue_stats payload documents Producer: SW / Consumer: REO; its payload fields are __le32",
        "helper_semantics": "bitfield.h le64_get_bits expands from=le64_to_cpu before mask; u64_get_bits from is empty; le64_encode_bits converts encoded value with cpu_to_le64",
        "internal_le_format_support": "same-version surrounding LE payload/helper conventions and post-unseal paired type/accessor/writer changes provide a conditional internal representation interpretation",
        "external_format_not_certified": "no hardware format specification/remote implementation examined, and parent tl lacks LE annotation",
        "hardware_mode_caveat": "hal.c source/destination init have DATA_TLV_SWAP, RING_PTR_SWAP and MSI_SWAP controls and bind srng->flags=params->flags; actual selected status-ring flag setup is beyond the four-extra-file boundary",
        "entry_and_configuration": "ATH12K depends on MAC80211 && HAS_DMA && PCI; initialized ring, driver/device and nonempty hardware status are required; interrupt/caller/device execution not traced to runtime",
        "conditional_failure": "if the active device ring supplies an LE 64-bit header to a BE host without a compensating hardware mode, a native extraction can misdecode the tag and change dispatch. Those antecedents and a concrete returned header were not demonstrated"},
    "proof_flags": {
        "parent_tl_declares_le": False, "fixed_tl_declares_le": True,
        "original_tool_primary_target_found": False,
        "source_ring_pointer_origin_traced": True,
        "helper_conversion_difference_source_proven": True,
        "nonzero_command_tags_in_source": True, "actual_nonzero_status_received": False,
        "internal_representation_relation_conditionally_supported": True,
        "external_hardware_format_proven": False, "actual_ring_swap_mode_proven": False,
        "supported_be_platform_configuration_proven": False,
        "runtime_fault_reproduced": False, "new_confirmed_cross_architecture_defect": False,
        "code_compiled_or_grid_added": False, "detector_changed_or_rerun": False},
    "five_dimension_initial_codes": {
        "trigger_architecture_or_platform": {"code": "conditional BE host / ath12k REO ring representation", "status": "BE support and actual hardware mode unknown; Tested-on is device/firmware claim only"},
        "subsystem": {"code": "network / wireless / Qualcomm ath12k / HAL and receive datapath", "status": "source paths established"},
        "vertical_or_horizontal": {"code": "vertical representation-contract candidate; horizontal not established", "status": "no architecture A change -> shared behavior -> architecture B regression chain"},
        "error_introduction_side": {"code": "driver format declaration plus read/write helpers", "status": "locations of patched code established; original introducing revision and effective fault onset unknown"},
        "time": {"fix_committer_date": "2024-11-21", "introduction_date": None, "first_discovery_date": None,
                 "introduction_to_discovery_days": None, "discovery_to_fix_days": None,
                 "status": "no Fixes trailer or independently verified discovery evidence; author/fix dates are not discovery dates"}},
    "unknowns": ["authoritative hardware TLV64 byte format and actual ring swap settings", "supported and bootable BE host/device configuration", "concrete returned status bytes and device failure", "initial introducing revision/effective fault date", "first discovery date and both requested discovery intervals", "whole-driver correctness outside the selected target"],
    "extra_source_limit": {"files_per_revision": 4, "source_records": 8, "manifest": "producer/manual_review/source_manifest_extra.json"},
    "quotes": quotes,
    "closeout": "scope/direction and format-annotation boundary found; retain new confirmed count 0, first discovery unknown; no sample replacement, rule changes, model calls, CLI rerun, compilation or grid"}

(HERE / "review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"review_json_sha256": sha((HERE / "review.json").read_bytes()), "quotes": len(quotes),
                  "new_confirmed_defects": 0}))
