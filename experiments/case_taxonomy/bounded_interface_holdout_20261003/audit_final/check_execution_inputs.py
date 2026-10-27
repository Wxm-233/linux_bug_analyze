"""Saved execution order and byte identity only; never execute rules or Git."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
RULES = STAGE.parent


def read(name):
    return json.loads((STAGE / name).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


checks, failures = {}, []


def require(condition, reason):
    if not condition:
        failures.append(reason)


def time(value):
    return datetime.fromisoformat(value)


start = len(failures)
for name, digest in (("audit_pre/final_review.json", "5056b41a19200643224db5bbad4c1aeebafc7857ce52b4036829ba30fba5147a"),
                     ("audit_pre/final_review.md", "bd3914acd2f0d811fd80ec01828bd6b76fd570a0c684c0e2fdb14630dbdfe579")):
    require(sha(STAGE / name) == digest, "pre audit changed " + name)
for name, digest in read("audit_pre/final_review.json")["bound_inputs_sha256"].items():
    require(sha(STAGE / name) == digest, "pre-bound input changed " + name)
for name in ("freeze_pre.json", "execution_gate_lock_pre.json", "parents_lock.json"):
    for item in read(name)["files"]:
        path = (STAGE / item["path"]).resolve()
        require(path.is_relative_to(RULES) and sha(path) == item["sha256"], "execution lock SHA " + item["path"])
checks["pre_audit_freeze_gate_and_parent_locks_unchanged"] = len(failures) == start

selection = read("selection.json")["selected"]
parents = read("commands_parents.json")
unseal = read("commands_unseal.json")
parent_lock = read("parents_lock.json")
auth = read("unseal_authorization.json")
start = len(failures)
require(len(parents) == len(selection) == 2, "exactly two selected parent CLI calls")
fixed = [c for c in unseal if c["argv"][0] == "python3"]
require(len(fixed) == len(selection), "exactly two fixed CLI calls")
for item in selection:
    script = {"consumer": "endian_consumer_single_revision.py", "producer": "endian_producer_single_revision.py"}[item["role"]]
    for phase, commands, revision in (("parent", parents, item["parent"]), ("fixed", fixed, item["commit"])):
        matches = [c for c in commands if c["argv"][2].endswith("/" + script)]
        require(len(matches) == 1, "unique original CLI " + item["role"] + " " + phase)
        if matches:
            command = matches[0]
            argv = command["argv"]
            require(command["returncode"] == 0 and argv[:2] == ["python3", "-B"], "successful original CLI")
            require(argv[argv.index("--revision") + 1] == revision and
                    argv[argv.index("--source") + 1] == item["source_file"], "fixed source/revision identity")
    summary = [x for x in parent_lock["summaries"] if x["role"] == item["role"]][0]
    require(summary["returncode"] == 0 and sha(STAGE / summary["raw_path"]) == summary["raw_sha256"], "parent raw seal identity")
require(parent_lock["patch_unsealed"] is False and auth["allowed"] is True and
        auth["all_parent_returncodes_zero"] is True and auth["all_raw_identity_and_hash_checked"] is True,
        "successful parent gate authorization")
require(auth["parent_lock_sha256"] == sha(STAGE / "parents_lock.json"), "authorization lock binding")
checks["one_original_cli_per_role_revision_same_fixed_source_successful"] = len(failures) == start

start = len(failures)
parent_start = time(read("parents_started.json")["started_at_utc"])
parent_seal = time(parent_lock["sealed_at_utc"])
auth_time = time(auth["authorized_at_utc"])
unseal_start = time(read("unseal_started.json")["started_at_utc"])
require(time(read("freeze_pre.json")["sealed_at_utc"]) <= time(read("execution_gate_lock_pre.json")["sealed_at_utc"]) < parent_start,
        "pre-freeze/gate before parent")
require(parent_start <= min(time(c["started_at_utc"]) for c in parents) and
        max(time(c["completed_at_utc"]) for c in parents) <= parent_seal < auth_time <= unseal_start,
        "parent output lock before authorization/unseal")
require(unseal_start <= min(time(c["started_at_utc"]) for c in unseal), "no patch before gate unseal start")
require(read("parents_started.json")["no_retry"] is True and read("unseal_started.json")["no_retry"] is True,
        "one-shot markers retained")
for phase in ("parents", "unseal"):
    record = read(f"gate_{phase}_command.json")
    require(record["returncode"] == 0 and record["argv"][-1] == phase, "successful gate child phase")
checks["gate_markers_parent_lock_and_patch_unseal_chronology"] = len(failures) == start

start = len(failures)
for commands in (parents, unseal, [read("gate_parents_command.json"), read("gate_unseal_command.json")]):
    for command in commands:
        for stream in ("stdout", "stderr"):
            require(sha(STAGE / command[stream]) == command[stream + "_sha256"], "execution command stream SHA")
checks["execution_stdout_stderr_hashes_bound"] = len(failures) == start

names = ["audit_pre/final_review.json", "audit_pre/final_review.md", "freeze_pre.json", "selection.json",
         "execution_gate_lock_pre.json", "parents_started.json", "parents_lock.json", "commands_parents.json",
         "gate_parents_command.json", "unseal_authorization.json", "unseal_started.json", "commands_unseal.json",
         "gate_unseal_command.json", "unseal_manifest.json", "audit_final/check_execution_inputs.py"]
result = {"status": "pass" if not failures else "blocked", "checks": checks, "blockers_found": failures,
          "final_inputs_sha256": {name: sha(STAGE / name) for name in names},
          "scope": "saved execution metadata and SHA only; no new source or patch content read, no Git/rules/compiler/model calls"}
(HERE / "execution_review.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": result["status"], "checks": checks, "blockers_found": failures}))
