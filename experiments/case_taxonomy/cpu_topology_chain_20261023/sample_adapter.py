"""Known-case archive integration; no new semantic or runtime proof engine.

The caller supplies externally reviewed contract premises.  This adapter binds
their documents and sampled values to one of four reviewed archived runs, then
delegates the relation to the unchanged contract evaluator.  It never consults
old observation verdicts, predicates or warning text as answers.
"""
from __future__ import annotations

import hashlib
import json
import re

from linux_bug_analyze.contract_protocol import evaluate_contract


REVISIONS = {"old": "88b604263f3d6eedae0b1c2c3bbd602d1e2e8775",
             "fixed": "a052096bdd6809eeab809202726634d1ac975aa1"}
PROFILES = {variant + "_" + arch: (revision, arch)
            for variant, revision in REVISIONS.items() for arch in ("s390", "x86")}
COMMON = ("64BIT", "SMP", "SCHED_SMT", "SCHED_CORE", "HOTPLUG_CPU", "SYSFS")
SOURCE_PATHS = {"kernel/cpu.c", "kernel/sched/core.c", "include/linux/r4_observe.h",
                "arch/s390/kernel/smp.c", "arch/s390/kernel/topology.c", "arch/x86/kernel/smpboot.c"}
SHA = re.compile(r"[a-f0-9]{64}\Z")
REQUIRED_ARTIFACTS = {"build", "boot", "config", "autoconf", "log", "source_manifest"}


