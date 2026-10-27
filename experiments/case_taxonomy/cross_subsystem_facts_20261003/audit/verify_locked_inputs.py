"""Read only saved cross-subsystem artifacts; write this audit's own receipt.

No subprocess, Git lookup, analyzer import/replay, compilation, or new input.
This verifies byte/quote identity. Semantic conclusions are independently read.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
TAXONOMY = STAGE.parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


failures = []
checks = {}
counts = {}
inputs = {}


def record(path):
    inputs[path.relative_to(STAGE).as_posix()] = sha(path)


def require(condition, label):
    if not condition:
        failures.append(label)


for case in ("ocfs2", "pwm"):
    base = STAGE / case
    manifest = read(base / "artifact_manifest.json")
    start = len(failures)
    for item in manifest["files"]:
        path = base / item["path"]
        require(path.is_file(), f"{case}: absent locked file {item['path']}")
        if path.is_file():
            require(sha(path) == item["sha256"], f"{case}: artifact SHA {item['path']}")
            if "bytes" in item:
                require(path.stat().st_size == item["bytes"], f"{case}: artifact length {item['path']}")
            record(path)
    record(base / "artifact_manifest.json")
    if (base / "lock.json").is_file():
        record(base / "lock.json")
        lock = read(base / "lock.json")
        for field, filename in (("artifact_manifest_sha256", "artifact_manifest.json"),
                                ("facts_sha256", "facts.json"), ("review_sha256", "review.md"),
                                ("source_manifest_sha256", "source_manifest.json"),
                                ("command_log_sha256", "commands.json")):
            require(lock[field] == sha(base / filename), f"{case}: lock {field}")
    checks[f"{case}_locked_artifact_hashes"] = len(failures) == start
    counts[f"{case}_locked_artifacts"] = len(manifest["files"])

    start = len(failures)
    source_manifests = ["source_manifest.json"]
    if case == "pwm":
        source_manifests += ["source_extension_manifest.json", "type_contract_manifest.json"]
    source_records = []
    for filename in source_manifests:
        source_records.extend(read(base / filename))
    present = [s for s in source_records if s.get("available", True)]
    for item in present:
        path = base / item["saved_path"]
        raw = path.read_bytes()
        require(sha(path) == item["sha256"], f"{case}: source SHA {item['saved_path']}")
        require(blob(raw) == item.get("blob", item.get("blob_oid")),
                f"{case}: source Git blob {item['saved_path']}")
        require(len(raw.splitlines()) == item["line_count"], f"{case}: line count {item['saved_path']}")
    checks[f"{case}_source_sha_git_blob_line_counts"] = len(failures) == start
    counts[f"{case}_source_records_available"] = len(present)
    counts[f"{case}_source_records_unavailable"] = len(source_records) - len(present)

    facts = read(base / "facts.json")
    start = len(failures)
    excerpts = []
    for item in nodes(facts):
        quote_key = "excerpt" if "excerpt" in item else "source_excerpt"
        if "line_start" not in item or quote_key not in item:
            continue
        excerpts.append(item)
        path = base / item.get("saved_path", item.get("saved_source"))
        lines = path.read_text(encoding="utf-8").splitlines()
        a, z = item["line_start"], item["line_end"]
        require(1 <= a <= z <= len(lines), f"{case}: excerpt range {path}:{a}-{z}")
        require("\n".join(lines[a-1:z]) == item[quote_key], f"{case}: excerpt bytes {path}:{a}-{z}")
        require(sha(path) == item.get("sha256", item.get("source_sha256")), f"{case}: excerpt SHA {path}")
        require(blob(path.read_bytes()) == item.get("blob", item.get("blob_oid")), f"{case}: excerpt blob {path}")
        matches = [s for s in present if s["saved_path"] == item.get("saved_path", item.get("saved_source"))]
        require(len(matches) == 1, f"{case}: excerpt unique source record {path}")
        if matches:
            revision = matches[0]["revision"]
            if case == "ocfs2" and revision.endswith("^"):
                revision = facts["selection"]["resolved_revisions"]["parent"]
            require(item["revision"] == revision, f"{case}: excerpt revision {path}")
    checks[f"{case}_all_excerpt_bindings"] = len(failures) == start
    counts[f"{case}_excerpts"] = len(excerpts)

    start = len(failures)
    command_logs = ["commands.json"] if case == "ocfs2" else facts["integrity"]["command_logs"]
    command_count = 0
    for filename in command_logs:
        for command in read(base / filename):
            command_count += 1
            for stream in ("stdout", "stderr"):
                path = base / command[stream]
                require(sha(path) == command[f"{stream}_sha256"], f"{case}: command {filename} {path.name}")
    checks[f"{case}_all_command_stream_hashes"] = len(failures) == start
    counts[f"{case}_command_records"] = command_count

    start = len(failures)
    labels = ("parent", "fix") if case == "ocfs2" else ("parent", "fixed")
    for label in labels:
        raw_path = base / "raw" / f"{label}.json"
        raw = read(raw_path)
        legacy = TAXONOMY / f"endian_{'consumer_ocfs2' if case == 'ocfs2' else 'producer_pwm'}_{'fix' if label != 'parent' else label}.json"
        require(raw_path.read_bytes() == legacy.read_bytes(), f"{case}: raw bytes differ from old development JSON {label}")
        for source in raw["files_read"]:
            candidate = [s for s in present if s.get("path", s.get("source_path")) == source["path"]
                         and s["revision"] == raw["revision"]]
            require(len(candidate) == 1, f"{case}: raw source unique {label} {source['path']}")
            if candidate:
                require(candidate[0]["sha256"] == source["sha256"], f"{case}: raw source hash {label} {source['path']}")
        if case == "ocfs2":
            automatic = facts["automatic_facts"]["revisions"][label]
            require(sha(raw_path) == automatic["raw_sha256"], f"{case}: summary raw SHA {label}")
            require(raw["counts"] == automatic["background_whole_file_counts"], f"{case}: summary counts {label}")
            require(automatic["primary"] in raw["findings"], f"{case}: primary copied exactly {label}")
            require(all(x in raw["findings"] for x in automatic["normal_control_reads"]), f"{case}: controls copied exactly {label}")
        else:
            require(raw["counts"] == facts["automatic_tool"]["file_counts"][label], f"{case}: summary counts {label}")
            require(facts["primary"][label]["automatic_fact"] in raw["findings"], f"{case}: primary copied exactly {label}")
            require(all(x in raw["findings"] for x in facts["normal_controls"][label]), f"{case}: controls copied exactly {label}")
    checks[f"{case}_raw_legacy_source_and_summary_identity"] = len(failures) == start

start = len(failures)
baseline = read(HERE / "baseline_inputs.json")
for item in baseline["inputs"]:
    require(sha(TAXONOMY / item["path"]) == item["sha256"], f"old baseline changed {item['path']}")
checks["old_baseline_inputs_unchanged"] = len(failures) == start

start = len(failures)
ocfs2 = STAGE / "ocfs2"
states = [read(ocfs2 / filename) for filename in
          ("tool_before.json", "tool_after_prepare.json", "tool_before_replay.json", "tool_after_replay.json", "final_tool_state.json")]
require(all({k: state[k] for k in states[0]} == states[0] for state in states),
        "ocfs2 direct imported module/state snapshot mismatch")
require(states[2] == states[3] == states[4], "ocfs2 replay/final protocol snapshot mismatch")
require(states[0]["script_sha256"] == sha(TAXONOMY / "endian_consumer_single_revision.py"), "ocfs2 current legacy script differs")
require(states[2]["protocol_sha256"] == sha(STAGE / "protocol_pre.md"), "ocfs2 current protocol differs")
facts = read(ocfs2 / "facts.json")
require(facts["integrity"]["facts_builder_sha256"] == sha(ocfs2 / "build_facts.py"), "ocfs2 final facts builder hash mismatch")
require(facts["integrity"]["runner_sha256_at_facts_lock"] == sha(ocfs2 / "runner.py"), "ocfs2 final runner hash mismatch")
checks["ocfs2_direct_dependency_snapshots_and_final_builder_consistent"] = len(failures) == start

start = len(failures)
pwm = STAGE / "pwm"
for phase in ("prepare", "replay", "extension", "type_contract"):
    before = read(pwm / f"{phase}_hashes_before.json")["files"]
    after = read(pwm / f"{phase}_hashes_after.json")["files"]
    require(before == after, f"pwm {phase} code/protocol snapshot mismatch")
    for name in ("endian_consumer_single_revision.py", "endian_producer_single_revision.py"):
        require(before[name]["sha256"] == sha(TAXONOMY / name), f"pwm {phase} old script mismatch {name}")
    require(before["protocol_pre.md"]["sha256"] == sha(STAGE / "protocol_pre.md"), f"pwm {phase} protocol mismatch")
for name, item in read(pwm / "facts.json")["integrity"]["current_code_and_protocol"].items():
    require(sha(Path(item["absolute_path"])) == item["sha256"], f"pwm final code/protocol mismatch {name}")
checks["pwm_legacy_dependency_and_runner_protocol_snapshots_consistent"] = len(failures) == start

for name in ("protocol_pre.md", "synthesis.md", "checkpoint.md"):
    record(STAGE / name)
for name in ("baseline_inputs.json", "review_criteria.md", "verify_locked_inputs.py"):
    record(HERE / name)

result = {"status": "pass" if not failures else "needs_review", "checks": checks,
          "counts": counts, "failures": failures, "final_inputs_sha256": dict(sorted(inputs.items())),
          "scope": "saved-byte, quote and identity checks only; no Git subprocess, analyzer replay, compiler, models or new kernel input",
          "dependency_limit": "consumer direct imported module origins are retained snapshot evidence, not recursively materialized dependency files; PWM records legacy producer plus consumer dependency",
          "snapshot_limit": "ocfs2 prepare before/after receipts predate addition of protocol fields; common tool/import fields match all snapshots, protocol fields match replay before/after and final only"}
(HERE / "mechanical_checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": result["status"], "checks": checks, "counts": counts, "failures": failures,
                  "input_count": len(inputs)}, ensure_ascii=False))
