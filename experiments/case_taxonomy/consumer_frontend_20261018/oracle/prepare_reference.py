"""Fresh assistant-written finite challenges, isolated from the v2 method.

Synthetic ordinary C, not Linux source/new defects/human expert gold.  The
native executable checks return values only.  All detailed observations are
the independently programmed Python sequential reference, not native probes.
"""
from __future__ import annotations

import gzip
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess


BASE = Path(__file__).resolve().parent
CODE = BASE / "challenge_sources"
BUILD = BASE / "build"
GCC = Path("C:/msys64/ucrt64/bin/gcc.exe")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save_rows(path: Path, rows: list[dict]) -> None:
    payload = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows)
    with path.open("wb") as out:
        with gzip.GzipFile(fileobj=out, filename="", mode="wb", mtime=0) as zipped:
            zipped.write(payload.encode("utf-8"))


def c_function(spec: dict) -> bytes:
    target, roster, relation, size, index, second, witness, flag, item, actor = spec["names"]
    ps = [target, "p0", "p1", "p2", "q0", "q1", "q2", "nomination"]
    bound = ("int" if spec.get("negative") == "mutable_bound" else "const /* immutable local bound */ int") + f" {size} = {spec['bound']};"
    flag_decl = f"  int {flag} = 0;\n" if spec["exit"] == "flag" else ""
    choice = "nomination" if spec.get("sentinel_choice") else item
    search_content = f"""    int {item} = {roster}[{index}];
    int earlier_relation = {relation}[{item}];
"""
    if spec.get("negative") == "mutable_bound":
        search_content += f"    if ({index} == 0)\n      {size} = 2;\n"
    search_content += f"""    if ({item} == {target})
      continue;
    if (earlier_relation == {item}) {{
      {witness} = {choice};
      break;
    }}
"""
    if spec.get("negative") == "while":
        search = f"  {index} = 0;\n  while ({index} < {size}) {{\n" + search_content + f"    {index}++;\n  }}\n"
    else:
        search = f"  for ({index} = 0; {index} < {size}; {index}++) {{\n" + search_content + "  }\n"
    body = f"    int {actor} = {roster}[{second}];\n    int inspected_unit = {actor};\n"
    if spec.get("skip_target"):
        body += f"    if (inspected_unit == {target})\n      continue;\n"
    update_guard = f"inspected_unit != {witness}" if spec.get("skip_target") else f"inspected_unit == {target}"
    update = f"    if ({update_guard})\n      {relation}[inspected_unit] = {witness};\n"
    action = f"{flag} = 1;" if spec["exit"] == "flag" else "return 37;"
    check = f"    if ({relation}[inspected_unit] != {witness})\n      {action}\n"
    body += (check + update) if spec.get("check_first") else (update + check)
    if spec.get("negative") == "flag_reset":
        body += f"    if (inspected_unit == {target})\n      {flag} = 0;\n"
    tail = f"  if ({flag})\n    return 37;\n" if spec["exit"] == "flag" else ""
    text = f"""/* Assistant-synthesized component input: not Linux or an expert gold standard.
 * Markers inside this comment: // and the word alpha; no executable evidence.
 */
int {spec['function']}({', '.join('int ' + p for p in ps)})
{{
  int {roster}[3] = {{p0, p1, p2}}; // bounded local sequence
  int {relation}[3] = {{q0, q1, q2}};
  {bound}
  int {witness} = -1;
{flag_decl}  int {index};
  int {second};

  if ({size} == 1)
    return 13;
{search}  if ({witness} < 0)
    return 29;
  // The following check is a neutral predicate, not a bug label.
  for ({second} = 0; {second} < {size}; {second}++) {{
{body}  }}
{tail}  return 5;
}}
"""
    if spec.get("crlf"):
        text = text.replace("\n", "\r\n")
    spec["parameters"] = ps
    return text.encode("utf-8")


def sequential_reference(spec: dict, roster: tuple[int, ...], focus: int, initial: tuple[int, ...], nomination: int) -> dict:
    state = list(initial)
    observations: list[dict] = []
    writes: list[dict] = []
    visited: list[int] = []
    witness = -1
    first_match_member = None
    if len(roster) == 1:
        return {"return": 13, "check_observations": observations, "witness": witness, "first_match_member": None, "final_state": state, "search_visited": visited, "array_writes_reference_only": writes, "exit": "singleton"}
    for member in roster:
        visited.append(member)
        if member == focus:
            continue
        if state[member] == member:
            first_match_member = member
            witness = nomination if spec.get("sentinel_choice") else member
            break
    if witness < 0:
        return {"return": 29, "check_observations": observations, "witness": witness, "first_match_member": first_match_member, "final_state": state, "search_visited": visited, "array_writes_reference_only": writes, "exit": "post_search_guard"}
    flagged = False
    for iteration, member in enumerate(roster):
        if spec.get("skip_target") and member == focus:
            continue
        write_now = member != witness if spec.get("skip_target") else member == focus
        writes_before = 0
        if not spec.get("check_first") and write_now:
            state[member] = witness
            writes_before = 1
            writes.append({"iteration": iteration, "index": member, "value": witness, "relative_to_check": "before"})
        predicate = state[member] != witness
        observations.append({"iteration": iteration, "predicate_value": bool(predicate), "writes_before": writes_before})
        if predicate:
            if spec["exit"] == "direct":
                return {"return": 37, "check_observations": observations, "witness": witness, "first_match_member": first_match_member, "final_state": state, "search_visited": visited, "array_writes_reference_only": writes, "exit": "check_return"}
            flagged = True
        if spec.get("check_first") and write_now:
            state[member] = witness
            writes.append({"iteration": iteration, "index": member, "value": witness, "relative_to_check": "after"})
    return {"return": 37 if flagged else 5, "check_observations": observations, "witness": witness, "first_match_member": first_match_member, "final_state": state, "search_visited": visited, "array_writes_reference_only": writes, "exit": "flag_return" if flagged else "tail"}


