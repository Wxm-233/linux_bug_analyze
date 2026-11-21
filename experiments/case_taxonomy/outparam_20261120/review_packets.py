"""outparam criteria 六.2: top 8 of each ranking, overlap once, shuffled, source hidden. WSL.

    python3 review_packets.py   -> review/packets.md, review/items.json (with hidden source map in review/source_map.json)
"""
import hashlib
import json
import random
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = "/root/repos/linux"
REV = "df2908090cda"


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def excerpt(path, line, before=3, after=40):
    src = git("show", f"{REV}:{path}").split("\n")
    if not src or line <= 0:
        return "(源码不可用)"
    i = max(0, line - 1 - before)
    j = min(len(src), line - 1 + after)
    return "\n".join(f"{k + 1:6d}  {src[k]}" for k in range(i, j))


def func_start(path, line):
    """walk back to the function head for a body '{' line"""
    src = git("show", f"{REV}:{path}").split("\n")
    k = line - 1
    while k > 0 and not (src[k - 1].strip() == "" or src[k - 1].startswith("}")):
        k -= 1
    return k + 1


def main():
    co = json.loads((HERE / "ranked_coarse.json").read_text(encoding="utf-8"))[:8]
    ev = json.loads((HERE / "ranked_evidence.json").read_text(encoding="utf-8"))[:8]
    items, src = {}, {}
    for name, lst in (("coarse", co), ("evidence", ev)):
        for m in lst:
            k = json.dumps(m["key"])
            items[k] = m
            src.setdefault(k, []).append(name)
    keys = sorted(items, key=lambda k: hashlib.sha256(("20261120|" + k).encode()).hexdigest())
    random.Random(20261120).shuffle(keys)
    (HERE / "review").mkdir(exist_ok=True)
    out, smap = [], {}
    md = ["# outparam 审查材料（隐去来源、已打乱）", "",
          "每条：被调接口、参数和字段、调用方读点、两个构建绑定到的实现及其写入状态、明确未写路径。",
          "判断：完整线索 / 不完整 / 排除 / 未知。完整线索须能指出公共成功条件、两个实际实现、同一对象的读写、可同时成立的分支条件、"
          "无初始化或后备写入的依据，并写出一种能推翻判断的具体观察。", ""]
    for n, k in enumerate(keys, 1):
        m = items[k]
        b = m["best"]
        smap[n] = src[k]
        out.append({"id": n, "key": m["key"], "best": b, "witnesses": len(m["witnesses"])})
        md.append(f"## [{n}] `{b['callee']}` 第 {b['argidx']} 个参数（`{b['argform']}`），字段 `{b['field']}`")
        md.append(f"- 调用方：`{b['caller'][0]}:{b['caller'][2]}`（函数 `{b['caller'][1]}`）；检查了返回值：{b['caller_checked']}；"
                  f"调用前初始化：{b['preinit'] or '无'}；成功分支上干净读：{b['clean_read']}；同类见证点 {len(m['witnesses'])} 个")
        for bb, x in b["builds"].items():
            md.append(f"- {bb}：`{x['loc'][0]}:{x['loc'][1]}`，返回类型 {x['rk']}，字段状态 **{x['status']}**")
        if b["missing_path"]:
            mp = b["missing_path"]
            md.append(f"- 明确未写路径（{b['missing_build']}）：返回于 `{mp['line']}`，最近条件 {mp['conds']}")
        md.append("")
        md.append("调用方：")
        md.append("```c")
        md.append(excerpt(b["caller"][0], b["caller"][2], 12, 14))
        md.append("```")
        for bb, x in b["builds"].items():
            f, ln = x["loc"]
            md.append(f"{bb} 的实现：")
            md.append("```c")
            md.append(excerpt(f, func_start(f, ln), 1, 45))
            md.append("```")
        md.append("")
    (HERE / "review/items.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    (HERE / "review/source_map.json").write_text(json.dumps(smap, indent=1))
    (HERE / "review/packets.md").write_text("\n".join(md), encoding="utf-8")
    print("items", len(out), "| coarse", len(co), "evidence", len(ev), "| overlap", sum(1 for v in smap.values() if len(v) == 2))


if __name__ == "__main__":
    main()
