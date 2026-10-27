import json
import tempfile
import unittest
from pathlib import Path

from linux_bug_analyze import round_close as rc

PLAN_TEXT = """# 接口验证后续规划

| 家族 | 状态 |
| --- | --- |
| A | old status |

## 阶段记录

| 日期 | 内容 |
| --- | --- |
| d1 | r1 |

## 当前执行顺序

old order paragraph.

## 其他
"""


class RoundCloseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.ws = base / "ws"
        (self.ws / "日志").mkdir(parents=True)
        for n in rc.NOTES:
            (self.ws / n).write_text("# " + n + "\n\n## old\n\nold body\n", encoding="utf-8")
        (self.ws / rc.PLAN).write_text(PLAN_TEXT, encoding="utf-8")
        (self.ws / "日志" / "2026-10-27.md").write_text("# log\n", encoding="utf-8")
        self.round = self.ws / "inner" / "exp" / "r1"
        self.round.mkdir(parents=True)
        (self.round / "result.json").write_text("{}\n", encoding="utf-8")
        self.mirror = base / "mirror"
        self.mirror.mkdir()
        for n in rc.NOTES:
            (self.mirror / n).write_bytes((self.ws / n).read_bytes())
        self.spec = {"section": "## 10月27日 最新进展：测试\n\n正文。", "log_date": "2026-10-27",
                     "plan_replacements": [["| A | old status |", "| A | new status |"]],
                     "plan_row": "| d2 | r2 |", "order_paragraph": "new order paragraph."}

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_round(self):
        self.assertEqual(rc.workspace_of(self.round), self.ws.resolve())
        rc.prepare(self.round)
        rc.apply(self.round, self.spec)
        for n in rc.NOTES:
            text = (self.ws / n).read_text(encoding="utf-8")
            self.assertTrue(text.startswith("# " + n + "\n\n## 10月27日 最新进展：测试\n\n正文。\n\n" + rc.HISTORY_LINE + "\n\n## old"))
        plan = (self.ws / rc.PLAN).read_text(encoding="utf-8")
        self.assertIn("| A | new status |", plan)
        self.assertIn("| d2 | r2 |\n\n## 当前执行顺序\n\nnew order paragraph.\n\n## 其他", plan)
        self.assertTrue((self.ws / "日志" / "2026-10-27.md").read_text(encoding="utf-8").endswith("正文。\n"))
        self.assertFalse(rc.verify(self.ws, str(self.mirror))["consistent"])
        receipt = rc.sync(self.round, str(self.mirror))
        self.assertEqual(receipt["status"], "synced")
        self.assertTrue(rc.verify(self.ws, str(self.mirror))["consistent"])
        m = rc.manifest(self.round, {"n": 1})
        self.assertIn("result.json", m["files"])
        self.assertNotIn("notes_sync.json", m["files"])

    def test_guards(self):
        rc.prepare(self.round)
        with self.assertRaises(rc.CloseError):
            rc.prepare(self.round)
        (self.ws / rc.NOTES[0]).write_text("changed\n", encoding="utf-8")
        with self.assertRaises(rc.CloseError):
            rc.apply(self.round, self.spec)

    def test_sync_refuses_unexpected_mirror(self):
        rc.prepare(self.round)
        rc.apply(self.round, self.spec)
        (self.mirror / rc.NOTES[1]).write_text("someone else edited\n", encoding="utf-8")
        with self.assertRaises(rc.CloseError):
            rc.sync(self.round, str(self.mirror))
        self.assertEqual((self.mirror / rc.NOTES[1]).read_text(encoding="utf-8"), "someone else edited\n")

    def test_bad_spec(self):
        rc.prepare(self.round)
        bad = dict(self.spec, plan_replacements=[["missing", "x"]])
        with self.assertRaises(rc.CloseError):
            rc.apply(self.round, bad)
        bad = dict(self.spec, section="no heading")
        with self.assertRaises(rc.CloseError):
            rc.apply(self.round, bad)


if __name__ == "__main__":
    unittest.main()
