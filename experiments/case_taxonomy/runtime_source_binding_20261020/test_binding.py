"""Known-archive identity/scope boundaries; no runner, CPP or kernel execution."""
import copy
from functools import lru_cache
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("runtime_direct_binding", HERE / "binding.py")
binding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(binding)


@lru_cache(maxsize=4)
def archived(profile):
    folder = HERE.parent / "die_arch_contract_20261013/runtime/profiles" / profile
    return (profile, json.loads((folder / "build.json").read_bytes()), json.loads((folder / "boot.json").read_bytes()),
            (folder / "kernel.config").read_bytes().decode("utf-8"), (folder / "autoconf.h").read_bytes().decode("utf-8"),
            json.loads((HERE / "cached_source_packet.json").read_bytes()))


def fixture(profile="old_x86_64"): return list(copy.deepcopy(archived(profile)))
def call(values): return binding.bind_run(*values)


def rebind_configuration(values, config=None, autoconf=None):
    if config is not None:
        values[3] = config
        digest = hashlib.sha256(config.encode("utf-8")).hexdigest()
        values[1]["config_sha256"] = digest
        values[5]["runs"][values[0]]["config_sha256"] = digest
    if autoconf is not None:
        values[4] = autoconf
        values[5]["runs"][values[0]]["archived_autoconf_sha256"] = hashlib.sha256(autoconf.encode("utf-8")).hexdigest()


