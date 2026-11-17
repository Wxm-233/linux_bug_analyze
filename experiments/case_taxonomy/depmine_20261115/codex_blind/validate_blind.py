"""Validate only this annotator's allowed inputs and outputs, offline."""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
SAMPLE = HERE.parent / "show_sample.txt"
CRITERIA = HERE.parent / "criteria.md"
JUDGEMENT = HERE / "codex_judgement.json"
NOTES = HERE / "notes.md"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


sample_rows = re.findall(r"(?m)^\[(\d+)\] ([0-9a-f]{12})  forms=", SAMPLE.read_text(encoding="utf-8"))
assert [int(i) for i, _ in sample_rows] == list(range(1, 61))
expected = [commit for _, commit in sample_rows]
assert len(set(expected)) == 60

rows = json.loads(JUDGEMENT.read_text(encoding="utf-8"))
assert isinstance(rows, list) and len(rows) == 60
assert [row["commit"] for row in rows] == expected
assert len({row["commit"] for row in rows}) == 60
fields = {"commit", "verdict", "direction", "missing", "archs", "why", "read_full_patch", "note"}
patches = []
for (index, commit), row in zip(sample_rows, rows):
    assert set(row) == fields, commit
    assert row["verdict"] in {"是", "不是", "说不清"}, commit
    assert row["read_full_patch"] is True, commit
    assert isinstance(row["why"], str) and len(row["why"]) >= 30, commit
    assert row["note"] is None or isinstance(row["note"], str), commit
    if row["verdict"] == "不是":
        assert all(row[k] is None for k in ("direction", "missing", "archs")), commit
    else:
        assert row["direction"] in {"c2a", "a2c"}, commit
        assert all(isinstance(row[k], str) and row[k].strip() for k in ("missing", "archs")), commit
    patch = HERE / "full_patches" / f"{int(index):02d}_{commit}.patch"
    data = patch.read_bytes()
    content = data.decode("utf-8")
    assert re.match(rf"commit {commit}[0-9a-f]{{28}}\n", content), commit
    assert "\ndiff --git " in content and "\n@@ " in content, commit
    patches.append({
        "index": int(index),
        "commit": commit,
        "path": patch.relative_to(HERE).as_posix(),
        "bytes": len(data),
        "lines": content.count("\n"),
        "sha256": sha256(patch),
        "changed_file_count": content.count("\ndiff --git "),
    })
assert NOTES.is_file() and NOTES.stat().st_size > 0

# Stable, readable JSON formatting; never change labels or their explanations.
JUDGEMENT.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
report = {
    "schema_valid": True,
    "expected_count": 60,
    "actual_count": len(rows),
    "unique_count": len({row["commit"] for row in rows}),
    "exact_input_order": True,
    "read_full_patch_true_count": sum(row["read_full_patch"] is True for row in rows),
    "verdict_counts": dict(Counter(row["verdict"] for row in rows)),
    "criteria_sha256": sha256(CRITERIA),
    "show_sample_sha256": sha256(SAMPLE),
    "codex_judgement_sha256": sha256(JUDGEMENT),
    "notes_sha256": sha256(NOTES),
    "patch_archive_count": len(patches),
    "patch_archive_total_bytes": sum(p["bytes"] for p in patches),
    "patch_archive_total_lines": sum(p["lines"] for p in patches),
    "patches": patches,
}
(HERE / "review_validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in report.items() if k != "patches"}, ensure_ascii=False, indent=2))
