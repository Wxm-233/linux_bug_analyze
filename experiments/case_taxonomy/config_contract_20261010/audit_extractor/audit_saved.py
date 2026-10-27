"""Read-only audit of saved bytes. Never imports/runs the fact extractor."""
from pathlib import Path
import hashlib
import json
import re

BASE = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
PARENT = "7ff730ca458e841dbcdc87f264d7afe3eaed525e"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((BASE / name).read_text(encoding="utf8"))


quote_count = 0
operation_count = 0


def check_quotes(obj, text):
    global quote_count, operation_count
    if isinstance(obj, dict):
        if {"start_line", "end_line", "text"} <= obj.keys():
            begin, end = obj["start_line"], obj["end_line"]
            lines = text.splitlines()
            assert 1 <= begin <= end <= len(lines)
            if "start_offset" in obj:
                start, finish = obj["start_offset"], obj["end_offset_exclusive"]
                assert 0 <= start < finish <= len(text)
                assert obj["text"] == text[start:finish]
                assert begin == text.count("\n", 0, start) + 1
                assert end == text.count("\n", 0, finish - 1) + 1
            else:
                assert obj["text"] == "\n".join(lines[begin - 1:end])
            quote_count += 1
        if obj.get("kind") == "lexical_nonempty_code_line":
            assert obj["quote"] == text.splitlines()[obj["line"] - 1]
            assert obj["executed"] is None
            operation_count += 1
        for value in obj.values():
            check_quotes(value, text)
    elif isinstance(obj, list):
        for value in obj:
            check_quotes(value, text)


names = ["extract_facts.py", "implementation_pre.json", "probe_inputs.json",
         "probe_results.json", "facts.json", "retrieval_manifest.json", "protocol_pre.md",
         "freeze_pre.json", "raw/receipts.json"]
before = {name: sha(BASE / name) for name in names}
pre, manifest, facts = read("implementation_pre.json"), read("retrieval_manifest.json"), read("facts.json")
inputs, probes = read("probe_inputs.json"), read("probe_results.json")
assert pre["phase"] == "pre_first_extraction" and pre["execution_count_before_freeze"] == 0
assert all(sha(BASE / name) == digest for name, digest in pre["files"].items())
assert manifest["parent"] == facts["parent"] == PARENT
assert len(manifest["sources"]) == len(facts["source_identities"]) == 8
source_text = {}
for item, identity in zip(manifest["sources"], facts["source_identities"]):
    assert item["revision"] == PARENT and item["status"] == "available"
    assert identity == {key: item[key] for key in ("path", "revision", "saved", "blob", "sha256", "bytes")}
    raw = (BASE / item["saved"]).read_bytes()
    assert len(raw) == item["bytes"] and hashlib.sha256(raw).hexdigest() == item["sha256"]
    assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == item["blob"]
    source_text[item["path"]] = raw.decode("utf8")

c = facts["c"]
target = source_text[manifest["target"]]
assert c["source"]["path"] == manifest["target"]
check_quotes(c, target)
assert len(c["references"]) == len(c["supported_guards"]) == len(facts["candidates"]) == 1
for ref in c["references"]:
    assert target[ref["offset"]:ref["offset"] + len(ref["symbol"])] == ref["symbol"]
    assert ref["actually_reachable"] is None
guard = c["supported_guards"][0]
assert guard["symbol"] == "CONFIG_BIG_ENDIAN" and guard["guard_quote"]["start_line"] == 665
assert all(guard[key] is False for key in ("cfg_certified", "preprocessor_value_certified",
                                        "actual_execution_certified", "enclosing_conditions_certified"))
assert c["translation_phase_splicing_complete"] is False and c["function_or_cfg_analysis"] is False
for branch in (guard["then"], guard["else"]):
    assert branch is not None and len(branch["operation_lines"]) == 5
    assert all(branch["quote"]["start_line"] <= op["line"] <= branch["quote"]["end_line"]
               for op in branch["operation_lines"])
for config in facts["kconfig"]:
    assert config["source"]["revision"] == PARENT
    check_quotes(config, source_text[config["source"]["path"]])
    assert config["solver_run"] is False
    for declaration in config["declarations"]:
        assert declaration["kconfig_context_resolved"] is False
        assert declaration["value_or_reachability_certified"] is False
complete_cpu = [k["source"]["path"] for k in facts["kconfig"]
                if any(d["symbol"] == "CPU_BIG_ENDIAN" for d in k["declarations"])]
