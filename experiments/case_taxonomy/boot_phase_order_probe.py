"""Check one source-annotated boot-phase contract against historical Git trees.

The JSON file supplies P/C/A roles after manual review. This script checks
source-call reachability and relative stages; it does not infer roles, execute
the kernel, or prove whether a particular firmware image contains the property.
"""

import argparse
import json
import re
import subprocess
from pathlib import Path


NONCODE = re.compile(
    r"//[^\n]*|/\*.*?\*/|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'",
    re.DOTALL,
)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, encoding="utf-8"
    )


def source(root: Path, commit: str, path: str) -> str:
    return git(root, "show", f"{commit}:{path}")


def mask_noncode(code: str) -> str:
    return NONCODE.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), code)


def closing_brace(code: str, opened: int) -> int:
    depth = 0
    for i in range(opened, len(code)):
        if code[i] == "{":
            depth += 1
        elif code[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("unbalanced braces in historical source")


def function(code: str, name: str) -> tuple[str, str]:
    masked = mask_noncode(code)
    pattern = re.compile(r"\b" + re.escape(name) + r"\s*\([^;{}]*\)\s*\{")
    matches = list(pattern.finditer(masked))
    if len(matches) != 1:
        raise ValueError(f"expected one definition of {name}; found {len(matches)}")
    opened = matches[0].end() - 1
    closed = closing_brace(masked, opened)
    return code[opened + 1 : closed], masked[opened + 1 : closed]


def call_pos(masked_body: str, name: str) -> int:
    match = re.search(r"\b" + re.escape(name) + r"\s*\(", masked_body)
    if not match:
        raise ValueError(f"call to {name} missing")
    return match.start()


def has_call(masked_body: str, name: str) -> bool:
    return bool(re.search(r"\b" + re.escape(name) + r"\s*\(", masked_body))


def assert_boot_stages(main: str, c: dict) -> dict:
    _, start = function(main, "start_kernel")
    _, mm = function(main, "mm_init")
    _, handoff = function(main, "arch_call_rest_init")
    _, rest = function(main, "rest_init")
    _, kernel_init = function(main, "kernel_init")
    _, late = function(main, "kernel_init_freeable")

    early_pos = call_pos(start, c["early_entry"])
    mm_pos = call_pos(start, "mm_init")
    handoff_pos = call_pos(start, "arch_call_rest_init")
    if not early_pos < mm_pos < handoff_pos:
        raise ValueError("early entry, mm_init and handoff are not ordered")
    call_pos(mm, "kmem_cache_init")
    call_pos(handoff, "rest_init")
    if not re.search(r"\buser_mode_thread\s*\(\s*kernel_init\s*,", rest):
        raise ValueError("rest_init does not spawn kernel_init")
    call_pos(kernel_init, "kernel_init_freeable")

    gate = re.search(r"\bgfp_allowed_mask\s*=\s*__GFP_BITS_MASK\s*;", late)
    if not gate or not gate.start() < call_pos(late, c["late_entry"]):
        raise ValueError("late entry does not follow GFP mask restoration")
    return {
        "early": f"start_kernel:{c['early_entry']} before mm_init",
        "late": f"kernel_init_freeable:{c['late_entry']} after mm_init and GFP restoration",
    }


def assert_consumer_path(topology: str, c: dict) -> dict:
    for caller, callee in c["topology_edges"]:
        _, body = function(topology, caller)
        call_pos(body, callee)

    raw, body = function(topology, c["allocation_function"])
    if c["property"] not in raw or "of_property_read_u32" not in raw:
        raise ValueError("property read is absent from allocation path")
    guard = re.search(r"\bif\s*\(\s*!ret\s*\)\s*\{", body)
    if not guard:
        raise ValueError("successful property-read guard is absent")
    guard_end = closing_brace(body, guard.end() - 1)
    if not has_call(body[guard.end() : guard_end], c["allocation_call"]):
        raise ValueError("allocation is outside successful property-read path")
    if not re.search(r"\bcap_parsing_failed\s*=\s*true\s*;", body):
        raise ValueError("allocation-failure marker missing")

    dt_raw, _ = function(topology, "parse_dt_topology")
    if c["tree_node"] not in dt_raw:
        raise ValueError("required DT topology node is absent")
    _, init_body = function(topology, "init_cpu_topology")
    call_pos(init_body, "of_have_populated_dt")
    return {
        "call_edges_checked": len(c["topology_edges"]),
        "property_guarded_allocation": True,
        "allocation_failure_marker": True,
    }


def moved_calls(root: Path, commit: str) -> list[str]:
    patch = git(root, "show", "--format=", "--unified=0", commit)
    added, removed = set(), set()
    for line in patch.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+") or line.startswith("-"):
            match = re.match(r"[+-]\s*([A-Za-z_]\w*)\s*\([^;{}]*\)\s*;\s*$", line)
            if match:
                (added if line[0] == "+" else removed).add(match.group(1))
    return sorted(added & removed)


def evaluate(root: Path, c: dict, revision: str) -> dict:
    main = source(root, revision, c["main_file"])
    arch = source(root, revision, c["arch_file"])
    topology = source(root, revision, c["topology_file"])
    stages = assert_boot_stages(main, c)
    path = assert_consumer_path(topology, c)
    _, early = function(arch, c["early_entry"])
    _, late = function(arch, c["late_entry"])
    locations = [stage for stage, body in (("early", early), ("late", late))
                 if has_call(body, c["consumer_call"])]
    if len(locations) != 1:
        raise ValueError(f"consumer call must appear in one boot stage: {locations}")
    return {
        "revision": revision,
        "consumer_stage": locations[0],
        "A_true": "precondition_order_violation" if locations[0] == "early" else "order_satisfied",
        "A_false": "allocation_path_inactive",
        "stage_evidence": stages[locations[0]],
        "consumer_path_evidence": path,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=Path(__file__).with_name("boot_phase_contract.json"))
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("boot_phase_order_result.json"))
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    fix = contract["fix_commit"]
    old = evaluate(args.linux_dir, contract, f"{fix}^")
    fixed = evaluate(args.linux_dir, contract, fix)
    result = {
        "contract_id": contract["id"],
        "condition_A": contract["condition_A"],
        "producer_P": contract["producer_P"],
        "consumer_C": contract["consumer_C"],
        "failed_preparation": contract["failed_preparation"],
        "commit_diff_candidate_calls": moved_calls(args.linux_dir, fix),
        "negative_commit_diff_candidate_calls": moved_calls(args.linux_dir, contract["negative_commit"]),
        "old": old,
        "fixed": fixed,
        "scope": "manual P/C/A annotation plus source-order check; no kernel execution or general automatic role extraction",
    }
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
