"""Read selected existing WSL artifacts; never compile, boot or call a model."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from linux_bug_analyze.preprocessed_evidence import extract_definitions

OLD = HERE.parent / "s390_arch_contract_20261013"
BASE = Path("/root/.cache/linux-bug-analyze/s390-contract-20261013")
REPO = Path("/root/repos/linux")
VERSIONS = {"old": "88b604263f3d6eedae0b1c2c3bbd602d1e2e8775",
            "fixed": "a052096bdd6809eeab809202726634d1ac975aa1"}
SELECTORS = {"sched_core_lock": "kernel/sched/core.c",
             "cpu_smt_mask": "include/linux/topology.h",
             "cpumask_next": "include/linux/cpumask.h"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def config(path):
    values = {}
    for line in path.read_text().splitlines():
        match = re.fullmatch(r"CONFIG_([A-Za-z_0-9]+)=(.*)", line)
        if match:
            values[match[1]] = match[2]
        else:
            match = re.fullmatch(r"# CONFIG_([A-Za-z_0-9]+) is not set", line)
            if match:
                values[match[1]] = "n"
    return values


def collect_profile(profile):
    variant, arch = profile.split("_")
    revision = VERSIONS[variant]
    prior = OLD / "profiles" / profile
    build = BASE / profile / "build"
    ledger_path = prior / "artifact_binding.json"
    ledger = read(ledger_path)
    recorded = read(prior / "result.json")
    if (ledger["revision"] != revision or recorded["revision"] != revision
            or ledger["arch"] != arch or ledger["variant"] != variant
            or recorded["cache_build"] != str(build)):
        raise ValueError("Profile/revision binding mismatch: " + profile)
    if (BASE / variant / "source_revision").read_text().strip() != revision:
        raise ValueError("Source revision marker mismatch")
    expected = {a["path"]: a["sha256"] for a in ledger["artifacts"]}
    selected = [prior / "result.json", prior / "commands.json", prior / "kernel.config", prior / "autoconf.h",
                prior / "preprocessed_facts.json", prior / "supplemental_preprocessed_facts.json",
                build / ".config", build / "include/generated/autoconf.h",
                build / "kernel/sched/core.i", build / "kernel/sched/core.o"]
    checked = []
    for path in selected:
        sha = digest(path)
        if expected.get(str(path)) != sha:
            raise ValueError("Changed/unbound selected artifact: " + str(path))
        checked.append({"path": str(path), "sha256": sha})
    actual = config(build / ".config")
    target = "S390" if arch == "s390" else "X86_64"
    required = ["SMP", "SCHED_SMT", "SCHED_CORE", "HOTPLUG_CPU", "SYSFS", target]
    if arch == "s390":
        required.append("SCHED_TOPOLOGY")
    generated = (build / "include/generated/autoconf.h").read_text()
    for name in required:
        if actual.get(name) != "y" or not re.search(r"^#define CONFIG_" + name + r" 1$", generated, re.M):
            raise ValueError("Effective configuration mismatch: " + name)
    if actual.get("NR_CPUS") != "4" or not re.search(r"^#define CONFIG_NR_CPUS 4$", generated, re.M):
        raise ValueError("Effective NR_CPUS mismatch")
    raw = (build / "kernel/sched/core.i").read_bytes().decode("utf-8")
    tree = BASE / variant / "linux"
    functions = extract_definitions(raw, {k: str(tree / relative) for k, relative in SELECTORS.items()},
                                    allow_declarations=("cpumask_next",))
    if not all(f["all_token_paths_match_name_location"] for f in functions.values()):
        raise ValueError("Mixed definition origins need separate review, not single-header attribution")
    snippets = read(prior / "supplemental_preprocessed_facts.json")["functions"]
    if snippets["sched_core_lock"] not in functions["sched_core_lock"]["text"]:
        raise ValueError("Previously saved consumer region differs")
    getter = read(prior / "preprocessed_facts.json")["functions"]["cpu_smt_mask"]
    if getter not in functions["cpu_smt_mask"]["text"]:
        raise ValueError("Previously saved getter region differs")
    commands = read(prior / "commands.json")
    targets = [c for c in commands if c["label"] == "targets"]
    if len(targets) != 1 or targets[0]["returncode"] != 0:
        raise ValueError("Prior successful build command not uniquely bound")
    row = {
        "profile": profile, "arch": arch, "variant": variant, "revision": revision,
        "artifact_stage": "original non-instrumented object build, separate from runtime/",
        "prior_binding_sha256": digest(ledger_path), "selected_artifacts": checked,
        "effective_config": {k: actual[k] for k in required + ["NR_CPUS", "LOCALVERSION"]},
        "prior_target_command": targets[0]["argv"], "functions": functions,
        "definition_count": sum(f["region_kind"] == "definition" for f in functions.values()),
        "declaration_only_count": sum(f["region_kind"] == "declaration_only" for f in functions.values()),
        "whole_contract": "insufficient",
        "exact_content_at_consumption": "unknown", "interval_stability": "unknown",
        "source_prepare_effects": "not_checked_in_this_step",
        "extraction_scope": "lexical regions/identifiers and compiler line mappings; not a CFG or type analysis",
    }
    save(HERE / (profile + ".json"), row)
    print(json.dumps({"profile": profile, "functions": len(functions), "bound_artifacts": len(checked),
                      "region_kind": {k: v["region_kind"] for k, v in functions.items()},
                      "source_locations": {k: v["name_location"] for k, v in functions.items()}}, ensure_ascii=False), flush=True)
    return row


def source_references():
    patterns = {
        "kernel/sched/core.c": [r"^static void sched_core_lock\("],
        "include/linux/topology.h": [r"^#define topology_sibling_cpumask\(", r"\*cpu_smt_mask\("],
        "include/linux/cpumask.h": [r"^#define for_each_cpu\(", r"\bcpumask_next\s*\("],
        "arch/s390/include/asm/topology.h": [r"topology_sibling_cpumask"],
        "arch/x86/include/asm/topology.h": [r"topology_sibling_cpumask"],
    }
    output = []
    for variant, revision in VERSIONS.items():
        for relative, searches in patterns.items():
            command = ["git", "-C", str(REPO), "show", revision + ":" + relative]
            raw = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
            cached = BASE / variant / "linux" / relative
            if cached.read_bytes() != raw:
                raise ValueError("Selected current source differs from Git: " + relative)
            lines = raw.decode("utf-8").splitlines()
            spans = []
            for index, line in enumerate(lines):
                if any(re.search(pattern, line) for pattern in searches):
                    lo, hi = max(0, index - 4), min(len(lines), index + 11)
                    spans.append({"anchor_line": index + 1, "start_line": lo + 1, "end_line": hi,
                                  "text": "\n".join(lines[lo:hi]) + "\n"})
            output.append({"variant": variant, "revision": revision, "path": relative,
                           "full_source_sha256": hashlib.sha256(raw).hexdigest(),
                           "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
                           "cached_source_matches_git": True, "excerpts": spans,
                           "selection_origin": "researcher_selected_symbols_then_program_source_slices",
                           "scope": "partial source references; not a macro-definition trace or full conditional context"})
    save(HERE / "source_references.json", output)
    return output


def main():
    if os.name != "posix":
        raise RuntimeError("Run within WSL against the existing bound artifacts")
    rows = [collect_profile(profile) for profile in ["old_s390", "fixed_s390", "old_x86", "fixed_x86"]]
    references = source_references()
    comparisons = []
    for arch in ["s390", "x86"]:
        old, fixed = [next(r for r in rows if r["arch"] == arch and r["variant"] == variant)
                      for variant in ["old", "fixed"]]
        old_config = config(OLD / "profiles" / ("old_" + arch) / "kernel.config")
        fixed_config = config(OLD / "profiles" / ("fixed_" + arch) / "kernel.config")
        differences = {k: [old_config.get(k), fixed_config.get(k)]
                       for k in sorted(set(old_config) | set(fixed_config))
                       if old_config.get(k) != fixed_config.get(k)}
        if set(differences) != {"LOCALVERSION"}:
            raise ValueError("Unexpected same-architecture configuration differences")
        comparisons.append({"arch": arch, "configuration_differences": differences,
                            "same_raw_region_text": {n: old["functions"][n]["text"] == fixed["functions"][n]["text"]
                                                       for n in SELECTORS}})
    summary = {
        "schema": "configured-consumer-evidence-v1", "date": "2026-10-16",
        "status": "bounded_source_evidence_collected", "case_scope": "one already-read development case",
        "profiles": [r["profile"] for r in rows],
        "definition_regions": sum(r["definition_count"] for r in rows),
        "declaration_only_regions": sum(r["declaration_only_count"] for r in rows),
        "plan_deviation": "cpumask_next has an external declaration, not an inline definition, in the configured TUs; preserve the initial missing-definition failure and do not import another configuration's body",
        "selected_bound_artifacts": sum(len(r["selected_artifacts"]) for r in rows),
        "source_references": len(references), "comparisons": comparisons,
        "runtime_content": "unknown", "whole_contract": "insufficient",
        "new_build_commands": 0, "new_kernel_runs": 0, "new_model_requests": 0,
        "new_defects": 0, "independent_detection_positives": 0,
        "current_versions": {str(p.relative_to(ROOT)): digest(p) for p in [
            ROOT / "linux_bug_analyze/preprocessed_evidence.py", Path(__file__).resolve(),
            ROOT / "tests/test_preprocessed_evidence.py"]},
    }
    save(HERE / "results.json", summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        save(HERE / "error.json", {"status": "incomplete", "error_type": type(error).__name__, "error": str(error)})
        raise
