"""Read only metadata/protocol/lock receipts; never query Git or load new sources."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
RULES = STAGE.parent


def read(name):
    return json.loads((STAGE / name).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


failures = []
checks = {}


def require(condition, reason):
    if not condition:
        failures.append(reason)


code = read("audit_pre/code_review.json")
start = len(failures)
for name, digest in code["bound_code_sha256"].items():
    require(sha(STAGE / name) == digest, "reviewed code changed " + name)
checks["reviewed_protocol_runner_gate_code_unchanged"] = len(failures) == start

start = len(failures)
for name in ("freeze_pre.json", "execution_gate_lock_pre.json"):
    lock = read(name)
    for item in lock["files"]:
        path = (STAGE / item["path"]).resolve()
        require(path.is_relative_to(RULES) and sha(path) == item["sha256"], "lock SHA " + item["path"])
checks["freeze_and_supplemental_gate_hashes_bound"] = len(failures) == start

pool = read("pool_metadata.json")
selection = read("selection.json")
freeze = read("freeze_pre.json")
commands = read("commands_prepare_complete.json")
start = len(failures)
require(set(pool["pools"]) == {"fs", "drivers"}, "metadata channels")
require(all(len(items) <= 32 for items in pool["pools"].values()), "metadata per-channel bound")
require(pool["count"] == sum(len(items) for items in pool["pools"].values()) <= 64, "metadata total bound")
require(0 <= len(selection["selected"]) <= 2 and selection["max_inputs"] == 2, "selection bound")
require(freeze["selected_count"] == len(selection["selected"]), "freeze selection count")
require(freeze["source_or_patch_read_before_seal"] is False and selection["no_source_or_patch_read"] is True,
        "metadata-only phase declaration")
for item in selection["selected"]:
    matches = [e for e in pool["pools"][item["channel"]] if e["commit"] == item["commit"]]
    require(len(matches) == 1, "selection identity in bounded pool")
    if matches:
        entry = matches[0]
        require(entry["selection_status"] == "selected" and not entry["prior_record_matches"], "prior record exclusion")
        require(item["parent"] == entry["parents"][0], "selected predecessor identity")
        require(1 <= len(entry["all_c_files"]) <= 3 and item["source_file"] == entry["channel_c_files"][0],
                "fixed channel first C file")
    require(item["preassigned_positive_label"] is False, "positive truth not preassigned")
    require(item["role"] == {"fs": "consumer", "drivers": "producer"}[item["channel"]], "fixed channel role")
checks["bounded_fixed_metadata_selection_without_positive_labels"] = len(failures) == start

start = len(failures)
for command in commands:
    argv = command["argv"]
    safe = False
    if argv[0] == "git":
        safe = (argv[1:] == ["--version"] or argv[1:] == ["rev-parse", "HEAD"] or
                (argv[1] == "log" and "--no-merges" in argv and "--format=%H%x09%P%x09%cI%x09%s" in argv and
                 "-n" in argv and argv[argv.index("-n") + 1] == "32") or
                (argv[1] == "diff-tree" and "--name-only" in argv and "--no-commit-id" in argv))
    elif argv[0] in ("rg", "grep"):
        safe = argv[1:] == ["--version"] or ("-l" in argv and "-F" in argv and
                ("--exclude-dir=" + STAGE.name in argv or "--glob=!**/" + STAGE.name + "/**" in argv))
    elif argv[0] == "python3":
        safe = argv[1:] == ["--version"]
    require(safe and not any(x in argv for x in ("--patch", "-p")), "unexpected prepare command " + repr(argv))
    require(command["returncode"] in (0, 1), "prepare command failure")
    for stream in ("stdout", "stderr"):
        require(sha(STAGE / command[stream]) == command[stream + "_sha256"], "prepare stream SHA")
checks["saved_prepare_commands_metadata_only_and_stream_hashes_bound"] = len(failures) == start

start = len(failures)
for name in ("parents_started.json", "parents_lock.json", "unseal_started.json", "unseal_authorization.json"):
    require(not (STAGE / name).exists(), "review no longer precedes parents/unseal " + name)
checks["binding_completed_before_parent_or_unseal_execution"] = len(failures) == start

names = list(code["bound_code_sha256"]) + ["audit_pre/code_review.json", "audit_pre/pending_findings.md",
        "audit_pre/bind_pre.py", "freeze_pre.json", "execution_gate_lock_pre.json", "selection.json",
        "pool_metadata.json", "commands_prepare_complete.json"]
result = {"date": "2026-10-03", "status": "pass" if not failures else "blocked",
          "checks": checks, "blockers_found": failures, "bound_inputs_sha256": {n: sha(STAGE / n) for n in names},
          "scope": "read saved protocol/code/metadata/locks and hash command streams; no Git, rules, new parent source or patch",
          "allowed_execution": "parents/unseal only through sealed execution_gate_pre.py; empty selection/failure stops",
          "selected_count": len(selection["selected"]), "metadata_count": pool["count"],
          "limits": code["limits"]}
(HERE / "final_review.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": result["status"], "checks": checks, "blockers_found": failures,
                  "metadata_count": pool["count"], "selected_count": len(selection["selected"])}))
