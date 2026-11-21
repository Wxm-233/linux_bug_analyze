"""Evidence for blind binding expectations (criteria 六.1): reads only source files and the three .config files,
never compile_commands.json or scope outputs. WSL.

    python3 expect_helper.py
For each sampled callee: every definition site (file, head line, '{' line), the enclosing #if/#ifdef stack, and the values of the
CONFIG_ symbols in those conditions for {riscv, arm64, x86_64}.
"""
import json
import sys
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = "/root/repos/linux"
REV = "df2908090cda"
CFG = {}
for a in ("riscv", "arm64", "x86_64"):
    vals = {}
    for ln in open(f"/root/work/boundary_build/{a}_defconfig/.config"):
        m = re.match(r"^(CONFIG_\w+)=(.*)$", ln.strip())
        if m:
            vals[m.group(1)] = m.group(2)
    CFG[a] = vals


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def stack_at(lines, n):
    st = []
    for i in range(n - 1):
        s = lines[i].strip()
        if re.match(r"#\s*(if|ifdef|ifndef)\b", s):
            st.append((i + 1, s))
        elif re.match(r"#\s*(elif|else)\b", s) and st:
            st[-1] = (i + 1, st[-1][1] + "  ⇒ " + s)
        elif re.match(r"#\s*endif\b", s) and st:
            st.pop()
    return st


def main():
    sample = json.loads((HERE / (sys.argv[1] if len(sys.argv) > 1 else "binding_sample.json")).read_text(encoding="utf-8"))
    for x in sample:
        name = x["callee"]
        print("=" * 90)
        print(name, "| caller", x["caller_file"], x["caller_func"], x["line"], "| caller compiled in", x["builds"])
        out = git("grep", "-n", "-E", rf"^[A-Za-z_].*[ *]{name}\s*\(", REV, "--", "*.c", "*.h")
        for ln in out.split("\n"):
            if not ln:
                continue
            _, f, n, text = ln.split(":", 3)
            if text.rstrip().endswith(";"):
                continue  # declaration
            src = git("show", f"{REV}:{f}").split("\n")
            n = int(n)
            brace = next((k + 1 for k in range(n - 1, min(n + 6, len(src))) if "{" in src[k]), None)
            st = stack_at(src, n)
            cfgs = sorted(set(re.findall(r"CONFIG_\w+", " ".join(s for _, s in st))))
            vals = " ".join(f"{c}={{{','.join(CFG[a].get(c, 'n') for a in CFG)}}}" for c in cfgs)
            print(f"  {f}:{n} brace={brace}  {text.strip()[:90]}")
            for ln2, s in st:
                print(f"      #{ln2}: {s[:110]}")
            if vals:
                print(f"      {vals}")


if __name__ == "__main__":
    main()
