"""Independent human-authored finite ordinary-C behavior oracle.

No Linux source, extractor, extracted IR, or model result is imported.  The
functions intentionally resemble a known search/update/check control pattern;
they are synthetic development inputs, not new defects or a blind holdout.
"""
from __future__ import annotations

import gzip
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "challenge_sources"
BUILD = ROOT / "build"
COMPILER = Path("C:/msys64/ucrt64/bin/gcc.exe")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def gzip_rows(path: Path, rows: list[dict]) -> None:
    # Fixed mtime makes exact records reproducible without altering the inputs.
    content = "".join(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n" for row in rows)
    with path.open("wb") as stream:
        with gzip.GzipFile(filename="", fileobj=stream, mode="wb", mtime=0) as compressed:
            compressed.write(content.encode("utf-8"))


def ordinary_source(name: str, bound: int, variant: str = "standard", alpha: bool = False) -> str:
    names = ("focus", "actors", "backref", "slot", "chosen", "inconsistent", "actor", "span") if alpha else ("target", "members", "owners", "pos", "witness", "mismatch", "member", "limit")
    target, members, owners, pos, witness, bad, member, limit = names
    parameters = [target, "m0", "m1", "m2", "r0", "r1", "r2"]
    guard = f"{member} != {target}" if variant == "update_others" else f"{member} == {target}"
    update = f"    if ({guard})\n      {owners}[{member}] = {witness};\n"
    check = f"    if ({owners}[{member}] != {witness})\n      {bad} = 1;\n"
    phase = check + update if variant == "check_first" else update + check
    declaration = f"const int {limit} = {bound};"
    if variant == "mutable_bound":
        declaration = f"int {limit} = {bound};"
    if variant == "while_search":
        search = f"""  {pos} = 0;
  while ({pos} < {limit}) {{
    int {member} = {members}[{pos}];
    {pos}++;
    if ({member} == {target})
      continue;
    if ({owners}[{member}] == {member}) {{
      {witness} = {member};
      break;
    }}
  }}
"""
    else:
        mutation = f"    if ({pos} == 0)\n      {limit} = 2;\n" if variant == "mutable_bound" else ""
        search = f"""  for ({pos} = 0; {pos} < {limit}; {pos}++) {{
    int {member} = {members}[{pos}];
{mutation}    if ({member} == {target})
      continue;
    if ({owners}[{member}] == {member}) {{
      {witness} = {member};
      break;
    }}
  }}
"""
    return f"""/* Artificial ordinary-C development input; not Linux source or a defect. */
int {name}({', '.join('int ' + p for p in parameters)})
{{
  int {members}[3] = {{m0, m1, m2}};
  int {owners}[3] = {{r0, r1, r2}};
  {declaration}
  int {witness} = -1;
  int {bad} = 0;
  int {pos};

  if ({limit} == 1)
    return 10;
{search}  if ({witness} < 0)
    return 20;
  for ({pos} = 0; {pos} < {limit}; {pos}++) {{
    int {member} = {members}[{pos}];
{phase}  }}
  if ({bad})
    return 30;
  return 0;
}}
"""


def sequential_reference(members: tuple[int, ...], target: int, initial: tuple[int, ...], variant: str) -> dict:
    # Direct operational reference: follow each statement/early exit in order.
    # It never calls an extractor or evaluates an extracted requirement.
    owners = list(initial)
    trace: list[dict] = []
    if len(members) == 1:
        return {"return": 10, "phase": "singleton_shortcut", "witness": None, "final_state": owners, "failed_members": [], "trace": trace}
    witness = None
    for member in members:
        if member == target:
            trace.append({"phase": "search", "member": member, "action": "skip_target"})
            continue
        if owners[member] == member:
            witness = member
            trace.append({"phase": "search", "member": member, "action": "choose_and_break"})
            break
        trace.append({"phase": "search", "member": member, "action": "reject_nonself_relation"})
    if witness is None:
        return {"return": 20, "phase": "no_witness_exit", "witness": None, "final_state": owners, "failed_members": [], "trace": trace}
    failures = []
    for member in members:
        update = member != target if variant == "update_others" else member == target
        if variant == "check_first":
            if owners[member] != witness:
                failures.append(member)
            trace.append({"phase": "check", "member": member, "value": owners[member]})
            if update:
                owners[member] = witness
                trace.append({"phase": "update", "member": member, "value": witness})
        else:
            if update:
                owners[member] = witness
                trace.append({"phase": "update", "member": member, "value": witness})
            if owners[member] != witness:
                failures.append(member)
            trace.append({"phase": "check", "member": member, "value": owners[member]})
    return {"return": 30 if failures else 0, "phase": "post_update_mismatch" if failures else "post_update_checks_pass", "witness": witness, "final_state": owners, "failed_members": failures, "trace": trace}


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    SOURCE.mkdir(exist_ok=True)
    BUILD.mkdir(exist_ok=True)
    if (ROOT / "freeze_manifest.json").exists():
        raise SystemExit("Oracle already sealed; do not overwrite or regenerate in-place.")
    specs = []
    for n in range(4):
        specs.append({"id": f"C{n}", "name": f"select_relation_{n}", "bound": n, "variant": "standard", "alpha": False, "eligibility": "supported_scope"})
    specs += [
        {"id": "A3", "name": "bind_actor_group", "bound": 3, "variant": "standard", "alpha": True, "eligibility": "supported_scope"},
        {"id": "V3", "name": "revise_other_relations", "bound": 3, "variant": "update_others", "alpha": False, "eligibility": "supported_scope"},
        {"id": "P3", "name": "inspect_before_revision", "bound": 3, "variant": "check_first", "alpha": False, "eligibility": "supported_scope"},
        {"id": "U1", "name": "moving_search_limit", "bound": 3, "variant": "mutable_bound", "alpha": False, "eligibility": "must_remain_insufficient", "reason": "Loop bound is written in the search body, outside immutable-bound protocol."},
        {"id": "U2", "name": "noncanonical_search", "bound": 3, "variant": "while_search", "alpha": False, "eligibility": "must_remain_insufficient", "reason": "Search uses while, outside registered canonical-for frontend scope."},
    ]
    for spec in specs:
        path = SOURCE / (spec["id"] + ".c")
        path.write_text(ordinary_source(spec["name"], spec["bound"], spec["variant"], spec["alpha"]), encoding="utf-8")
        spec["path"] = str(path.relative_to(ROOT))
        spec["sha256"] = digest(path)
        spec["parameters"] = ["focus" if spec["alpha"] else "target", "m0", "m1", "m2", "r0", "r1", "r2"]
    dump(ROOT / "challenge_index.json", {"synthetic": True, "sources": specs, "eligibility_is_researcher_scope_registration_not_extractor_result": True})

    generation = []
    unique = {}
    for bits, target, initial, order in itertools.product(range(8), range(3), itertools.product(range(3), repeat=3), itertools.permutations(range(3))):
        members = tuple(item for item in order if bits & (1 << item))
        generation.append({"mask": bits, "target": target, "owners": initial, "full_order": order, "members": members})
        unique[(members, target, initial)] = None
    gzip_rows(ROOT / "generation_records.jsonl.gz", generation)
    records = []
    executable = [spec for spec in specs if spec["eligibility"] == "supported_scope"]
    record_number = 0
    for spec in executable:
        for members, target, initial in sorted(unique):
            if len(members) != spec["bound"]:
                continue
            slots = list(members) + [0] * (3 - len(members))
            arguments = [target] + slots + list(initial)
            result = sequential_reference(members, target, initial, spec["variant"])
            records.append({"record": record_number, "source_id": spec["id"], "function": spec["name"], "bound": spec["bound"], "target": target, "members": members, "owners": initial, "args": arguments, "expected": result})
            record_number += 1
    gzip_rows(ROOT / "expected_records.jsonl.gz", records)
    by_source = {}
    for spec in executable:
        subset = [r for r in records if r["source_id"] == spec["id"]]
        counts = {}
        for row in subset:
            key = str(row["expected"]["return"])
            counts[key] = counts.get(key, 0) + 1
        by_source[spec["id"]] = {"executions": len(subset), "return_counts": counts}
    dump(ROOT / "expected_behavior_summary.json", {"status": "expected_before_extractor_disclosure", "by_source": by_source})

    # Standalone harness is never an extractor challenge: scanf/stdio and all
    # pointer uses below are solely test transport, not accepted input syntax.
    declarations = [f"int {spec['name']}(int,int,int,int,int,int,int);" for spec in executable]
    dispatch = [f"    case {i}: status = {spec['name']}(t,a,b,c,x,y,z); break;" for i, spec in enumerate(executable)]
    harness = "#include <stdio.h>\n" + "\n".join(declarations) + "\nint main(void) {\n  int k,t,a,b,c,x,y,z,status;\n  while (scanf(\"%d %d %d %d %d %d %d %d\", &k,&t,&a,&b,&c,&x,&y,&z) == 8) {\n    switch (k) {\n" + "\n".join(dispatch) + "\n    default: return 2;\n    }\n    printf(\"%d\\n\", status);\n  }\n  return 0;\n}\n"
    (ROOT / "c_harness.c").write_text(harness, encoding="utf-8")
    env = dict(os.environ)
    env["PATH"] = str(COMPILER.parent) + os.pathsep + env.get("PATH", "")
    version = subprocess.run([str(COMPILER), "--version"], capture_output=True, text=True, check=True, env=env).stdout.splitlines()[0]
    command = [str(COMPILER), "-std=c11", "-O0", "-Wall", "-Wextra", "-pedantic"] + [str(ROOT / spec["path"]) for spec in executable] + [str(ROOT / "c_harness.c"), "-o", str(BUILD / "oracle.exe")]
    compiled = subprocess.run(command, capture_output=True, text=True, env=env)
    if compiled.returncode:
        raise RuntimeError(compiled.stderr)
    syntax_command = [str(COMPILER), "-std=c11", "-Wall", "-Wextra", "-pedantic", "-fsyntax-only"] + [str(ROOT / spec["path"]) for spec in specs if spec["eligibility"] != "supported_scope"]
    syntax = subprocess.run(syntax_command, capture_output=True, text=True, env=env)
    if syntax.returncode:
        raise RuntimeError(syntax.stderr)
    source_numbers = {spec["id"]: i for i, spec in enumerate(executable)}
    input_text = "".join(" ".join(str(x) for x in [source_numbers[row["source_id"]]] + row["args"]) + "\n" for row in records)
    actual = subprocess.run([str(BUILD / "oracle.exe")], input=input_text, capture_output=True, text=True, env=env)
    if actual.returncode:
        raise RuntimeError(actual.stderr)
    statuses = [int(line) for line in actual.stdout.splitlines()]
    if len(statuses) != len(records):
        raise RuntimeError("C output count differs from independent reference")
    mismatch = [{"record": row["record"], "expected": row["expected"]["return"], "actual": status} for row, status in zip(records, statuses) if row["expected"]["return"] != status]
    dump(ROOT / "native_validation.json", {"compiler": version, "compiler_path": str(COMPILER), "compile_argv": command, "syntax_only_argv": syntax_command, "compile_exit": compiled.returncode, "compile_stderr": compiled.stderr, "syntax_exit": syntax.returncode, "syntax_stderr": syntax.stderr, "executable_sha256": digest(BUILD / "oracle.exe"), "source_functions_executed": len(executable), "finite_executions": len(records), "C_output_sha256": hashlib.sha256(actual.stdout.encode()).hexdigest(), "independent_python_agreement": not mismatch, "mismatches": mismatch, "only_C_return_is_cross_checked": True, "witness_final_state_and_trace_are_python_reference_not_C_observed": True})
    if mismatch:
        raise RuntimeError("Native C/reference mismatch; preserve before any repair")

    dump(ROOT / "expected_summary.json", {"role": "independent assistant finite behavior oracle; not human expert gold standard", "material": "Human-authored ordinary C, inspired by known search/update/check shape; not Linux source, new defects or independent holdout", "source_functions": len(specs), "supported_scope_functions": len(executable), "scope_negative_functions": len(specs) - len(executable), "generation_records": len(generation), "unique_baseline_inputs": len(unique), "native_C_executions_including_renamed_and_changed_order_update_controls": len(records), "native_vs_sequential_python_agreement": not mismatch, "extractor_implementation_or_results_read": False, "concrete_challenges_and_expected_records_release": "Only after implementation freeze; expected_behavior_summary and records are sealed private test details", "counting": "Inputs/executions/source variants are synthetic component validation, not Linux cases, defects or generalization."})
    files = [p for p in ROOT.rglob("*") if p.is_file() and "build" not in p.relative_to(ROOT).parts and p.name != "freeze_manifest.json"]
    dump(ROOT / "freeze_manifest.json", {"schema": "n29_independent_oracle_freeze_v1", "date": "2026-10-18", "registration": "Expected records and source prepared without reading extractor implementation/output; disclose only after implementation freeze", "files": {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(files)}, "native_binary": {"path": "build/oracle.exe", "sha256": digest(BUILD / "oracle.exe"), "git_ignored": True}, "source_indices_not_normative_truth": True, "no_Linux_source_or_API_or_kernel_or_R3": True})
    print(json.dumps({"status": "oracle_sealed", "generation_records": len(generation), "unique_baseline_inputs": len(unique), "native_executions": len(records), "native_python_agreement": not mismatch, "source_functions": len(specs), "freeze_manifest_sha256": digest(ROOT / "freeze_manifest.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
