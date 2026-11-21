"""capguard criteria 三.4: review packets for the current-version candidates (head.json). WSL.

    python3 review_packets.py    -> review/RNN.txt (candidate, the calling function's source, the arch implementation or guarded example)
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import capguard as G  # noqa: E402

C = G.C


def func_src(rev, path, name):
    src = C.cat_files(rev, [path]).get(path, "")
    lines = src.split("\n")
    t = C.tokenize(C.strip(src))
    for fn, params, lo, hi in C.functions(t):
        if fn == name:
            a = t[lo][1]
            j = a - 1
            while j > 0 and lines[j - 1].strip() and not lines[j - 1].startswith(("}", "#")):
                j -= 1
            return "\n".join(lines[j - 1:t[hi][1]])[:5000]
    return f"(definition of {name} not found in {path})"


def main():
    d = json.loads((HERE / "head.json").read_text())
    rev = G.full(d["rev"])
    out = HERE / "review"
    out.mkdir(exist_ok=True)
    for n, c in enumerate(d["cands"], 1):
        parts = [f"候选 R{n:02d}  规则 {c['rule']}  版本 {rev[:12]}",
                 f"位置 {c['file']}:{c['line']}  所在函数 {c['func']}  调用 {c['callee']}  能力判断 {c['pred']}  相关架构 {', '.join(c['archs'])}", "",
                 f"==== 所在函数 {c['func']}（{c['file']}）", func_src(rev, c["file"], c["func"])]
        if c["rule"] == "B1":
            for a in c["archs"]:
                hits = [ln.split(":", 2) for ln in G.git("grep", "-n", "-E", r"^[a-z].*\b" + re.escape(c["callee"]) + r"\(", rev, "--", f"arch/{a}/").splitlines()]
                for h in hits[:2]:
                    p = h[1]                       # git grep at a revision prints rev:path:line:text
                    parts += ["", f"==== 架构 {a} 的实现 {c['callee']}（{p}）", func_src(rev, p, c["callee"])]
        else:
            g, _, _ = c["guarded_example"].partition(":")
            parts += ["", f"==== 被 {c['pred']} 保护的调用处所在函数 {g}", func_src(rev, c["file"], g),
                      "", f"==== 被调用的本文件函数 {c['callee']}", func_src(rev, c["file"], c["callee"])]
        (out / f"R{n:02d}.txt").write_text("\n".join(parts) + "\n")
    print("review packets", len(d["cands"]))


if __name__ == "__main__":
    main()
