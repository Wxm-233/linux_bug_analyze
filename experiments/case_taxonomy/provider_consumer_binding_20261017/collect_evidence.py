"""Read existing non-instrumented s390 build artifacts; never build or boot."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from linux_bug_analyze.preprocessed_evidence import extract_definitions, _MARKER, _filename

spec = importlib.util.spec_from_file_location(
    "prior_consumer_helpers", HERE.parent / "consumer_preprocessing_20261016/collect_evidence.py")
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
BASE, OLD, VERSIONS = prior.BASE, prior.OLD, prior.VERSIONS
NAMES = {"cpu_topology", "cpu_setup_mask", "__cpu_possible_mask", "__cpu_online_mask"}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def global_excerpts(text):
    """Selected declaration-line excerpts, not a C declaration/alias parser."""
    points, rows, source, number = [], [], None, None
    lines = text.splitlines()
    for physical, line in enumerate(lines, 1):
        marker = _MARKER.fullmatch(line)
        if marker:
            source, number = _filename(marker[2]), int(marker[1])
            points.append({"physical_line": physical, "marker": True})
        else:
            points.append({"physical_line": physical, "path": source, "line": number})
            if number is not None:
                number += 1
    pattern = re.compile(r"^\s*(?P<extern>extern\s+)?(?:struct\s+cpu_topology_s390\s+(?P<topology>cpu_topology)|cpumask_t\s+(?P<setup>cpu_setup_mask))\b")
    for index, line in enumerate(lines):
        match = pattern.match(line)
        if not match:
            continue
        end = index
        while ";" not in lines[end] and end < min(index + 4, len(lines) - 1):
            end += 1
        if ";" not in lines[end] or not points[index].get("path"):
            raise ValueError("Unbounded/unmapped selected declaration excerpt")
        raw = "\n".join(lines[index:end + 1])
        rows.append({"symbol": match["topology"] or match["setup"],
                     "textual_form": "extern_declaration" if match["extern"] else "non_extern_declaration",
                     "text": raw, "sha256": hashlib.sha256(raw.encode()).hexdigest(),
                     "physical_start_line": index + 1, "physical_end_line": end + 1,
                     "source_locations": points[index:end + 1],
                     "evidence_layer": "researcher_selected_declaration_line_pattern_not_general_C_binding"})
    return rows


def object_evidence(path):
    argv = ["readelf", "--wide", "--file-header", "--symbols", "--relocs", str(path)]
    completed = subprocess.run(argv, capture_output=True, text=True,
                               env={**os.environ, "LC_ALL": "C"})
    if completed.returncode:
        raise ValueError("readelf failed: " + completed.stderr[:400])
    raw, header = completed.stdout, {}
    for label in ("Class", "Data", "Type", "Machine"):
        match = re.search(r"^\s*" + label + r":\s*(.+)$", raw, re.M)
        if not match:
            raise ValueError("Missing ELF header field: " + label)
        header[label] = match[1]
    if header["Class"] != "ELF64" or not header["Type"].startswith("REL ") or header["Machine"] != "IBM S/390":
        raise ValueError("Unexpected object kind/architecture")
    symbols, relocations, section = [], [], None
    for line in raw.splitlines():
        fields = line.split()
        # Exact final symbol field avoids confusing ___ksymtab_gpl+name with name.
        if len(fields) == 8 and fields[0].endswith(":") and fields[-1] in NAMES:
            symbols.append(dict(zip(("index", "value", "size", "type", "bind", "visibility", "section", "name"), fields)))
        if line.startswith("Relocation section "):
            section = line
        match = re.match(r"^\s*([0-9a-f]+)\s+([0-9a-f]+)\s+(R_\S+)\s+([0-9a-f]+)\s+(\S+)(.*)$", line)
        if match and match[5] in NAMES:
            relocations.append({"relocation_section_header": section, "offset": match[1],
                                "info": match[2], "type": match[3], "symbol_value": match[4],
                                "symbol": match[5], "addend_text": match[6].strip(), "raw": line})
    return {"argv": argv, "returncode": completed.returncode, "header": header,
            "symbols": symbols, "relocations": relocations,
            "scope": "ET_REL symbols and relocation references; no final link, runtime address or instruction semantics"}


def profile_evidence(variant):
    profile, revision = variant + "_s390", VERSIONS[variant]
    build, tree = BASE / profile / "build", BASE / variant / "linux"
    saved = OLD / "profiles" / profile
    ledger, recorded = read(saved / "artifact_binding.json"), read(saved / "result.json")
    consumer = read(HERE.parent / "consumer_preprocessing_20261016" / (profile + ".json"))
    for item in (ledger, recorded, consumer):
        if item["revision"] != revision or item["variant"] != variant or item["arch"] != "s390":
            raise ValueError("Profile/revision disagreement")
    if recorded["cache_build"] != str(build) or consumer["profile"] != profile:
        raise ValueError("Wrong build/profile")
    if recorded["status"] != "CONFIG_BUILD_VERIFIED" or ledger["status"] != "SAVED_ARTIFACTS_VERIFIED":
        raise ValueError("Prior configuration/build status is not verified")
    if (BASE / variant / "source_revision").read_text().strip() != revision:
        raise ValueError("Source revision marker differs")
    relative = [".config", "include/generated/autoconf.h", "arch/s390/kernel/topology.i",
                "arch/s390/kernel/topology.o", "arch/s390/kernel/smp.i", "arch/s390/kernel/smp.o",
                "kernel/sched/core.i", "kernel/sched/core.o"]
    paths = [build / p for p in relative] + [saved / p for p in ("result.json", "commands.json", "kernel.config", "autoconf.h")]
    expected = {row["path"]: row["sha256"] for row in ledger["artifacts"]}
    bound = []
    for path in paths:
        value = sha(path)
        if expected.get(str(path)) != value:
            raise ValueError("Missing/changed registered artifact: " + str(path))
        bound.append({"path": str(path), "sha256": value})
    config = prior.config(build / ".config")
    generated = (build / "include/generated/autoconf.h").read_text()
    required = ("S390", "SMP", "SCHED_TOPOLOGY", "SCHED_SMT", "SCHED_CORE", "HOTPLUG_CPU", "SYSFS")
    if any(config.get(n) != "y" or not re.search(r"^#define CONFIG_" + n + " 1$", generated, re.M) for n in required):
        raise ValueError("Effective configuration differs")
    if config.get("NR_CPUS") != "4" or not re.search(r"^#define CONFIG_NR_CPUS 4$", generated, re.M):
        raise ValueError("Effective NR_CPUS differs")
    commands = [c for c in read(saved / "commands.json") if c["label"] == "targets"]
    if len(commands) != 1 or commands[0]["returncode"] != 0:
        raise ValueError("Missing unique successful target command")
    argv = commands[0]["argv"]
    if "ARCH=s390" not in argv or "O=" + str(build) not in argv or "CROSS_COMPILE=s390x-linux-gnu-" not in argv:
        raise ValueError("Build target command context differs")

    functions, declarations, original = {}, {}, []
    selectors = {
        "arch/s390/kernel/topology.i": {
            "cpu_thread_map": "arch/s390/kernel/topology.c", "update_cpu_masks": "arch/s390/kernel/topology.c",
            "cpu_online": "include/linux/cpumask.h", "cpumask_test_cpu": "include/linux/cpumask.h"},
        "arch/s390/kernel/smp.i": {"smp_start_secondary": "arch/s390/kernel/smp.c"},
    }
    for rel in ("arch/s390/kernel/topology.i", "arch/s390/kernel/smp.i", "kernel/sched/core.i"):
        raw = (build / rel).read_bytes().decode("utf-8")
        declarations[rel] = global_excerpts(raw)
        if rel in selectors:
            functions[rel] = extract_definitions(raw, {n: str(tree / source) for n, source in selectors[rel].items()})
        else:
            getter = consumer["functions"]["cpu_smt_mask"]
            if raw[getter["start_offset"]:getter["end_offset"]] != getter["text"]:
                raise ValueError("Prior getter region differs from bound consumer preprocessing")
            functions[rel] = {"cpu_smt_mask": getter}
    for rel in ("arch/s390/kernel/topology.c", "arch/s390/kernel/smp.c"):
        content = subprocess.run(["git", "-C", str(prior.REPO), "show", revision + ":" + rel],
                                 check=True, capture_output=True).stdout
        if (tree / rel).read_bytes() != content:
            raise ValueError("Selected source differs from original Git object")
        original.append({"revision": revision, "path": rel, "sha256": hashlib.sha256(content).hexdigest(),
                         "cached_source_matches_git": True})
    objects = {rel: object_evidence(build / rel) for rel in (
        "arch/s390/kernel/topology.o", "arch/s390/kernel/smp.o", "kernel/sched/core.o")}
    def symbol(obj, name, defined):
        return [s for s in objects[obj]["symbols"] if s["name"] == name
                and ((s["section"] != "UND") == defined) and s["bind"] == "GLOBAL"]
    def reloc(obj, name):
        return any(r["symbol"] == name for r in objects[obj]["relocations"])
    links = {
        "topology_object_defines_cpu_topology": len(symbol("arch/s390/kernel/topology.o", "cpu_topology", True)) == 1,
        "consumer_object_undefined_cpu_topology": len(symbol("kernel/sched/core.o", "cpu_topology", False)) == 1,
        "consumer_relocates_cpu_topology": reloc("kernel/sched/core.o", "cpu_topology"),
    }
    if variant == "fixed":
        links.update({"startup_defines_cpu_setup_mask": len(symbol("arch/s390/kernel/smp.o", "cpu_setup_mask", True)) == 1,
                      "topology_undefined_cpu_setup_mask": len(symbol("arch/s390/kernel/topology.o", "cpu_setup_mask", False)) == 1,
                      "topology_relocates_cpu_setup_mask": reloc("arch/s390/kernel/topology.o", "cpu_setup_mask")})
    else:
        links["no_selected_object_cpu_setup_mask_symbol"] = not any(s["name"] == "cpu_setup_mask" for o in objects.values() for s in o["symbols"])
    if not all(links.values()):
        raise ValueError("Expected bounded object linkage not established")
    row = {"profile": profile, "variant": variant, "arch": "s390", "revision": revision,
           "status": "configured_regions_and_object_references_collected", "artifact_stage": "original non-instrumented object build",
           "effective_config": {k: config[k] for k in required + ("NR_CPUS", "LOCALVERSION")},
           "selected_artifacts": bound, "prior_target_command": argv,
           "consumer_reference": "../consumer_preprocessing_20261016/" + profile + ".json",
           "functions_by_translation_unit": functions, "global_declaration_excerpts": declarations,
           "original_sources": original, "object_evidence": objects, "object_link_checks": links,
           "final_link_identity": "not_checked", "runtime_address_identity": "unknown",
           "target_iteration_reached": "unknown", "helper_effects_proved": False,
           "content_at_consumption": "unknown", "whole_contract": "insufficient"}
    save(HERE / (profile + ".json"), row)
    print(json.dumps({"profile": profile, "bound_artifacts": len(bound), "object_link_checks": links}, ensure_ascii=False), flush=True)
    return row, config


def main():
    if os.name != "posix":
        raise RuntimeError("Run in WSL against existing registered artifacts")
    rows = [profile_evidence(variant) for variant in ("old", "fixed")]
    old, fixed = [c for _, c in rows]
    differences = {k: [old.get(k), fixed.get(k)] for k in sorted(set(old) | set(fixed)) if old.get(k) != fixed.get(k)}
    if set(differences) != {"LOCALVERSION"}:
        raise ValueError("Unexpected configuration difference")
    summary = {"date": "2026-10-17", "status": "bounded_configuration_and_object_binding_completed",
               "case_scope": "one already-read development case", "profiles": [r["profile"] for r, _ in rows],
               "selected_bound_artifacts": sum(len(r["selected_artifacts"]) for r, _ in rows),
               "configuration_differences": differences,
               "object_link_checks": {r["profile"]: r["object_link_checks"] for r, _ in rows},
               "final_link_identity": "not_checked", "runtime_content": "unknown", "whole_contract": "insufficient",
               "new_model_requests": 0, "new_builds": 0, "new_kernel_runs": 0, "new_defects": 0,
               "independent_positive_cases": 0, "independent_normal_cases": 0, "r3_resumed": False}
    save(HERE / "results.json", summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        save(HERE / "failure.json", {"status": "incomplete", "error_type": type(error).__name__, "error": str(error)})
        raise
