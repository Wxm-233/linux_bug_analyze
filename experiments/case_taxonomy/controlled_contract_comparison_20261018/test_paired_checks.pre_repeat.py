"""Wrapper gates only. Synthetic records are not successful Linux analyses."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("n28_wrapper", HERE / "run_paired_checks.py")
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)


def delivery():
    return ({"status": "complete_final_received", "exit_code": 0, "result_subtype": "success",
             "result_is_error": False, "actual_models": ["AWS-Claude-Opus-5.5"],
             "response_models": ["AWS-Claude-Opus-5.5"], "stop_reasons": ["end_turn"],
             "refusal_observed": False}, {"prompt_sha256": "a" * 64}, {"prompt_sha256": "a" * 64})


class PairedWrapperGates(unittest.TestCase):
    def test_complete_synthetic_delivery_gate_accepts_only_a_record_not_analysis(self):
        receipt, plan, manifest = delivery()
        self.assertIsNone(wrapper.verify_delivery(receipt, plan, manifest))
        receipt["stop_reasons"] = ["end_turn", "stop_sequence"]
        self.assertIsNone(wrapper.verify_delivery(receipt, plan, manifest))

    def test_incomplete_error_refusal_or_unapproved_stop_records_reject(self):
        changes = [{"status": "running"}, {"exit_code": 1}, {"result_subtype": "error"},
                   {"result_is_error": True}, {"refusal_observed": True},
                   {"stop_reasons": []}, {"stop_reasons": ["refusal", "end_turn"]},
                   {"stop_reasons": ["max_tokens"]}, {"stop_reasons": [["end_turn"]]}]
        for change in changes:
            receipt, plan, manifest = delivery(); receipt.update(change)
            with self.subTest(change=change), self.assertRaises(wrapper.old.EvidenceError):
                wrapper.verify_delivery(receipt, plan, manifest)

    def test_model_or_prompt_identity_is_not_borrowed(self):
        for mode in ["actual", "response", "prompt"]:
            receipt, plan, manifest = delivery()
            if mode == "actual": receipt["actual_models"] = ["different-model"]
            if mode == "response": receipt["response_models"] = []
            if mode == "prompt": plan["prompt_sha256"] = "b" * 64
            with self.subTest(mode=mode), self.assertRaises(wrapper.old.EvidenceError):
                wrapper.verify_delivery(receipt, plan, manifest)

    def make_packet(self, root):
        artifact = root / "synthetic_artifact.json"
        artifact.write_bytes(b'{"synthetic":true}')
        packet = {"input_manifest": [{"path": artifact.name, "sha256": wrapper.sha(artifact.read_bytes())}]}
        path = root / wrapper.SOURCE_PATH
        path.parent.mkdir(parents=True)
        path.write_bytes(json.dumps(packet).encode())
        manifest = {"documents_path": wrapper.SOURCE_PATH, "documents_sha256": wrapper.sha(path.read_bytes()),
                    "input_manifest": copy.deepcopy(packet["input_manifest"])}
        return path, artifact, manifest

    def test_packet_and_input_manifest_are_exactly_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path, artifact, manifest = self.make_packet(root)
            raw, packet, artifacts = wrapper.load_packet(manifest, root)
            self.assertEqual(raw, path.read_bytes())
            self.assertEqual(artifacts[artifact.name], artifact.read_bytes())
            for key, value in [("documents_path", "different.json"), ("documents_sha256", "0" * 64),
                               ("input_manifest", [])]:
                changed = dict(manifest); changed[key] = value
                with self.subTest(key=key), self.assertRaises(wrapper.old.EvidenceError): wrapper.load_packet(changed, root)

    def test_artifact_drift_or_escape_is_rejected_before_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path, artifact, manifest = self.make_packet(root)
            artifact.write_bytes(b"changed")
            with self.assertRaisesRegex(wrapper.old.EvidenceError, "source_artifact_digest_mismatch"):
                wrapper.load_packet(manifest, root)
            packet = {"input_manifest": [{"path": "../outside.json", "sha256": "0" * 64}]}
            path.write_bytes(json.dumps(packet).encode())
            manifest.update(documents_sha256=wrapper.sha(path.read_bytes()), input_manifest=packet["input_manifest"])
            with self.assertRaisesRegex(wrapper.old.EvidenceError, "artifact_outside_project"):
                wrapper.load_packet(manifest, root)

    def test_baseline_requires_wrapper_old_checker_lexer_and_rejects_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); files = {}
            for name in wrapper.REQUIRED_METHOD_FILES:
                p = root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b"synthetic method bytes")
                files[name] = wrapper.sha(p.read_bytes())
            path = root / "baseline.json"
            path.write_text(json.dumps({"schema": "n28_paired_method_baseline_v1", "files": files}))
            self.assertEqual(wrapper.verify_method_baseline(path, root)["files"], files)
            removed = dict(files); removed.pop(wrapper.LEXER_PATH)
            path.write_text(json.dumps({"schema": "n28_paired_method_baseline_v1", "files": removed}))
            with self.assertRaisesRegex(wrapper.old.EvidenceError, "required_frozen_method_missing"):
                wrapper.verify_method_baseline(path, root)
            path.write_text(json.dumps({"schema": "n28_paired_method_baseline_v1", "files": files}))
            (root / wrapper.CHECKER_PATH).write_bytes(b"drift")
            with self.assertRaisesRegex(wrapper.old.EvidenceError, "frozen_method_changed"):
                wrapper.verify_method_baseline(path, root)

    def test_existing_output_is_preserved_before_any_input_is_read(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output.json"; output.write_bytes(b"original")
            with self.assertRaisesRegex(wrapper.old.EvidenceError, "output_exists_preserve_prior_record"):
                wrapper.run(Path(directory) / "missing_final.md", output)
            self.assertEqual(output.read_bytes(), b"original")


if __name__ == "__main__":
    unittest.main()
