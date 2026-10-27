"""Offline tests for the narrow producer-side review rule."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import endian_producer_single_revision as producer  # noqa: E402


class EndianProducerTests(unittest.TestCase):
    def outcomes(self, source: str) -> list[tuple[str, str]]:
        return [(item["field"], item["status"])
                for item in producer.analyze_text(source)["findings"]]

    def test_host_write_requires_downstream_object_call(self):
        source = """
struct wire { __le32 reg; __be16 mode; };
int send(u32 reg, u16 mode) {
    struct wire msg = { .reg = reg, .mode = mode };
    transport(&msg, sizeof(msg));
    return 0;
}
"""
        report = producer.analyze_text(source)
        self.assertEqual(report["counts"],
                         {"candidate": 2, "normal": 0, "insufficient": 0})
        self.assertTrue(all(item["interface_evidence"] for item in report["findings"]))

    def test_explicit_conversion_and_same_representation_are_local_normals(self):
        source = """
struct wire { __le32 reg; };
int send(u32 host, __le32 wire_reg) {
    struct wire first = { .reg = cpu_to_le32(host) };
    struct wire second = { .reg = wire_reg };
    transport(&first);
    transport(&second);
    return 0;
}
"""
        self.assertEqual(self.outcomes(source), [("reg", "normal"), ("reg", "normal")])

    def test_direct_member_assignment_and_unknown_rhs(self):
        source = """
struct wire { __be32 code; };
int send(u32 host) {
    struct wire msg;
    msg.code = host;
    msg.code = get_code();
    transport(&msg);
    return 0;
}
"""
        self.assertEqual(self.outcomes(source),
                         [("code", "candidate"), ("code", "insufficient")])

    def test_refuse_without_interface_or_with_wrong_conversion(self):
        source = """
struct wire { __le32 code; };
void local(u32 host) {
    struct wire msg = { .code = host };
}
void mismatch(u32 host, __le32 encoded) {
    struct wire msg = { .code = cpu_to_be32(host) };
    transport(&msg);
    struct wire another = { .code = cpu_to_le32(encoded) };
    transport(&another);
}
"""
        self.assertEqual(self.outcomes(source),
                         [("code", "insufficient"), ("code", "insufficient"),
                          ("code", "insufficient")])

    def test_reject_nested_field_and_ignore_comment(self):
        source = """
struct wire { struct { __le32 inner; } nested; __le32 reg; };
int send(u32 host) {
    struct wire msg = { .inner = host, .reg = host };
    /* msg.reg = host; */
    transport(&msg);
}
"""
        self.assertEqual(self.outcomes(source), [("reg", "candidate")])

    def test_field_address_or_size_alone_is_not_object_passing_evidence(self):
        source = """
struct wire { __le32 reg; };
void local(u32 host) {
    struct wire msg = { .reg = host };
    inspect(&msg.reg);
    log_size(sizeof(msg));
}
"""
        self.assertEqual(self.outcomes(source), [("reg", "insufficient")])

    def test_revision_reader_gets_only_given_revision_and_file(self):
        source = "struct wire { __le32 reg; };\n"
        with patch.object(producer, "source_tree",
                          return_value=({"drivers/x.c": source}, [])) as read:
            report = producer.analyze_revision(Path("/repo"), "abcd1234^", "drivers/x.c")
        read.assert_called_once_with(Path("/repo"), "abcd1234^", "drivers/x.c")
        self.assertEqual(report["files_read"],
                         [{"path": "drivers/x.c", "sha256": producer.sha256(source)}])

    def test_same_revision_quoted_header_declaration(self):
        source = """
#include "wire.h"
int send(u32 host) {
    struct wire msg = { .reg = host };
    transport(&msg);
}
"""
        report = producer.analyze_text(
            source, "drivers/x.c",
            {"drivers/x.c": source, "drivers/wire.h": "struct wire { __be32 reg; };\n"},
        )
        self.assertEqual(report["counts"]["candidate"], 1)
        self.assertEqual(report["findings"][0]["declaration"][0]["file"],
                         "drivers/wire.h")


if __name__ == "__main__":
    unittest.main()
