"""Focused tests for the one-revision field/consumer prototype."""

from __future__ import annotations

import unittest

from representation_field_consumer import analyze_one_revision, typed_consumers


PREFIX = """struct bversion { __u32 hi; __u64 lo; } __packed;
struct bkey {
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
    struct bversion bversion;
#elif __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    struct bversion {big_name};
#endif
} __packed;
#define bkey_format_field(name, field) sizeof(((struct bkey *) NULL)->field)
#define BKEY_FORMAT_CURRENT bkey_format_field(VERSION_HI, bversion.hi)
"""


def analyze(header: str, *, big_cc: str = "s390x-linux-gnu-gcc") -> dict:
    return analyze_one_revision(
        header,
        'config BCACHEFS_FS\n\tdepends on BLOCK\n',
        'obj-$(CONFIG_BCACHEFS_FS) += bcachefs.o\nbcachefs-y := bkey.o\n',
        'source "fs/bcachefs/Kconfig"\n',
        '#include "bkey.h"\nconst int x = BKEY_FORMAT_CURRENT;\n',
        revision="single-fixture-revision", format_path="fs/bcachefs/bcachefs_format.h",
        profiles={"little": ("gcc", "little"), "big": (big_cc, "big")},
    )


class FieldConsumerTest(unittest.TestCase):
    def test_mismatched_big_endian_member_is_candidate(self) -> None:
        result = analyze(PREFIX.replace("{big_name}", "version"))
        self.assertEqual(result["summary"]["candidate_paths"], 1)
        item = result["field_checks"][0]
        self.assertEqual(item["profiles"]["little"]["status"], "compiled")
        self.assertEqual(item["profiles"]["big"]["missing_member"], "bversion")
        self.assertEqual(result["build_paths"]["BKEY_FORMAT_CURRENT"]["status"],
                         "static_build_path_found")
        self.assertEqual({m["name"]: m["recognized_profiles"]
                          for m in item["direct_struct_members"]},
                         {"bversion": ["little"], "version": ["big"]})

    def test_same_name_in_both_branches_is_normal_for_expression(self) -> None:
        result = analyze(PREFIX.replace("{big_name}", "bversion"))
        self.assertEqual(result["summary"]["normal_paths"], 1)
        self.assertEqual(result["summary"]["candidate_paths"], 0)

    def test_unrecognized_field_expression_is_refused(self) -> None:
        header = PREFIX.replace("{big_name}", "version").replace(
            "bkey_format_field(VERSION_HI, bversion.hi)",
            "bkey_format_field(VERSION_HI, choose_field())")
        consumers, refusals = typed_consumers(header)
        self.assertFalse(consumers)
        self.assertEqual(len(refusals), 1)

    def test_conditionally_used_consumer_is_refused(self) -> None:
        header = PREFIX.replace("{big_name}", "version").replace(
            "#define BKEY_FORMAT_CURRENT bkey_format_field(VERSION_HI, bversion.hi)",
            "#ifdef CONFIG_ONLY_ON_ONE_ARCH\n"
            "#define BKEY_FORMAT_CURRENT bkey_format_field(VERSION_HI, bversion.hi)\n"
            "#endif")
        consumers, refusals = typed_consumers(header)
        self.assertFalse(consumers)
        self.assertEqual(refusals[0]["reason"],
                         "consumer is under an unproved preprocessor guard")

    def test_missing_compiler_does_not_become_candidate(self) -> None:
        result = analyze(PREFIX.replace("{big_name}", "version"),
                         big_cc="missing-s390-compiler-for-test")
        self.assertEqual(result["summary"]["candidate_paths"], 0)
        self.assertEqual(result["summary"]["insufficient_paths"], 1)

    def test_wrong_endian_compiler_does_not_become_candidate(self) -> None:
        result = analyze(PREFIX.replace("{big_name}", "version"), big_cc="gcc")
        self.assertEqual(result["summary"]["candidate_paths"], 0)
        self.assertEqual(result["summary"]["insufficient_paths"], 1)


if __name__ == "__main__":
    unittest.main()
