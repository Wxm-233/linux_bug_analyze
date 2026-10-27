"""Offline tests for v2 producer-side representation review leads."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import representation_producer_v2 as producer  # noqa: E402


class RepresentationProducerV2Tests(unittest.TestCase):
    def test_array_and_nested_fields_with_local_normals(self):
        header = """
struct frame { __be32 length; __be32 address; };
struct descriptor { struct frame frame; };
"""
        source = """
void fill(struct frame *cf, u32 value, dma_addr_t addr, __be32 encoded) {
    cf[1].length = value;
    cf[1].address = upper_32_bits(addr);
    cf[0].length = cpu_to_be32(value);
    cf[0].address = encoded;
    cf[2].length = 0;
    cf[2].address = opaque();
}
void next(struct descriptor *desc, u32 value) {
    desc->frame.length = value;
    desc->frame.address = cpu_to_be32(value);
}
"""
        report = producer.analyze_text(source, "driver.c",
                                       {"driver.c": source, "driver.h": header})
        self.assertEqual(report["counts"],
                         {"candidate": 3, "normal": 4, "insufficient": 1})
        self.assertTrue(all(item["interface_evidence"]
                            for item in report["findings"]
                            if item["status"] == "candidate"))

    def test_alias_slot_requires_adjacency_and_endian_layout(self):
        header = """
struct flow {
    struct {
        u8 command;
        u8 timestamp[3];
        __le16 tag;
    } word;
};
union descriptor { struct flow flow; };
"""
        source = """
void old(union descriptor *desc, u8 command) {
    *(u32 *)&desc->flow.word.command = command;
}
void fixed(union descriptor *desc, u32 value) {
    *(__le32 *)&desc->flow.word.command = cpu_to_le32(value);
}
"""
        report = producer.analyze_text(source, "driver.c",
                                       {"driver.c": source, "driver.h": header})
        aliased = [item for item in report["findings"]
                   if item["assignment_kind"] == "wide_alias_store"]
        self.assertEqual([(item["status"], item["function"]) for item in aliased],
                         [("candidate", "old"), ("normal", "fixed")])

    def test_alias_refuses_untyped_or_nonadjacent_slot(self):
        source = """
struct no_contract { u8 command; u8 timestamp[3]; };
struct wrong_width { u8 command; u8 timestamp[2]; __le16 tag; };
void one(struct no_contract *x, u32 value) {
    *(u32 *)&x->command = value;
}
void two(struct wrong_width *x, u32 value) {
    *(u32 *)&x->command = value;
}
"""
        self.assertEqual(producer.analyze_text(source)["counts"]["candidate"], 0)

    def test_pointer_or_proven_host_source_required(self):
        source = """
struct wire { __be32 value; };
void local(u32 host) {
    struct wire message;
    message.value = host;
}
void unknown(struct wire *message) {
    message->value = get_value();
}
"""
        report = producer.analyze_text(source)
        self.assertEqual([(item["function"], item["status"])
                          for item in report["findings"]],
                         [("local", "insufficient"), ("unknown", "insufficient")])

    def test_wrong_or_unproven_conversion_is_not_normal(self):
        source = """
struct wire { __be32 value; };
void send(struct wire *message, u32 host, __be32 encoded) {
    message->value = cpu_to_le32(host);
    message->value = cpu_to_be32(encoded);
}
"""
        report = producer.analyze_text(source)
        self.assertEqual(report["counts"],
                         {"candidate": 0, "normal": 0, "insufficient": 2})

    def test_direct_v1_write_remains_supported_without_duplicate(self):
        source = """
struct wire { __le32 value; };
void send(u32 host) {
    struct wire message = { .value = host };
    transport(&message);
}
"""
        report = producer.analyze_text(source)
        self.assertEqual(report["counts"],
                         {"candidate": 1, "normal": 0, "insufficient": 0})

    def test_same_revision_reader_adds_one_quoted_include_edge(self):
        source = '#include "first.h"\nvoid f(void) {}\n'
        first = '#include "second.h"\n'
        second = '#include "third.h"\n'
        third = 'struct wire { __be32 value; };\n'
        with patch.object(producer, "source_tree",
                          return_value=({"drivers/a.c": source,
                                         "drivers/first.h": first,
                                         "drivers/second.h": second}, [])), \
             patch.object(producer, "git_file", return_value=third) as reader:
            report = producer.analyze_revision(Path("/repo"), "abcd1234",
                                               "drivers/a.c")
        reader.assert_called_once_with(Path("/repo"), "abcd1234",
                                       "drivers/third.h")
        self.assertEqual(len(report["files_read"]), 4)


if __name__ == "__main__":
    unittest.main()