class BindingError(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise BindingError(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(raw):
    return json.loads(raw.decode("utf-8-sig"))


def _setting(text, key):
    yes = re.findall(r"(?m)^" + re.escape(key) + r"=([^\r\n]*)\r?$", text)
    no = re.findall(r"(?m)^# " + re.escape(key) + r" is not set\r?$", text)
    need(len(yes) + len(no) == 1, "configuration_key_missing_or_ambiguous:" + key)
    return "n" if no else yes[0]


def _option(argv, option):
    need(argv.count(option) == 1 and argv.index(option) + 1 < len(argv), "boot_option_ambiguous:" + option)
    return argv[argv.index(option) + 1]


def _sample(log, selected):
    need(isinstance(selected, dict) and type(selected.get("cpu")) is int and selected["cpu"] == 1
         and selected.get("phase") == "lock_snapshot" and type(selected.get("line")) is int
         and type(selected.get("seq")) is int and selected["seq"] > 0, "unsupported_sample_identity")
    rows = []
    for line_number, line in enumerate(log.splitlines(), 1):
        match = re.search(r"\bR4 phase=lock_snapshot (.*)$", line)
        if not match:
            continue
        values = {}
        for token in match[1].split():
            pair = re.fullmatch(r"([a-z_]+)=([0-9a-f]+)", token)
            need(pair is not None and pair[1] not in values, "malformed_or_duplicate_sample_field")
            values[pair[1]] = int(pair[2], 16 if pair[1] == "mask" else 10)
        need(set(values) == {"cpu", "current", "seq", "mask", "self", "weight", "locks", "rq_self", "online", "printed_after_unlock"},
             "unsupported_sample_field_set")
        if values["cpu"] == selected["cpu"]:
            rows.append(dict(values, line=line_number))
    need(len(rows) == 1, "target_sample_missing_or_ambiguous")
    sample = rows[0]
    need(sample["line"] == selected["line"] and sample["seq"] == selected["seq"]
         and sample["current"] == selected["cpu"], "sample_line_sequence_or_cpu_mismatch")
    need(0 <= sample["mask"] < 16 and sample["self"] == int(bool(sample["mask"] & (1 << sample["cpu"])))
         and sample["weight"] == sample["mask"].bit_count() and sample["locks"] >= 0
         and sample["online"] in (0, 1) and sample["printed_after_unlock"] == 1, "inconsistent_sample_fields")
    return sample


def evaluate_bound_sample(contract, ledger, record, binding, artifacts):
    """Verify supplied bytes/identity and evaluate only a separate sample.

    ``binding`` has profile/revision/arch/context_id/image_sha256/initrd_sha256,
    ``artifact_sha256`` (the complete key-to-digest map), and ``sample`` with
    cpu=1, phase=lock_snapshot, one-based raw-log line and sequence.  Artifacts
    are key-to-bytes: build/boot/config/autoconf/log/source_manifest plus each
    source:<manifest path>; additional reviewed documents may be registered.

    Every ledger document must name its artifact_key, actual sha256 and line
    bounds. Required observed facts are members and target_cpu; selected_path,
    online and lock_count are the only additional recognized fact names.
    No semantic claim is generated or approved here.  Image hashes are linked
    through archived receipts only, never freshly certified against an ELF.
    """
    result = {"status": "insufficient", "binding_status": "insufficient", "evaluation": {
                  "applicability": "insufficient", "relation_at_observation": "insufficient",
                  "relation_at_deadline": "insufficient", "whole_path": "insufficient"},
              "reasons": [], "case_specific_integration": True,
              "provider_preparation_effect_proved": False, "physical_lock_object_proved": False,
              "exact_consumption_value_proved": False, "continuous_stability_proved": False,
              "fresh_image_certification": False, "automatic_contract_derivation": False}
    try:
        need(all(isinstance(item, dict) for item in (contract, ledger, record, binding, artifacts)), "malformed_input_envelope")
        profile = binding.get("profile")
        need(profile in PROFILES, "unsupported_profile")
        revision, arch = PROFILES[profile]
        need(binding.get("revision") == revision and binding.get("arch") == arch, "profile_revision_or_arch_mismatch")
        expected = binding.get("artifact_sha256")
        need(isinstance(expected, dict) and set(expected) == set(artifacts)
             and REQUIRED_ARTIFACTS <= set(expected), "artifact_registry_incomplete")
        for key, raw in artifacts.items():
            need(isinstance(raw, bytes) and isinstance(expected[key], str) and SHA.fullmatch(expected[key])
                 and digest(raw) == expected[key], "artifact_digest_mismatch:" + str(key))
        build, boot, manifest = (_json(artifacts[key]) for key in ("build", "boot", "source_manifest"))
        need(isinstance(build, dict) and isinstance(boot, dict) and isinstance(manifest, dict), "malformed_archive_metadata")
        need(build.get("status") == "READY" and build.get("source_instrumented") is True
             and build.get("profile") == boot.get("profile") == profile
             and build.get("revision") == manifest.get("revision") == revision
             and build.get("arch") == arch and build.get("variant") == profile.split("_", 1)[0], "build_boot_or_source_identity_mismatch")
        for key in ("image_sha256", "initrd_sha256"):
            need(isinstance(binding.get(key), str) and SHA.fullmatch(binding[key]) and binding[key] == build.get(key),
                 "archived_image_binding_mismatch:" + key)
        need(build.get("config_sha256") == expected["config"], "configuration_digest_mismatch")
        config, autoconf, log = (artifacts[key].decode("utf-8-sig") for key in ("config", "autoconf", "log"))
        required = COMMON + (("S390", "SCHED_TOPOLOGY") if arch == "s390" else ("X86_64",))
        for key in required + ("NR_CPUS",):
            value = "4" if key == "NR_CPUS" else "y"
            need(_setting(config, "CONFIG_" + key) == value, "outside_reviewed_configuration:" + key)
            generated = re.findall(r"(?m)^#define CONFIG_" + key + r" ([^\r\n]*)\r?$", autoconf)
            need(generated == ["4" if key == "NR_CPUS" else "1"], "configuration_autoconf_mismatch:" + key)
        receipt = boot.get("receipt")
        need(isinstance(receipt, dict) and receipt.get("name") == "qemu_boot" and receipt.get("state") == "finished"
             and type(receipt.get("attempt")) is int and receipt["attempt"] == 1
             and type(receipt.get("exit_code")) is int and receipt["exit_code"] == 0, "boot_receipt_incomplete")
        archive = "/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/s390_arch_contract_20261013/runtime/profiles/" + profile
        need(receipt.get("stdout") == archive + "/qemu_boot.stdout.log" and receipt.get("stderr") == archive + "/qemu_boot.stderr.log", "boot_log_profile_mismatch")
        argv = receipt.get("argv")
        need(isinstance(argv, list) and argv and all(isinstance(arg, str) for arg in argv)
             and argv[0] == ("qemu-system-s390x" if arch == "s390" else "qemu-system-x86_64"), "boot_argv_arch_mismatch")
        need(_option(argv, "-kernel") == build.get("image") and _option(argv, "-initrd") == build.get("initrd"), "boot_image_argument_mismatch")
        cmdline = _option(argv, "-append")
        need([item for item in cmdline.split() if item.startswith("r4_case=")] == ["r4_case=" + profile], "boot_case_mismatch")
        identities = re.findall(r"(?m)^.*\bR4_USER release=(\S+) machine=(\S+) pid=(\d+)\s*$", log)
        need(identities == [(build.get("release"), "s390x" if arch == "s390" else "x86_64", "1")], "observed_run_identity_mismatch")
        observed_cmdline = re.findall(r"(?m)^.*\bR4_USER field=cmdline value=([^\r\n]*)\r?$", log)
        need(len(observed_cmdline) == 1 and observed_cmdline[0].strip() == cmdline.strip(), "observed_command_line_mismatch")
        files = manifest.get("files")
        need(isinstance(files, list) and all(isinstance(item, dict) for item in files)
             and len(files) == len(SOURCE_PATHS) and {item.get("path") for item in files} == SOURCE_PATHS, "source_manifest_scope_mismatch")
        for item in files:
            key = "source:" + item["path"]
            need(key in expected and item.get("observed_sha256") == expected[key], "observed_source_digest_mismatch:" + key)
        context = binding.get("context_id")
        need(isinstance(context, str) and bool(context) and context == ledger.get("context_id") == record.get("context_id"), "record_context_mismatch")
        need(contract.get("revision") == ledger.get("revision") == record.get("revision") == revision
             and ledger.get("basis") == record.get("basis") == "archived_runtime", "record_revision_or_basis_mismatch")
        need(record.get("sample_kind") == "sample"
             and record.get("sample_event") == context + ".pre_irq_disable_sample"
             and record.get("deadline_event") == context + ".mask_content_iteration", "sample_promoted_or_relabelled")
        documents = ledger.get("documents")
        need(isinstance(documents, dict) and documents, "ledger_documents_missing")
        for doc in documents.values():
            need(isinstance(doc, dict) and doc.get("artifact_key") in artifacts, "ledger_document_artifact_missing")
            key = doc["artifact_key"]
            lines = artifacts[key].decode("utf-8-sig").splitlines()
            need(doc.get("sha256") == expected[key] and doc.get("context_revision") == revision,
                 "ledger_document_digest_or_revision_mismatch")
            need(type(doc.get("start_line")) is int and type(doc.get("end_line")) is int
                 and 1 <= doc["start_line"] <= doc["end_line"] <= len(lines), "ledger_document_lines_outside_actual_bytes")
        if "semantic_review_sha256" in binding:
            need(binding["semantic_review_sha256"] == expected.get("semantic_review"), "semantic_review_digest_mismatch")
        observed = _sample(log, binding.get("sample"))
        facts = record.get("facts")
        need(isinstance(facts, dict) and {"members", "target_cpu"} <= set(facts)
             and set(facts) <= {"members", "target_cpu", "selected_path", "online", "lock_count"}, "sample_fact_set_missing_or_unsupported")
        members = [cpu for cpu in range(4) if observed["mask"] & (1 << cpu)]
        raw_members = facts["members"].get("value")
        need(isinstance(raw_members, list) and all(type(cpu) is int for cpu in raw_members)
             and len(raw_members) == len(set(raw_members)) and set(raw_members) == set(members), "sample_members_disagree_with_raw_log")
        need(type(facts["target_cpu"].get("value")) is int and facts["target_cpu"]["value"] == observed["cpu"], "sample_target_cpu_mismatch")
        for key, value in (("selected_path", True), ("online", bool(observed["online"])), ("lock_count", observed["locks"])):
            if key in facts:
                need(type(facts[key].get("value")) is type(value) and facts[key]["value"] == value, "sample_fact_mismatch:" + key)
        result.update(binding_status="bound", sample=observed,
                      artifact_sha256=dict(expected), source_scope="archived_observer_source_and_receipt_only")
        result["evaluation"] = evaluate_contract(contract, ledger, record)
        result["status"] = result["evaluation"]["relation_at_observation"]
    except (BindingError, ValueError, TypeError, KeyError, AttributeError, UnicodeError) as exc:
        result["reasons"].append(str(exc))
    return result
