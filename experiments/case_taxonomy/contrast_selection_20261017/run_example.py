"""Metadata-only replay of four known profiles; never opens boot/event results."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from linux_bug_analyze.contrast_selection import (
    SCHEMA, contract_binding, metadata_sha256, profile_binding, select_contrasts,
)

SOURCE = ROOT / "experiments/case_taxonomy/s390_arch_contract_20261013"
SEED = "N2-finite-pool-20261017-v1"
REQUIRED = {"CONFIG_64BIT": "y", "CONFIG_SMP": "y", "CONFIG_SCHED_SMT": "y",
            "CONFIG_SCHED_CORE": "y", "CONFIG_HOTPLUG_CPU": "y", "CONFIG_SYSFS": "y",
            "CONFIG_NR_CPUS": "4"}
# Explicit manual normalization of already-reviewed provider behavior. Neither
# source inference nor unknown-case validation is performed by this example.
PROFILES = [
    ("P01", "old_s390", "s390", "online_set", "after_shared_notify"),
    ("P02", "fixed_s390", "s390", "setup_set", "before_shared_notify"),
    ("P03", "old_x86", "x86_64", "setup_set", "before_shared_notify"),
    ("P04", "fixed_x86", "x86_64", "setup_set", "before_shared_notify"),
]


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(path):
    return str(path.relative_to(ROOT)).replace("\\", "/")


def reviewed(binding, references):
    return {"status": "reviewed", "origin": "researcher_review", "binding_sha256": binding,
            "references": references}


def option(argv, key):
    return argv[argv.index(key) + 1]


def main():
    protocol = HERE / "protocol_pre.json"
    assert protocol.is_file(), "pre-registration must precede example collection"
    consumer = {"interface": "kernel/sched/core.c", "operation": "sched_core_lock:pre_irq_disable_content_sample",
                "stage": "CPUHP_AP_SCHED_STARTING", "object_role": "secondary_cpu_smt_mask"}
    execution = {"cpu_count": 2, "memory_mib": 512, "accelerator": "tcg", "network": "none",
                 "target_cpu": 1, "scenario": "initial_secondary_cpu_startup",
                 "hardware_smt_claim": False}
    contract = {"schema": SCHEMA, "id": "known_initial_topology_preparation",
                "purpose": "common_scheduler_initial_mask_readiness", "consumer": consumer,
                "execution": execution, "required_config": REQUIRED,
                "contrast_features": ["qualification_domain", "preparation_phase"]}
    protocol_refs = [ref(SOURCE / "protocol_pre.md"), ref(SOURCE / "runtime/protocol_pre.md")]
    contract["review"] = reviewed(contract_binding(contract), protocol_refs)
    provenance = {"schema": "known_profile_metadata_provenance_v1",
                  "development_material": True, "independent_sample": False,
                  "protocol_sha256": digest(protocol), "inputs": [], "profiles": [],
                  "manual_semantic_inputs": ["common purpose and consumer equivalence", "legality of ordinary SMP profile",
                                             "setup_set/online_set normalization", "before/after shared notify",
                                             "feature priority", "CPU-model differences acceptable only for this narrow purpose"],
                  "limits": ["No runtime/event/result/model response files are opened", "Archived build metadata is not a live image-existence or bootability check",
                             "Pre-IRQ sample is not exact loop-content consumption or interval stability",
                             "Machine, CPU model and console differ across architecture; abstract execution equivalence is manually approved for this narrow scenario",
                             "Metadata hash and assistant review are not human-expert semantic authority", "This is a known-case development replay, not blinded selection gain"]}
    profiles = []
    for pid, folder, architecture, qualification, phase in PROFILES:
        base = SOURCE / "runtime/profiles" / folder
        paths = {name: base / name for name in ["kernel.config", "autoconf.h", "build.json", "commands.json"]}
        build = json.loads(paths["build.json"].read_text(encoding="utf-8"))
        commands = json.loads(paths["commands.json"].read_text(encoding="utf-8"))
        cfg = dict(re.findall(r"^(CONFIG_[A-Za-z0-9_]+)=(.+)$", paths["kernel.config"].read_text(encoding="utf-8"), re.M))
        autoconf = dict(re.findall(r"^#define (CONFIG_[A-Za-z0-9_]+) (.+)$", paths["autoconf.h"].read_text(encoding="utf-8"), re.M))
        required = dict(REQUIRED)
        required["CONFIG_S390" if architecture == "s390" else "CONFIG_X86_64"] = "y"
        if architecture == "s390": required["CONFIG_SCHED_TOPOLOGY"] = "y"
        values = {}
        for key, expected in required.items():
            assert cfg.get(key) == expected, (pid, key, "effective config mismatch")
            assert autoconf.get(key) == ("1" if expected == "y" else expected), (pid, key, "autoconf mismatch")
            values[key] = cfg[key]
        assert build["status"] == "READY" and build["config_sha256"] == digest(paths["kernel.config"])
        assert build["source_instrumented"] is True
        # Only argv is projected from launch ledger; no exit, time, boot state,
        # stderr, stdout, events or later acceptance results influence selection.
        launch = [x["argv"] for x in commands if x.get("name") == "qemu_boot"]
        assert len(launch) == 1
        argv = launch[0]
        assert option(argv, "-accel") == "tcg" and option(argv, "-m") == "512"
        assert option(argv, "-smp").split(",", 1)[0] == "2" and option(argv, "-nic") == "none"
        evidence_refs = [ref(paths["kernel.config"]), ref(paths["autoconf.h"]), ref(paths["build.json"]), *protocol_refs]
        p = {"id": pid, "revision": build["revision"], "architecture": architecture,
             "purpose": contract["purpose"], "consumer": dict(consumer), "execution": dict(execution),
             "configuration": {"sha256": digest(paths["kernel.config"]), "autoconf_sha256": digest(paths["autoconf.h"]),
                               "values": values, "facts_sha256": metadata_sha256(values), "verification": "config_and_autoconf_verified"},
             "availability": {"build_status": "archived_built", "build_record_sha256": digest(paths["build.json"]),
                              "image_sha256": build["image_sha256"], "adapter": "R4_lock_snapshot_observer",
                              "adapter_stage": consumer["stage"], "references": protocol_refs + [ref(paths["build.json"])]},
             "legality": "legal", "provider": {"signature": "arch/s390/kernel/{smp,topology}.c" if architecture == "s390" else "arch/x86/kernel/smpboot.c",
                                                "features": {"qualification_domain": qualification, "preparation_phase": phase},
                                                "references": protocol_refs}, "cost": 1}
        p["review"] = reviewed(profile_binding(p), evidence_refs)
        profiles.append(p)
        provenance["profiles"].append({"id": pid, "source_directory": ref(base), "revision": build["revision"],
                                      "actual_values": values, "launch_arguments": {"smp": option(argv, "-smp"),
                                      "memory_mib": option(argv, "-m"), "machine": option(argv, "-machine"), "cpu": option(argv, "-cpu")},
                                      "semantic_review_scope": "assistant-authored replay of already-read source/protocol; not an independent expert adjudication"})
        provenance["inputs"].extend({"path": ref(path), "sha256": digest(path)} for path in paths.values())
    for path in [SOURCE / "protocol_pre.md", SOURCE / "runtime/protocol_pre.md"]:
        provenance["inputs"].append({"path": ref(path), "sha256": digest(path)})
    pool = {"contract": contract, "profiles": profiles,
            "options": {"max_pairs": 1, "max_cost": 2, "seed": SEED}}
    save("example_pool.json", pool)
    save("example_provenance.json", provenance)
    result = select_contrasts(contract, profiles, **pool["options"])
    save("selection.json", result)
    save("selection_receipt.json", {"pool_sha256": digest(HERE / "example_pool.json"),
                                   "selection_sha256": digest(HERE / "selection.json"),
                                   "outcome_files_read_before_save": 0, "new_api_calls": 0, "new_builds": 0, "new_runs": 0})
    print(json.dumps({"status": result["status"], "profiles": len(profiles), "selected": result["pairs"],
                      "pair_exclusions": [{"left": x["left"], "right": x["right"], "reasons": x["reasons"]}
                                          for x in result["pair_decisions"] if x["status"] != "selected"]}))


if __name__ == "__main__":
    main()
