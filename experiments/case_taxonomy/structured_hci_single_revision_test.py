"""Development-only boundaries for structure payload representation evidence."""
import unittest

import outbound_scalar_single_revision as scalar
import structured_hci_single_revision as structured
from outbound_scalar_single_revision_test import REQUEST, SKBUFF


HCI = """#ifndef HCI_H
#define HCI_H
struct command { __le16 value; __le16 second; } __packed;
#endif
"""
CORE = """#ifndef CORE_H
#define CORE_H
struct device { __u16 value; __u16 second; };
#endif
"""


class StructuredPayloadTests(unittest.TestCase):
    def source(self, expression="dev->value", extra="", declaration="struct command cp;", length="sizeof(cp)"):
        return ('#include <net/bluetooth/hci.h>\n#include <net/bluetooth/hci_core.h>\n'
                f'void send(struct device *dev) {{ {declaration} cp.value = {expression}; {extra} hci_req_add(req, OP, {length}, &cp); }}')

    def report(self, source=None, hci=HCI, core=CORE, request=REQUEST, skbuff=SKBUFF):
        return structured.analyze_files("driver.c", {"driver.c": source or self.source(),
            structured.HCI: hci, structured.HCI_CORE: core,
            scalar.REQUEST: request, scalar.SKBUFF: skbuff})

    def one(self, source=None, **kwargs):
        report = self.report(source, **kwargs)
        self.assertEqual(len(report["findings"]), 1, report)
        return report["findings"][0]

    def test_host_member_to_endian_payload_is_only_conditional_candidate(self):
        finding = self.one()
        self.assertEqual(finding["status"], "candidate", finding)
        self.assertEqual(finding["target_declaration"]["type"], "__le16")
        self.assertEqual(finding["source_member"]["declaration"]["type"], "__u16")
        self.assertEqual(finding["consumer"]["status"], "proven_byte_copy_chain")
        self.assertEqual(finding["defect_verdict"], "not assessed")
        self.assertEqual(finding["reader_or_schema"]["external_controller_contract"], "unproven")
        self.assertFalse(finding["suggested_check"]["automated_patch"])

    def test_matching_conversion_is_field_syntax_only(self):
        finding = self.one(self.source("cpu_to_le16(dev->value)"))
        self.assertEqual(finding["status"], "matched_conversion", finding)
        self.assertEqual(finding["source_value_paths"], "not_proven")

    def test_simple_local_pointer_type_declaration_is_retained(self):
        source = self.source().replace("struct device *dev)", "struct request *req)").replace("struct command cp;", "struct device *dev = req->dev; struct command cp;")
        self.assertEqual(self.one(source)["status"], "candidate")

    def test_width_mismatch_is_insufficient(self):
        self.assertEqual(self.one(core=CORE.replace("__u16 value", "__u32 value"))["status"], "insufficient")

    def test_encoded_source_is_not_host_source(self):
        self.assertEqual(self.one(core=CORE.replace("__u16 value", "__le16 value"))["status"], "insufficient")

    def test_wrong_or_double_conversion_is_insufficient(self):
        for expression in ("cpu_to_be16(dev->value)", "cpu_to_le32(dev->value)", "cpu_to_le16(cpu_to_le16(dev->value))"):
            self.assertEqual(self.one(self.source(expression))["status"], "insufficient")

    def test_source_member_write_or_escape_is_insufficient(self):
        for extra in ("dev->value = cpu_to_le16(7);", "adjust(&dev->value);"):
            self.assertEqual(self.one(self.source(extra=extra))["status"], "insufficient")

    def test_same_field_multistore_is_not_chosen_as_last_write(self):
        report = self.report(self.source(extra="cp.value = cpu_to_le16(dev->value);"))
        self.assertEqual(report["counts"], {"candidate": 0, "matched_conversion": 0, "insufficient": 2})

    def test_payload_object_and_member_address_escape_is_insufficient(self):
        for extra in ("adjust(&cp);", "adjust(&cp.value);", "void *alias = &cp;"):
            self.assertEqual(self.one(self.source(extra=extra))["status"], "insufficient")

    def test_whole_object_compound_and_opaque_use_is_insufficient(self):
        for extra in ("cp = other;", "cp.value += 1;", "inspect(cp.value);", "cp = cp;"):
            self.assertEqual(self.one(self.source(extra=extra))["status"], "insufficient")

    def test_payload_shadow_is_not_global_name_association(self):
        source = self.source().replace("struct command cp;", "{ struct other cp; } struct command cp;")
        self.assertEqual(self.one(source)["status"], "candidate")
        source = self.source().replace("cp.value = dev->value;", "{ struct other cp; cp.value = dev->value;") + "}"
        self.assertEqual(self.one(source)["status"], "insufficient")

    def test_unsigned_scalar_shadow_cannot_reuse_outer_structure_type(self):
        source = self.source().replace("cp.value = dev->value;", "{ __u16 cp; cp.value = dev->value;") + "}"
        report = self.report(source)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["sites"][0]["status"], "insufficient")

    def test_unknown_typedef_payload_shadow_cannot_reuse_outer_structure_type(self):
        source = self.source().replace("cp.value = dev->value;", "{ alternate_command cp; cp.value = dev->value;") + "}"
        report = self.report(source)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["sites"][0]["status"], "insufficient")

    def test_source_pointer_shadow_or_reassignment_is_insufficient(self):
        for extra in ("{ struct other *dev; }", "dev = other;", "adjust(&dev);"):
            self.assertEqual(self.one(self.source(extra=extra))["status"], "insufficient")

    def test_unknown_typedef_array_or_scalar_shadow_cannot_bind_host_parameter(self):
        for declaration in ("encoded_dev dev[1]={{.value=cpu_to_le16(7)}};", "encoded_dev dev;", "encoded_dev *dev;"):
            source = self.source().replace("struct command cp;", "{ " + declaration + " struct command cp;") + "}"
            self.assertEqual(self.one(source)["status"], "insufficient")

    def test_parenthesized_or_dereference_member_write_cannot_hide_source_encoding(self):
        for extra in ("(dev)->value = cpu_to_le16(7);", "(&*dev)->value = cpu_to_le16(7);", "(*dev).value = cpu_to_le16(7);"):
            self.assertEqual(self.one(self.source(extra=extra))["status"], "insufficient")

    def test_declaration_not_at_call_scope_is_insufficient(self):
        source = self.source(extra="{", length="sizeof(cp)") + "}"
        self.assertEqual(self.one(source)["status"], "insufficient")

    def test_nested_or_unbraced_assignment_is_insufficient(self):
        for replacement in ("if (flag) cp.value = dev->value;", "{ cp.value = dev->value; }"):
            source = self.source().replace("cp.value = dev->value;", replacement)
            self.assertEqual(self.one(source)["status"], "insufficient")

    def test_size_not_exact_object_is_insufficient(self):
        for length in ("2", "sizeof(other)", "sizeof(cp)+1"):
            self.assertEqual(self.one(self.source(length=length))["status"], "insufficient")

    def test_unknown_config_function_and_field_is_insufficient(self):
        self.assertEqual(self.one("#ifdef CONFIG_X\n" + self.source() + "\n#endif")["status"], "insufficient")
        hci = HCI.replace("__le16 value;", "\n#ifdef CONFIG_X\n__le16 value;\n#endif\n")
        self.assertEqual(self.one(hci=hci)["status"], "insufficient")

    def test_payload_field_header_must_be_reachable(self):
        source = self.source().replace("#include <net/bluetooth/hci.h>", "")
        self.assertEqual(self.one(source)["status"], "insufficient")

    def test_unknown_or_inactive_include_does_not_establish_field_visibility(self):
        for condition in ("#if 0", "#ifdef UNKNOWN"):
            source = self.source().replace("#include <net/bluetooth/hci.h>", condition + "\n#include <net/bluetooth/hci.h>\n#endif")
            self.assertEqual(self.one(source)["status"], "insufficient")
        source = self.source().replace("#include <net/bluetooth/hci.h>", "#ifdef __KERNEL__\n#include <net/bluetooth/hci.h>\n#endif")
        self.assertEqual(self.one(source)["status"], "candidate")

    def test_unrelated_source_member_address_does_not_escape_pointer_object(self):
        self.assertEqual(self.one(self.source(extra="inspect(&dev->second);"))["status"], "candidate")

    def test_duplicate_struct_definition_is_insufficient(self):
        self.assertEqual(self.one(hci=HCI + "struct command { __le16 value; };")["status"], "insufficient")

    def test_nested_array_pointer_bitfield_or_multidecl_target_is_unknown(self):
        for field in ("union { __le16 value; };", "__le16 value[2];", "__le16 *value;", "__le16 value:4;", "__le16 value, second;"):
            hci = "struct command { " + field + " };"
            self.assertEqual(self.one(hci=hci)["status"], "insufficient")

    def test_conversion_member_or_type_macro_is_insufficient(self):
        for macro in ("cpu_to_le16(x) (x)", "value other", "__le16 u16", "command other"):
            self.assertEqual(self.one("#define " + macro + "\n" + self.source("cpu_to_le16(dev->value)"))["status"], "insufficient")

    def test_unknown_source_literal_call_or_nested_member_is_insufficient(self):
        for expression in ("7", "host", "make()", "dev->inner.value"):
            self.assertEqual(self.one(self.source(expression))["status"], "insufficient")

    def test_missing_or_transformed_copy_chain_is_insufficient(self):
        self.assertEqual(self.one(request=REQUEST.replace("skb_put_data(skb, param, plen)", "skb_put_data(skb, param+1, plen)"))["status"], "insufficient")

    def test_zero_sites_is_out_of_scope_not_normal(self):
        report = self.report('void unrelated(void) { int x=1; }')
        self.assertEqual(report["findings"], [])
        self.assertEqual(sum(report["counts"].values()), 0)
        self.assertIn("never normal", report["scope"])

    def test_host_only_target_is_outside_endian_rule(self):
        report = self.report(hci=HCI.replace("__le16 value", "u16 value"))
        self.assertEqual(report["findings"], [])

    def test_evidence_has_source_line_and_hash(self):
        finding = self.one()
        self.assertEqual(finding["target_declaration"]["evidence"]["line"], 3)
        self.assertEqual(finding["assignment"]["source_sha256"], scalar.digest(self.source()))


if __name__ == "__main__":
    unittest.main()
