"""weakov2 criteria 三.2: mechanical prefilter of mined.json, and annotation packets for 三.3.

    python3 prefilter.py          -> prefiltered.json, packets/<n>.md (commit message + override diff + weak implementation)
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import weakov2 as V  # noqa: E402

W, C = V.W, V.C


def weak_impl(rev, name):
    files = [ln.split(":", 1)[1] for ln in C.git("grep", "-l", "-w", "-e", name, rev, "--", "*.c", ":(exclude)arch").split("\n") if ln]
    for p, s in C.cat_files(rev, files).items():
        if "__weak" not in s:
            continue
        for n, hd, w, st, t, b0, b1 in W.defs_in(s):
            if n == name and w and not st:
                src = C.strip(s).split("\n")
                body = "\n".join(s.split("\n")[t[b0][1] - 4:t[b1][1]])
                return p, W.weak_effects(t, b0, b1, name), body
    return None, [], ""


def func_diff(c, path, name):
    """+/- lines inside function `name` of `path` in commit c, and the hunk text"""
    diff = C.git("show", "--format=", "-U3", "--function-context", c, "--", path)
    plus, minus, text, cur = [], [], [], None
    for ln in diff.split("\n"):
        if ln.startswith(("+++", "---", "diff ", "index ")):
            continue
        if ln.startswith("@@"):
            cur = None
            continue
        if ln[:1] in (" ", "+", "-"):
            m = re.match(r"^[ +-](?:[A-Za-z_][\w\s\*]*?\s+\**)?([A-Za-z_]\w*)\s*\([^;]*$", ln)
            if m and not ln[1:2].isspace():
                cur = m.group(1)
            if cur == name:
                text.append(ln)
                if ln[:1] == "+":
                    plus.append(ln[1:])
                elif ln[:1] == "-":
                    minus.append(ln[1:])
    return plus, minus, "\n".join(text)


def main():
    mined = json.loads((HERE / "mined.json").read_text())
    out = []
    (HERE / "packets").mkdir(exist_ok=True)
    for row in mined:
        c = row["commit"]
        for pf in row["funcs"]:
            path, name = pf.rsplit(":", 1)
            wp, eff, wbody = weak_impl(c + "^", name)
            if not eff:
                continue
            plus, minus, text = func_diff(c, path, name)
            add_eff = sorted({e for e in eff for ln in plus if re.search(r"\b" + re.escape(e) + r"\s*\(", ln)})
            rm_exit = [ln.strip() for ln in minus if re.search(r"\b(return|goto)\b", ln)]
            if not (add_eff or rm_exit):
                continue
            n = len(out) + 1
            msg = C.git("log", "-1", "--format=%B", c)
            item = {"n": n, "commit": c, "subject": row["subject"], "fixes": row["fixes"], "override": f"{path}:{name}",
                    "arch": path.split("/")[1], "weak": wp, "effects": eff, "added_effect_calls": add_eff, "removed_exits": rm_exit}
            out.append(item)
            (HERE / "packets" / f"{n:03d}.md").write_text(
                f"# 样本 {n:03d}\n\n提交 {c}\n\n## 提交说明\n\n```\n{msg.strip()}\n```\n\n"
                f"## 通用实现（{wp}）\n\n```c\n{wbody}\n```\n\n## 架构覆盖实现 {path} 中 {name}() 的改动\n\n```diff\n{text}\n```\n")
    (HERE / "prefiltered.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print("prefiltered", len(out), "of", sum(len(r["funcs"]) for r in mined), "function changes in", len(mined), "commits")
    for it in out:
        print(f"  {it['n']:03d} {it['commit']} {it['override']}  +eff={it['added_effect_calls']} -exit={len(it['removed_exits'])}  {it['subject'][:70]}")


if __name__ == "__main__":
    main()
