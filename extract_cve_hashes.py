#!/usr/bin/env python3
"""linux-cve-announce 候选 hash 提取兼容入口。"""

from linux_bug_analyze.cve_cli import main


if __name__ == "__main__":
    raise SystemExit(main())
