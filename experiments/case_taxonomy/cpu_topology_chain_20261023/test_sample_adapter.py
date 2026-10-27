"""Synthetic adapter boundary tests; not new runs or independent cases."""
import copy
import hashlib
import json
import unittest

from linux_bug_analyze.contract_protocol import CLAIM_ROLES
from sample_adapter import PROFILES, SOURCE_PATHS, evaluate_bound_sample


def packed(value):
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def sha(value):
    return hashlib.sha256(value).hexdigest()


def fixture(profile="old_s390", members=()):
    revision, arch = PROFILES[profile]
    context = "component." + profile
    mask = sum(1 << value for value in members)
    image, initrd = "/cache/" + profile + "/kernel", "/cache/" + profile + "/initrd"
    release = "test-kernel-" + profile
    cmdline = "rdinit=/init r4_case=" + profile
    keys = ["64BIT", "SMP", "SCHED_SMT", "SCHED_CORE", "HOTPLUG_CPU", "SYSFS"]
    keys += ["S390", "SCHED_TOPOLOGY"] if arch == "s390" else ["X86_64"]
    config = ("\n".join("CONFIG_" + key + "=y" for key in keys) + "\nCONFIG_NR_CPUS=4\n").encode()
    autoconf = ("\n".join("#define CONFIG_" + key + " 1" for key in keys) + "\n#define CONFIG_NR_CPUS 4\n").encode()
    build = {"status": "READY", "source_instrumented": True, "profile": profile,
             "variant": profile.split("_", 1)[0], "revision": revision, "arch": arch,
             "release": release, "image": image, "initrd": initrd,
             "image_sha256": "1" * 64, "initrd_sha256": "2" * 64, "config_sha256": sha(config)}
    archive = "/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/s390_arch_contract_20261013/runtime/profiles/" + profile
    boot = {"profile": profile, "receipt": {"name": "qemu_boot", "state": "finished", "attempt": 1, "exit_code": 0,
            "stdout": archive + "/qemu_boot.stdout.log", "stderr": archive + "/qemu_boot.stderr.log",
            "argv": ["qemu-system-s390x" if arch == "s390" else "qemu-system-x86_64",
                     "-kernel", image, "-initrd", initrd, "-append", cmdline]}}
    log = (f"R4 phase=lock_snapshot cpu=1 current=1 seq=7 mask={mask:x} self={int(1 in members)} "
           f"weight={len(members)} locks={len(members)} rq_self=1 online=0 printed_after_unlock=1\n"
           f"R4_USER release={release} machine={'s390x' if arch == 's390' else 'x86_64'} pid=1\n"
           f"R4_USER field=cmdline value={cmdline}\n"
           "R4_USER field=online value=0-1\nR4_USER field=cpu1_threads value=1\n").encode()
    artifacts = {"build": packed(build), "boot": packed(boot), "config": config, "autoconf": autoconf,
                 "log": log, "semantic_review": b"Synthetic external-review fixture, not evidence of a real run.\n"}
    for path in SOURCE_PATHS:
        artifacts["source:" + path] = b"/* Synthetic observed source fixture. */\n"
    artifacts["source_manifest"] = packed({"revision": revision, "files": [
        {"path": path, "original_sha256": "3" * 64, "observed_sha256": sha(artifacts["source:" + path])}
        for path in sorted(SOURCE_PATHS)]})
    binding = {"profile": profile, "revision": revision, "arch": arch, "context_id": context,
               "image_sha256": build["image_sha256"], "initrd_sha256": build["initrd_sha256"],
               "artifact_sha256": {key: sha(raw) for key, raw in artifacts.items()},
               "sample": {"cpu": 1, "phase": "lock_snapshot", "line": 1, "seq": 7},
               "semantic_review_sha256": sha(artifacts["semantic_review"])}
    symbols = {"selected_path": {"type": "bool", "role": "configuration"},
               "members": {"type": "int_set", "role": "observation"},
               "target_cpu": {"type": "int", "role": "observation"}}
    contract = {"schema": "architecture_contract_v1", "id": "component.membership", "revision": revision,
                "authority_kind": "consumer_inferred", "sufficient_for_correctness": False,
                "field_origins": {key: "researcher_authored" for key in ("scope", "relation", "symbols", "required_claims", "authority_kind")},
                "required_claims": {role: "review." + role for role in CLAIM_ROLES}, "symbols": symbols,
                "scope": {"symbol": "selected_path"},
                "relation": {"op": "contains", "args": [{"symbol": "members"}, {"symbol": "target_cpu"}]}}
    sample_id, deadline_id = context + ".pre_irq_disable_sample", context + ".mask_content_iteration"
    obj = context + ".cpu1.smt_mask"
    record = {"id": "component.record", "revision": revision, "basis": "archived_runtime", "context_id": context,
              "object_id": obj, "sample_event": sample_id, "deadline_event": deadline_id, "sample_kind": "sample",
              "observation_binding": {"object_id": obj, "event_id": sample_id, "deadline_id": deadline_id, "claim": "review.observation"}, "facts": {}}
    documents = {key: {"context_revision": revision, "artifact_key": key, "sha256": sha(artifacts[key]), "path": key,
                       "start_line": 1, "end_line": len(artifacts[key].decode().splitlines())}
                 for key in ("log", "semantic_review")}
    refs = [{"document": "semantic_review", "start_line": 1, "end_line": 1}]
    ledger = {"contract_id": contract["id"], "revision": revision, "basis": "archived_runtime", "context_id": context,
              "field_origins": copy.deepcopy(contract["field_origins"]), "documents": documents, "claims": {}}
    for role in CLAIM_ROLES:
        ledger["claims"]["review." + role] = {"role": role, "origin": "researcher_review", "status": "supported",
              "statement": "Explicit synthetic external-review premise for adapter testing only.", "context_id": context,
              "references": copy.deepcopy(refs)}
    ledger["claims"]["review.authority"].update(authority_kind="consumer_inferred", supports_requirement="review.consumer_requirement")
    for role, expression in (("applicability", "scope"), ("consumer_requirement", "relation")):
        ledger["claims"]["review." + role].update(expression=copy.deepcopy(contract[expression]), symbols=copy.deepcopy(symbols))
    for role in ("consumer_requirement", "provider_binding", "object_binding", "deadline_binding"):
        ledger["claims"]["review." + role]["object_id"] = obj
    ledger["claims"]["review.deadline_binding"].update(event_id=deadline_id, event_kind="content_consumption")
    ledger["claims"]["review.observation"] = {"role": "observation_binding", "origin": "researcher_review", "status": "supported",
             "statement": "Explicit synthetic sample binding.", "context_id": context, "references": copy.deepcopy(refs),
             "binding": {"object_id": obj, "event_id": sample_id, "deadline_id": deadline_id, "context_id": context, "event_kind": "sample"}}
    for name, value in {"selected_path": True, "members": list(members), "target_cpu": 1}.items():
        fact = {"value": value, "claim": "fact." + name}
        expected = {"symbol": name, "value": value, "role": symbols[name]["role"], "context_id": context}
        if name != "selected_path":
            fact.update(object_id=obj, event_id=sample_id)
            expected.update(object_id=obj, event_id=sample_id)
        record["facts"][name] = fact
        ledger["claims"]["fact." + name] = {"role": "fact", "origin": "program_projection", "status": "supported",
                "statement": "Synthetic fixture projection, not an independent run.", "context_id": context,
                "references": [{"document": "log", "start_line": 1, "end_line": 1}], "fact": expected}
    return contract, ledger, record, binding, artifacts


