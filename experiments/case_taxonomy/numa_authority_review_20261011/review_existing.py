"""Parse fixed historical records and verify identities; execute no experiments."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def storage(bits, width):
    return ((bits + width - 1) // width) * (width // 8)


def main():
    materials = load(HERE / "materials_pre.json")
    repo = Path(materials["source_root"])
    assert sha(HERE / "protocol_pre.md") == materials["protocol_sha256"]
    for item in materials["materials"]:
        assert item["status"] == "available"
        assert sha(repo / item["path"]) == item["sha256"]
    pause = load(HERE / "pause_manifest.json")
    for path, expected in pause["files"].items():
        assert sha(HERE / path) == expected, path
    old = load(repo / "analysis_out/numa-boundary-review-20260921/results.json")
    assert len(old) == 12
    variants = ["original_effective_bits", "declared_maxnode", "declared_maxnode_padded64"]
    expected_keys = {(v, bits, tail) for v in variants for bits in [65, 96] for tail in [0, 1]}
    indexed = {(r["variant"], r["effective_bits"], r["tail"]): (i, r) for i, r in enumerate(old)}
    assert len(indexed) == 12 and set(indexed) == expected_keys
    normalized = []
    for variant in variants:
        for bits in [65, 96]:
            for tail in [0, 1]:
                index, row = indexed[variant, bits, tail]
                call_maxnode = bits + 1
                assert row["syscall_maxnode"] == call_maxnode
                declared32 = storage(call_maxnode, 32)
                allocated = storage(bits, 32) if variant == variants[0] else (
                    declared32 if variant == variants[1] else storage(call_maxnode, 64))
                assert row["storage_bytes"] == allocated
                recorded_rc = -14 if allocated == 12 else (0 if tail == 0 else -22)
                # This checks the recorded profile, not the validity of the ABI oracle.
                assert row["actual"]["rc"] == recorded_rc
                assert row["actual"]["consumed"] == int(recorded_rc == 0)
                assert row["actual"]["value"] == int(recorded_rc == 0)
                assert row["actual"]["page_faults"] == int(recorded_rc == -14)
                normalized.append({"record_index_zero_based": index, "variant": variant,
                    "effective_bits": bits, "call_maxnode": call_maxnode, "tail": tail,
                    "readable_bytes": allocated, "declared32_bytes_under_reported_storage_rule": declared32,
                    "native64_bytes_under_same_rule": storage(call_maxnode, 64),
                    "tail_start_byte_in_saved_64bit_slice": ((bits - 1) // 64) * 8,
                    "tail_read_end_exclusive_in_saved_slice": ((bits - 1) // 64) * 8 + 8,
                    "saved_rc": recorded_rc, "tail1_location": "node64_at_byte8_within_12byte_input",
                    "new_kernel_observation": False})
    recent = [json.loads(line) for line in (repo / "analysis_out/numa-padding-20260928/results.jsonl").read_text().splitlines() if line]
    expected = [(1026, 132, 0, -14), (1026, 136, 0, 0), (1026, 136, 1, -22), (1057, 136, 1, -22)]
    assert len(recent) == 4
    for row, values in zip(recent, expected):
        assert (row["maxnode"], row["bytes"], row["poison_word34"], row["set_rc"]) == values
        assert row["first_allowed_node"] == 0
    harness = repo / "analysis_out/numa-entry-20260915-v2/followup/harness.c"
    probe = repo / "experiments/case_taxonomy/numa_padding_probe.c"
    htext, ptext = harness.read_text(), probe.read_text()
    assert "((uint32_t*)data)[2]=1" in htext
    assert "p[132] = 1" in ptext
    for name, expected_values in [("maxnodes", [1026, 1026, 1026, 1057]), ("bytes", [132, 136, 136, 136]), ("poison", [0, 0, 1, 1])]:
        match = re.search(r"const int " + name + r"\[\] = \{([^}]+)\}", ptext)
        assert match and [int(v.strip()) for v in match.group(1).split(",")] == expected_values
    quotations = []
    for path, ranges in [(harness, [(14, 24), (32, 54), (55, 103), (104, 137), (150, 177), (180, 196)]),
                         (probe, [(6, 13), (45, 53), (65, 83)])]:
        lines = path.read_text().splitlines()
        for first, last in ranges:
            assert 1 <= first <= last <= len(lines)
            quotations.append({"source": str(path.relative_to(repo)).replace("\\", "/"),
                "sha256": sha(path), "line_start": first, "line_end": last,
                "quote": "\n".join(lines[first - 1:last])})
    out = {"status": "PASS_for_saved_record_integrity_not_ABI_adjudication",
        "historical_slice_records": normalized, "prior_i386_return_records": recent,
        "historical_tail1_is_range_external_word_test": False,
        "recent_external_word_location_bytes": [132, 135],
        "harness_error_observation_groups": 2, "unresolved_compat_observation_groups": 2,
        "ABI_text_and_Microsoft_tag_evidence_level": "reported_in_existing_reviews",
        "running_binary_to_source_mapping": "not_in_fixed_materials",
        "new_kernel_tests": 0, "new_Git_or_web_retrievals": 0, "new_confirmed_cases": 0}
    (HERE / "parsed_evidence.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "source_quotes.json").write_text(json.dumps({"quotes": quotations}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": out["status"], "stored_slice_records": 12, "stored_i386_records": 4,
                      "source_quotes": len(quotations), "old_materials_modified": 0, "new_kernel_tests": 0}))


if __name__ == "__main__":
    main()
