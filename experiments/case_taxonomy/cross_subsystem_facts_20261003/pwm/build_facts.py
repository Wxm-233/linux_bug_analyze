"""Write the human-reviewed PWM facts from saved evidence, without new experiments."""
import json
from pathlib import Path
from run_pwm import HERE, REVISIONS, SOURCE, hashes, now, sha, write_json

manifests = [json.loads((HERE / name).read_text(encoding="utf-8")) for name in
             ("source_manifest.json", "source_extension_manifest.json", "type_contract_manifest.json")]
sources = [item for manifest in manifests for item in manifest]
lookup = {(item["revision_label"], item["source_path"]): item for item in sources if item["available"]}
evidence = []


def cite(label, name, path, first, last, kind="human_source_binding"):
    item = lookup[(label, path)]
    raw = (HERE / item["saved_path"]).read_bytes()
    assert sha(raw) == item["sha256"]
    lines = raw.decode("utf-8").splitlines()
    assert 1 <= first <= last <= len(lines)
    identity = label + ":" + name
    evidence.append({"id": identity, "origin": kind, "revision": item["revision"],
                     "source_path": path, "blob_oid": item["blob_oid"],
                     "source_sha256": item["sha256"], "saved_source": item["saved_path"],
                     "line_start": first, "line_end": last,
                     "source_excerpt": "\n".join(lines[first - 1:last])})
    return identity


firmware = "drivers/firmware/raspberrypi.c"
header = "include/soc/bcm2835/raspberrypi-firmware.h"
for label in REVISIONS:
    cite(label, "pwm_property_layout", SOURCE, 34, 38)
    cite(label, "get_complete_function", SOURCE, 65, 83)
    cite(label, "set_complete_function", SOURCE, 46, 63)
    cite(label, "zero_reg_macro", SOURCE, 26, 26)
    cite(label, "probe_complete_function_and_only_get_caller", SOURCE, 139, 176)
    cite(label, "set_caller_and_duty_value_source", SOURCE, 98, 131)
    cite(label, "driver_binding", SOURCE, 178, 191)
    cite(label, "property_complete_function", firmware, 148, 177)
    cite(label, "property_list_complete_function", firmware, 87, 131)
    cite(label, "transaction_complete_function", firmware, 47, 71)
    cite(label, "property_channel_and_message_macros", firmware, 18, 21)
    cite(label, "response_callback", firmware, 37, 41)
    cite(label, "firmware_probe_and_mailbox_request", firmware, 253, 287)
    cite(label, "firmware_handle_get", firmware, 322, 343)
    cite(label, "tag_header_layout_and_source_documentation", header, 14, 34)
    cite(label, "poe_tag_numbers", header, 91, 92)
    cite(label, "firmware_enabled_declarations_and_disabled_stubs", header, 139, 172)
    cite(label, "mailbox_generic_send", "drivers/mailbox/mailbox.c", 250, 282)
    cite(label, "mailbox_generic_submit", "drivers/mailbox/mailbox.c", 53, 89)
    cite(label, "mailbox_generic_receive", "drivers/mailbox/mailbox.c", 152, 157)
    cite(label, "bcm2835_mailbox_send_and_receive", "drivers/mailbox/bcm2835-mailbox.c", 66, 90)
    cite(label, "bcm2835_mailbox_ops", "drivers/mailbox/bcm2835-mailbox.c", 120, 125)
    cite(label, "pwm_kconfig", "drivers/pwm/Kconfig", 435, 442)
    cite(label, "firmware_kconfig", "drivers/firmware/Kconfig", 149, 154)
    cite(label, "mailbox_kconfig", "drivers/mailbox/Kconfig", 121, 127)
    cite(label, "arm_bcm2835_kconfig", "arch/arm/mach-bcm/Kconfig", 153, 169)
    cite(label, "arm64_bcm2835_kconfig", "arch/arm64/Kconfig.platforms", 37, 49)
    cite(label, "arm_big_endian_kconfig", "arch/arm/mm/Kconfig", 741, 756)
    cite(label, "arm64_big_endian_kconfig", "arch/arm64/Kconfig", 1177, 1187)
    cite(label, "dt_binding_poe_pwm_child", "Documentation/devicetree/bindings/arm/bcm/raspberrypi,bcm2835-firmware.yaml", 64, 85)
    cite(label, "dt_binding_example", "Documentation/devicetree/bindings/arm/bcm/raspberrypi,bcm2835-firmware.yaml", 87, 107)
    cite(label, "le32_typedef", "include/uapi/linux/types.h", 21, 32)
    cite(label, "u32_underlying_typedef", "include/uapi/asm-generic/int-ll64.h", 23, 29)
    cite(label, "packed_attribute", "include/linux/compiler_attributes.h", 285, 289)
    cite(label, "generic_conversion_names", "include/linux/byteorder/generic.h", 86, 89)
    cite(label, "big_endian_conversion_definition", "include/uapi/linux/byteorder/big_endian.h", 32, 35)
    cite(label, "little_endian_conversion_definition", "include/uapi/linux/byteorder/little_endian.h", 32, 35)
    cite(label, "arm_byteorder_selection", "arch/arm/include/uapi/asm/byteorder.h", 19, 24)
    cite(label, "arm64_byteorder_selection", "arch/arm64/include/uapi/asm/byteorder.h", 20, 25)