def main() -> None:
    if (BASE / "freeze_manifest.json").exists():
        raise SystemExit("Already frozen: preserve exact reference and challenge files")
    CODE.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(exist_ok=True)
    (BASE / ".gitignore").write_text("build/\n__pycache__/\n", encoding="utf-8")
    normal_names = ["focus", "sequence", "parent", "extent", "scan", "walk", "selected", "changed", "entry", "unit"]
    renamed = ["pivot", "items", "route", "ceiling", "cursor", "ordinal", "nominee", "marked", "element", "subject"]
    specs = [
        {"id": "K0", "function": "empty_relation_pass", "bound": 0, "exit": "direct", "names": normal_names},
        {"id": "K1", "function": "singleton_relation_pass", "bound": 1, "exit": "flag", "names": renamed},
        {"id": "K2", "function": "choose_then_test_relation", "bound": 3, "exit": "direct", "names": renamed, "crlf": True},
        {"id": "K3", "function": "record_before_revision", "bound": 3, "exit": "flag", "names": normal_names, "check_first": True},
        {"id": "K4", "function": "omit_focus_and_relate", "bound": 2, "exit": "flag", "names": renamed, "skip_target": True},
        {"id": "K5", "function": "selected_payload_gate", "bound": 3, "exit": "direct", "names": normal_names, "sentinel_choice": True},
        {"id": "Z0", "function": "changing_local_extent", "bound": 3, "exit": "direct", "names": normal_names, "negative": "mutable_bound", "reason": "Writes loop bound in loop; outside immutable-bound scope."},
        {"id": "Z1", "function": "revocable_recording", "bound": 3, "exit": "flag", "names": renamed, "negative": "flag_reset", "reason": "Resets accumulated check flag, outside monotonic-zero-to-one scope."},
        {"id": "Z2", "function": "noncanonical_lookup", "bound": 3, "exit": "direct", "names": normal_names, "negative": "while", "reason": "Search uses while, outside canonical-for scope."},
    ]
    for spec in specs:
        path = CODE / (spec["id"] + ".c")
        path.write_bytes(c_function(spec))
        spec.update(path=path.relative_to(BASE).as_posix(), sha256=sha(path), eligibility="unsupported_scope" if spec.get("negative") else "supported_scope")
    save_json(BASE / "challenge_index.json", {"schema": "n210_independent_synthetic_sources_v1", "actual_author": "independent assistant, manually synthesized relative to automatic extraction; not a human expert", "independence": "No v2 implementation, developer tests or results read before this freeze. Old n29 forms were already known; fresh forms are component challenges only.", "sources": specs})

    records: list[dict] = []
    unique_states = set()
    for spec in specs:
        if spec["eligibility"] != "supported_scope":
            continue
        nominations = [-1, 0, 1, 2] if spec.get("sentinel_choice") else [0]
        for roster, focus, initial, nomination in itertools.product(itertools.permutations(range(3), spec["bound"]), range(3), itertools.product(range(3), repeat=3), nominations):
            args = [focus] + list(roster) + [0] * (3 - len(roster)) + list(initial) + [nomination]
            expected = sequential_reference(spec, roster, focus, initial, nomination)
            records.append({"record": len(records), "source_id": spec["id"], "args": args, "members": roster, "focus": focus, "initial": initial, "nomination": nomination, "expected": expected})
            unique_states.add((roster, focus, initial, nomination))
    save_rows(BASE / "expected_records.jsonl.gz", records)
    positive = [s for s in specs if s["eligibility"] == "supported_scope"]
    declarations = [f"int {s['function']}(int,int,int,int,int,int,int,int);" for s in positive]
    dispatch = [f"    case {i}: answer={s['function']}(a,b,c,d,e,f,g,h); break;" for i, s in enumerate(positive)]
    harness = "#include <stdio.h>\n" + "\n".join(declarations) + "\nint main(void) {\n  int k,a,b,c,d,e,f,g,h,answer;\n  while (scanf(\"%d %d %d %d %d %d %d %d %d\",&k,&a,&b,&c,&d,&e,&f,&g,&h)==9) {\n    switch(k) {\n" + "\n".join(dispatch) + "\n    default:return 2;\n    }\n    printf(\"%d\\n\",answer);\n  }\n  return 0;\n}\n"
    (BASE / "transport_harness.c").write_text(harness, encoding="utf-8")
    environment = dict(os.environ)
    environment["PATH"] = str(GCC.parent) + os.pathsep + environment.get("PATH", "")
    version = subprocess.run([str(GCC), "--version"], env=environment, capture_output=True, text=True, check=True).stdout.splitlines()[0]
    command = [str(GCC), "-std=c11", "-O0", "-Wall", "-Wextra", "-pedantic"] + [str(BASE / s["path"]) for s in positive] + [str(BASE / "transport_harness.c"), "-o", str(BUILD / "finite_reference.exe")]
    compiled = subprocess.run(command, env=environment, capture_output=True, text=True)
    if compiled.returncode:
        raise RuntimeError(compiled.stderr)
    syntax_argv = [str(GCC), "-std=c11", "-fsyntax-only"] + [str(BASE / s["path"]) for s in specs if s["eligibility"] == "unsupported_scope"]
    syntax = subprocess.run(syntax_argv, env=environment, capture_output=True, text=True)
    if syntax.returncode:
        raise RuntimeError(syntax.stderr)
    source_number = {s["id"]: i for i, s in enumerate(positive)}
    batch = "".join(" ".join(str(v) for v in [source_number[row["source_id"]]] + row["args"]) + "\n" for row in records)
    actual = subprocess.run([str(BUILD / "finite_reference.exe")], env=environment, input=batch, capture_output=True, text=True)
    if actual.returncode:
        raise RuntimeError(actual.stderr)
    answers = [int(x) for x in actual.stdout.splitlines()]
    if len(answers) != len(records):
        raise RuntimeError("Native return record count differs")
    mismatches = [{"record": row["record"], "expected": row["expected"]["return"], "actual": answer} for row, answer in zip(records, answers) if answer != row["expected"]["return"]]
    save_json(BASE / "native_validation.json", {"compiler": version, "compiler_path": str(GCC), "compile_argv": command, "compile_exit": compiled.returncode, "compile_stderr": compiled.stderr, "syntax_only_argv": syntax_argv, "syntax_exit": syntax.returncode, "syntax_stderr": syntax.stderr, "binary_sha256": sha(BUILD / "finite_reference.exe"), "executions": len(records), "return_count": len(answers), "mismatches": mismatches, "return_agreement": not mismatches, "native_return_stdout_sha256": hashlib.sha256(actual.stdout.encode()).hexdigest(), "native_measurement": "return only", "observations_witness_finalstate": "Python sequential reference only, not native C observations"})
    if mismatches:
        raise RuntimeError("Native/reference disagree; preserve outcome without adapting method")

    per_source = {}
    for spec in positive:
        subset = [r for r in records if r["source_id"] == spec["id"]]
        per_source[spec["id"]] = {"executions": len(subset), "return_counts": {str(code): sum(row['expected']['return'] == code for row in subset) for code in sorted({row['expected']['return'] for row in subset})}, "check_observations": sum(len(row['expected']['check_observations']) for row in subset)}
    save_json(BASE / "expected_behavior_summary.json", {"by_source": per_source, "scope_negatives_have_no_finite_behavior_expectations": True})
    save_json(BASE / "expected_summary.json", {"actual_author": "independent assistant manual synthesis, not human expert", "source_variants": len(specs), "registered_supported_scope": len(positive), "scope_negatives": len(specs) - len(positive), "unique_input_states_ignoring_source_id": len(unique_states), "finite_source_input_executions": len(records), "native_return_reference_agreement": not mismatches, "additional_check_observations": "Independently written Python sequential reference; not native observations", "implementation_tests_and_results_read": False, "independence_level": "Fresh isolated synthetic component challenge, not new Linux source, unseen defects or human gold standard", "release": "Concrete sources and expectations remain hidden until method freeze"})
    all_files = [p for p in BASE.rglob("*") if p.is_file() and "build" not in p.relative_to(BASE).parts and p.name != "freeze_manifest.json"]
    save_json(BASE / "freeze_manifest.json", {"schema": "n210_independent_oracle_freeze_v1", "date": "2026-10-18", "files": {p.relative_to(BASE).as_posix(): sha(p) for p in sorted(all_files)}, "binary": {"path": "build/finite_reference.exe", "sha256": sha(BUILD / "finite_reference.exe"), "ignored": True}, "expected_prepared_before_method_read_or_challenge_outcome": True, "actual_author": "independent assistant, not human expert", "API_Linux_kernel_calls": 0})
    print(json.dumps({"status": "frozen", "source_variants": len(specs), "unique_input_states": len(unique_states), "source_input_executions": len(records), "native_return_agreement": not mismatches, "manifest_sha256": sha(BASE / "freeze_manifest.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
