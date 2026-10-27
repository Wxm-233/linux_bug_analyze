"""Offline bounded-shape checks; synthetic fixtures are development data."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import outbound_scalar_single_revision as outbound

REQUEST = """
struct sk_buff *__hci_cmd_sync(struct hci_dev *hdev, u16 opcode, u32 plen,
                             const void *param, u32 timeout)
{ return __hci_cmd_sync_ev(hdev, opcode, plen, param, 0, timeout); }
struct sk_buff *__hci_cmd_sync_ev(struct hci_dev *hdev, u16 opcode, u32 plen,
                                const void *param, u8 event, u32 timeout)
{ hci_req_add_ev(&req, opcode, plen, param, event); return skb; }
void hci_req_add_ev(struct hci_request *req, u16 opcode, u32 plen,
                   const void *param, u8 event)
{ skb = hci_prepare_cmd(hdev, opcode, plen, param); }
void hci_req_add(struct hci_request *req, u16 opcode, u32 plen, const void *param)
{ hci_req_add_ev(req, opcode, plen, param, 0); }
struct sk_buff *hci_prepare_cmd(struct hci_dev *hdev, u16 opcode, u32 plen,
                               const void *param)
{ hdr->opcode = cpu_to_le16(opcode); hdr->plen = plen;
  if (plen) skb_put_data(skb, param, plen); return skb; }
