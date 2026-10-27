"""Boundary tests for the restricted representation-layout extractor."""

import shutil
import unittest

from bcachefs_auto_layout_extract import (
    analyze_texts,
    declarations,
    embedding_sites,
)


OLD = """/* struct bogus { } __packed __aligned(4); */
struct item {
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
    __u32 value;
#elif __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    __u32 value;
#endif
} __packed __aligned(4);
struct container {
    __u8 prefix[8];
    struct item value;
} __packed;
struct unsupported {
    union { struct item value; __u32 raw; } u;
} __packed;
"""

FIXED = OLD.replace("__u32 value;\n#endif\n} __packed __aligned(4);",
                    "__u32 value;\n#endif\n} __packed __aligned(8);")


class RepresentationExtractorTest(unittest.TestCase):
    def test_comment_is_not_struct_and_field_locations_are_source_lines(self):
        decls = declarations(OLD)
        self.assertNotIn("bogus", decls)
        self.assertEqual(decls["item"].line, 2)
        site = embedding_sites(OLD, decls, "item")
        self.assertEqual({(s["parent"], s["field"]) for s in site},
                         {("container", "value"), ("unsupported", "value")})
        self.assertEqual(next(s["lines"] for s in site if s["parent"] == "container"), [11])

    @unittest.skipUnless(shutil.which("gcc"), "native GCC unavailable")
    def test_changed_type_can_have_normal_and_refused_sites(self):
        result = analyze_texts(OLD, FIXED, path="fixture.h", old_revision="A",
                               fixed_revision="B", profiles={"native": ("gcc", [])})
        by_parent = {entry["embedded_in"]: entry for entry in result["candidates"]}
        self.assertEqual(by_parent["container"]["classification"], "normal_control")
        self.assertEqual(by_parent["unsupported"]["classification"], "insufficient")
        self.assertIn("unsupported union", by_parent["unsupported"]["measurements"]["old"]["native"]["reason"])

    def test_unchanged_type_is_excluded_even_with_packed_alignment(self):
        result = analyze_texts(OLD, OLD, path="fixture.h", old_revision="A",
                               fixed_revision="A", profiles={})
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["excluded_unchanged"][0]["type"], "item")

    def test_comment_only_change_is_not_candidate(self):
        result = analyze_texts(OLD, OLD.replace("struct item {", "/* note */\nstruct item {"),
                               path="fixture.h", old_revision="A",
                               fixed_revision="B", profiles={})
        self.assertEqual(result["candidates"], [])


if __name__ == "__main__":
    unittest.main()
