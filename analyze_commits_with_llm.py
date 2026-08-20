#!/usr/bin/env python3
"""兼容入口；实际实现位于 ``linux_bug_analyze`` 包中。"""

from linux_bug_analyze.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
