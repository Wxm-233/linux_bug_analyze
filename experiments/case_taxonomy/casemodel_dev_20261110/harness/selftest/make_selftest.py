"""Executor v2 self-test cases (expected.md written first).   python make_selftest.py"""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
NR = json.loads((HERE.parents[1] / "gen" / "nr_tables.json").read_text())
MSG = "0:56:z:0:16/8/t1:24/8/i1:32/8/t2:40/8/l2;1:16:z:0:0/8/t3:8/8/l3;2:128:a:{off};3:64:a:0"
ATTR = "0:136:z:0:0/4/i{t}:4/4/i88"
C = [
    (1, "getpid", [], ""), (2, "read", ["f:piperd", "b:a:0", "i:40"], ""),
    (3, "recvmsg", ["f:udgram", "t:0", "i:0"], MSG.format(off=1)),
    (4, "recvmsg", ["f:udgram", "t:0", "i:0"], MSG.format(off=0)),
    (5, "perf_event_open", ["t:0", "i:0", "i:ffffffffffffffff", "f:neg", "i:0"], ATTR.format(t=1)),
    (6, "perf_event_open", ["t:0", "i:0", "i:ffffffffffffffff", "f:neg", "i:0"], ATTR.format(t="7777")),
    (7, "msgctl", ["x:msq", "i:2", "b:z:0"], ""), (8, "semctl", ["x:sem", "i:0", "i:c"], ""),
    (9, "shmctl", ["x:shm", "i:2", "b:z:0"], ""), (10, "timer_gettime", ["x:timer", "b:z:0"], ""),
    (11, "io_destroy", ["x:aio"], ""),
] + [(12 + i, "fcntl", [f"f:{k}", "i:3"], "") for i, k in enumerate(
    ["epoll", "timerfd", "signalfd", "inotify", "pidfd", "perfsw", "mq"])] + [
    (19, "msgget", ["i:0", "i:380"], "")]
for arch in ("riscv", "arm64", "x86_64"):
    lines = ["# SH_SELFTEST"]
    for cid, sc, args, sd in C:
        line = f"{cid} {NR[arch][sc]} none " + " ".join((args + ["i:0"] * 6)[:6])
        if sd:
            line += " | " + sd
        lines.append(line)
    (HERE / f"selftest_cases_{arch}.txt").write_text("\n".join(lines) + "\n")
print(len(C), "cases")
