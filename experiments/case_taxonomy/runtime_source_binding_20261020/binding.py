"""Four archived runs: reviewed direct-source candidates, never effective TU facts.

This finite, versioned summary checks exact files/short bodies and configuration.
It does not execute CPP, expand includes, infer arbitrary macro semantics or
promote a source candidate into the observed runtime provider origin.
"""
from copy import deepcopy
import hashlib
import re

OLD = "555a0ce4558d87d5b97c4321f34b19e051c7b0c1"
FIXED = "2c4dcd7fd57b20a21b65da04d89c38a7217d79cf"
PUBLIC, X86, S390, DRIVER = "include/linux/topology.h", "arch/x86/include/asm/topology.h", "arch/s390/include/asm/topology.h", "drivers/base/topology.c"
PROFILES = {"old_x86_64": (OLD, "x86_64"), "fixed_x86_64": (FIXED, "x86_64"), "old_s390": (OLD, "s390"), "fixed_s390": (FIXED, "s390")}
REVIEW_ID = "reviewed-die-direct-source-candidates-v1"
# These are the finite complete files reviewed in source_review.md, not a rule
# that arbitrary architecture-header definitions are native implementations.
REVIEWED_BLOBS = {
    OLD: {PUBLIC: "0b3704ad13c8861fab27eea7c863f9b3f69ffdbf", X86: "cc164777e66193f45581c3fa775588dae3bfabc5", S390: "3a0ac0c7a9a39b030e316f7074e38793146b93ed", DRIVER: "8f2b641d0b8cce447ac4b6706785adc37b8ca6c8"},
    FIXED: {PUBLIC: "8d1bdae762300634e5e4c5309bc63c046210df0b", X86: "cc164777e66193f45581c3fa775588dae3bfabc5", S390: "3a0ac0c7a9a39b030e316f7074e38793146b93ed", DRIVER: "f079a55793ec8b630aa147bbf91814af2d1d1784"},
}
SHORT_BODIES = {
    "native_id": "#define topology_die_id(cpu) (cpu_data(cpu).cpu_die_id)",
    "native_mask": "#define topology_die_cpumask(cpu) (per_cpu(cpu_die_map, cpu))",
    "fallback_id": "#define topology_die_id(cpu) ((void)(cpu), -1)",
    "fallback_mask": "#define topology_die_cpumask(cpu) cpumask_of(cpu)",
}


class Insufficient(ValueError): pass
def need(condition, reason):
    if not condition: raise Insufficient(reason)
def sha(text): return hashlib.sha256(text.encode("utf-8")).hexdigest()
def git_blob(text):
    raw = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
def normalized(text): return re.sub(r"\s+", "", text)


def _config(text, key):
    yes = [line.split("=", 1)[1] for line in text.splitlines() if line.startswith(key + "=")]
    no = [line for line in text.splitlines() if line == "# " + key + " is not set"]
    need(len(yes) + len(no) <= 1, "ambiguous_config_key:" + key)
    if no: return False
    if not yes: return None
    if key == "CONFIG_NR_CPUS":
        need(re.fullmatch(r"[1-9]\d*", yes[0]) is not None, "unsupported_nr_cpus")
        return int(yes[0])
    need(yes[0] in {"y", "n"}, "unsupported_boolean_config:" + key)
    return yes[0] == "y"


def _autoconf(text, key):
    definitions = re.findall(r"(?m)^#define\s+" + re.escape(key) + r"(?:[ \t]+([^\r\n]+))?[ \t]*$", text)
    undefs = re.findall(r"(?m)^#undef\s+" + re.escape(key) + r"\b", text)
    need(len(definitions) <= 1 and not undefs, "ambiguous_autoconf_key:" + key)
    return definitions[0].strip() if definitions else None


