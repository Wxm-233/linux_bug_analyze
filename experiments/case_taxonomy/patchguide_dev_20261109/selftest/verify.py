"""Self-test for mine_patches.py + pguide.py on a tiny git repository with dated commits.

    python3 selftest/verify.py        (run in WSL from the round directory)

Fixture history (x86 is the counterpart, riscv the target):
  c1 2020-01-01  initial tree
  c2 2020-02-01  x86 fix in arch_foo: adds check_it() call, p->state write, -EINVAL, and a comment naming fake_fn()
                 -> riscv arch_foo lacks all three: flags (arch_foo, call, check_it), (field, state), (errno, EINVAL);
                    fake_fn is inside a comment: no flag
  c3 2020-03-01  x86 fix in patch_map (static in .c on both sides): adds flush_it(); riscv patch_map already calls it
                 -> nothing
  c4 2020-04-01  x86 change WITHOUT a Fixes: line adds other_fn() to arch_foo -> not mined, nothing
  c5 2020-05-01  x86 fix in x86_helper (arch/x86, called by the candidate arch_bar): adds sync_it() and p->mode = 2;
                 riscv arch_bar reaches sync_it through rv_helper, but never writes mode
                 -> (arch_bar, field, mode) only
  c6 2021-01-01  x86 fix in arch_foo adds late_fn(); the run uses cutoff 2020-12-01 -> nothing
"""
import gzip
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent
WORK = Path("/root/work/pgdev/selftest")
REPO = WORK / "repo"
BIN = "/root/work/checks2/archbound_ext/archbound"
sys.path.insert(0, str(ROUND))
sys.path.insert(0, str(ROUND.parent / "checks2_xarch_20261109"))
import mine_patches  # noqa: E402
import pguide  # noqa: E402
import xcmp  # noqa: E402

EXPECTED = {("arch_foo", "call", "check_it"), ("arch_foo", "field", "state"), ("arch_foo", "errno", "EINVAL"),
            ("arch_bar", "field", "mode")}
CUTOFF = 1606780800  # 2020-12-01

FILES_C1 = {
    "include/linux/s.h": "#ifndef S_H\n#define S_H\n#define EINVAL 22\nstruct s { int state; int mode; };\n"
                         "int check_it(struct s *p);\nvoid flush_it(void);\nvoid sync_it(void);\nvoid other_fn(void);\n"
                         "void late_fn(void);\n#endif\n",
    "common/lib.c": "#include <linux/s.h>\nint check_it(struct s *p) { return p->state; }\nvoid flush_it(void) { }\n"
                    "void sync_it(void) { }\nvoid other_fn(void) { }\nvoid late_fn(void) { }\n",
    "arch/x86/a.c": "#include <linux/s.h>\n"
                    "int arch_foo(struct s *p)\n{\n\treturn 0;\n}\n\n"
                    "static void patch_map(int x)\n{\n\t(void)x;\n}\n\n"
                    "static void x86_helper(struct s *p)\n{\n\t(void)p;\n}\n\n"
                    "void arch_bar(struct s *p)\n{\n\tx86_helper(p);\n}\n\n"
                    "void use_x86(void)\n{\n\tpatch_map(1);\n}\n",
    "arch/riscv/b.c": "#include <linux/s.h>\n"
                      "int arch_foo(struct s *p)\n{\n\treturn 0;\n}\n\n"
                      "static void patch_map(int x)\n{\n\t(void)x;\n\tflush_it();\n}\n\n"
                      "static void rv_helper(struct s *p)\n{\n\t(void)p;\n\tsync_it();\n}\n\n"
                      "void arch_bar(struct s *p)\n{\n\trv_helper(p);\n}\n\n"
                      "void use_rv(void)\n{\n\tpatch_map(1);\n}\n",
}


