"""Read exactly the two saved selections; no build/boot imports or entrypoints."""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
ROOT = STAGE.parents[2]
RUNTIME = ROOT / "experiments/case_taxonomy/s390_arch_contract_20261013/runtime"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ref(path):
    return str(path.relative_to(ROOT)).replace("\\", "/")


def main():
    assert (HERE / "protocol_pre.json").is_file()
    receipt = json.loads((STAGE / "selection_receipt.json").read_text())
    pool_sha = sha(STAGE / "example_pool.json")
    selected_sha = sha(STAGE / "selection.json")
    assert pool_sha == receipt["pool_sha256"] and selected_sha == receipt["selection_sha256"]
    pool = json.loads((STAGE / "example_pool.json").read_text())
    selection = json.loads((STAGE / "selection.json").read_text())
    selected = {name for pair in selection["pairs"] for name in (pair["left"], pair["right"])}
    assert selected == {"P01", "P03"} and len(selection["pairs"]) == 1
    profiles = {x["id"]: x for x in pool["profiles"]}
    provenance = json.loads((STAGE / "example_provenance.json").read_text())
    mappings = {x["id"]: x for x in provenance["profiles"]}
    parser_path = RUNTIME / "run_runtime.py"
    parsed_module = ast.parse(parser_path.read_text(encoding="utf-8"))
    nodes = [n for n in parsed_module.body if isinstance(n, ast.FunctionDef) and n.name == "analyse"]
    assert len(nodes) == 1
    # Compile precisely the existing self-contained parser function, unchanged;
    # never import the runner's build, instrument, prepare, boot or batch main.
    namespace = {"re": re}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(parser_path), "exec"), namespace)
    analyse = namespace["analyse"]
    rows = []
    reads = []
    for pid in sorted(selected):
        profile = profiles[pid]
        base = (ROOT / mappings[pid]["source_directory"]).resolve()
        assert base.parent == (RUNTIME / "profiles").resolve()
        assert base.name in {"old_s390", "old_x86"}
        paths = {name: base / name for name in ["kernel.config", "autoconf.h", "build.json", "boot.json",
                                               "qemu_boot.stdout.log", "qemu_boot.stderr.log"]}
        assert sha(paths["kernel.config"]) == profile["configuration"]["sha256"]
        assert sha(paths["autoconf.h"]) == profile["configuration"]["autoconf_sha256"]
        assert sha(paths["build.json"]) == profile["availability"]["build_record_sha256"]
        build = json.loads(paths["build.json"].read_text())
        boot = json.loads(paths["boot.json"].read_text())
        assert build["revision"] == profile["revision"]
        assert build["arch"] == ("x86" if profile["architecture"] == "x86_64" else profile["architecture"])
        assert build["profile"] == base.name and boot["profile"] == base.name
        assert boot["receipt"]["exit_code"] == 0 and boot["receipt"]["attempt"] == 1
        assert paths["qemu_boot.stderr.log"].read_bytes() == b""
        observed = analyse(build, paths["qemu_boot.stdout.log"])
        # Original EXPECTED_CONTRAST/status and old-specific expectation fields
        # are deliberately not the replay truth rule. Reproduce the parsed
        # archive and validate its neutral identity/sequence/config foundations.
        exact_archive = observed["events"] == boot["observations"]["events"]
        foundation = observed["foundation"]
        events = observed["events"]
        lock = [e for e in events if e.get("cpu") == 1 and e["phase"] == "lock_snapshot"]
        callback = [e for e in events if e.get("cpu") == 1 and e["phase"] == "cpuhp_before"]
        valid = exact_archive and all(foundation.values()) and len(lock) == len(callback) == 1
        core = lock[0] if len(lock) == 1 else None
        before = callback[0] if len(callback) == 1 else None
        relation = None if not valid else bool(core["self"] == 1)
        raw_lines = paths["qemu_boot.stdout.log"].read_text(errors="replace").splitlines()
        rows.append({"profile_id": pid, "revision": build["revision"], "architecture": profile["architecture"],
                     "status": "insufficient" if relation is None else ("local_relation_satisfied" if relation else "local_relation_violated"),
                     "relation": "target CPU belongs to its SMT mask at archived pre-IRQ content sample",
                     "relation_truth": relation, "archive_events_reproduced": exact_archive,
                     "parser_foundation": foundation,
                     "observation": None if core is None else {"cpu": core["cpu"], "current_cpu": core["current"],
                         "phase": core["phase"], "sequence": core["seq"], "source_log_line": core["line"],
                         "raw_line": raw_lines[core["line"] - 1], "mask": core["mask"], "self": core["self"],
                         "actual_lock_count": core["locks"], "online": core["online"],
                         "cpuhp_state": None if before is None else before["state"],
                         "cpuhp_sched_state": None if before is None else before["sched_state"]},
                     "binding": {"consumer": profile["consumer"], "configuration_sha256": sha(paths["kernel.config"]),
                                  "adapter": profile["availability"]["adapter"], "cpu_role": "secondary_cpu_1",
                                  "object_binding": "adapter role and target CPU; actual memory address not recorded",
                                  "exact_loop_read_proved": False, "global_first_read_proved": False,
                                  "interval_stability_proved": False},
                     "mode": observed["mode"],
                     "artifacts": [{"path": ref(path), "sha256": sha(path)} for path in paths.values()]})
        reads.extend(ref(path) for path in paths.values())
    assert sha(STAGE / "example_pool.json") == pool_sha and sha(STAGE / "selection.json") == selected_sha
    result = {"schema": "selected_contrast_replay_v1", "status": "known_case_replay_complete",
              "selection_identity": {"pool_sha256": pool_sha, "selection_sha256": selected_sha},
              "parser": {"path": ref(parser_path), "sha256": sha(parser_path), "function": "analyse",
                         "first_line": nodes[0].lineno, "last_line": nodes[0].end_lineno,
                         "execution_scope": "unchanged analyse function only; no runner main/build/boot executed"},
              "profiles": rows, "selected_pair_has_local_relation_difference":
                  None if any(x["relation_truth"] is None for x in rows) else rows[0]["relation_truth"] != rows[1]["relation_truth"],
              "opened_profile_artifacts": reads, "unselected_outcome_files_read": 0,
              "new_api_calls": 0, "new_builds": 0, "new_runs": 0, "new_cases": 0,
              "independent_selection_gain_evaluated": False,
              "limits": "Known case and manual source features; no original-result status used as contract truth; no exact content deadline/stability/SMT/hotplug guarantee"}
    save("selected_replay.json", result)
    print(json.dumps({"status": result["status"], "profiles": [{"id": row["profile_id"], "architecture": row["architecture"],
                      "relation": row["status"], "self": row["observation"]["self"] if row["observation"] else None,
                      "locks": row["observation"]["actual_lock_count"] if row["observation"] else None} for row in rows],
                      "local_relation_difference": result["selected_pair_has_local_relation_difference"]}))


if __name__ == "__main__":
    main()