def _identity(profile, build, boot):
    """Same bounded archived identity checks as N2.15, without importing a runner."""
    revision, arch = PROFILES[profile]
    need(isinstance(build, dict) and isinstance(boot, dict), "build_or_boot_missing")
    need(build.get("status") == "READY" and build.get("source_c_modified") is False, "not_ready_original_source_build")
    need(build.get("profile") == boot.get("profile") == profile, "profile_mismatch")
    need(build.get("revision") == boot.get("revision") == revision and build.get("arch") == boot.get("arch") == arch, "revision_or_arch_mismatch")
    for key in ("release", "image_sha256", "init_source_sha256", "init_binary_sha256", "initrd_sha256"):
        need(isinstance(build.get(key), str) and bool(build[key]) and boot.get(key) == build[key], "boot_build_identity_mismatch:" + key)
    receipt = boot.get("qemu_receipt")
    need(isinstance(receipt, dict) and receipt.get("status") == "finished" and type(receipt.get("exit_code")) is int and receipt["exit_code"] == 0
         and type(receipt.get("attempt")) is int and receipt["attempt"] == 1, "boot_receipt_incomplete")
    archive = "/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/die_arch_contract_20261013/runtime/profiles/" + profile
    need(receipt.get("stdout") == archive + "/qemu_boot.stdout.log" and receipt.get("stderr") == archive + "/qemu_boot.stderr.log", "boot_archive_profile_mismatch")
    argv = boot.get("qemu_argv")
    need(isinstance(argv, list) and all(isinstance(arg, str) for arg in argv) and receipt.get("argv") == argv, "boot_argv_mismatch")
    for option, key in (("-kernel", "image"), ("-initrd", "initrd")):
        need(argv.count(option) == 1 and argv.index(option) + 1 < len(argv) and argv[argv.index(option) + 1] == build.get(key), "boot_image_argument_mismatch")
    need(argv.count("-append") == 1 and argv.index("-append") + 1 < len(argv), "boot_cmdline_missing")
    need([v for v in argv[argv.index("-append") + 1].split() if v.startswith("die_case=")] == ["die_case=" + profile], "boot_case_mismatch")
    events = boot.get("observations", {}).get("events")
    need(isinstance(events, list) and all(isinstance(event, dict) for event in events), "boot_events_missing")
    uname = [event for event in events if event.get("event") == "uname"]
    command = [event for event in events if event.get("event") == "file_read" and event.get("path") == "/proc/cmdline"]
    need(len(uname) == len(command) == 1, "boot_identity_event_ambiguous")
    need(uname[0].get("release") == build["release"] and uname[0].get("machine") == ("s390x" if arch == "s390" else "x86_64"), "boot_uname_mismatch")
    need(isinstance(command[0].get("raw"), str) and [v for v in command[0]["raw"].split() if v.startswith("die_case=")] == ["die_case=" + profile], "observed_case_mismatch")


def _reference(source, start, end=None):
    end = start if end is None else end
    lines = source["text"].splitlines()
    need(1 <= start <= end <= len(lines), "reviewed_source_range_missing")
    return {"path": source["path"], "revision": source["revision"], "git_blob": source["git_blob"], "sha256": source["sha256"],
            "start_line": start, "end_line": end, "text": "\n".join(lines[start - 1:end])}


def _line(source, number, expected):
    ref = _reference(source, number)
    need(normalized(ref["text"]) == normalized(expected), "reviewed_short_body_or_guard_changed:" + source["path"] + ":" + str(number))
    return ref