raw_reports = {label: json.loads((HERE / "raw" / (label + ".json")).read_text(encoding="utf-8")) for label in REVISIONS}
primary = {}
for label, report in raw_reports.items():
    matches = [item for item in report["findings"] if item["function"] == "raspberrypi_pwm_get_property" and item["field"] == "reg"]
    assert len(matches) == 1
    primary[label] = {"automatic_fact": matches[0], "human_binding": {
        "interface_identity": "Raspberry Pi PoE HAT PWM firmware property; not Tegra",
        "field_contract": "source-declared __le32, written from host u32 reg parameter",
        "local_only_caller": "raspberrypi_pwm_probe at line 168",
        "argument_expression": "RPI_PWM_CUR_DUTY_REG", "macro_value": "0x0",
        "source_visible_value_domain": [0], "ordinary_cross_translation_unit_direct_call": "not permitted: helper is static",
        "indirect_function_pointer_use_found": False,
        "local_value_domain_scope": "full saved translation unit and same-revision Git grep for helper and macro; no preprocessing/build/device execution",
        "runtime_write_difference_for_visible_zero_value": "none attributable to this assignment: byte-order exchange preserves all-zero bytes",
        "nonzero_runtime_argument_proven": False, "added_nonzero_probe_or_grid": False,
        "candidate_interpretation": "type-directed review lead; not a demonstrated BE hardware failure",
        "evidence_ids": [label + ":get_complete_function", label + ":zero_reg_macro", label + ":probe_complete_function_and_only_get_caller"]}}

