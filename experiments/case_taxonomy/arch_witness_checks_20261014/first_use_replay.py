"""Researcher-defined narrow first-use replay, not a model or unseen detector.

Read archived evidence only. Never import the historical boot runner, read its
observations as an oracle, open a key, start a kernel, or send a request.
"""
from pathlib import Path
import hashlib
import json
import re


HERE = Path(__file__).resolve().parent
R4 = HERE.parent / "s390_arch_contract_20261013" / "runtime"
PROFILES = ("old_s390", "fixed_s390", "old_x86", "fixed_x86")
PHASES = (
    "arch_before_notify", "notify_enter", "cpuhp_before", "core_enter",
    "lock_snapshot", "core_exit", "cpuhp_after", "notify_exit", "arch_after_notify",
)
COMMON = ("64BIT", "SMP", "SCHED_SMT", "SCHED_CORE", "HOTPLUG_CPU", "SYSFS")
INPUTS = {}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    data = path.read_bytes()
    INPUTS[str(path.relative_to(HERE.parent))] = digest(data)
    return data.decode("utf-8-sig")


def configuration(raw):
    values = dict(re.findall(r"^(CONFIG_\w+)=(.*)$", raw, re.M))
    values.update({name: "n" for name in re.findall(
        r"^# (CONFIG_\w+) is not set$", raw, re.M)})
    return values


def cpu_list(value):
    """Kernel *_list is decimal CPU indices/ranges, never a hex bitmap."""
    members = set()
    if not value.strip():
        raise ValueError("empty CPU list")
    for part in value.strip().split(","):
        if not re.fullmatch(r"\d+(?:-\d+)?", part):
            raise ValueError("bad CPU list")
        ends = [int(x) for x in part.split("-")]
        lo, hi = (ends[0], ends[-1])
        if not 0 <= lo <= hi < 4:
            raise ValueError("CPU list outside NR_CPUS=4")
        members.update(range(lo, hi + 1))
    return members


def function(text, signature):
    """Bound one known archived C function, not a general C parser."""
    start = text.index(signature)
    opening = text.index("{", start)
    level = 1
    pos = opening + 1
    while level and pos < len(text):
        level += (text[pos] == "{") - (text[pos] == "}")
        pos += 1
    if level:
        raise ValueError("unterminated archived function")
    return text[start:pos]


def in_order(text, tokens):
    offset = 0
    for token in tokens:
        at = text.find(token, offset)
        if at < 0:
            return False
        offset = at + len(token)
    return True


