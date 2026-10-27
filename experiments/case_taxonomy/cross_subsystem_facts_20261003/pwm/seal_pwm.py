"""Integrity audit and final file inventory of this new PWM directory only."""
import hashlib
import json
from pathlib import Path
from run_pwm import HERE, LEGACY, REVISIONS, hashes, now, sha, write_json

facts = json.loads((HERE / "facts.json").read_text(encoding="utf-8"))
checked_sources = 0
for item in facts["source_inventory"]:
    if not item["available"]:
        continue
    raw = (HERE / item["saved_path"]).read_bytes()
    assert sha(raw) == item["sha256"]
    assert hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest() == item["blob_oid"]
    checked_sources += 1
for item in facts["evidence"]:
    raw = (HERE / item["saved_source"]).read_bytes()
    assert sha(raw) == item["source_sha256"]
    excerpt = "\n".join(raw.decode("utf-8").splitlines()[item["line_start"]-1:item["line_end"]])
    assert excerpt == item["source_excerpt"]
expected_counts = {"parent": {"candidate": 1, "normal": 2, "insufficient": 0},
                   "fixed": {"candidate": 0, "normal": 3, "insufficient": 0}}
for label, old_name in (("parent", "endian_producer_pwm_parent.json"), ("fixed", "endian_producer_pwm_fix.json")):
    raw = (HERE / "raw" / (label + ".json")).read_bytes()
    assert raw == (LEGACY / old_name).read_bytes()
    report = json.loads(raw)
    assert report["revision"] == REVISIONS[label]
    assert report["counts"] == expected_counts[label]
    saved = next(item for item in facts["source_inventory"] if item["available"] and item["revision_label"] == label and item["source_path"] == report["source_file"])
    assert report["source_sha256"] == saved["sha256"]
for phase in ("prepare", "replay", "source_extension", "type_contract"):
    commands = json.loads((HERE / ("commands_" + phase + ".json")).read_text(encoding="utf-8"))
    for item in commands:
        for stream in ("stdout", "stderr"):
            assert sha((HERE / item[stream]).read_bytes()) == item[stream + "_sha256"]
before = json.loads((HERE / "replay_hashes_before.json").read_text(encoding="utf-8"))["files"]
after = json.loads((HERE / "replay_hashes_after.json").read_text(encoding="utf-8"))["files"]
assert before == after == hashes()
write_json(HERE / "integrity_check.json", {
    "checked_at_utc": now(), "status": "pass", "checked_source_records": checked_sources,
    "checked_evidence_records": len(facts["evidence"]), "raw_replay_identical_to_legacy_bytes": True,
    "source_blob_oid_and_sha256_verified_from_saved_bytes": True,
    "command_stream_sha256_verified": True, "legacy_dependency_runner_protocol_unchanged": True,
    "check_scope": "artifact integrity and source binding; not a runtime or normative-contract test"})
files = []
for path in sorted(HERE.rglob("*")):
    if path.is_file() and path.name != "artifact_manifest.json":
        raw = path.read_bytes()
        files.append({"path": str(path.relative_to(HERE)), "bytes": len(raw), "sha256": sha(raw)})
write_json(HERE / "artifact_manifest.json", {
    "sealed_at_utc": now(), "scope": str(HERE), "files": files,
    "self_excluded": "artifact_manifest.json; its final SHA is reported to parent separately",
    "no_further_edits_after_parent_notification": True})
print(json.dumps({"status": "pass", "files": len(files),
                  "facts_sha256": sha((HERE / "facts.json").read_bytes()),
                  "review_sha256": sha((HERE / "review.md").read_bytes()),
                  "artifact_manifest_sha256": sha((HERE / "artifact_manifest.json").read_bytes())}))
