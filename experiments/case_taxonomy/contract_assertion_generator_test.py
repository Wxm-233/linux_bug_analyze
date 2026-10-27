"""Meaningful refusal and oracle-shape boundaries using development fixtures."""
import copy
import unittest

import contract_assertion_generator as generator
import structured_hci_single_revision as structured
from structured_hci_single_revision_test import HCI, CORE
from outbound_scalar_single_revision_test import REQUEST, SKBUFF


class ContractGeneratorTests(unittest.TestCase):
    def files(self, producer="raw", payload=HCI, source_core=CORE, assignment_extra=""):
        expression = "dev->value" if producer == "raw" else "cpu_to_le16(dev->value)"
        source = ('#include <net/bluetooth/hci.h>\n#include <net/bluetooth/hci_core.h>\n'
            f'void send(struct device *dev) {{ struct command cp; cp.value={expression}; '
            f'cp.second=dev->second; {assignment_extra} hci_req_add(req,OP,sizeof(cp),&cp); }}')
        return {"driver.c": source, structured.HCI: payload, structured.HCI_CORE: source_core,
                structured.scalar.REQUEST: REQUEST, structured.scalar.SKBUFF: SKBUFF}

    def plan(self, files=None, report_change=None):
        files = files or self.files()
        report = structured.analyze_files("driver.c", files)
        if report_change:
            report_change(report)
        return generator.build_plan(report, files)

    def test_complete_payload_produces_source_assignments_and_independent_schema(self):
        result = self.plan()
        self.assertEqual(result["status"], "generated", result["rejections"])
        program = result["programs"][0]
        source = generator.emit_c(program)
        self.assertIn("cp.value=dev->value;", source)
        self.assertIn("offsetof(struct command, value)", source)
        self.assertIn("expected_value >>", source)
        self.assertEqual(program["variants"], ["actual", "reference", "partial_value", "partial_second"])
        self.assertEqual(program["test_values"]["16"], [0x1234, 0xab37, 0])
        self.assertEqual(program["compiler_binding_contract"]["target_object"], "cp")

    def test_matching_original_conversion_retained_not_rebuilt_as_raw(self):
        program = self.plan(self.files("encoded"))["programs"][0]
        self.assertEqual(program["fields"][0]["producer_status"], "matched_conversion")
        self.assertIn("cp.value=cpu_to_le16(dev->value);", generator.emit_c(program))

    def test_report_assignment_tamper_refused(self):
        result = self.plan(report_change=lambda report: report["findings"][0]["assignment"].update(text="cp.value=make();"))
        self.assertEqual(result["status"], "refused")
        self.assertIn("does not reproduce", result["rejections"][0]["reason"])

    def test_header_and_evidence_hash_tamper_refused(self):
        files = self.files()
        report = structured.analyze_files("driver.c", files)
        files[structured.HCI] = files[structured.HCI].replace("__le16 value", "__be16 value")
        self.assertEqual(generator.build_plan(report, files)["status"], "refused")
        result = self.plan(report_change=lambda report: report["findings"][0]["target_declaration"]["evidence"].update(source_sha256="0" * 64))
        self.assertEqual(result["status"], "refused")

    def test_fake_git_blob_refused(self):
        result = self.plan(report_change=lambda report: report["files_read"][0].update(git_blob="0" * 40))
        self.assertEqual(result["status"], "refused")

    def test_missing_payload_field_is_not_partial_test(self):
        files = self.files()
        files["driver.c"] = files["driver.c"].replace("cp.second=dev->second;", "")
        result = self.plan(files)
        self.assertEqual(result["status"], "refused")
        self.assertIn("incomplete", result["rejections"][0]["reason"])

    def test_nonendian_extra_field_invalidates_whole_payload(self):
        for field in ("u16 count;", "__le16 third[2];", "__le16 *third;", "__le16 third:3;", "union { __le16 third; };"):
            payload = HCI.replace("__le16 second;", "__le16 second; " + field)
            self.assertEqual(self.plan(self.files(payload=payload))["status"], "refused")

    def test_complex_layout_suffix_is_refused(self):
        for suffix in ("__attribute__((aligned(8)))", "__aligned(4)", "__packed __aligned(8)"):
            self.assertEqual(self.plan(self.files(payload=HCI.replace("__packed", suffix)))["status"], "refused")

    def test_locally_redefined_packing_is_not_assumed_standard(self):
        self.assertEqual(self.plan(self.files(payload="#define __packed __attribute__((aligned(8)))\n" + HCI))["status"], "refused")

    def test_packing_pragma_context_not_discarded_from_mixed_width_struct(self):
        payload = HCI.replace("__le16 second", "__le32 second").replace("__packed", "")
        core = CORE.replace("__u16 second", "__u32 second")
        for pragma in ("#pragma pack(1)\n", "#pragma pack(push,1)\n", '_Pragma("pack(1)")\n'):
            result = self.plan(self.files(payload=pragma + payload, source_core=core))
            self.assertEqual(result["status"], "refused")
            self.assertIn("pragma/packing", result["rejections"][0]["reason"])

    def test_plain_layout_and_comment_are_preserved(self):
        payload = HCI.replace("__packed", "").replace("__le16 value;", "/* original comment */ __le16 value;")
        result = self.plan(self.files(payload=payload))
        self.assertEqual(result["status"], "generated")
        self.assertIn("/* original comment */", generator.emit_c(result["programs"][0]))

    def test_multiple_assignments_or_escape_refuses_complete_program(self):
        for extra in ("cp.value=dev->value;", "change(&cp);"):
            self.assertEqual(self.plan(self.files(assignment_extra=extra))["status"], "refused")

    def test_duplicate_source_mapping_refused(self):
        files = self.files()
        files["driver.c"] = files["driver.c"].replace("cp.second=dev->second;", "cp.second=dev->value;")
        self.assertEqual(self.plan(files)["status"], "refused")

    def test_emit_modified_assignment_or_declaration_refused(self):
        for key in ("original_assignment", "source_field"):
            program = copy.deepcopy(self.plan()["programs"][0])
            program["fields"][0][key] = "invalid; system(\"anything\");"
            with self.assertRaises(ValueError):
                generator.emit_c(program)

    def test_emit_unvalidated_plan_is_refused(self):
        with self.assertRaises(ValueError):
            generator.emit_c({"id": "untrusted", "payload_declaration": "arbitrary"})

    def test_unknown_structure_and_zero_sites_are_refused(self):
        self.assertEqual(self.plan(self.files(payload=HCI.replace("struct command", "struct other")))["status"], "refused")
        files = self.files()
        files["driver.c"] = "void empty(void) {}"
        self.assertEqual(self.plan(files)["status"], "refused")

    def test_supported_widths_and_domains_are_not_case_name_rules(self):
        for bits in (16, 32, 64):
            for endian in ("le", "be"):
                files = self.files(payload=HCI.replace("__le16", f"__{endian}{bits}"), source_core=CORE.replace("__u16", f"__u{bits}"))
                result = self.plan(files)
                self.assertEqual(result["status"], "generated", result["rejections"])
                program = result["programs"][0]
                self.assertEqual(program["fields"][0]["bits"], bits)
                self.assertEqual(program["fields"][0]["endian"], endian)
                self.assertEqual(program["test_values"][str(bits)][-1], 0)


if __name__ == "__main__":
    unittest.main()
