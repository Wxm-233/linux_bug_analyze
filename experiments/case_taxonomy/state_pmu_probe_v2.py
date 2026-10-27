"""Post-read LoongArch PMU/SMP phase development extractor.

This is intentionally not an independent holdout or defect classifier.  It
accepts the historical compound Kbuild line, pure_initcall, and a one-hop
on_each_cpu -> cpu_online_mask chain observed after unsealing f3334ebb8a2a.
No commit message or patch is an input to an individual evaluation.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


INITCALL = re.compile(
    r"(?m)^\s*(early_initcall|pure_initcall|core_initcall|postcore_initcall|arch_initcall|"
    r"subsys_initcall|fs_initcall|device_initcall|late_initcall)\s*"
    r"\(\s*([A-Za-z_]\w*)\s*\)\s*;"
)
DIRECT_ONLINE = re.compile(
    r"\b(?:for_each_online_cpu|num_online_cpus|cpu_online_mask|"
    r"cpu_online\s*\()"
)
ON_EACH_CPU = re.compile(r"\bon_each_cpu\s*\(\s*([A-Za-z_]\w*)\s*,")
INDIRECT_HINT = re.compile(r"\b(?:perf_pmu_register|cpuhp_setup_state\w*)\s*\(")
NONCODE = re.compile(
    r"//[^\n]*|/\*.*?\*/|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'",
    re.DOTALL,
)


def git(repo: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True, encoding="utf-8", errors="replace", capture_output=True,
    )
    return result.stdout if result.returncode == 0 else None


def source(repo: Path, revision: str, path: str) -> str | None:
    return git(repo, "show", f"{revision}:{path}")


def mask(code: str) -> str:
    return NONCODE.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), code)


def line_of(code: str, offset: int) -> int:
    return code.count("\n", 0, offset) + 1


def function_body(code: str, name: str) -> tuple[str, int] | None:
    masked = mask(code)
    matches = list(re.finditer(
        r"\b" + re.escape(name) + r"\s*\([^;{}]*\)\s*\{", masked
    ))
    if len(matches) != 1:
        return None
    start = matches[0].end() - 1
    depth = 0
    for offset in range(start, len(masked)):
        if masked[offset] == "{":
            depth += 1
        elif masked[offset] == "}":
            depth -= 1
            if depth == 0:
                return masked[start + 1:offset], start + 1
    return None


def boot_order(main: str) -> dict:
    found = function_body(main, "kernel_init_freeable")
    if found is None:
        return {"known": False, "reason": "kernel_init_freeable body unresolved"}
    body, offset = found
    names = ("do_pre_smp_initcalls", "smp_init", "do_basic_setup")
    positions = [re.search(r"\b" + name + r"\s*\(", body) for name in names]
    if any(item is None for item in positions):
        return {"known": False, "reason": "required boot calls absent"}
    if not positions[0].start() < positions[1].start() < positions[2].start():
        return {"known": False, "reason": "boot call order not recognized"}
    pre = function_body(main, "do_pre_smp_initcalls")
    basic = function_body(main, "do_basic_setup")
    if pre is None or basic is None:
        return {"known": False, "reason": "pre-SMP or basic setup body unresolved"}
    if not re.search(r"fn\s*=\s*__initcall_start\s*;", pre[0]) or not re.search(
        r"fn\s*<\s*__initcall0_start\s*;", pre[0]
    ) or not re.search(r"\bdo_initcalls\s*\(", basic[0]):
        return {"known": False, "reason": "initcall dispatch boundaries unresolved"}
    return {
        "known": True,
        "order": list(names),
        "line_refs": {name: line_of(main, offset + item.start())
                      for name, item in zip(names, positions)},
        "pre_smp_loop_ref": line_of(main, pre[1]),
        "post_smp_initcalls_ref": line_of(main, basic[1]),
    }


def evaluate(repo: Path, revision: str, arch: str = "loongarch",
             perf_events: bool = True, smp: bool = True) -> dict:
    path = f"arch/{arch}/kernel/perf_event.c"
    make_path = f"arch/{arch}/kernel/Makefile"
    out = {
        "revision": revision, "arch": arch, "profile": {
            "CONFIG_PERF_EVENTS": perf_events, "CONFIG_SMP": smp},
        "status": "insufficient", "reason": "not evaluated", "phase": None,
        "source_refs": {}, "online_consumer_sites": [], "indirect_hints": [],
        "scope": "source-level conditional phase evidence; no kernel execution",
    }
    if arch != "loongarch":
        out["reason"] = "this frozen probe supports only LoongArch"
        return out
    main = source(repo, revision, "init/main.c")
    pmu = source(repo, revision, path)
    make = source(repo, revision, make_path)
    init_header = source(repo, revision, "include/linux/init.h")
    smp_header = source(repo, revision, "include/linux/smp.h")
    if any(item is None for item in (main, pmu, make, init_header, smp_header)):
        out["reason"] = "historical source file missing"
        return out
    # Only this simple, explicit Kbuild shape proves the off-profile control.
    rules = list(re.finditer(
        r"(?m)^\s*obj-\$\(CONFIG_PERF_EVENTS\)\s*\+=\s*"
        r"(?:[A-Za-z_][A-Za-z_0-9]*\.o\s+)*perf_event\.o"
        r"(?:\s+[A-Za-z_][A-Za-z_0-9]*\.o)*\s*$", make
    ))
    if len(rules) != 1:
        out["reason"] = "PMU Kbuild reachability unresolved"
        return out
    out["source_refs"]["kbuild"] = f"{revision}:{make_path}:{line_of(make, rules[0].start())}"
    if not perf_events:
        out["status"] = "not_applicable"
        out["reason"] = "perf_event.o is not built when CONFIG_PERF_EVENTS=n"
        return out
    if not smp:
        out["status"] = "not_applicable"
        out["reason"] = "the secondary-CPU readiness contract is inactive with CONFIG_SMP=n"
        return out
    order = boot_order(main)
    out["boot_order"] = order
    if not order["known"]:
        out["reason"] = order["reason"]
        return out
    out["source_refs"]["boot_order"] = {
        name: f"{revision}:init/main.c:{line}"
        for name, line in order["line_refs"].items()
    }
    out["source_refs"]["boot_dispatch"] = {
        "pre_smp": f"{revision}:init/main.c:{order['pre_smp_loop_ref']}",
        "post_smp": f"{revision}:init/main.c:{order['post_smp_initcalls_ref']}",
    }
    calls = list(INITCALL.finditer(mask(pmu)))
    if len(calls) != 1:
        out["reason"] = f"expected one recognized PMU initcall, found {len(calls)}"
        return out
    kind, name = calls[0].groups()
    macro_level = "early" if kind == "early_initcall" else "0" if kind == "pure_initcall" else None
    if macro_level is None or not re.search(
        rf"(?m)^#define\s+{kind}\(fn\)\s+__define_initcall\(fn,\s*{macro_level}\)",
        init_header,
    ):
        out["reason"] = f"{kind} macro's historical phase unresolved"
        return out
    found = function_body(pmu, name)
    if found is None:
        out["reason"] = f"initcall function {name} body unresolved"
        return out
    body, offset = found
    out["phase"] = "pre_smp" if kind == "early_initcall" else "post_smp"
    out["source_refs"]["initcall"] = f"{revision}:{path}:{line_of(pmu, calls[0].start())}"
    macro_match = re.search(rf"(?m)^#define\s+{kind}\(fn\)", init_header)
    out["source_refs"]["initcall_macro"] = (
        f"{revision}:include/linux/init.h:{line_of(init_header, macro_match.start())}"
    )
    out["source_refs"]["init_function"] = f"{revision}:{path}:{line_of(pmu, offset)}"
    out["online_consumer_sites"] = [
        f"{revision}:{path}:{line_of(pmu, offset + m.start())}"
        for m in DIRECT_ONLINE.finditer(body)
    ]
    wrapper = function_body(smp_header, "on_each_cpu")
    wrapper_known = bool(wrapper and re.search(
        r"on_each_cpu_cond_mask\s*\(\s*NULL\s*,\s*func\s*,\s*info\s*,"
        r"\s*wait\s*,\s*cpu_online_mask\s*\)", wrapper[0]
    ))
    for match in ON_EACH_CPU.finditer(body):
        callback = match.group(1)
        if not wrapper_known or function_body(pmu, callback) is None:
            continue
        out["online_consumer_sites"].append(
            f"{revision}:{path}:{line_of(pmu, offset + match.start())}"
        )
        out["source_refs"]["online_mask_wrapper"] = (
            f"{revision}:include/linux/smp.h:{line_of(smp_header, wrapper[1])}"
        )
        out["source_refs"]["callback"] = callback
    out["indirect_hints"] = [
        f"{revision}:{path}:{line_of(pmu, offset + m.start())}"
        for m in INDIRECT_HINT.finditer(body)
    ]
    if not out["online_consumer_sites"]:
        out["reason"] = "no direct online-CPU read or resolved one-hop on_each_cpu consumer"
        return out
    if out["phase"] == "pre_smp":
        out["status"] = "hit"
        out["reason"] = "online-CPU use reaches cpu_online_mask before smp_init; review conditional contract"
    else:
        out["status"] = "normal"
        out["reason"] = "online-CPU use reaches cpu_online_mask after smp_init"
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--arch", default="loongarch")
    parser.add_argument("--perf-events", choices=("y", "n"), default="y")
    parser.add_argument("--smp", choices=("y", "n"), default="y")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.linux_dir, args.revision, args.arch,
                      args.perf_events == "y", args.smp == "y")
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"status": result["status"], "reason": result["reason"]}))


if __name__ == "__main__":
    main()
