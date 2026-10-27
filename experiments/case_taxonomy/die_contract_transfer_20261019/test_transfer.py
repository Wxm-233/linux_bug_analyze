"""Adapter trust boundaries; counterexamples are not new Linux cases."""
import copy
import unittest
import transfer


class TransferBoundaryTests(unittest.TestCase):
    def packet(self, projection, revision=transfer.OLD, basis="source_projection"):
        return transfer.envelope("synthetic_boundary", revision, basis, "boundary.only", projection, True,
                                 transfer.HERE / "protocol_pre.json")

    def evaluate(self, packet):
        return transfer.evaluate_contract(packet["contract"], packet["ledger"], packet["record"])

    def test_partial_source_diagnostics_cannot_become_supported_facts(self):
        row = self.packet({"status": "insufficient", "id_native": True, "mask_native": True,
                           "listed_any": True, "count": 1, "provider_body_reviewed": True})
        self.assertEqual(set(row["record"]["facts"]), {"sysfs_enabled"})
        self.assertEqual(self.evaluate(row)["relation_at_observation"], "insufficient")

    def test_old_policy_is_counterfactual_and_sample_does_not_prove_deadline(self):
        row = self.packet({"status": "supported", "id_native": False, "mask_native": False,
                           "listed_any": True, "provider_body_reviewed": True})
        result = self.evaluate(row)
        self.assertEqual(result["relation_at_observation"], "violated")
        self.assertEqual(result["relation_at_deadline"], "insufficient")
        self.assertEqual(row["historical_normative_verdict"], "insufficient")
        self.assertEqual(row["policy_application"], "counterfactual_policy_from_fixed")
        evidence = row["ledger"]["documents"]["policy_application"]
        self.assertEqual(evidence["context_revision"], transfer.OLD)
        self.assertEqual(evidence["source_policy_revision"], transfer.FIXED)

    def test_runtime_absence_cannot_replace_unknown_provider_sources(self):
        row = self.packet({"status": "supported", "id_native": None, "mask_native": None,
                           "listed_any": False, "provider_body_reviewed": False}, basis="archived_runtime")
        self.assertEqual(self.evaluate(row)["relation_at_observation"], "insufficient")

    def test_arch_header_path_does_not_certify_fallback_macro_body(self):
        sources = transfer.load(transfer.HERE.parent / "arch_witness_checks_20261014/requests/export_pair.json")
        material = transfer.load(transfer.BASE / "profiles/old_x86_smp/preprocessed_evidence.json")
        self.assertTrue(transfer.native_body_review(material, sources))
        fallback = transfer.load(transfer.BASE / "profiles/old_s390_smp/preprocessed_evidence.json")
        material["macro_definitions"]["topology_die_id"][0]["definition"] = fallback["macro_definitions"]["topology_die_id"][0]["definition"]
        self.assertFalse(transfer.native_body_review(material, sources))

    def test_archived_runtime_identity_rejects_receipt_or_profile_substitution(self):
        folder = transfer.BASE / "runtime/profiles/old_s390"
        boot, build = transfer.load(folder / "boot.json"), transfer.load(folder / "build.json")
        events = boot["observations"]["events"]
        self.assertTrue(transfer.validate_runtime_identity("old_s390", boot, build, events))
        for change in ("receipt", "profile", "release", "initrd", "machine", "case", "log_path"):
            with self.subTest(change=change):
                b, d, e = copy.deepcopy(boot), copy.deepcopy(build), copy.deepcopy(events)
                if change == "receipt": b["qemu_receipt"]["exit_code"] = 1
                if change == "profile": b["profile"] = "fixed_s390"
                if change == "release": b["release"] = "other-version"
                if change == "initrd": b["initrd_sha256"] = "different-initrd"
                if change == "machine": next(x for x in e if x["event"] == "uname")["machine"] = "x86_64"
                if change == "case": next(x for x in e if x["event"] == "file_read" and x.get("path") == "/proc/cmdline")["raw"] = "die_case=fixed_s390"
                if change == "log_path": b["qemu_receipt"]["stdout"] = b["qemu_receipt"]["stdout"].replace("old_s390", "fixed_s390")
                with self.assertRaises(AssertionError):
                    transfer.validate_runtime_identity("old_s390", b, d, e)


if __name__ == "__main__":
    unittest.main()
