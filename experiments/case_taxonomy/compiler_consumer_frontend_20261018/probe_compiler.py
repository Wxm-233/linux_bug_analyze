"""Plan first; one approved existing-GCC assembly/dump probe per profile.

Run in the existing Ubuntu WSL with argument arrays. --plan emits JSON only;
the Windows caller saves command_plan.json. No compiler runs during planning.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ORIGINAL_C = "/root/.cache/linux-bug-analyze/s390-contract-20261013/old/linux/kernel/sched/core.c"
FUNCTION = "sched_core_cpu_starting"


def require(condition, reason):
    if not condition: raise ValueError(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(path):
    path = Path(path)
    return {"path": str(path), "exists": path.is_file(), "sha256": digest(path.read_bytes()) if path.is_file() else None}


def under(path, parent):
    return Path(path).resolve().is_relative_to(Path(parent).resolve())


def saved_argv(raw, compiler):
    text = raw.decode("utf-8")
    lines = [line for line in text.splitlines() if line.startswith(("cmd_", "savedcmd_"))]
    require(len(lines) == 1 and re.match(r"(?:savedcmd|cmd)_kernel/sched/core\.o\s*:=", lines[0]), "single_saved_core_command_required")
    command = lines[0].split(":=", 1)[1].strip()
    require(not any(x in command for x in ["\n", "\r", "`", "$(", "${", ";", "&&", "||", "|", ">", "<"]), "shell_or_multicommand_syntax_rejected")
    args = shlex.split(command, posix=True)
    require(args and Path(args[0]).name == Path(compiler).name, "saved_compiler_mismatch")
    require([x for x in args if x.endswith(".c")] == [ORIGINAL_C] and args.count("-c") == 1 and args.count("-o") == 1,
            "single_known_core_input_and_compile_required")
    return command, args


def derive(args, compiler, source_i, output_dir):
    output_dir = Path(output_dir).resolve()
    outputs = {"assembly": str(output_dir / "core.s"), "original": str(output_dir / "core.original.dump"),
               "gimple": str(output_dir / "core.gimple.dump")}
    result, changes = [compiler], [{"index": 0, "operation": "replace", "old": [args[0]], "new": [compiler]}]
    paired_reads = {"-isystem", "-I", "-include", "-iquote", "-idirafter"}
    dep_pairs = {"-MF", "-MT", "-MQ", "-MJ", "-dependency-file"}
    dep_single = {"-M", "-MM", "-MD", "-MMD", "-MP", "-MG"}
    danger = ("-fplugin", "-fprofile", "-fauto-profile", "-ftest-coverage", "-fstack-usage", "-fcallgraph-info",
              "-fdump", "-fopt-info", "-fsave-optimization-record", "-fdiagnostics", "-fcompare-debug", "-ftime-report",
              "-save-temps", "--coverage", "-specs", "--specs", "-wrapper", "-B", "-Wl", "-X", "@")
    old_outputs, index = [], 1
    while index < len(args):
        arg = args[index]
        if arg == ORIGINAL_C:
            replacement = ["-x", "cpp-output", source_i]
        elif arg == "-c": replacement = ["-S"]
        elif arg == "-o":
            require(index + 1 < len(args), "output_operand_missing")
            old_outputs.append(args[index + 1]); replacement = ["-o", outputs["assembly"]]
            changes.append({"index": index, "operation": "replace", "old": args[index:index + 2], "new": replacement})
            result += replacement; index += 2; continue
        elif arg.startswith("-Wp,"):
            pieces = arg.split(",")
            require(len(pieces) == 3 and pieces[1] in {"-MMD", "-MD"} and pieces[2], "unsupported_preprocessor_forwarding")
            old_outputs.append(pieces[2]); replacement = []
        elif arg in dep_single: replacement = []
        elif arg in dep_pairs:
            require(index + 1 < len(args), "dependency_operand_missing")
            if arg in {"-MF", "-MJ", "-dependency-file"}: old_outputs.append(args[index + 1])
            changes.append({"index": index, "operation": "remove", "old": args[index:index + 2], "new": []})
            index += 2; continue
        elif arg.startswith(("-MF", "-MJ")):
            old_outputs.append(arg[3:]); replacement = []
        else:
            require(not arg.startswith(danger), "potential_extra_output_or_execution_flag:" + arg)
            if arg in paired_reads:
                require(index + 1 < len(args), "read_operand_missing")
                result += args[index:index + 2]; index += 2; continue
            require(arg == "-pg" or arg.startswith(("-f", "-m", "-W", "-D", "-O", "-std=", "-I", "-nostdinc", "-pipe")), "unclassified_argument:" + arg)
            require(not arg.startswith("-Wa,") or (arg.startswith("-Wa,-I") and arg.count(",") == 1), "unsafe_assembler_forwarding")
            result.append(arg); index += 1; continue
        changes.append({"index": index, "operation": "remove" if not replacement else "replace", "old": [arg], "new": replacement})
        result += replacement; index += 1
    added = ["-fdump-tree-original-lineno=" + outputs["original"], "-fdump-tree-gimple-lineno=" + outputs["gimple"]]
    changes.append({"index": len(args), "operation": "append", "old": [], "new": added})
    result += added
    require(result.count("-S") == 1 and result.count("-x") == 1 and result[result.index("-x") + 1] == "cpp-output", "derived_mode_invalid")
    require(all(under(path, output_dir) and Path(path).is_absolute() for path in outputs.values()), "derived_output_escape")
    return result, changes, outputs, old_outputs


def make_plan(admit_existing=False):
    require(os.name == "posix", "run_planning_in_existing_WSL")
    protocol_path = HERE / "protocol_pre.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    profiles = []
    for item in protocol["inputs"]:
        require(item["profile"] in {"old_s390", "old_x86"}, "unregistered_profile")
        for key in ["source_i", "config"]:
            require(identity(item[key]["path"])["sha256"] == item[key]["sha256"], key + "_identity_mismatch")
        manifest_path = ROOT / item["prior_manifest"]
        require(digest(manifest_path.read_bytes()) == item["prior_manifest_sha256"], "prior_manifest_changed")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        require(manifest["profile"] == item["profile"] and manifest["arch"] == item["arch"] and manifest["revision"] == item["revision"], "prior_profile_identity_mismatch")
        compiler = Path(item["compiler"])
        require(compiler.is_file() and os.access(compiler, os.X_OK), "known_compiler_unavailable")
        cmd_raw = Path(item["saved_command_path"]).read_bytes()
        command, original = saved_argv(cmd_raw, item["compiler"])
        output_dir = HERE / "raw" / item["profile"]
        require(under(HERE / "raw", HERE) and (HERE / "raw").resolve() != HERE
                and under(output_dir, HERE / "raw") and (admit_existing or not output_dir.exists()), "profile_output_already_exists_or_escapes")
        argv, changes, outputs, old_outputs = derive(original, item["compiler"], item["source_i"]["path"], output_dir)
        cwd = Path(item["source_i"]["path"]).parents[2]
        guard_paths = [item["source_i"]["path"], item["config"]["path"], item["saved_command_path"], ORIGINAL_C]
        guard_paths += [str((cwd / name).resolve()) for name in old_outputs]
        profiles.append({"profile": item["profile"], "arch": item["arch"], "revision": item["revision"],
                         "prior_manifest_sha256": item["prior_manifest_sha256"], "source_i": item["source_i"], "config": item["config"],
                         "saved_command_path": item["saved_command_path"], "saved_command_file_sha256": digest(cmd_raw),
                         "saved_command_text": command, "saved_command_text_sha256": digest(command.encode()),
                         "compiler": identity(compiler), "compiler_realpath": str(compiler.resolve()),
                         "original_argv": original, "argv": argv, "argument_changes": changes,
                         "cwd": str(cwd), "output_directory": str(output_dir), "outputs": outputs,
                         "protected_before": [identity(path) for path in dict.fromkeys(guard_paths)]})
    return {"schema": "n211_compiler_command_plan_v1", "protocol_sha256": digest(protocol_path.read_bytes()),
            "probe_script_sha256": digest(Path(__file__).read_bytes()), "stage_path": str(HERE), "profiles": profiles,
            "environment": {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C", "TMPDIR": "per-profile raw directory", "TMP": "same", "TEMP": "same"},
            "profile_order": ["old_s390", "old_x86"], "secondary_gate": "primary exit0 + all planned files present + unique complete target GIMPLE section",
            "timeout_seconds": 120, "compiler_invocations_during_plan": 0}


def extract_function(raw):
    text = raw.decode("utf-8")
    pattern = re.compile(r"(?m)^(?:\[[^\n\]]+\]\s*)?(?:[A-Za-z_]\w*(?:\s+|\s*\*\s*))+" + FUNCTION + r"\s*\([^;\n]*\)\s*$")
    matches = list(pattern.finditer(text))
    require(len(matches) == 1, "target_declaration_not_unique")
    start, position = matches[0].start(), matches[0].end()
    opening = text.find("{", position)
    require(opening >= 0 and "\n\n" not in text[position:opening] and ";" not in text[position:opening], "target_opening_boundary_unsupported")
    depth, index, end = 0, opening, None
    while index < len(text):
        if text.startswith("/*", index):
            stop = text.find("*/", index + 2); require(stop >= 0, "dump_comment_unterminated"); index = stop + 2; continue
        if text.startswith("//", index):
            stop = text.find("\n", index + 2); index = len(text) if stop < 0 else stop + 1; continue
        if text[index] in {'"', "'"}:
            quote = text[index]; index += 1
            while index < len(text):
                if text[index] == "\\": index += 2
                elif text[index] == quote: index += 1; break
                else: index += 1
            else: raise ValueError("dump_quote_unterminated")
            continue
        if text[index] == "{": depth += 1
        if text[index] == "}":
            depth -= 1
            if depth == 0: end = index + 1; break
        index += 1
    require(end is not None, "target_closing_boundary_missing")
    if text[end:end + 1] == "\n": end += 1
    byte_start, byte_end = len(text[:start].encode()), len(text[:end].encode())
    fragment = raw[byte_start:byte_end]
    inventory = [{"line": text.count("\n", 0, start) + number, "text": line,
                  "branch_or_goto_candidate": bool(re.search(r"\b(?:if|goto|switch)\b", line)),
                  "field_names_lexical_only": re.findall(r"(?:->|\.)\s*([A-Za-z_]\w*)", line)}
                 for number, line in enumerate(fragment.decode("utf-8").splitlines(), 1)
                 if re.search(r"\b(?:if|goto|switch)\b|->|\.", line)]
    return {"status": "unique_complete_target_section", "function": FUNCTION, "dump_sha256": digest(raw),
            "start_byte": byte_start, "end_byte_exclusive": byte_end, "start_line": text.count("\n", 0, start) + 1,
            "end_line": text.count("\n", 0, end - 1) + 1, "sha256": digest(fragment), "text": fragment.decode("utf-8"),
            "tentative_line_inventory": inventory, "def_use_or_obligation_proved": False}


def execute(plan_path, approved_sha, profile):
    require(os.name == "posix", "execute_only_in_existing_WSL")
    raw = plan_path.read_bytes(); require(digest(raw) == approved_sha, "unapproved_plan_bytes")
    plan = json.loads(raw)
    require(plan == make_plan(admit_existing=True), "planned_method_or_inputs_changed")
    item = next(x for x in plan["profiles"] if x["profile"] == profile)
    if profile == "old_x86":
        prior = json.loads((HERE / "raw/old_s390/result.json").read_text())
        require(prior.get("approved_plan_sha256") == approved_sha and prior.get("status") == "frontend_and_target_section_available", "primary_gate_not_satisfied")
    out = Path(item["output_directory"])
    out.parent.mkdir(exist_ok=True); out.mkdir(exist_ok=False)
    with (out / "attempt.json").open("x") as stream: json.dump({"profile": profile, "approved_plan_sha256": approved_sha, "invocations_reserved": 1}, stream)
    env = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C", "TMPDIR": str(out), "TMP": str(out), "TEMP": str(out)}
    record = {"profile": profile, "approved_plan_sha256": approved_sha, "argv": item["argv"], "cwd": item["cwd"], "status": "compiler_failed", "compiler_exit_code": None}
    started = time.monotonic()
    try:
        process = subprocess.Popen(item["argv"], cwd=item["cwd"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    except OSError as exc:
        stdout, stderr = b"", str(exc).encode("utf-8")
        record["status"] = "compiler_launch_failed_no_retry"
    else:
        try:
            stdout, stderr = process.communicate(timeout=120)
            record["compiler_exit_code"] = process.returncode
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate(); record["status"] = "timeout_no_retry"
    record["elapsed_seconds"] = time.monotonic() - started
    (out / "stdout.txt").write_bytes(stdout); (out / "stderr.txt").write_bytes(stderr)
    record["protected_after"] = [identity(x["path"]) for x in item["protected_before"]]
    record["old_guarded_files_unchanged"] = record["protected_after"] == item["protected_before"]
    record["planned_output_inventory"] = {key: identity(path) for key, path in item["outputs"].items()}
    if record["compiler_exit_code"] == 0 and record["old_guarded_files_unchanged"] and all(x["exists"] for x in record["planned_output_inventory"].values()):
        try:
            extracted = extract_function(Path(item["outputs"]["gimple"]).read_bytes())
            (out / "consumer.gimple.txt").write_bytes(extracted.pop("text").encode())
            (out / "consumer.extract.json").write_text(json.dumps(extracted, indent=2) + "\n")
            record["extraction"] = extracted; record["status"] = "frontend_and_target_section_available"
        except (ValueError, UnicodeError) as exc:
            record.update(status="compiler_succeeded_target_section_insufficient", extraction_error=str(exc))
    record["all_files_under_profile_raw"] = [{"path": str(p), "sha256": digest(p.read_bytes())} for p in out.rglob("*") if p.is_file()]
    with (out / "result.json").open("x") as stream: json.dump(record, stream, indent=2); stream.write("\n")
    print(json.dumps({"profile": profile, "status": record["status"], "compiler_exit_code": record["compiler_exit_code"]}))


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--plan-file", type=Path, default=HERE / "command_plan.json")
    parser.add_argument("--approved-plan-sha")
    parser.add_argument("--profile", choices=["old_s390", "old_x86"])
    args = parser.parse_args()
    if args.plan:
        print(json.dumps(make_plan(), ensure_ascii=False, indent=2))
    else:
        require(args.approved_plan_sha and args.profile, "explicit_approved_plan_and_profile_required")
        execute(args.plan_file, args.approved_plan_sha, args.profile)


if __name__ == "__main__": main()