def git(*args, date=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t")
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    subprocess.run(["git", "-C", str(REPO), *args], check=True, env=env, capture_output=True)


def edit(path, old, new):
    p = REPO / path
    s = p.read_text()
    assert s.count(old) == 1, (path, old)
    p.write_text(s.replace(old, new))


def commit(msg, date):
    git("add", "-A")
    git("commit", "-q", "-m", msg, date=date)


def build_repo():
    if WORK.exists():
        shutil.rmtree(WORK)
    REPO.mkdir(parents=True)
    git("init", "-q")
    for f, s in FILES_C1.items():
        (REPO / f).parent.mkdir(parents=True, exist_ok=True)
        (REPO / f).write_text(s)
    commit("initial", "2020-01-01T00:00:00")
    edit("arch/x86/a.c", "int arch_foo(struct s *p)\n{\n\treturn 0;\n}",
         "int arch_foo(struct s *p)\n{\n\t/* fake_fn() is only mentioned here */\n\tif (!check_it(p))\n\t\treturn -EINVAL;\n"
         "\tp->state = 1;\n\treturn 0;\n}")
    commit("x86: fix arch_foo\n\nFixes: 111111111111 (\"x\")", "2020-02-01T00:00:00")
    edit("arch/x86/a.c", "static void patch_map(int x)\n{\n\t(void)x;\n}", "static void patch_map(int x)\n{\n\t(void)x;\n\tflush_it();\n}")
    commit("x86: fix patch_map\n\nFixes: 222222222222 (\"x\")", "2020-03-01T00:00:00")
    edit("arch/x86/a.c", "\tp->state = 1;\n", "\tp->state = 1;\n\tother_fn();\n")
    commit("x86: cleanup arch_foo", "2020-04-01T00:00:00")
    edit("arch/x86/a.c", "static void x86_helper(struct s *p)\n{\n\t(void)p;\n}",
         "static void x86_helper(struct s *p)\n{\n\t(void)p;\n\tsync_it();\n\tp->mode = 2;\n}")
    commit("x86: fix helper\n\nFixes: 333333333333 (\"x\")", "2020-05-01T00:00:00")
    edit("arch/x86/a.c", "\tother_fn();\n", "\tother_fn();\n\tlate_fn();\n")
    commit("x86: late fix\n\nFixes: 444444444444 (\"x\")", "2021-01-01T00:00:00")


def collect(arch, units):
    bdir = WORK / arch
    bdir.mkdir()
    rows = [{"directory": str(REPO), "file": str(REPO / u),
             "arguments": ["clang", "-c", "-std=gnu11", "-I", "include", "-o", str(bdir / (u.replace("/", "_") + ".o")), u]}
            for u in units]
    (bdir / "compile_commands.json").write_text(json.dumps(rows))
    subprocess.run([BIN, "collect", "-p", str(bdir / "compile_commands.json"), "--root", str(REPO), "--arch", arch,
                    "-j", "2", "--out", str(bdir / "facts.json")], check=True, capture_output=True)
    xcmp.reduce_facts(str(bdir / "facts.json"), str(bdir / "facts.json.gz"))
    return xcmp.load(str(bdir / "facts.json.gz"))


def main():
    build_repo()
    rf = collect("riscv", ["common/lib.c", "arch/riscv/b.c"])
    xf = collect("x86", ["common/lib.c", "arch/x86/a.c"])
    out = WORK / "patches.json.gz"
    mine_patches.mine(str(REPO), "2019-01-01", str(out), ["arch/x86"])
    with gzip.open(out, "rt") as fh:
        mined = json.load(fh)
    flags, summary = pguide.run(rf, str(REPO), "HEAD", {"x86": xf}, {"arch_foo", "arch_bar"}, mined["commits"], CUTOFF)
    got = {(f["target"], f["kind"], f["element"]) for f in flags}
    mined_subjects = sorted(c["subject"] for c in mined["commits"])
    ok = got == EXPECTED and mined_subjects == ["x86: fix arch_foo", "x86: fix helper", "x86: fix patch_map", "x86: late fix"]
    # the riscv-fix extractor on the same machinery: elements of c2 restricted to arch/x86
    c2 = subprocess.run(["git", "-C", str(REPO), "rev-list", "--reverse", "HEAD"], capture_output=True, text=True).stdout.split()[1]
    c2_elems = mine_patches.hunk_elements(str(REPO), c2, ["arch/x86"])
    ext_ok = (len(c2_elems) == 1 and c2_elems[0]["func"] == "arch_foo"
              and c2_elems[0]["added"] == {"call": ["check_it"], "field": ["state"], "errno": ["EINVAL"]})
    ok = ok and ext_ok
    result = {"passed": ok, "missing": sorted(EXPECTED - got), "unexpected": sorted(got - EXPECTED),
              "mined_subjects": mined_subjects, "hunk_elements_c2_ok": ext_ok, "summary": summary, "flags": flags}
    (HERE / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
    print(json.dumps({k: result[k] for k in ("passed", "missing", "unexpected", "mined_subjects", "hunk_elements_c2_ok",
                                              "summary")}, ensure_ascii=False, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
