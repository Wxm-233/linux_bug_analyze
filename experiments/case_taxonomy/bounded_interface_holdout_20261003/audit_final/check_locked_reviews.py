"""Saved-byte/quote audit only. No subprocess, Git, rules, compiler or model."""
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent


def read(name):
    return json.loads((STAGE / name).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


checks, failures, counts = {}, [], {}


def require(condition, reason):
    if not condition:
        failures.append(reason)


start = len(failures)
for name, expected in {
    "consumer/manual_review/review.json": "156ba94413980a68e649e6061688e183c5379efec0a7624076a12e73f72531c9",
    "consumer/manual_review/artifact_manifest.json": "ede025c8fbb7fee66b245968ecf1fdec01c21f9e0da02d7dc2ebee4e478256a9",
    "producer/manual_review/review.json": "ad0e4f4b4eb56205b8e6e4b5cbd697069bf79ed3167f7676790f707813c10294",
    "producer/manual_review/locked_manifest.json": "a928898701c0846783f51b26949a0589bb8527a34817f06a6bb00fd0da225ddc",
}.items():
    require(sha(STAGE / name) == expected, "leaf locked SHA " + name)
for role, filename in (("consumer", "artifact_manifest.json"), ("producer", "locked_manifest.json")):
    manifest = read(f"{role}/manual_review/{filename}")
    for item in manifest["files"]:
        relative = item["path"]
        path = STAGE / relative if relative.startswith(role + "/") else STAGE / role / "manual_review" / relative
        require(sha(path) == item["sha256"], "leaf artifact SHA " + str(path))
        if "bytes" in item:
            require(path.stat().st_size == item["bytes"], "leaf artifact size " + str(path))
    counts[role + "_manifest_members"] = len(manifest["files"])
checks["both_leaf_locks_and_manifest_members_match"] = len(failures) == start

sources = read("source_manifest.json")
start = len(failures)
for role in ("consumer", "producer"):
    extra = read(f"{role}/manual_review/source_manifest_extra.json")
    per_label = Counter(item["label"] for item in extra)
    require(all(count <= 4 for count in per_label.values()), role + " extra source bound")
    sources += extra
    counts[role + "_extra_sources"] = len(extra)
for item in sources:
    path = STAGE / item["saved_path"]
    raw = path.read_bytes()
    require(sha(path) == item["sha256"] and len(raw) == item["bytes"], "source SHA/size " + item["saved_path"])
    require(blob(raw) == item["blob_sha1"], "source Git blob " + item["saved_path"])
checks["all_saved_sources_sha_blob_and_extra_bounds_match"] = len(failures) == start
counts["source_records"] = len(sources)

start = len(failures)
for role in ("consumer", "producer"):
    review = read(f"{role}/manual_review/review.json")
    quotes = [q for q in nodes(review["quotes"]) if all(k in q for k in ("start_line", "end_line", "text", "saved_path"))]
    counts[role + "_quotes"] = len(quotes)
    for quote in quotes:
        path = STAGE / quote["saved_path"]
        lines = path.read_text(encoding="utf-8").splitlines()
        a, z = quote["start_line"], quote["end_line"]
        require(1 <= a <= z <= len(lines) and "\n".join(lines[a-1:z]) == quote["text"], "quote range/text " + quote["saved_path"])
        require(sha(path) == quote["sha256"] and blob(path.read_bytes()) == quote["blob_sha1"], "quote SHA/blob")
        matches = [s for s in sources if s["saved_path"] == quote["saved_path"]]
        require(len(matches) == 1 and matches[0]["revision"] == quote["revision"] and
                matches[0]["source_path"] == quote["source_path"], "quote source identity")
checks["all_84_quote_text_revision_path_hash_bindings_match"] = len(failures) == start

start = len(failures)
for role in ("consumer", "producer"):
    for command in read(f"{role}/manual_review/commands_extra.json"):
        for stream in ("stdout", "stderr"):
            relative = command[stream]
            path = STAGE / relative if relative.startswith(role + "/") else STAGE / role / "manual_review" / relative
            require(sha(path) == command[stream + "_sha256"], "extra command stream SHA")
    for label in ("parent", "fixed"):
        raw = read(f"{role}/raw/{label}.json")
        for item in raw["files_read"]:
            matches = [s for s in sources if s["role"] == role and s["label"] == label and s["source_path"] == item["path"]]
            require(len(matches) == 1 and matches[0]["sha256"] == item["sha256"], "CLI source binding " + item["path"])
consumer = read("consumer/manual_review/review.json")
producer = read("producer/manual_review/review.json")
for label in ("parent", "fixed"):
    raw = read(f"consumer/raw/{label}.json")
    require(raw["counts"] == consumer["machine_result"]["counts_each"], "SMB counts summary")
    require(sha(STAGE / consumer["machine_result"][label + "_raw"]) == consumer["machine_result"][label + "_raw_sha256"], "SMB raw SHA")
    raw = read(f"producer/raw/{label}.json")
    summary = producer["raw_outputs"][label]
    require(raw["counts"] == summary["counts"] and raw["findings"] == summary["findings"] and
            sha(STAGE / summary["path"]) == summary["sha256"], "ath12k raw summary identity")
checks["extra_command_hashes_and_original_cli_source_summary_bindings_match"] = len(failures) == start

result = {"status": "pass" if not failures else "blocked", "checks": checks,
          "blockers_found": failures, "counts": counts,
          "scope": "only locked current-stage saved bytes and quotes; no earlier-stage recursion or executable replay"}
(HERE / "locked_review_checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