facts = {
    "schema_version": 1, "recorded_at_utc": now(), "date": "2026-10-03",
    "experiment_kind": "already-read development facts-contract-consumption review; not blind test or holdout",
    "case_identity": "pwm_raspberrypi_poe_get_reg", "case_count": 1,
    "primary_unit": "one reg write in raspberrypi_pwm_get_property", "revisions": REVISIONS,
    "count_unit": "assignment sites; file counts are not independent cases",
    "automatic_tool": {"name": "endian_producer_single_revision.py", "dependency": "endian_consumer_single_revision.py",
                       "execution": "original CLI directly in WSL python3 -B; no getter adapter",
                       "source_scope": "source file plus quoted local includes <=2 edges; this file has no quoted includes",
                       "never_claimed": ["cross-function dataflow", "macro value domain", "firmware wire protocol", "runtime reachability"],
                       "hash_records": ["prepare_hashes_before.json", "prepare_hashes_after.json", "replay_hashes_before.json", "replay_hashes_after.json"],
                       "file_counts": {label: report["counts"] for label, report in raw_reports.items()}},
    "primary": primary,
    "normal_controls": {label: [item for item in report["findings"] if item["function"] == "raspberrypi_pwm_set_property"]
                        for label, report in raw_reports.items()},
    "manual_payload_layout": {
        "definition": "packed raspberrypi_pwm_prop: __le32 reg, val, ret in that order",
        "derived_expected_size_bytes": 12, "derived_expected_offsets": {"reg": 0, "val": 4, "ret": 8},
        "basis": "source fixed-width/endian typedef plus __packed attribute; no target layout compilation",
        "compiled_layout_proof": False,
        "initialization": "get initializes reg explicitly; omitted val/ret zero-initialized under C aggregate rules",
        "tag_ids": {"GET_POE_HAT_VAL": "0x00030049", "SET_POE_HAT_VAL": "0x00030050"}},
    "manual_consumption_chain": [
        {"step": 1, "consumer": "rpi_firmware_property", "source": firmware, "lines": [148, 177],
         "action": "allocate sizeof(header)+buf_size; native u32 tag/buf_size/req_resp_size header with req_resp_size=0; memcpy original tag_data bytes behind header",
         "payload_byteorder_conversion": False, "caller_buffer_copyback": "memcpy entire original buf_size after property_list returns, without testing ret first"},
        {"step": 2, "consumer": "rpi_firmware_property_list", "source": firmware, "lines": [87, 131],
         "action": "size=tag_size+12; allocate coherent DMA buffer; write native u32 size/status/end words; memcpy entire tags at buf[2]; barrier; transaction channel 8 and bus address; barrier; memcpy entire tag_size back",
         "payload_byteorder_conversion": False, "caller_buffer_copyback": "after transaction regardless of transaction return; earlier alignment/allocation failures return before this copyback"},
        {"step": 3, "consumer": "rpi_firmware_transaction", "source": firmware, "lines": [47, 71],
         "action": "message combines bus address high 28 bits and channel 8 low 4 bits; mbox_send_message receives address of u32 message, not address of msg.reg; synchronous completion wait",
         "payload_field_semantics_consumed_in_this_function": False},
        {"step": 4, "consumer": "mbox_send_message -> msg_submit -> bcm2835_send_data", "source": "drivers/mailbox/mailbox.c and bcm2835-mailbox.c",
         "action": "generic mailbox queues pointer and calls ops->send_data; bcm2835 dereferences u32 message and writel to mailbox MMIO",
         "payload_field_semantics_consumed_in_this_function": False},
        {"step": 5, "consumer": "external VPU firmware", "action": "local comments identify remote property interface and DMA buffer; remote reg parser, field wire endianness and firmware version not present in saved Linux source",
         "external_parser_or_normative_spec_proof": False},
        {"step": 6, "consumer": "PWM return handling", "source": SOURCE, "lines": [75, 80],
         "action": "return API error first; test msg.ret for zero/nonzero; only then decode msg.val with le32_to_cpu into caller u32",
         "msg_ret_zero_test_representation_invariant": True, "msg_val_decode_local_type_contract": "explicit LE-to-native conversion"}
    ],
    "manual_length_and_error_checks": {
        "property_allocation_failure": "-ENOMEM",
        "property_list_alignment": "(tag_size+12)&3 rejected with -EINVAL",
        "property_list_allocation_failure": "-ENOMEM",
        "one_mib_size": "WARN_ON(size>=1024*1024), not a hard rejection",
        "transaction": "negative mbox_send_message error or completion timeout (-ETIMEDOUT)",
        "outer_reply_status": "when transaction ret==0, buf[1] must equal RPI_FIRMWARE_STATUS_SUCCESS (0x80000000), else -EINVAL",
        "per_tag_reply_length_or_response_bit_validation_in_property_wrapper": False,
        "req_resp_size": "set to zero on request; source header comment discusses response length/bit, but wrapper does not inspect returned field",
        "pwm_reply_status": "msg.ret nonzero -> -EIO; msg.val read only after both API return and msg.ret are zero",
        "new_defect_claim_from_unchecked_tag_length": False},
    "manual_configuration_and_applicability": {
        "PWM_RASPBERRYPI_POE": "RASPBERRYPI_FIRMWARE || (COMPILE_TEST && !RASPBERRYPI_FIRMWARE)",
        "RASPBERRYPI_FIRMWARE": "depends on BCM2835_MBOX",
        "BCM2835_MBOX": "depends on ARCH_BCM2835",
        "compile_test_only": "disabled firmware header stubs return -ENOSYS / NULL; PWM probe cannot acquire firmware handle and returns -EPROBE_DEFER",
        "source_binding": "firmware-poe-pwm compatible child under firmware node; parent handle and mailbox must exist",
        "DT_binding_evidence": "same-revision schema contains required firmware mailbox and PWM child, plus example; not a deployed DT",
        "architecture_source": "ARM ARCH_BCM2835 (multi_v6/multi_v7) and ARM64 ARCH_BCM2835 declarations saved; generic ARM/ARM64 CPU_BIG_ENDIAN options saved",
        "support_claim": "these selected Kconfig declarations do not establish Raspberry Pi firmware/board BE runtime support or prohibit it",
        "effective_config_preprocessing_build_or_device_reachability_proof": False,
        "tegra_policy_transferred": False},
    "proof_flags": {
        "source_declared_le32_field": True,
        "source_host_u32_parameter": True,
        "local_payload_copy_path_without_conversion": True,
        "local_only_get_caller_value_zero": True,
        "request_bytes_differ_for_observed_local_zero_domain": False,
        "external_normative_firmware_byteorder_proven": False,
        "external_firmware_parser_observed": False,
        "applicable_big_endian_supported_device_configuration_proven": False,
        "compiled_or_runtime_reachability_proven": False,
        "runtime_bug_demonstrated": False,
        "patch_confirms_actual_fault": False,
        "independent_generalization_or_detection_accuracy": False},
    "unknowns": [
        "External PoE tag field wire specification and actual VPU implementation/version were not supplied or examined.",
        "A supported, bootable Raspberry Pi BE configuration and deployment DT/hardware reachability were not established.",
        "No compiled layout, sparse rerun, preprocessing, DMA/MMIO execution or response buffer contents were observed.",
        "No nonzero get reg source was found in the saved translation unit; future/generated/out-of-tree code is outside this bounded review.",
        "The source documentation of req_resp_size is not independently verified against the remote firmware specification.",
        "Correctness of the complete envelope/native-u32 framing and the entire driver is outside the primary one-field conclusion."],
    "system_check_statement": "At the fixed versions, review host u32 writes into the local __le32 reg field and follow the payload memcpy path. Before claiming a firmware endian fault require the remote format, supported configuration and an actual non-invariant value source. This saved get helper has only reg=0, so the observed local domain does not expose an assignment-byte difference.",
    "machine_human_difference": {
        "machine": "parameter u32 -> __le32 assignment plus later &msg call yields candidate; fix explicit cpu_to_le32 yields normal",
        "human_additions": ["static helper unique caller and zero macro value", "property API/DMA byte-copy chain and return overwrite", "outer error/length checks and lack of per-tag length inspection", "Raspberry Pi configuration conditions", "external contract/runtime unknowns"],
        "interpretation": "candidate retained as local type-review lead; current visible value domain makes runtime fault conclusion unsupported"},
    "patch_role": "saved already-read fix shows only reg initializer conversion and mentions sparse; used as development contrast, not independent truth or hardware proof",
    "integrity": {"source_manifests": ["source_manifest.json", "source_extension_manifest.json", "type_contract_manifest.json"],
                  "command_logs": ["commands_prepare.json", "commands_replay.json", "commands_source_extension.json", "commands_type_contract.json"],
                  "stdout_stderr": "raw bytes retained separately; NUL WSL startup warnings never parsed as SHA",
                  "raw_manifest": "replay_manifest.json", "current_code_and_protocol": hashes()},
    "source_inventory": sources, "evidence": evidence,
}
write_json(HERE / "facts.json", facts)
print(json.dumps({"facts_sha256": sha((HERE / "facts.json").read_bytes()), "evidence_records": len(evidence),
                  "available_source_records": sum(item["available"] for item in sources)}, ensure_ascii=False))