def metadata(profile):
    dest = R4 / "profiles" / profile
    build = json.loads(read(dest / "build.json"))
    # Deliberately discard historical expected-variant observations.
    boot = json.loads(read(dest / "boot.json"))
    receipt = boot.get("receipt", {})
    raw = read(dest / "qemu_boot.stdout.log")
    stderr = read(dest / "qemu_boot.stderr.log")
    cfg_raw = read(dest / "kernel.config")
    cfg = configuration(cfg_raw)
    auto = dict(re.findall(r"^#define (CONFIG_\w+) (.*)$",
                          read(dest / "autoconf.h"), re.M))
    arch = build.get("arch")
    variant = build.get("variant")
    checks = {
        "record_identity": build.get("status") == "READY"
            and build.get("profile") == boot.get("profile") == profile
            and arch in ("s390", "x86") and variant in ("old", "fixed")
            and profile == variant + "_" + arch,
        "config_digest": digest((dest / "kernel.config").read_bytes())
            == build.get("config_sha256"),
        "config_and_autoconf": all(cfg.get("CONFIG_" + k) == "y"
            and auto.get("CONFIG_" + k) == "1" for k in COMMON)
            and cfg.get("CONFIG_NR_CPUS") == auto.get("CONFIG_NR_CPUS") == "4",
        "successful_single_boot": receipt.get("name") == "qemu_boot"
            and receipt.get("state") == "finished" and receipt.get("attempt") == 1
            and receipt.get("exit_code") == 0 and not stderr.strip(),
    }
    expected_arch = "S390" if arch == "s390" else "X86_64"
    checks["actual_arch_config"] = cfg.get("CONFIG_" + expected_arch) == "y" \
        and auto.get("CONFIG_" + expected_arch) == "1"
    if arch == "s390":
        checks["actual_topology_config"] = cfg.get("CONFIG_SCHED_TOPOLOGY") == "y" \
            and auto.get("CONFIG_SCHED_TOPOLOGY") == "1"
    checks["build_effective_config"] = all(
        value == "y" and cfg.get("CONFIG_" + key) == value
        and auto.get("CONFIG_" + key) == "1"
        for key, value in build.get("effective_required", {}).items()) \
        and all(key in build.get("effective_required", {}) for key in COMMON)
    argv = receipt.get("argv", [])
    def arg(name):
        try:
            return argv[argv.index(name) + 1]
        except (ValueError, IndexError):
            return None
    checks["boot_image_initrd_binding"] = arg("-kernel") == build.get("image") \
        and arg("-initrd") == build.get("initrd") \
        and all(re.fullmatch(r"[a-f0-9]{64}", build.get(k, ""))
                for k in ("image_sha256", "initrd_sha256"))
    checks["ordinary_two_cpu_command"] = arg("-accel") == "tcg" \
        and arg("-smp") in ("2", "2,sockets=1,cores=2,threads=1") \
        and arg("-m") == "512" and arg("-nic") == "none" \
        and "-no-reboot" in argv
    checks["simulator_arch"] = bool(argv) and argv[0] == (
        "qemu-system-s390x" if arch == "s390" else "qemu-system-x86_64")
    manifest = json.loads(read(R4 / (str(variant) + "_observer_sources.json")))
    checks["source_revision_binding"] = manifest.get("revision") == build.get("revision") \
        and re.fullmatch(r"[a-f0-9]{40}", build.get("revision", "")) is not None \
        and build.get("source_instrumented") is True
    sources = {}
    source_hashes = {}
    for item in manifest.get("files", []):
        rel = item["path"]
        text = read(R4 / "observer_sources" / variant / rel)
        sources[rel] = text
        source_hashes[rel] = item.get("original_sha256")
        checks["source_digest:" + rel] = digest(
            (R4 / "observer_sources" / variant / rel).read_bytes()) \
            == item.get("observed_sha256")
    required = ("kernel/cpu.c", "kernel/sched/core.c", "include/linux/r4_observe.h",
                "arch/s390/kernel/smp.c", "arch/s390/kernel/topology.c",
                "arch/x86/kernel/smpboot.c")
    checks["source_material_complete"] = all(p in sources for p in required)
    details = {"revision": build.get("revision"), "arch": arch,
               "source_binding_scope": "Archived observer digests and existing build/boot receipts; no fresh ELF/cache certification"}
    if checks["source_material_complete"]:
        core = sources["kernel/sched/core.c"]
        lock = function(core, "static void sched_core_lock(int cpu,")
        starting = function(core, "static void sched_core_cpu_starting(unsigned int cpu)")
        scheduler = function(core, "int sched_cpu_starting(unsigned int cpu)")
        cpu = sources["kernel/cpu.c"]
        header = sources["include/linux/r4_observe.h"]
        checks["source_same_public_callback"] = re.search(
            r"\[CPUHP_AP_SCHED_STARTING\] = \{[^}]*\.startup\.single\s*= sched_cpu_starting,",
            cpu, re.S) is not None and "sched_core_cpu_starting(cpu);" in scheduler
        checks["source_actual_state_observation"] = in_order(cpu, [
            "if (bringup && state == CPUHP_AP_SCHED_STARTING)",
            'r4_note("cpuhp_before", cpu, 0, -1, state, st->target, 0);',
            "ret = cb(cpu);", 'r4_note("cpuhp_after", cpu, 0, -1, state, st->target, ret);',
        ]) and "ret, CPUHP_AP_SCHED_STARTING);" in header
        checks["source_actual_mask_lock_count"] = in_order(lock, [
            "const struct cpumask *smt_mask = cpu_smt_mask(cpu);",
            "o->mask = cpumask_bits(smt_mask)[0];",
            "o->self = cpumask_test_cpu(cpu, smt_mask);",
            "o->weight = cpumask_weight(smt_mask);",
            "o->online = cpu_online(cpu);", "o->count = 0;",
            "for_each_cpu(t, smt_mask) {", "raw_spin_lock_nested(&cpu_rq(t)->__lock, i++);",
            "o->count++;",
        ])
        checks["source_snapshot_before_lock_print_after_unlock"] = in_order(starting, [
            'r4_note("core_enter"', "sched_core_lock(cpu, &flags);",
            "sched_core_unlock(cpu, &flags);", 'pr_info("R4 phase=lock_snapshot',
            "printed_after_unlock=1", "o->seq, o->mask, o->self, o->weight, o->count",
        ])
        checks["source_singleton_or_leader_constraint"] = in_order(starting, [
            "sched_core_lock(cpu, &flags);", "if (cpumask_weight(smt_mask) == 1)",
            "if (WARN_ON_ONCE(!core_rq))",
        ])
        arch_src = sources["arch/s390/kernel/smp.c" if arch == "s390"
                           else "arch/x86/kernel/smpboot.c"]
        anchor = re.search(r'r4_note\("arch_before_notify", (?:cpu|cpuid), '
                           r'([01]), (.*?), -1, -1, 0\);', arch_src)
        checks["source_arch_observation"] = anchor is not None and (
            (anchor.group(1) == "0" and anchor.group(2) == "-1")
            or (anchor.group(1) == "1" and anchor.group(2).startswith("cpumask_test_cpu(")))
        details["provider_preparation_expression"] = anchor.group(0) if anchor else None
        details["prepared_known_from_source"] = int(anchor.group(1)) if anchor else None
        if arch == "s390":
            startup = function(arch_src, "static void smp_start_secondary(void *cpuvoid)")
            topology = sources["arch/s390/kernel/topology.c"]
            thread_map = function(topology, "static void cpu_thread_map(cpumask_t *dst, unsigned int cpu)")
            online_gate = "if (!cpu_online(cpu))" in thread_map
            setup_gate = "if (!cpumask_test_cpu(cpu, &cpu_setup_mask))" in thread_map
            details["provider_membership_gate"] = (
                "cpu_online" if online_gate else "cpu_setup_mask" if setup_gate else "unknown")
            checks["source_provider_gate_and_preparation_order"] = (
                online_gate and in_order(startup, [
                    'r4_note("arch_before_notify"', "notify_cpu_starting(cpu);",
                    "set_cpu_online(cpu, true);", "update_cpu_masks();"])
                or setup_gate and in_order(startup, [
                    "cpumask_set_cpu(cpu, &cpu_setup_mask);", "update_cpu_masks();",
                    'r4_note("arch_before_notify"', "notify_cpu_starting(cpu);",
                    "set_cpu_online(cpu, true);"]))
            details["provider_update_position"] = (
                "after shared notify and online" if online_gate else
                "setup membership and masks before shared notify" if setup_gate else "unknown")
            checks["source_single_mode_definition"] = re.search(
                r"enum\s*\{\s*TOPOLOGY_MODE_HW,\s*TOPOLOGY_MODE_SINGLE,", topology) is not None
            checks["source_single_mode_self_rule"] = in_order(thread_map, [
                "cpumask_clear(&mask);", "goto out;", "cpumask_set_cpu(cpu, &mask);",
                "if (topology_mode != TOPOLOGY_MODE_HW)", "goto out;", "cpumask_copy(dst, &mask);"])
        else:
            startup = function(arch_src, "static void smp_callin(void)")
            sibling = function(arch_src, "void set_cpu_sibling_map(int cpu)")
            checks["source_provider_gate_and_preparation_order"] = in_order(startup, [
                "set_cpu_sibling_map(raw_smp_processor_id());",
                'r4_note("arch_before_notify"', "notify_cpu_starting(cpuid);"])
            checks["source_provider_self_construction"] = (
                "cpumask_set_cpu(cpu, cpu_sibling_setup_mask);" in sibling
                and "cpumask_set_cpu(cpu, topology_sibling_cpumask(cpu));" in sibling
                and "(i == cpu)" in sibling)
            details["provider_membership_gate"] = "cpu_sibling_setup_mask"
            details["provider_update_position"] = "set_cpu_sibling_map before shared notify"
    return {"profile": profile, "raw": raw, "build": build, "argv_append": arg("-append"),
            "checks": checks, "details": details, "cfg": cfg,
            "source_hashes": source_hashes}


