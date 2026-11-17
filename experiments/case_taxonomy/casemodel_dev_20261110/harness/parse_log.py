#!/usr/bin/env python3
"""解析 @@SH 日志；自测附加行不进入正式比较结果。"""
import json
import re
import sys
from pathlib import Path


def parse_log(text):
    result = {"probe": {}, "cases": {}, "taint_changed": None, "complete": False}
    active = False
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if line == "@@SH BEGIN":
            active = True
            continue
        if line == "@@SH END":
            result["complete"] = True
            active = False
            continue
        if not active or not line.startswith("{"):
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"第 {lineno} 行 JSON 无效: {exc.msg}") from exc
        if "harness_error" in item:
            # Claude 改：逐条记录，不让单个用例的准备失败使整份日志作废
            result.setdefault("harness_errors", []).append(item)
            continue
        if "r" in item and "id" in item:
            case_id = str(item["id"])
            if type(item["id"]) is not int or item["id"] < 0 or case_id in result["cases"]:
                raise ValueError(f"第 {lineno} 行用例 id 无效或重复")
            if not isinstance(item["r"], str) or type(item.get("t")) is not int or item["t"] not in (-1, 0, 1):
                raise ValueError(f"第 {lineno} 行 r/t 无效")
            buffers = item["b"]
            previous = -1
            for entry in buffers if buffers is not None else []:
                if not isinstance(entry, list) or len(entry) != 3:
                    raise ValueError(f"第 {lineno} 行 b 无效")
                ai, count, digest = entry
                if type(ai) is not int or not previous < ai < 6:
                    raise ValueError(f"第 {lineno} 行缓冲区参数下标无效")
                _check_delta(count, digest, lineno)
                previous = ai
            pool = item["pool"]
            if pool is not None and pool != [None, None]:
                if not isinstance(pool, list) or len(pool) != 2:
                    raise ValueError(f"第 {lineno} 行 pool 无效")
                _check_delta(*pool, lineno)
            entry = [item["r"], item["t"], buffers, pool]
            if "s" in item:  # casemodel: structured-buffer observations (executor v2)
                entry.append(item["s"])
            result["cases"][case_id] = entry
        elif "taint_changed" in item:
            result["taint_changed"] = item["taint_changed"]
        elif "probe" in item:
            name = item["probe"]
            if name == "pmu_events":
                result["probe"].setdefault(name, {})[item["pmu"]] = item["value"]
            elif name == "cpuinfo":
                result["probe"].setdefault(name, {})[item["key"]] = item["value"]
            else:
                result["probe"][name] = item["value"]
    return result


def _check_delta(count, digest, lineno):
    if type(count) is not int or count < 0 or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{8}", digest):
        raise ValueError(f"第 {lineno} 行变化计数/哈希无效")


def main():
    if len(sys.argv) != 2:
        print("用法: parse_log.py <日志>", file=sys.stderr)
        return 2
    try:
        parsed = parse_log(Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(parsed, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