class SampleAdapterTests(unittest.TestCase):
    def test_explicit_membership_uses_one_sample_not_version_labels(self):
        for profile in PROFILES:
            for members, expected in (([], "violated"), ([1], "satisfied")):
                with self.subTest(profile=profile, members=members):
                    result = evaluate_bound_sample(*fixture(profile, members))
                    self.assertEqual(result["status"], expected, result["reasons"])
                    self.assertEqual(result["evaluation"]["relation_at_deadline"], "insufficient")
                    self.assertEqual(result["evaluation"]["whole_path"], "insufficient")
                    self.assertFalse(result["continuous_stability_proved"])
                    self.assertFalse(result["fresh_image_certification"])

    def test_wrong_profile_revision_arch_or_context_fails_binding(self):
        for key, value in (("profile", "fixed_s390"), ("revision", "0" * 40), ("arch", "x86"), ("context_id", "another")):
            inputs = fixture()
            inputs[3][key] = value
            with self.subTest(key=key):
                self.assertEqual(evaluate_bound_sample(*inputs)["binding_status"], "insufficient")

    def test_changed_bytes_or_incomplete_artifact_registry_are_rejected(self):
        for key in ("config", "autoconf", "log", "source_manifest", "source:kernel/sched/core.c"):
            inputs = fixture()
            inputs[4][key] += b"\n"
            with self.subTest(key=key):
                self.assertEqual(evaluate_bound_sample(*inputs)["status"], "insufficient")
        inputs = fixture()
        del inputs[4]["config"]
        self.assertEqual(evaluate_bound_sample(*inputs)["status"], "insufficient")

    def test_source_manifest_must_match_observed_source_bytes(self):
        inputs = fixture()
        key = "source:kernel/sched/core.c"
        inputs[4][key] += b"changed\n"
        inputs[3]["artifact_sha256"][key] = sha(inputs[4][key])
        result = evaluate_bound_sample(*inputs)
        self.assertEqual(result["status"], "insufficient")
        self.assertIn("observed_source_digest_mismatch", str(result["reasons"]))

    def test_exact_raw_log_line_sequence_and_cpu_are_required(self):
        for key, value in (("line", 2), ("seq", 8), ("cpu", 0), ("phase", "core_enter")):
            inputs = fixture()
            inputs[3]["sample"][key] = value
            with self.subTest(key=key):
                self.assertEqual(evaluate_bound_sample(*inputs)["status"], "insufficient")

    def test_sampling_cannot_be_promoted_or_renamed_to_consumption(self):
        for key, value in (("sample_kind", "content_consumption"), ("sample_event", "invented.consume"), ("deadline_event", "invented.deadline")):
            inputs = fixture()
            inputs[2][key] = value
            with self.subTest(key=key):
                self.assertEqual(evaluate_bound_sample(*inputs)["status"], "insufficient")

    def test_late_members_cannot_replace_earlier_empty_sample(self):
        inputs = fixture(members=[])
        inputs[2]["facts"]["members"]["value"] = [1]
        inputs[1]["claims"]["fact.members"]["fact"]["value"] = [1]
        result = evaluate_bound_sample(*inputs)
        self.assertEqual(result["status"], "insufficient")
        self.assertIn("sample_members_disagree", str(result["reasons"]))

    def test_missing_effect_value_and_unknown_object_review_remain_insufficient(self):
        inputs = fixture()
        del inputs[2]["facts"]["members"]
        self.assertEqual(evaluate_bound_sample(*inputs)["status"], "insufficient")
        for role in ("object_binding", "provider_binding"):
            inputs = fixture(members=[1])
            inputs[1]["claims"]["review." + role]["status"] = "unknown"
            result = evaluate_bound_sample(*inputs)
            self.assertEqual(result["binding_status"], "bound")
            self.assertEqual(result["evaluation"]["relation_at_observation"], "insufficient")

    def test_ledger_document_actual_hash_and_line_bounds_are_checked(self):
        for key, value in (("sha256", "0" * 64), ("end_line", 999), ("artifact_key", "other")):
            inputs = fixture()
            inputs[1]["documents"]["log"][key] = value
            with self.subTest(key=key):
                self.assertEqual(evaluate_bound_sample(*inputs)["status"], "insufficient")

    def test_prior_expected_verdict_and_warning_do_not_supply_answer(self):
        inputs = fixture(members=[])
        boot = json.loads(inputs[4]["boot"])
        boot["observations"] = {"status": "satisfied", "predicates": {"membership": True}}
        inputs[4]["boot"] = packed(boot)
        inputs[3]["artifact_sha256"]["boot"] = sha(inputs[4]["boot"])
        result = evaluate_bound_sample(*inputs)
        self.assertEqual(result["status"], "violated", result["reasons"])

    def test_boolean_cpu_duplicate_members_and_unregistered_facts_rejected(self):
        for value in ([True], [1, 1]):
            inputs = fixture(members=[1])
            inputs[2]["facts"]["members"]["value"] = value
            with self.subTest(value=value):
                self.assertEqual(evaluate_bound_sample(*inputs)["status"], "insufficient")
        inputs = fixture()
        inputs[2]["facts"]["final_members"] = {"value": [1]}
        self.assertEqual(evaluate_bound_sample(*inputs)["status"], "insufficient")

    def test_malformed_input_remains_insufficient(self):
        inputs = list(fixture())
        inputs[3] = None
        self.assertEqual(evaluate_bound_sample(*inputs)["status"], "insufficient")

    def test_crlf_log_is_hashed_as_bytes_without_changing_line_binding(self):
        inputs = fixture(members=[1])
        inputs[4]["log"] = inputs[4]["log"].replace(b"\n", b"\r\n")
        changed = sha(inputs[4]["log"])
        inputs[3]["artifact_sha256"]["log"] = changed
        inputs[1]["documents"]["log"]["sha256"] = changed
        result = evaluate_bound_sample(*inputs)
        self.assertEqual(result["status"], "satisfied", result["reasons"])
        self.assertEqual(result["sample"]["line"], 1)
        self.assertEqual(result["artifact_sha256"]["log"], changed)

    def test_archived_image_and_success_receipt_links_are_required(self):
        inputs = fixture()
        inputs[3]["image_sha256"] = "9" * 64
        self.assertEqual(evaluate_bound_sample(*inputs)["status"], "insufficient")
        inputs = fixture()
        boot = json.loads(inputs[4]["boot"])
        boot["receipt"]["attempt"] = 2
        inputs[4]["boot"] = packed(boot)
        inputs[3]["artifact_sha256"]["boot"] = sha(inputs[4]["boot"])
        self.assertEqual(evaluate_bound_sample(*inputs)["status"], "insufficient")


if __name__ == "__main__":
    unittest.main()