class RuntimeSourceBindingTests(unittest.TestCase):
    def test_four_own_archives_produce_only_conditional_source_candidates(self):
        for profile in binding.PROFILES:
            with self.subTest(profile=profile):
                result = call(fixture(profile))
                self.assertEqual(result["status"], "source_candidate_supported", result["unknowns"])
                expected = binding.PROFILES[profile][1] == "x86_64"
                self.assertIs(result["source_candidate"]["id_native"], expected)
                self.assertIs(result["source_candidate"]["mask_native"], expected)
                self.assertTrue(result["source_candidate"]["conditional"])
                self.assertEqual(result["runtime_facts"], {"id_native": None, "mask_native": None, "provider_binding": "unknown"})
                self.assertIn("runtime_TU_closure", result["unknowns"])
                self.assertTrue(result["no_physical_truth"])

    def test_wrong_profile_revision_arch_receipt_or_observed_identity_refuses(self):
        for change in ["profile", "revision", "arch", "image", "receipt", "uname", "case"]:
            with self.subTest(change=change):
                values = fixture()
                build, boot = values[1], values[2]
                if change == "profile": build["profile"] = "fixed_x86_64"
                if change == "revision": build["revision"] = binding.FIXED
                if change == "arch": build["arch"] = boot["arch"] = "s390"
                if change == "image": boot["image_sha256"] = "0" * 64
                if change == "receipt": boot["qemu_receipt"]["exit_code"] = False
                if change == "uname": next(e for e in boot["observations"]["events"] if e["event"] == "uname")["machine"] = "s390x"
                if change == "case": next(e for e in boot["observations"]["events"] if e.get("path") == "/proc/cmdline")["raw"] = "die_case=fixed_x86_64"
                result = call(values)
                self.assertEqual(result["status"], "insufficient")
                self.assertIsNone(result["source_candidate"]["id_native"])

    def test_config_or_autoconf_drift_and_internal_disagreement_refuse(self):
        for change in ["config_bytes", "autoconf_bytes", "auto_disagrees", "duplicate_config"]:
            with self.subTest(change=change):
                values = fixture()
                if change == "config_bytes": values[3] += "\n"
                if change == "autoconf_bytes": values[4] += "\n"
                if change == "auto_disagrees": rebind_configuration(values, autoconf=values[4].replace("#define CONFIG_SMP 1", "#define CONFIG_SMP 0"))
                if change == "duplicate_config": rebind_configuration(values, config=values[3] + "CONFIG_SMP=y\n")
                self.assertEqual(call(values)["status"], "insufficient")

    def test_re_signed_guard_closed_or_different_nr_scope_is_not_approved(self):
        for key, config_value, auto_value in [("CONFIG_SMP", "n", None), ("CONFIG_SYSFS", "n", None), ("CONFIG_NR_CPUS", "8", "8")]:
            with self.subTest(key=key):
                values = fixture()
                config = re.sub(r"(?m)^" + key + r"=.*$", "# " + key + " is not set" if config_value == "n" else key + "=" + config_value, values[3])
                auto = re.sub(r"(?m)^#define " + re.escape(key) + r"(?=[ \t])[^\n]*\n", "" if auto_value is None else "#define " + key + " " + auto_value + "\n", values[4])
                values[1]["effective_configuration"][key] = config_value
                rebind_configuration(values, config, auto)
                result = call(values)
                self.assertEqual(result["status"], "insufficient")
                self.assertIn("outside_reviewed_runtime_guard_scope", result["unknowns"])

    def test_macro_changed_to_fallback_is_not_approved_even_after_resigning(self):
        values = fixture()
        key = binding.OLD + ":" + binding.X86
        source = values[5]["sources"][key]
        source["text"] = source["text"].replace("(cpu_data(cpu).cpu_die_id)", "((void)(cpu), -1)")
        raw = source["text"].encode("utf-8")
        source["sha256"] = hashlib.sha256(raw).hexdigest()
        source["git_blob"] = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
        next(row for row in values[1]["source_identity"] if row["path"] == binding.X86)["git_blob"] = source["git_blob"]
        result = call(values)
        self.assertEqual(result["status"], "insufficient")
        self.assertTrue(any("outside_reviewed_whole_file_summary" in why for why in result["unknowns"]))
        self.assertIsNone(result["source_candidate"]["id_native"])

    def test_missing_foreign_duplicate_or_unmatched_source_identity_refuses(self):
        for change in ["missing_key", "foreign_revision", "blob", "duplicate_build", "content"]:
            with self.subTest(change=change):
                values = fixture()
                run = values[5]["runs"][values[0]]
                if change == "missing_key": run["source_keys"].pop()
                if change == "foreign_revision": run["source_keys"][0] = binding.FIXED + ":" + binding.PUBLIC
                if change == "blob": next(row for row in values[1]["source_identity"] if row["path"] == binding.PUBLIC)["git_blob"] = "0" * 40
                if change == "duplicate_build": values[1]["source_identity"].append(copy.deepcopy(next(row for row in values[1]["source_identity"] if row["path"] == binding.PUBLIC)))
                if change == "content": values[5]["sources"][binding.OLD + ":" + binding.PUBLIC]["text"] += "\n"
                self.assertEqual(call(values)["status"], "insufficient")

    def test_candidate_cannot_become_runtime_native_and_old_policy_is_not_rewritten(self):
        values = fixture()
        original = copy.deepcopy(values)
        result = call(values)
        self.assertEqual(values, original)
        self.assertEqual(result["historical_normative_verdict"], "insufficient")
        self.assertFalse(result["policy_modified"])
        result["source_candidate"]["id_native"] = False
        result["source_candidate"]["origins"]["id"]["body"]["text"] = "changed_output"
        self.assertEqual(result["runtime_facts"], {"id_native": None, "mask_native": None, "provider_binding": "unknown"})
        self.assertEqual(values, original)

    def test_no_closure_upgrade_from_packet_or_expected_output_labels(self):
        values = fixture()
        values[5]["runtime_effective_macro_closure_proved"] = True
        result = call(values)
        self.assertEqual(result["status"], "insufficient")
        self.assertEqual(result["runtime_facts"]["provider_binding"], "unknown")
        values = fixture()
        values[2]["observations"].update(status="MISMATCH", matches_contract=False, expected_native_sources=False)
        result = call(values)
        self.assertEqual(result["status"], "source_candidate_supported", result["unknowns"])
        self.assertEqual(result["historical_normative_verdict"], "insufficient")
        self.assertIsNone(result["runtime_facts"]["id_native"])


if __name__ == "__main__": unittest.main()