def events(raw):
    rows = []
    for line, text in enumerate(raw.splitlines(), 1):
        match = re.search(r"\bR4 phase=(\w+) (.*)$", text)
        if not match:
            continue
        row = {"phase": match.group(1), "line": line}
        pairs = re.findall(r"(\w+)=(-?[0-9a-f]+)(?:\s|$)", match.group(2))
        if len({key for key, _ in pairs}) != len(pairs):
            raise ValueError("duplicate event field")
        for key, val in pairs:
            row[key] = int(val, 16 if key == "mask" else 10)
        rows.append(row)
    return rows


def replay(material, raw=None):
    raw = material["raw"] if raw is None else raw
    checks = dict(material["checks"])
    result = {"profile": material["profile"], "status": "insufficient",
              "foundation": checks, "provenance": material["details"],
              "predicates": None}
    try:
        parsed = events(raw)
        target = 1
        found = {phase: [row for row in parsed if row.get("cpu") == target
                        and row["phase"] == phase] for phase in PHASES}
        checks["nine_target_events_exactly_once"] = all(len(v) == 1 for v in found.values())
        user = {}
        for field, value in re.findall(r"R4_USER field=(\w+) value=([^\r\n]*)", raw):
            user.setdefault(field, []).append(value.strip())
        identities = re.findall(r"R4_USER release=(\S+) machine=(\S+) pid=(\d+)\s*$", raw, re.M)
        checks["pid1_release_machine"] = identities == [(
            material["build"]["release"],
            "s390x" if material["details"]["arch"] == "s390" else "x86_64", "1")]
        checks["mounts_and_end"] = len(re.findall(r"R4_USER mount_proc=0 mount_sysfs=0\s*$", raw, re.M)) == 1 \
            and len(re.findall(r"R4_USER end=1\s*$", raw, re.M)) == 1
        checks["user_fields_complete"] = all(len(user.get(k, [])) == 1
            for k in ("cmdline", "online", "cpu1_threads"))
        checks["user_no_read_errors"] = not re.search(r"R4_USER field=\w+ error=", raw)
        if checks["user_fields_complete"]:
            online_set = cpu_list(user["online"][0])
            final_threads = cpu_list(user["cpu1_threads"][0])
            checks["both_cpus_finally_online"] = online_set == {0, 1}
            checks["cmdline_matches_boot_receipt"] = user["cmdline"][0] == material["argv_append"]
            result["final_lists"] = {"online": sorted(online_set),
                                     "cpu1_thread_siblings": sorted(final_threads),
                                     "decimal_list_not_hex": True}
        if material["details"]["arch"] == "s390":
            modes = re.findall(r"R4_MODE mode=(\d+) facility=(\d+) mtid=(\d+)\s*$", raw, re.M)
            checks["mode_within_frozen_single_scope"] = modes == [("1", "0", "0")]
            result["observed_s390_mode"] = modes
        if checks["nine_target_events_exactly_once"]:
            rows = [found[p][0] for p in PHASES]
            first = found["lock_snapshot"][0]
            before = found["arch_before_notify"][0]
            pre, post = found["cpuhp_before"][0], found["cpuhp_after"][0]
            checks["same_target_cpu"] = all(e["current"] == target for e in rows)
            checks["event_sequence_and_position"] = all(
                a["seq"] < b["seq"] and a["line"] < b["line"]
                for a, b in zip(rows, rows[1:])) and rows[0]["seq"] > 0
            note_rows = [e for e in rows if e["phase"] != "lock_snapshot"]
            states = {e["sched_state"] for e in note_rows}
            checks["actual_cpuhp_sched_stage"] = len(states) == 1 \
                and pre["state"] == post["state"] == pre["sched_state"] > 0 \
                and pre["target"] == post["target"] >= pre["state"] \
                and post["ret"] == 0
            checks["notify_covers_actual_stage"] = found["notify_enter"][0]["state"] \
                <= pre["state"] <= found["notify_enter"][0]["target"] \
                and found["notify_exit"][0]["state"] == found["notify_exit"][0]["target"]
            checks["mask_self_weight_are_consistent"] = all(
                0 <= e["mask"] < 16 and e["self"] == int(bool(e["mask"] & (1 << target)))
                and e["weight"] == e["mask"].bit_count() for e in rows)
            checks["actual_locks_match_members"] = first["locks"] == first["weight"] \
                and first["locks"] >= 0
            checks["same_mask_until_first_consumer"] = all(
                e["mask"] == first["mask"] for e in rows[:5])
            checks["first_online_snapshot_matches_entry"] = first["online"] \
                == found["core_enter"][0]["online"] and first["online"] in (0, 1)
            checks["snapshot_output_after_unlock"] = first["printed_after_unlock"] == 1
            known = material["details"].get("prepared_known_from_source")
            checks["provider_expression_matches_record"] = known is not None \
                and before["prepared_known"] == known \
                and ((known == 0 and before["prepared"] == -1)
                     or (known == 1 and before["prepared"] in (0, 1)))
            result["first_consumption"] = first
            result["cpu1_events"] = rows
            result["architecture_preparation"] = {
                k: before[k] for k in ("prepared_known", "prepared", "online", "mask", "self")}
            if all(checks.values()):
                narrow_ok = bool(first["mask"] & (1 << target))
                result["status"] = "satisfied" if narrow_ok else "violation"
                result["predicates"] = {
                    "first_use_contains_target": {
                        "satisfied": narrow_ok,
                        "definition": "target CPU bit present at actual sched_core_lock mask snapshot",
                        "actual_locks": first["locks"],
                        "source_constraint": "original loop locks every mask member; singleton/leader path follows"},
                    "final_only_contains_target": {
                        "satisfied": target in final_threads,
                        "definition": "target belongs to final decimal thread_siblings_list",
                        "misses_first_use_violation": not narrow_ok and target in final_threads},
                    "online_before_first_consumption": {
                        "satisfied": first["online"] == 1,
                        "definition": "require online=1 at first use (deliberately wrong simplification)",
                        "false_alarm_relative_to_narrow_contract": narrow_ok and first["online"] != 1},
                }
    except (KeyError, ValueError, TypeError, IndexError) as exc:
        checks["parsable_complete_material"] = False
        result["parse_failure"] = type(exc).__name__ + ": " + str(exc)
    result["failed_foundation"] = [key for key, value in checks.items() if not value]
    return result


