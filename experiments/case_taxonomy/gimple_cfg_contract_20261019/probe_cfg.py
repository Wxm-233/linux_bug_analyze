"""Reuse the reviewed N2.11 commands, relocating dumps and adding the CFG dump.

One attempt per profile in existing Ubuntu WSL. No source or build-tree writes.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "compiler_consumer_frontend_20261018"
OLD_PLAN_SHA = "fb174a23f1126e899099839d503af7148f62678e681a0e6b5ec4d9f8c07ce6af"
OLD_PROBE_SHA = "cc62b5b01b890164ebf1d7b84b4060dd5dba0b34ac97c853828bf8a8dbcf565e"
FUNCTION = "sched_core_cpu_starting"


def sha(raw): return hashlib.sha256(raw).hexdigest()


def require(value, message):
    if not value: raise ValueError(message)


def identity(path):
    p = Path(path)
    return {"path": str(p), "exists": p.is_file(), "sha256": sha(p.read_bytes()) if p.is_file() else None}


def previous():
    require(sha((OLD / "command_plan.json").read_bytes()) == OLD_PLAN_SHA, "old_plan_changed")
    require(sha((OLD / "probe_compiler.py").read_bytes()) == OLD_PROBE_SHA, "old_probe_changed")
    spec = importlib.util.spec_from_file_location("n211_probe_readonly", OLD / "probe_compiler.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return json.loads((OLD / "command_plan.json").read_bytes()), module


def plan():
    require(os.name == "posix", "existing_WSL_only")
    old, _ = previous()
    raw_root = (HERE / "raw").resolve()
    require(raw_root != HERE.resolve() and raw_root.is_relative_to(HERE.resolve()), "raw_root_escape")
    profiles = []
    for item in old["profiles"]:
        require([identity(x["path"]) for x in item["protected_before"]] == item["protected_before"], "old_guard_changed")
        require(identity(item["compiler"]["path"]) == item["compiler"], "compiler_changed")
        out = HERE / "raw" / item["profile"]
        require(out.resolve() != raw_root and out.resolve().is_relative_to(raw_root), "profile_root_escape")
        outputs = {key: str(out / Path(path).name) for key, path in item["outputs"].items()}
        outputs["cfg"] = str(out / "core.cfg.dump")
        replacements = {item["outputs"][key]: value for key, value in outputs.items() if key != "cfg"}
        argv = []
        changes = []
        for index, arg in enumerate(item["argv"]):
            replaced = replacements.get(arg, arg)
            for name in ("original", "gimple"):
                prefix = "-fdump-tree-" + name + "-lineno="
                if arg == prefix + item["outputs"][name]: replaced = prefix + outputs[name]
            argv.append(replaced)
            if replaced != arg: changes.append({"index": index, "old": arg, "new": replaced})
        argv.append("-fdump-tree-cfg-lineno=" + outputs["cfg"])
        require(len(changes) == 3 and len(argv) == len(item["argv"]) + 1, "unexpected_argv_change")
        require(all(Path(p).resolve().is_relative_to(out.resolve()) for p in outputs.values()), "output_escape")
        profiles.append({key: item[key] for key in ("profile", "arch", "revision", "source_i", "config", "compiler", "cwd", "protected_before")} | {
            "argv": argv, "relocations": changes, "output_directory": str(out), "outputs": outputs})
    return {"schema": "n213_cfg_probe_v1", "protocol_sha256": sha((HERE / "protocol_pre.json").read_bytes()),
            "probe_sha256": sha(Path(__file__).read_bytes()), "old_plan_sha256": OLD_PLAN_SHA,
            "old_probe_sha256": OLD_PROBE_SHA, "profiles": profiles, "timeout_seconds": 120,
            "secondary_gate": "primary exit0, six guards unchanged, all outputs and unique complete CFG record",
            "environment": {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C", "TMPDIR": "profile output directory"}}


def extract_cfg(raw, old_probe):
    text = raw.decode("utf-8")
    headers = list(re.finditer(r"(?m)^;; Function ([A-Za-z_]\w*) \(", text))
    hits = [i for i, m in enumerate(headers) if m.group(1) == FUNCTION]
    require(len(hits) == 1, "unique_target_CFG_record_required")
    i = hits[0]; start = headers[i].start(); end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
    fragment = text[start:end]
    body = old_probe.extract_function(fragment.encode())
    require(re.search(r"(?m)^;;\s*\d+ succs \{", fragment), "CFG_successor_metadata_missing")
    require(re.search(r"(?m)^\s*<bb \d+>", fragment), "CFG_basic_blocks_missing")
    bstart, bend = len(text[:start].encode()), len(text[:end].encode())
    return fragment, {"function": FUNCTION, "full_dump_sha256": sha(raw), "record_sha256": sha(fragment.encode()),
                      "record_start_byte": bstart, "record_end_byte_exclusive": bend,
                      "record_start_line": text.count("\n", 0, start) + 1,
                      "record_end_line": text.count("\n", 0, end - 1) + 1,
                      "body_start_byte_in_record": body["start_byte"], "body_end_byte_in_record": body["end_byte_exclusive"],
                      "body_sha256": body["sha256"], "normal_CFG_only": True, "runtime_reachability_proved": False}


def execute(approved, profile):
    raw_plan = (HERE / "command_plan.json").read_bytes()
    require(sha(raw_plan) == approved, "plan_SHA_mismatch")
    saved = json.loads(raw_plan); require(plan() == saved, "inputs_or_method_changed")
    item = next(x for x in saved["profiles"] if x["profile"] == profile)
    if profile == "old_x86":
        first = json.loads((HERE / "raw/old_s390/result.json").read_bytes())
        require(first["status"] == "CFG_record_available" and first["approved_plan_sha256"] == approved, "primary_gate_failed")
    out = Path(item["output_directory"])
    out.parent.mkdir(exist_ok=True); out.mkdir(exist_ok=False)
    (out / "attempt.json").write_text(json.dumps({"profile": profile, "approved_plan_sha256": approved, "reserved_invocations": 1}) + "\n")
    env = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C", "TMPDIR": str(out), "TMP": str(out), "TEMP": str(out)}
    result = {"profile": profile, "approved_plan_sha256": approved, "argv": item["argv"], "status": "compiler_failed", "compiler_exit_code": None}
    started = time.monotonic()
    try:
        process = subprocess.Popen(item["argv"], cwd=item["cwd"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    except OSError as exc:
        stdout, stderr = b"", str(exc).encode(); result["status"] = "launch_failed_no_retry"
    else:
        try:
            stdout, stderr = process.communicate(timeout=120); result["compiler_exit_code"] = process.returncode
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL); stdout, stderr = process.communicate(); result["status"] = "timeout_no_retry"
    result["elapsed_seconds"] = time.monotonic() - started
    (out / "stdout.txt").write_bytes(stdout); (out / "stderr.txt").write_bytes(stderr)
    result["protected_after"] = [identity(x["path"]) for x in item["protected_before"]]
    result["old_guarded_files_unchanged"] = result["protected_after"] == item["protected_before"]
    result["outputs"] = {key: identity(path) for key, path in item["outputs"].items()}
    if result["compiler_exit_code"] == 0 and result["old_guarded_files_unchanged"] and all(x["exists"] for x in result["outputs"].values()):
        try:
            _, helper = previous()
            fragment, binding = extract_cfg(Path(item["outputs"]["cfg"]).read_bytes(), helper)
            binding.update({key: item[key] for key in ("profile", "arch", "revision", "source_i", "config")})
            with (HERE / (profile + ".consumer.cfg.txt")).open("x", encoding="utf-8", newline="\n") as f: f.write(fragment)
            with (HERE / (profile + ".consumer_binding.json")).open("x") as f: json.dump(binding, f, indent=2); f.write("\n")
            result["binding"] = binding; result["status"] = "CFG_record_available"
        except (ValueError, UnicodeError) as exc:
            result.update(status="compiler_succeeded_CFG_insufficient", extraction_error=str(exc))
    with (out / "result.json").open("x") as f: json.dump(result, f, indent=2); f.write("\n")
    print(json.dumps({key: result[key] for key in ("profile", "status", "compiler_exit_code", "elapsed_seconds", "old_guarded_files_unchanged")}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--profile", choices=["old_s390", "old_x86"])
    parser.add_argument("--approved-plan-sha")
    args = parser.parse_args()
    if args.plan: print(json.dumps(plan(), indent=2))
    else:
        require(args.profile and args.approved_plan_sha, "explicit_profile_and_approved_plan_required")
        execute(args.approved_plan_sha, args.profile)


if __name__ == "__main__": main()