"""
SKBUFF = """
#ifndef _LINUX_SKBUFF_H
#define _LINUX_SKBUFF_H
static inline void *skb_put_data(struct sk_buff *skb, const void *data,
                                 unsigned int len)
{ void *tmp = skb_put(skb, len); memcpy(tmp, data, len); return tmp; }
#endif
"""


class OutboundScalarTests(unittest.TestCase):
    def report(self, source, request=REQUEST, skbuff=SKBUFF):
        return outbound.analyze_files("driver.c", {"driver.c": source,
            outbound.REQUEST: request, outbound.SKBUFF: skbuff})

    def result(self, source, request=REQUEST, skbuff=SKBUFF):
        report = self.report(source, request, skbuff)
        self.assertEqual(len(report["findings"]), 1, report)
        return report["findings"][0]

    def sync(self, declaration="u32 x = 7;", middle="", pointer="&x", length="sizeof(x)", host_type="u32"):
        return f"void send({host_type} host) {{ {declaration} {middle} __hci_cmd_sync(dev, OP, {length}, {pointer}, T); }}"

    def test_host_local_bytes_are_review_fact_not_defect(self):
        finding = self.result(self.sync())
        self.assertEqual(finding["status"], "raw_host_bytes", finding)
        self.assertEqual(finding["required_payload_format"], "unproven")
        self.assertEqual(finding["defect_verdict"], "not assessed")
        self.assertEqual(len(finding["consumer"]["chain"]), 5)

    def test_host_parameter(self):
        finding = self.result("void send(u32 x) { __hci_cmd_sync(dev, OP, sizeof(x), &x, T); }")
        self.assertEqual(finding["status"], "raw_host_bytes", finding)

    def test_matching_explicit_conversion_widths_and_endianness(self):
        for endian in ("le", "be"):
            for bits in (16, 32, 64):
                with self.subTest(endian=endian, bits=bits):
                    finding = self.result(self.sync(f"__{endian}{bits} x = cpu_to_{endian}{bits}(host);", host_type=f"u{bits}"))
                    self.assertEqual(finding["status"], "matched_endian_scalar", finding)
                    self.assertEqual(finding["required_payload_format"], "unproven")

    def test_direct_async_entry_has_same_revision_chain(self):
        finding = self.result("void send(u32 x) { hci_req_add(req, OP, sizeof(x), &x); }")
        self.assertEqual(finding["status"], "raw_host_bytes", finding)
        self.assertEqual(len(finding["consumer"]["chain"]), 4)
        self.assertEqual(finding["consumer"]["chain"][0]["function"], "hci_req_add")

    def test_uninitialized_local_is_insufficient(self):
        self.assertEqual(self.result(self.sync("u32 x;"))["status"], "insufficient")

    def test_overwritten_endian_value_rejected(self):
        finding = self.result(self.sync("__le32 x = cpu_to_le32(host);", "x = host;"))
        self.assertEqual(finding["status"], "insufficient", finding)
        self.assertIn("assignment", finding["reason"])

    def test_multiple_branch_assignments_are_not_path_proved(self):
        finding = self.result(self.sync("u32 x;", "if(a) x=1; else x=2;"))
        self.assertEqual(finding["status"], "insufficient", finding)
        self.assertIn("multiple assignments", finding["reason"])
        self.assertEqual(finding["consumer"]["status"], "proven_byte_copy_chain")
        self.assertTrue(finding["declarations"])

    def test_alias_escape_rejected(self):
        self.assertEqual(self.result(self.sync(middle="void *p = &x;"))["status"], "insufficient")

    def test_opaque_address_call_rejected(self):
        self.assertEqual(self.result(self.sync(middle="adjust(&x);"))["status"], "insufficient")

    def test_same_type_shadow_rejected(self):
        source = "void send(u32 x) { { u32 x=9; __hci_cmd_sync(dev, OP, sizeof(x), &x, T); } }"
        self.assertEqual(self.result(source)["status"], "insufficient")

    def test_different_type_shadow_rejected(self):
        self.assertEqual(self.result(self.sync(middle="{ int x=9; }"))["status"], "insufficient")

    def test_size_mismatch_and_fixed_literal_rejected(self):
        for length in ("4", "sizeof(host)", "sizeof(x)+1", "size"):
            with self.subTest(length=length):
                self.assertEqual(self.result(self.sync(length=length))["status"], "insufficient")

    def test_array_not_scalar(self):
        finding = self.result(self.sync("u32 x[2];"))
        self.assertEqual(finding["status"], "insufficient", finding)

    def test_member_address_not_direct_scalar(self):
        finding = self.result(self.sync(pointer="&obj->x"))
        self.assertEqual(finding["status"], "insufficient", finding)

    def test_pointer_cast_out_of_scope_not_normal(self):
        report = self.report(self.sync(pointer="(void *)&x"))
        self.assertEqual(report["findings"], [])
        self.assertEqual(sum(report["counts"].values()), 0)

    def test_comment_and_literal_fake_calls_not_matched(self):
        report = self.report('void send(void) { /* __hci_cmd_sync(dev,OP,sizeof(x),&x,T); */ "__hci_cmd_sync(dev,OP,sizeof(x),&x,T)"; }')
        self.assertEqual(report["findings"], [])

    def test_conditional_body_rejected(self):
        self.assertEqual(self.result(self.sync(middle="\n#if FLAG\n#endif\n"))["status"], "insufficient")

    def test_outer_conditional_rejected(self):
        self.assertEqual(self.result("#if FLAG\n"+self.sync()+"\n#endif\n")["status"], "insufficient")

    def test_kernel_context_simple_true_branch_is_explicit_assumption(self):
        source = "#ifdef __KERNEL__\n"+self.sync()+"\n#endif\n"
        self.assertEqual(self.result(source)["status"], "raw_host_bytes")
        self.assertTrue(any("__KERNEL__=true" in item for item in self.report(source)["assumptions"]))

    def test_kernel_context_else_and_reverse_condition_correct(self):
        rejected = "#ifdef __KERNEL__\n#else\n"+self.sync()+"\n#endif\n"
        self.assertEqual(self.result(rejected)["status"], "insufficient")
        accepted = "#ifndef __KERNEL__\n#else\n"+self.sync()+"\n#endif\n"
        self.assertEqual(self.result(accepted)["status"], "raw_host_bytes")

    def test_kernel_expression_and_redefinition_not_inferred(self):
        for source in ("#if defined(__KERNEL__)\n"+self.sync()+"\n#endif\n",
                       "#undef __KERNEL__\n#ifdef __KERNEL__\n"+self.sync()+"\n#endif\n"):
            self.assertEqual(self.result(source)["status"], "insufficient")

    def test_consumer_kernel_context_is_accepted(self):
        skbuff = SKBUFF.replace("#define _LINUX_SKBUFF_H", "#define _LINUX_SKBUFF_H\n#ifdef __KERNEL__") + "\n#endif\n"
        self.assertEqual(self.result(self.sync(), skbuff=skbuff)["status"], "raw_host_bytes")

    def test_local_macro_name_rejected(self):
        self.assertEqual(self.result("#define x y\n"+self.sync())["status"], "insufficient")

    def test_mismatched_conversion_rejected(self):
        self.assertEqual(self.result(self.sync("__le32 x=cpu_to_be32(host);"))["status"], "insufficient")

    def test_endian_parameter_does_not_prove_conversion(self):
        self.assertEqual(self.result("void send(__le32 x) { __hci_cmd_sync(dev,OP,sizeof(x),&x,T); }")["status"], "insufficient")

    def test_conversion_redefinition_rejected(self):
        self.assertEqual(self.result("#define cpu_to_le32(x) (x)\n"+self.sync("__le32 x=cpu_to_le32(host);"))["status"], "insufficient")

    def test_host_storage_with_explicit_encoding_is_not_raw_host(self):
        self.assertEqual(self.result(self.sync("u32 x=cpu_to_le32(7);"))["status"], "insufficient")

    def test_host_storage_unknown_initializer_is_not_raw_host(self):
        self.assertEqual(self.result(self.sync("u32 x=unknown_source();"))["status"], "insufficient")

    def test_double_encoding_not_matched_normal(self):
        source = self.sync("__le32 a=cpu_to_le32(7); __le32 x=cpu_to_le32(a);")
        self.assertEqual(self.result(source)["status"], "insufficient")

    def test_encoded_host_temporary_not_matched_normal(self):
        source = self.sync("u32 a=cpu_to_le32(7); __le32 x=cpu_to_le32(a);")
        self.assertEqual(self.result(source)["status"], "insufficient")

    def test_unknown_and_mismatched_width_conversion_sources_refuse(self):
        for declaration in ("__le32 x=cpu_to_le32(unknown);", "u16 a=1; __le32 x=cpu_to_le32(a);", "__le16 x=cpu_to_le16(host);"):
            with self.subTest(declaration=declaration):
                self.assertEqual(self.result(self.sync(declaration))["status"], "insufficient")

    def test_conversion_literal_requires_nonnegative_fitting_width(self):
        for value in ("-1", "65536", "0xffffffffffffffffULL"):
            self.assertEqual(self.result(self.sync(f"__le16 x=cpu_to_le16({value});"))["status"], "insufficient")
        self.assertEqual(self.result(self.sync("__le16 x=cpu_to_le16(65535);"))["status"], "matched_endian_scalar")

    def test_conversion_source_address_escape_refuses(self):
        self.assertEqual(self.result(self.sync("adjust(&host); __le32 x=cpu_to_le32(host);"))["status"], "insufficient")

    def test_branch_filled_host_source_remains_explicitly_value_unproved(self):
        source = "void send(void) { u32 host; if(flag) host=obj->a; else host=0; __le32 x=cpu_to_le32(host); __hci_cmd_sync(dev,OP,sizeof(x),&x,T); }"
        finding = self.result(source)
        self.assertEqual(finding["status"], "matched_endian_scalar", finding)
        self.assertEqual(finding["source_value_paths"], "not_proven")

    def test_source_later_encoding_assignment_refuses(self):
        source = "void send(void) { u32 host=1; host=cpu_to_le32(7); __le32 x=cpu_to_le32(host); __hci_cmd_sync(dev,OP,sizeof(x),&x,T); }"
        self.assertEqual(self.result(source)["status"], "insufficient")

    def test_no_consumer_file_no_proof(self):
        report = outbound.analyze_files("driver.c", {"driver.c": self.sync()})
        self.assertEqual(report["findings"][0]["status"], "insufficient")

    def test_transformed_consumer_pointer_refuses(self):
        request = REQUEST.replace("skb_put_data(skb, param, plen)", "skb_put_data(skb, param + 1, plen)")
        self.assertEqual(self.result(self.sync(), request)["status"], "insufficient")

    def test_modified_forward_parameter_refuses(self):
        request = REQUEST.replace("if (plen) skb_put_data", "plen += 1; if (plen) skb_put_data")
        self.assertEqual(self.result(self.sync(), request)["status"], "insufficient")

    def test_shadowed_forward_parameter_refuses(self):
        request = REQUEST.replace("if (plen) skb_put_data", "{ u32 plen = 2; if (plen) skb_put_data")
        request = request.replace("return skb; }", "return skb; } }")
        self.assertEqual(self.result(self.sync(), request)["status"], "insufficient")

    def test_opaque_consumer_pointer_call_refuses(self):
        request = REQUEST.replace("if (plen) skb_put_data", "scramble(param); if (plen) skb_put_data")
        self.assertEqual(self.result(self.sync(), request)["status"], "insufficient")

    def test_consumer_alias_cast_content_write_refuses(self):
        request = REQUEST.replace("if (plen) skb_put_data", "const void *p=param; ((u8 *)p)[0]=0; if (plen) skb_put_data")
        finding = self.result(self.sync(), request)
        self.assertEqual(finding["status"], "insufficient", finding)
        self.assertIn("pointer referenced outside", finding["consumer"]["reason"])

    def test_consumer_direct_cast_content_write_refuses(self):
        request = REQUEST.replace("if (plen) skb_put_data", "((u8 *)param)[0]=0; if (plen) skb_put_data")
        self.assertEqual(self.result(self.sync(), request)["status"], "insufficient")

    def test_missing_memcpy_refuses(self):
        skbuff = SKBUFF.replace("memcpy(tmp, data, len)", "special_copy(tmp, data, len)")
        self.assertEqual(self.result(self.sync(), skbuff=skbuff)["status"], "insufficient")

    def test_duplicate_consumer_definition_refuses(self):
        skbuff = SKBUFF + "void *skb_put_data(struct sk_buff *skb,const void *data,unsigned int len) { memcpy(tmp,data,len); }"
        self.assertEqual(self.result(self.sync(), skbuff=skbuff)["status"], "insufficient")

    def test_terminal_length_mismatch_refuses(self):
        skbuff = SKBUFF.replace("memcpy(tmp, data, len)", "memcpy(tmp, data, len+1)")
        self.assertEqual(self.result(self.sync(), skbuff=skbuff)["status"], "insufficient")

    def test_source_hash_and_evidence_offsets_are_retained(self):
        source = "\n" + self.sync()
        report = self.report(source)
        finding = report["findings"][0]
        self.assertEqual(finding["call"]["line"], 2)
        self.assertEqual(finding["call"]["source_sha256"], outbound.digest(source))
        self.assertEqual(len(report["files_read"]), 3)


if __name__ == "__main__":
    unittest.main()
