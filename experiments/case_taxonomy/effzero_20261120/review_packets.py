"""Review packets for the current-version top 20 (criteria 四). WSL.

    python3 review_packets.py  -> review/packets.md, review/top20.json
"""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = "/root/repos/linux"
REV = "df2908090cda"


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def body(path, line, maxl=70):
    src = git("show", f"{REV}:{path}").split("\n")
    i = line - 1
    j = i
    while j > max(0, i - 8) and src[j - 1].strip() and not src[j - 1].startswith("}"):
        j -= 1
    out, depth, started = [], 0, False
    for k in range(j, min(len(src), j + 400)):
        ln = src[k]
        out.append(f"{k + 1:6d}  {ln}")
        depth += ln.count("{") - ln.count("}")
        if "{" in ln:
            started = True
        if started and depth <= 0:
            break
    if len(out) > maxl:
        out = out[:maxl] + [f"        ...（共 {len(out)} 行，后略）"]
    return "\n".join(out)


def main():
    res = json.loads((HERE / "cur/effzero.json").read_text())
    top = res["cands"][:20]
    (HERE / "review").mkdir(exist_ok=True)
    (HERE / "review/top20.json").write_text(json.dumps(top, indent=1, ensure_ascii=False))
    md = ["# 当前版本 df2908090cda：E-ZERO 检查前 20 条的审查材料", "",
          "每条给出：检查形、组、被报实现的位置和源码、不清零路径上的条件、同组清零的实现、三个 defconfig 是否编入。",
          "判断：确认（有隐含或显式的清零约定，被报实现在可达的正常路径上不清零，对象会交给使用者，可写成补丁）/ 可能 / 排除 / 证据不足。", ""]
    for c in top:
        md.append(f"## [{c['rank']}] {c['form']} {c['file']}:{c['line']} {c['func']}")
        md.append(f"- 组：`{c['group']}`；架构证据：{c['arch']}；编入：{c.get('compiled')}")
        if c["form"] == "E1":
            md.append(f"- 组里：清零 {c['n_zero']}、不清零 {c['n_nonzero']}、未知 {c['n_unknown']}；来源函数：{c.get('origin')}")
            md.append(f"- 清零的实现（最多 6 个）：{c['zero_impls']}")
            for p in c["paths"]:
                md.append(f"- 不清零路径：来源 `{p['src']}`，返回行 {p['line']}，最近的条件 {p['conds']}")
        elif c["form"] == "E2":
            md.append(f"- 置假的开关：`{c['skip_var']}`；清零的实现：{c['zero_impls']}；不清零的实现：{c['nonzero_impls']}")
        else:
            md.append(f"- 调用方：{c['caller']}（调用方去掉了 __GFP_ZERO：{c['caller_strips_zero']}）")
            for p in c["early_paths"]:
                md.append(f"- 提前返回：行 {p['line']}，条件 {p['conds']}")
        md.append("")
        md.append("```c")
        md.append(body(c["file"], c["line"]))
        md.append("```")
        if c["form"] == "E1" and c.get("origin") and c["origin"] != c["func"]:
            src = git("grep", "-n", "-E", rf"^[a-z].*\b{c['origin']}\s*\(", REV, "--", c["file"]).split("\n")
            ln = next((int(x.split(":")[2]) for x in src if x.count(":") >= 3), None)
            if ln:
                md.append(f"来源函数 `{c['origin']}`：")
                md.append("```c")
                md.append(body(c["file"], ln))
                md.append("```")
        md.append("")
    (HERE / "review/packets.md").write_text("\n".join(md), encoding="utf-8")
    print("packets", len(top))


if __name__ == "__main__":
    main()
