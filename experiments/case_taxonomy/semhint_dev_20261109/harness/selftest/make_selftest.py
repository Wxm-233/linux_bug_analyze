"""Hand-written self-test cases for sh_init.c (Claude; replaces the part Codex could not finish).
    python make_selftest.py -> selftest_cases_<arch>.txt  (first line "# SH_SELFTEST" turns on debug output)"""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
NR = json.loads((HERE.parents[1] / "gen/nr_tables.json").read_text())
CASES = [  # (id, syscall, tmpl, args, what I expect)
    (1, "getpid", "none", [], "small number (pid)"),
    (2, "getpid", "none", ["s:self"], "arg0"),
    (3, "read", "none", ["f:piperd", "b:a:0", "i:40"], "16, buffer 0..15 changed (16 positions)"),
    (4, -1, "none", [], "ENOSYS"),
    (5, "read", "none", ["f:pipeblockrd", "b:z:0", "i:40"], "timeout"),
    (6, "mmap", "occ:0:1", ["i:40000000", "i:1000", "i:3", "i:22", "f:neg", "i:0"], "t=1, big (placed elsewhere)"),
    (7, "mmap", "adj:0:1", ["i:40000000", "i:1000", "i:3", "i:22", "f:neg", "i:0"], "t=1, arg0 (hint free)"),
    (8, "mmap", "none", ["i:40000000", "i:1000", "i:3", "i:22", "f:neg", "i:0"], "t=-1, arg0"),
    (9, "recvmsg", "none", ["f:udgram", "b:g:0", "i:0"], "some errno or count; graph identical across archs"),
    (10, "write", "none", ["f:file", "b:z:1", "i:a"], "10"),
    (11, "openat", "none", ["f:atcwd", "p:f", "i:2"], "small fd number"),
    (12, "futex", "none", ["o:z:62", "i:1", "i:1", "i:0", "i:0", "i:0"], "EFAULT on current kernels"),
    (13, "read", "none", ["f:piperd", "b:a:8184", "i:40"], "partial 8 or EFAULT"),
    (14, "fcntl", "none", ["f:eventfd", "i:3"], "number (F_GETFL)"),
    (15, "fcntl", "none", ["f:memfd", "i:3"], "number"),
    (16, "fcntl", "none", ["f:udp", "i:3"], "number"),
    (17, "fcntl", "none", ["f:ustream", "i:3"], "number"),
    (18, "fcntl", "none", ["f:dir", "i:3"], "number"),
    (19, "fcntl", "none", ["f:pipewr", "i:3"], "number"),
    (20, "fcntl", "none", ["f:unopen", "i:3"], "EBADF"),
    (21, "fcntl", "none", ["f:neg", "i:3"], "EBADF"),
    (22, "faccessat", "none", ["f:atcwd", "p:d", "i:0"], "0"),
    (23, "faccessat", "none", ["f:atcwd", "p:nx", "i:0"], "ENOENT"),
    (24, "faccessat", "none", ["f:atcwd", "p:empty", "i:0"], "ENOENT"),
    (25, "faccessat", "none", ["f:atcwd", "p:null", "i:0"], "EFAULT"),
    (26, "read", "none", ["f:file", "b:g:0", "i:100"], "100; pool unchanged"),
    (27, "getppid", "none", ["o:a:0"], "1"),
    (28, "write", "none", ["f:file", "o:a:63", "i:8"], "EFAULT"),
    (29, "mkdirat", "none", ["f:atcwd", "p:nx", "i:1ff"], "0 (then /tmp reset: case 30 must see ENOENT)"),
    (30, "faccessat", "none", ["f:atcwd", "p:nx", "i:0"], "ENOENT (independence)"),
    (31, "read", "none", ["f:piperd", "i:ffffffffffffffff", "i:40"], "EFAULT"),
]
for arch in ("riscv", "arm64", "x86_64"):
    lines = ["# SH_SELFTEST"]
    for cid, sc, tmpl, args, _ in CASES:
        nr = sc if isinstance(sc, int) else NR[arch][sc]
        lines.append(f"{cid} {nr} {tmpl} " + " ".join((args + ["i:0"] * 6)[:6]))
    (HERE / f"selftest_cases_{arch}.txt").write_text("\n".join(lines) + "\n")
(HERE / "selftest_expect.json").write_text(json.dumps({c[0]: c[4] for c in CASES}, ensure_ascii=False, indent=0))
print(len(CASES), "cases")
