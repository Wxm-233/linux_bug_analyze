"""Shared round-closing tool: delivery manifest, SHA-guarded note/plan/log update and mirror sync.

Replaces the per-round copies of close_notes.py / sync_work_notes.py. Every write is guarded by
recorded SHA-256 values; existing receipts are never overwritten.

    python -m linux_bug_analyze.round_close prepare --round DIR [--stats stats.json]
    python -m linux_bug_analyze.round_close apply   --round DIR --spec close_spec.json
    python -m linux_bug_analyze.round_close sync    --round DIR [--target wsl|PATH]
    python -m linux_bug_analyze.round_close verify  [--target wsl|PATH]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

NOTES = ("当前代办.md", "当前研究方向与进展.md", "项目研究与文档写作交接说明.md")
PLAN = "接口验证后续规划.md"
NOTES_SUBDIRS = ("", "md files")  # notes and family plan live in the workspace root or in this subfolder; logs stay in 日志/
HISTORY_LINE = "以下为历史记录，以本节及用户最新指示为准。"
ORDER_HEADING = "\n## 当前执行顺序\n"
WSL_ROOT = "/root"
WSL_SOURCE = "/mnt/d/homework/software/linux_bug_analyze"


class CloseError(RuntimeError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def need(value: Any, reason: str) -> None:
    if not value:
        raise CloseError(reason)


def _holds_notes(folder: Path) -> bool:
    return all((folder / n).is_file() for n in NOTES)


def notes_dir(workspace: Path) -> Path:
    """Folder holding the three working notes and the family plan: the workspace itself or one of NOTES_SUBDIRS."""
    for sub in NOTES_SUBDIRS:
        folder = Path(workspace) / sub if sub else Path(workspace)
        if _holds_notes(folder) and (folder / PLAN).is_file():
            return folder
    raise CloseError("three working notes and family plan not found in " + str(workspace))


def workspace_of(round_dir: Path) -> Path:
    """Outer workspace: the directory above the round directory holding the three working notes, directly or in
    one of NOTES_SUBDIRS."""
    for parent in Path(round_dir).resolve().parents:
        if any(_holds_notes(parent / sub if sub else parent) for sub in NOTES_SUBDIRS):
            return parent
    raise CloseError("workspace with the three working notes not found")


def _source(ws: Path, target: str) -> str:
    """Where the mirror script reads the updated notes: the WSL mount of the notes folder, or the folder itself."""
    nd = notes_dir(ws)
    if target != "wsl":
        return str(nd)
    rel = nd.relative_to(ws).as_posix()
    return WSL_SOURCE if rel == "." else WSL_SOURCE + "/" + rel


def write_json_once(path: Path, value: Any) -> None:
    need(not path.exists(), "preserve existing " + path.name)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def manifest(round_dir: Path, statistics: Mapping[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    round_dir = Path(round_dir)
    skip = {"delivery_manifest.json", "notes_before.json", "notes_update.json", "notes_sync.json", "plan_before.md"}
    files = {p.relative_to(round_dir).as_posix(): sha(p) for p in sorted(round_dir.rglob("*"))
             if p.is_file() and p.name not in skip and "__pycache__" not in p.parts}
    value = {"files": files, "statistics": dict(statistics or {}), **extra}
    (round_dir / "delivery_manifest.json").write_text(json.dumps(value, ensure_ascii=False, indent=1) + "\n",
                                                      encoding="utf-8")
    return value


def prepare(round_dir: Path, workspace: Path | None = None) -> dict[str, Any]:
    round_dir = Path(round_dir)
    ws = Path(workspace) if workspace else workspace_of(round_dir)
    nd = notes_dir(ws)
    before = {"before_sha256": {n: sha(nd / n) for n in NOTES}, "plan_before_sha256": sha(nd / PLAN)}
    write_json_once(round_dir / "notes_before.json", before)
    need(not (round_dir / "plan_before.md").exists(), "preserve existing plan_before.md")
    shutil.copyfile(nd / PLAN, round_dir / "plan_before.md")
    return before


def apply(round_dir: Path, spec: Mapping[str, Any], workspace: Path | None = None) -> dict[str, Any]:
    """spec: section (markdown, without the history line), log_date, plan_replacements [[old,new],...],
    plan_row (one table row or ''), order_paragraph (replaces the first paragraph under 当前执行顺序 or '')."""
    round_dir = Path(round_dir)
    ws = Path(workspace) if workspace else workspace_of(round_dir)
    nd = notes_dir(ws)
    need(not (round_dir / "notes_update.json").exists(), "preserve existing notes_update.json")
    before = json.loads((round_dir / "notes_before.json").read_text(encoding="utf-8"))
    for name, digest in before["before_sha256"].items():
        need(sha(nd / name) == digest, "work note changed during round: " + name)
    plan_path = nd / PLAN
    need(sha(plan_path) == before["plan_before_sha256"] == sha(round_dir / "plan_before.md"), "family plan changed during round")
    section = spec["section"].rstrip("\n") + "\n"
    need(section.startswith("## ") and HISTORY_LINE not in section, "section must be one '## ' block without the history line")
    text = plan_path.read_text(encoding="utf-8")
    for old, new in spec.get("plan_replacements", []):
        need(text.count(old) == 1, "plan replacement not unique: " + old[:30])
        text = text.replace(old, new)
    need(text.count(ORDER_HEADING) == 1, "execution heading not unique")
    if spec.get("plan_row"):
        row = spec["plan_row"].rstrip("\n") + "\n"
        need(row.startswith("| ") and row.rstrip().endswith("|"), "plan_row must be a table row")
        text = text.replace(ORDER_HEADING, row + ORDER_HEADING)
    if spec.get("order_paragraph"):
        start = text.index(ORDER_HEADING) + len(ORDER_HEADING)
        while text[start] == "\n":
            start += 1
        end = text.index("\n\n", start)
        text = text[:start] + spec["order_paragraph"].strip() + text[end:]
    block = section + "\n" + HISTORY_LINE + "\n\n"
    for name in NOTES:
        path = nd / name
        title, rest = path.read_text(encoding="utf-8").split("\n", 1)
        path.write_text(title + "\n\n" + block + rest.lstrip("\n"), encoding="utf-8")
    plan_path.write_text(text, encoding="utf-8")
    log = ws / "日志" / (spec["log_date"] + ".md")
    with log.open("a", encoding="utf-8") as f:
        f.write("\n\n" + section)
    update = {"before_sha256": before["before_sha256"], "after_sha256": {n: sha(nd / n) for n in NOTES},
              "family_plan_sha256": sha(plan_path), "daily_log_sha256": sha(log)}
    write_json_once(round_dir / "notes_update.json", update)
    return update


_REMOTE = r'''from pathlib import Path
import hashlib,json,sys
args=json.loads(sys.stdin.buffer.read().decode('utf-8')); root=Path(args['root']); source=Path(args['source']); rows=args['rows']
h=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for row in rows:
    p=root/row['name']
    if args['mode']=='sync':
        assert h(p)==row['before'],row['name']
        assert h(source/row['name'])==row['after'],row['name']
if args['mode']=='sync':
    for row in rows:
        p=root/row['name']; p.write_bytes((source/row['name']).read_bytes()); assert h(p)==row['after']
sys.stdout.buffer.write(json.dumps({'status':'synced' if args['mode']=='sync' else 'read','files':rows,
                  'mirror':{r['name']:h(root/r['name']) for r in rows}},ensure_ascii=False).encode('utf-8')+bytes([10]))
'''


def _run_remote(payload: dict[str, Any], target: str) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if target == "wsl":
        argv = ["wsl.exe", "-d", "Ubuntu", "--", "python3", "-c", _REMOTE]
    else:
        argv = [sys.executable, "-c", _REMOTE]
    done = subprocess.run(argv, input=data, capture_output=True)
    if done.returncode != 0:
        raise CloseError(done.stderr.decode("utf-8", errors="replace")[-800:])
    return json.loads(done.stdout.decode("utf-8").strip().splitlines()[-1])


def sync(round_dir: Path, target: str = "wsl", workspace: Path | None = None) -> dict[str, Any]:
    round_dir = Path(round_dir)
    ws = Path(workspace) if workspace else workspace_of(round_dir)
    need(not (round_dir / "notes_sync.json").exists(), "preserve existing notes_sync.json")
    update = json.loads((round_dir / "notes_update.json").read_text(encoding="utf-8"))
    nd = notes_dir(ws)
    rows = []
    for name, before in update["before_sha256"].items():
        need(sha(nd / name) == update["after_sha256"][name], "workspace note changed after apply: " + name)
        rows.append({"name": name, "before": before, "after": update["after_sha256"][name]})
    root, source = (WSL_ROOT if target == "wsl" else str(Path(target))), _source(ws, target)
    result = _run_remote({"mode": "sync", "root": root, "source": source, "rows": rows}, target)
    receipt = {"status": result["status"], "files": result["files"]}
    write_json_once(round_dir / "notes_sync.json", receipt)
    return receipt


def verify(workspace: Path, target: str = "wsl") -> dict[str, Any]:
    ws = Path(workspace)
    rows = [{"name": n} for n in NOTES]
    root, source = (WSL_ROOT if target == "wsl" else str(Path(target))), _source(ws, target)
    result = _run_remote({"mode": "read", "root": root, "source": source, "rows": rows}, target)
    local = {n: sha(notes_dir(ws) / n) for n in NOTES}
    return {"consistent": local == result["mirror"], "workspace": local, "mirror": result["mirror"]}


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["prepare", "apply", "sync", "verify", "manifest"])
    p.add_argument("--round", type=Path)
    p.add_argument("--spec", type=Path)
    p.add_argument("--stats", type=Path)
    p.add_argument("--target", default="wsl")
    p.add_argument("--workspace", type=Path)
    a = p.parse_args(argv)
    if a.command == "verify":
        ws = a.workspace or workspace_of(a.round or Path.cwd())
        out = verify(ws, a.target)
    elif a.command == "manifest":
        out = {"files": len(manifest(a.round, json.loads(a.stats.read_text(encoding="utf-8")) if a.stats else {})["files"])}
    elif a.command == "prepare":
        out = prepare(a.round, a.workspace)
    elif a.command == "apply":
        out = apply(a.round, json.loads(a.spec.read_text(encoding="utf-8")), a.workspace)
    else:
        out = sync(a.round, a.target, a.workspace)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
