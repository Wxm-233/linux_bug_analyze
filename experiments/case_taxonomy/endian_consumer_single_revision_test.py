"""Focused tests for the single-revision endian-consumer triage prototype."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import endian_consumer_single_revision as probe


HEADER = """struct disk_inode {
    __le32 flags;
    __le16 mode;
    __le64 size;
    __le32 count;
    struct { __le32 nested; } inner;
};
"""


class EndianConsumerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fields = probe.typed_fields({"fs/demo/disk.h": HEADER})

    def inspect(self, condition: str) -> list[tuple[str, str]]:
        source = ("static int inspect(struct disk_inode *di)\n{\n"
                  f"    if ({condition}) return 1;\n"
                  "    return 0;\n}\n")
        findings = probe.analyze_source("fs/demo/inspect.c", source, self.fields)
        return [(item["field"], item["status"]) for item in findings]

    def test_host_bitmask_and_mode_are_review_leads(self) -> None:
        self.assertEqual(self.inspect("di->flags & FLAG"), [("flags", "candidate")])
        self.assertEqual(self.inspect("S_ISLNK(di->mode)"), [("mode", "candidate")])

    def test_same_representation_masks_are_not_flagged(self) -> None:
        self.assertEqual(self.inspect("di->flags & cpu_to_le32(FLAG)"),
                         [("flags", "normal")])
        self.assertEqual(self.inspect("cpu_to_le32(FLAG) & di->flags"),
                         [("flags", "normal")])

    def test_conversion_and_zero_tests(self) -> None:
        self.assertEqual(self.inspect("le32_to_cpu(di->flags) & FLAG"),
                         [("flags", "normal")])
        self.assertEqual(self.inspect("di->count == 0"), [("count", "normal")])
        self.assertEqual(self.inspect("!di->count"), [("count", "normal")])
        self.assertEqual(self.inspect("S_ISLNK(di->mode) && di->size && !di->count"),
                         [("mode", "candidate"), ("size", "normal"),
                          ("count", "normal")])

    def test_ambiguous_expression_is_not_guessed(self) -> None:
        self.assertEqual(self.inspect("di->flags + offset"),
                         [("flags", "insufficient")])
        self.assertNotIn(("nested", "flags"), self.fields)

    def test_raw_copy_and_comments_are_out_of_scope(self) -> None:
        source = ("static void copy(struct disk_inode *di) {\n"
                  "  /* if (di->flags & BAD) */\n"
                  "  memcpy(dst, &di->flags, sizeof(di->flags));\n}\n")
        self.assertEqual(probe.analyze_source("fs/demo/copy.c", source, self.fields), [])

    def test_local_include_reads_only_supplied_revision(self) -> None:
        source = '#include "disk.h"\nstatic int inspect(struct disk_inode *di) { if (di->flags & X) return 1; return 0; }\n'
        seen: list[tuple[str, str]] = []

        def fake_git_file(_repo: Path, revision: str, path: str) -> str | None:
            seen.append((revision, path))
            return {"fs/demo/inspect.c": source, "fs/demo/disk.h": HEADER}.get(path)

        with patch.object(probe, "git_file", side_effect=fake_git_file):
            report = probe.analyze_revision(Path("/unused"), "abcdef123^", "fs/demo/inspect.c")
        self.assertEqual(seen, [("abcdef123^", "fs/demo/inspect.c"),
                                ("abcdef123^", "fs/demo/disk.h")])
        self.assertEqual(report["counts"]["candidate"], 1)

    def test_previously_reviewed_ocfs2_development_pair(self) -> None:
        linux = Path("/root/repos/linux")
        if not linux.is_dir():
            self.skipTest("local Linux Git checkout unavailable")
        commit = "c9dff86eb78a4b6b02b1e407993c946ccaf9bfb4"
        by_revision = {}
        for name, revision in (("parent", commit + "^"), ("fix", commit)):
            report = probe.analyze_revision(linux, revision, "fs/ocfs2/inode.c")
            by_revision[name] = {
                item["field"]: item["status"] for item in report["findings"]
                if item["function"] == "ocfs2_dinode_has_extents"
            }
        self.assertEqual(by_revision["parent"], {
            "i_flags": "candidate", "i_mode": "candidate", "i_size": "normal",
            "i_clusters": "normal", "i_dyn_features": "candidate",
        })
        self.assertEqual(by_revision["fix"], {
            "i_flags": "normal", "i_mode": "normal", "i_size": "normal",
            "i_clusters": "normal", "i_dyn_features": "normal",
        })


if __name__ == "__main__":
    unittest.main()