assert complete_cpu == ["arch/arm64/Kconfig"]

receipts = read("raw/receipts.json")
assert len(receipts) == 4 and [r["exit"] for r in receipts] == [0, 0, 0, 1]
for receipt in receipts:
    raw = (BASE / "raw" / (receipt["label"] + ".stdout.bin")).read_bytes()
    assert len(raw) == receipt["stdout_bytes"]
    assert hashlib.sha256(raw).hexdigest() == receipt["stdout_sha256"]
for query, receipt in zip(facts["queries"], receipts[1:]):
    assert query["argv"] == receipt["argv"] and query["exit"] == receipt["exit"]
    assert query["stdout_sha256"] == receipt["stdout_sha256"]
    assert query["query_complete_for_all_kconfig_syntax"] is False
    assert query["generated_outputs_or_external_definitions_covered"] is False
    raw_lines = (BASE / "raw" / (receipt["label"] + ".stdout.bin")).read_text(encoding="utf8").splitlines()
    assert len(raw_lines) == query["hit_count"] == len(query["hits"])
    for line, hit in zip(raw_lines, query["hits"]):
        match = re.fullmatch(r"([0-9a-f]{40}):(.+):(\d+):(.*)", line)
        assert match and match.group(1) == hit["revision"] == PARENT
        assert match.group(2) == hit["path"] and int(match.group(3)) == hit["line"] and match.group(4) == hit["text"]
        if hit["path"] in source_text:
            assert source_text[hit["path"]].splitlines()[hit["line"] - 1] == hit["text"]
        assert hit["complete_definition_text_available"] == (hit["path"] in source_text)
assert [q["hit_count"] for q in facts["queries"]] == [15, 1, 0]
arm = [h for h in facts["queries"][0]["hits"] if h["path"] == "arch/arm/mm/Kconfig"]
assert len(arm) == 1 and arm[0]["line"] == 740 and arm[0]["complete_definition_text_available"] is False
candidate = facts["candidates"][0]
check_quotes(candidate, target)
assert candidate["verdict"] == "needs_source_review" and candidate["automatic_replacement"] is None
assert candidate["runtime_or_compile_error_certified"] is False and candidate["property_contract_certified"] is False
assert facts["new_confirmed_cases"] == facts["independent_positive_cases"] == facts["new_git_commands"] == 0
assert facts["scope"] == "message_informed_development" and facts["repair_patch_read"] is False

assert probes["kind"] == inputs["kind"] == "synthetic_implementation_probes_not_cases"
assert probes["count"] == len(probes["results"]) == len(inputs["probes"]) == 8
for probe, result in zip(inputs["probes"], probes["results"]):
    assert probe["id"] == result["id"] and probe["kind"] == result["kind"]
    assert probe["expected"] == result["expected"] == result["actual_summary"]
    assert result["passed"] is True
    check_quotes(result["facts"], probe["text"])
assert probes["passed"] == 8
after = {name: sha(BASE / name) for name in names}
assert before == after
result = {"result": "pass_for_saved_bounded_lexical_development", "inputs_unchanged": True,
          "input_sha256": before, "same_parent_sources": 8, "checked_quote_objects": quote_count,
          "checked_operation_line_objects": operation_count,
          "real_reference_count": 1, "real_supported_guard_count": 1,
          "source_insufficient_candidate_count": 1,
          "stored_synthetic_probe_count": 8, "extractor_execution_by_auditor": 0,
          "additional_probes_by_auditor": 0, "git_requests_by_auditor": 0,
          "new_confirmed_cases": 0, "independent_positive_cases": 0,
          "limitations": ["lexical_operations uses whole lines: compact mixed lines may omit or overinclude operations",
                          "no full translation phase splicing; escaped CRLF and token joins are outside coverage",
                          "Kconfig item bounds use indentation; not a complete Kconfig parser/solver",
                          "frozen declaration grep only matches commands at column zero",
                          "ARM mm Kconfig definition is grep-hit-only; complete item was not retrieved",
                          "guard branch ranges are lexical, not CFG, configuration values or actual execution",
                          "stored probe success is implementation checking, not unknown-case detection"]}
(OUT / "audit_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
print(json.dumps({k: result[k] for k in ("result", "inputs_unchanged", "same_parent_sources", "checked_quote_objects", "checked_operation_line_objects")}, ensure_ascii=False))
