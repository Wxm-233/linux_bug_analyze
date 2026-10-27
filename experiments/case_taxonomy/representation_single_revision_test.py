"""Boundary checks for the one-revision representation scanner."""

import shutil
import unittest

from representation_single_revision import analyze_single_header


HEADER = """/* A deliberately packed wire format can still be a candidate. */
struct item {
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
    __u32 value;
#elif __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    __u32 value;
#endif
} __packed __aligned(4);
struct ordinary {
    __u8 prefix[4];
    struct item value;
} __packed;
/* Intentional packed prefix; the scanner must not claim a defect. */
struct wire {
    __u8 prefix[3];
    struct item value;
} __packed;
struct unfamiliar {
    union { struct item value; __u32 raw; } u;
} __packed;
"""


class SingleRevisionTest(unittest.TestCase):
    @unittest.skipUnless(all(shutil.which(tool) for tool in
                             ("gcc", "s390x-linux-gnu-gcc", "qemu-s390x")),
                         "two compiler ABIs unavailable")
    def test_both_real_abis_classify_the_same_fixture(self):
        result = analyze_single_header(
            HEADER, path="example.h", revision="A",
            profiles={"little": ("gcc", [], "little"),
                      "big": ("s390x-linux-gnu-gcc",
                              ["qemu-s390x", "-L", "/usr/s390x-linux-gnu"],
                              "big")})
        by_parent = {site["embedded_in"]: site for site in result["sites"]}
        self.assertEqual(by_parent["ordinary"]["classification"], "normal")
        self.assertEqual(by_parent["wire"]["classification"], "candidate")
        self.assertEqual(set(by_parent["wire"]["alignment_review_profiles"]),
                         {"little", "big"})
        self.assertEqual(by_parent["wire"]["measurements"]["big"]["status"],
                         "measured")

    @unittest.skipUnless(shutil.which("gcc"), "native GCC unavailable")
    def test_normal_packed_candidate_and_refusal(self):
        result = analyze_single_header(
            HEADER, path="example.h", revision="one-old-revision",
            profiles={"native_little": ("gcc", [], "little")})
        by_parent = {site["embedded_in"]: site for site in result["sites"]}
        self.assertEqual(by_parent["ordinary"]["classification"], "normal")
        self.assertEqual(by_parent["wire"]["classification"], "candidate")
        self.assertEqual(by_parent["wire"]["alignment_review_profiles"],
                         ["native_little"])
        self.assertEqual(by_parent["unfamiliar"]["classification"], "insufficient")
        self.assertIn("unsupported union", by_parent["unfamiliar"]["reason"])
        self.assertEqual(by_parent["wire"]["field_lines"], [16])
        self.assertEqual(result["summary"],
                         {"candidate": 1, "normal": 1, "insufficient": 1})
        self.assertEqual(result["source"]["revision"], "one-old-revision")
        self.assertNotIn("fixed_revision", result["source"])
        self.assertEqual(result["field_name_consistency"], "not_checked")

    @unittest.skipUnless(shutil.which("gcc"), "native GCC unavailable")
    def test_wrong_endian_compiler_refuses_instead_of_measuring(self):
        result = analyze_single_header(
            HEADER, path="example.h", revision="A",
            profiles={"claimed_big": ("gcc", [], "big")})
        ordinary = next(site for site in result["sites"]
                        if site["embedded_in"] == "ordinary")
        self.assertEqual(ordinary["classification"], "insufficient")
        self.assertEqual(ordinary["measurements"]["claimed_big"]["status"],
                         "insufficient")

    def test_missing_toolchain_and_empty_profiles_refuse(self):
        missing = analyze_single_header(
            HEADER, path="example.h", revision="A",
            profiles={"little": ("absent-compiler-for-test", [], "little")})
        self.assertEqual(missing["summary"]["insufficient"], 3)
        empty = analyze_single_header(
            HEADER, path="example.h", revision="A", profiles={})
        self.assertEqual(empty["summary"]["insufficient"], 3)


if __name__ == "__main__":
    unittest.main()