def bind_run(profile, build, boot, config_text, autoconf_text, packet):
    result = {"status": "insufficient", "profile": profile,
              "source_candidate": {"id_native": None, "mask_native": None, "conditional": True, "origin": "researcher_review", "review_id": REVIEW_ID, "origins": {}},
              "runtime_facts": {"id_native": None, "mask_native": None, "provider_binding": "unknown"},
              "unknowns": ["runtime_TU_closure", "forced_and_transitive_include_effects", "hardware_topology_truth",
                           "actual_first_content_consumption_deadline", "whole_path_and_stability", "historical_ABI_normative_verdict"],
              "no_physical_truth": True, "historical_normative_verdict": "insufficient", "policy_modified": False}
    try:
        need(profile in PROFILES, "unsupported_profile")
        _identity(profile, build, boot)
        need(isinstance(config_text, str) and isinstance(autoconf_text, str) and isinstance(packet, dict), "configuration_or_source_packet_missing")
        need(packet.get("runtime_effective_macro_closure_proved") is False, "packet_scope_is_not_conditional_source_only")
        run = packet.get("runs", {}).get(profile)
        need(isinstance(run, dict), "run_not_in_source_packet")
        revision, arch = PROFILES[profile]
        need(run.get("revision") == revision and run.get("arch") == arch, "packet_run_identity_mismatch")
        need(sha(config_text) == build.get("config_sha256") == run.get("config_sha256") and run.get("cached_config_matches_archive") is True, "configuration_digest_mismatch")
        need(sha(autoconf_text) == run.get("archived_autoconf_sha256") and run.get("cached_autoconf_matches_archive") is True, "autoconf_digest_mismatch")
        values = {key: _config(config_text, key) for key in ("CONFIG_SMP", "CONFIG_SYSFS", "CONFIG_X86_64", "CONFIG_S390", "CONFIG_NR_CPUS")}
        for key, value in values.items():
            actual = _autoconf(autoconf_text, key)
            expected = str(value) if type(value) is int else "1" if value is True else None
            need(actual == expected, "config_autoconf_disagree:" + key)
        selected_arch = "CONFIG_S390" if arch == "s390" else "CONFIG_X86_64"
        other_arch = "CONFIG_X86_64" if arch == "s390" else "CONFIG_S390"
        need(values[selected_arch] is True and values[other_arch] is not True, "selected_architecture_not_established")
        need(values["CONFIG_SMP"] is True and values["CONFIG_SYSFS"] is True and values["CONFIG_NR_CPUS"] == 4, "outside_reviewed_runtime_guard_scope")
        for key in ("CONFIG_SMP", "CONFIG_SYSFS", selected_arch, "CONFIG_NR_CPUS"):
            expected = "y" if values[key] is True else str(values[key])
            need(build.get("effective_configuration", {}).get(key) == expected, "build_effective_configuration_disagrees:" + key)
        paths = set(REVIEWED_BLOBS[revision])
        keys = run.get("source_keys")
        need(isinstance(keys, list) and len(keys) == len(set(keys)) == 4 and set(keys) == {revision + ":" + path for path in paths}, "source_key_set_mismatch")
        sources = {}
        identities = build.get("source_identity")
        need(isinstance(identities, list) and all(isinstance(row, dict) for row in identities), "build_source_identity_missing")
        for path in paths:
            source = packet.get("sources", {}).get(revision + ":" + path)
            need(isinstance(source, dict) and source.get("revision") == revision and source.get("path") == path and source.get("whole_direct_file") is True and isinstance(source.get("text"), str), "source_record_identity_mismatch:" + path)
            raw = source["text"]
            need(sha(raw) == source.get("sha256") and git_blob(raw) == source.get("git_blob"), "source_content_digest_mismatch:" + path)
            need(source["git_blob"] == REVIEWED_BLOBS[revision][path], "outside_reviewed_whole_file_summary:" + path)
            need(source.get("cached_path") == build.get("source_tree", "") + "/" + path, "cached_source_tree_mismatch:" + path)
            rows = [row for row in identities if row.get("path") == path]
            need(len(rows) == 1 and rows[0].get("matches") is True and rows[0].get("git_blob") == source["git_blob"], "archived_build_blob_mismatch:" + path)
            sources[path] = source
        public, x86, s390, driver = (sources[path] for path in (PUBLIC, X86, S390, DRIVER))
        _line(public, 27, "#ifndef _LINUX_TOPOLOGY_H"); _line(public, 28, "#define _LINUX_TOPOLOGY_H")
        include = _line(public, 36, "#include <asm/topology.h>")
        _line(driver, 15, "#include <linux/topology.h>")
        id_line, mask_line = (187, 205) if revision == OLD else (191, 209)
        fallback_id = _line(public, id_line, SHORT_BODIES["fallback_id"])
        fallback_mask = _line(public, mask_line, SHORT_BODIES["fallback_mask"])
        _line(public, id_line - 1, "#ifndef topology_die_id"); _line(public, id_line + 1, "#endif")
        _line(public, mask_line - 1, "#ifndef topology_die_cpumask"); _line(public, mask_line + 1, "#endif")
        need(not re.search(r"(?m)^\s*#\s*(?:define|undef)\s+topology_die_(?:id|cpumask)\b", s390["text"]), "s390_has_unreviewed_direct_definition")
        _line(s390, 2, "#ifndef _ASM_S390_TOPOLOGY_H"); _line(s390, 3, "#define _ASM_S390_TOPOLOGY_H")
        _line(x86, 25, "#ifndef _ASM_X86_TOPOLOGY_H"); _line(x86, 26, "#define _ASM_X86_TOPOLOGY_H")
        native_id = _line(x86, 111, SHORT_BODIES["native_id"])
        native_mask = _line(x86, 118, SHORT_BODIES["native_mask"])
        _line(x86, 116, "#ifdef CONFIG_SMP"); _line(x86, 157, "#endif")
        if revision == FIXED:
            _line(public, 183, "#if defined(topology_die_id) && defined(topology_die_cpumask)")
            _line(public, 184, "#define TOPOLOGY_DIE_SYSFS"); _line(public, 185, "#endif")
        native = arch == "x86_64"
        origins = {
            "id": {"classification": "direct_architecture_candidate" if native else "public_fallback_if_undefined_candidate",
                   "body": native_id if native else fallback_id, "guard_refs": [_reference(x86, 25, 26)] if native else [_reference(s390, 1, len(s390["text"].splitlines())), _reference(public, id_line - 1, id_line + 1)]},
            "mask": {"classification": "direct_architecture_candidate" if native else "public_fallback_if_undefined_candidate",
                     "body": native_mask if native else fallback_mask, "guard_refs": [_reference(x86, 116, 157)] if native else [_reference(s390, 1, len(s390["text"].splitlines())), _reference(public, mask_line - 1, mask_line + 1)]},
        }
        result["source_candidate"].update(id_native=native, mask_native=native, origins=origins,
             conditions=["reviewed_header_loaded_under_normal_file_guard", "unexpanded_includes_do_not_override_related_macros_or_configuration", "no_prior_guard_interference", "no_unseen_later_macro_override"],
             public_arch_include=include, fallback_refs=[fallback_id, fallback_mask],
             configuration={"sha256": sha(config_text), "autoconf_sha256": sha(autoconf_text), "values": values,
                            "independent_historical_autoconf_digest": run.get("autoconf_independent_historical_digest")},
             source_keys=list(keys), source_scope="four reviewed complete direct files; not runtime effective preprocessing")
        result["status"] = "source_candidate_supported"
    except (Insufficient, KeyError, ValueError, TypeError, AttributeError) as exc:
        result["unknowns"].append(str(exc))
    return result