def main():
    # The frozen protocol is fingerprinted only; no expectation text is parsed.
    read(HERE / "first_use_replay_protocol_pre.md")
    materials = []
    load_failures = []
    for profile in PROFILES:
        try:
            materials.append(metadata(profile))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            load_failures.append({"profile": profile, "status": "insufficient",
                                  "error": type(exc).__name__ + ": " + str(exc)})
    pair_details = {}
    for arch in ("s390", "x86"):
        pair = [m for m in materials if m["details"]["arch"] == arch]
        if len(pair) != 2:
            for m in pair:
                m["checks"]["same_arch_config_pair_complete"] = False
            continue
        old, fixed = pair
        diffs = {key: [old["cfg"].get(key), fixed["cfg"].get(key)]
                 for key in set(old["cfg"]) | set(fixed["cfg"])
                 if old["cfg"].get(key) != fixed["cfg"].get(key)}
        valid = set(diffs) <= {"CONFIG_LOCALVERSION"}
        for m in pair:
            m["checks"]["paired_config_only_localversion_differs"] = valid
        pair_details[arch] = diffs
    common_original = {}
    for path in ("kernel/cpu.c", "kernel/sched/core.c", "arch/x86/kernel/smpboot.c"):
        hashes = {m["source_hashes"].get(path) for m in materials}
        common_original[path] = len(hashes) == 1 and None not in hashes and len(materials) == 4
    for m in materials:
        m["checks"]["shared_original_sources_agree"] = all(common_original.values())
    rows = [replay(m) for m in materials] + load_failures
    verifier_checks = []
    if materials:
        base = materials[0]
        raw = base["raw"]
        edits = {
            "missing_first_event": re.sub(r"^.*R4 phase=lock_snapshot cpu=1[^\n]*\n", "", raw, flags=re.M),
            "wrong_real_callback_stage": re.sub(r"(R4 phase=cpuhp_before cpu=1[^\n]* state=)(\d+)",
                lambda m: m.group(1) + str(int(m.group(2)) + 1), raw),
            "final_cpu1_not_online": raw.replace("field=online value=0-1", "field=online value=0"),
        }
        for name, changed in edits.items():
            observed = replay(base, changed)
            verifier_checks.append({"name": name, "in_memory_only": True,
                "changed_input": changed != raw, "status": observed["status"],
                "rejects_judgment": changed != raw and observed["status"] == "insufficient"
                    and observed["predicates"] is None,
                "failed_foundation": observed["failed_foundation"]})
        reduced_details = dict(base["details"])
        reduced_details.pop("prepared_known_from_source", None)
        reduced = {**base, "details": reduced_details}
        observed = replay(reduced)
        verifier_checks.append({"name": "missing_source_material", "in_memory_only": True,
            "changed_input": True, "status": observed["status"],
            "rejects_judgment": observed["status"] == "insufficient" and observed["predicates"] is None,
            "failed_foundation": observed["failed_foundation"]})
    unchanged = all(digest((HERE.parent / rel).read_bytes()) == value for rel, value in INPUTS.items())
    result = {
        "study": "Researcher-synthesized first-use narrow contract; read development data replay",
        "date": "2026-10-14", "profiles": rows, "paired_config_differences": pair_details,
        "shared_original_source_hashes_agree": common_original,
        "verifier_checks": verifier_checks,
        "verifier_checks_pass": len(verifier_checks) == 4 and all(c["rejects_judgment"] for c in verifier_checks),
        "input_fingerprints": INPUTS, "original_inputs_unchanged": unchanged,
        "new_kernel_boots": 0, "new_builds": 0, "new_cases": 0, "external_model_calls": 0,
        "manual_expectation_not_detector_input": {
            "old_s390": "first-use violation; final-only misses",
            "other_three": "first-use satisfied; online-before-use gives false alarms",
            "origin": "Already read sources and R4 logs, not unseen labels or model-generated rules"},
        "limits": ["Same previously read case, four archived ordinary two-CPU runs",
            "Not independent accuracy, automatic model extraction, unseen detection or real SMT/hotplug/concurrency",
            "No fresh kernel/image/cache certification; local archived source/config and recorded build/boot binding",
            "Insufficient evidence rejects judgment; absence of warning is not a pass condition"],
    }
    out = HERE / "first_use_replay.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"profiles": [{"profile": r["profile"], "status": r["status"]} for r in rows],
                      "verifier_checks_pass": result["verifier_checks_pass"],
                      "original_inputs_unchanged": unchanged}, ensure_ascii=False))


if __name__ == "__main__":
    main()
