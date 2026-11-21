"""evcard criteria 六: top 12 of each queue, merged, shuffled, source hidden; card + source excerpt. WSL.

    python3 review_packets.py  -> review/packets.md, review/items.json, review/source_map.json
"""
import json
import random
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = "/root/repos/linux"
REV = "df2908090cda"


def excerpt(path, line, before=25, after=20):
    src = subprocess.run(["git", "-C", REPO, "show", f"{REV}:{path}"], capture_output=True, text=True, errors="replace").stdout.split("\n")
    i, j = max(0, line - 1 - before), min(len(src), line - 1 + after)
    return "\n".join(f"{k + 1:6d}{'>' if k + 1 == line else ' '} {src[k]}" for k in range(i, j))


def main():
    s = json.loads((HERE / "cards_summary.json").read_text(encoding="utf-8"))
    cards = {}
    for ln in open(HERE / "cards.jsonl", encoding="utf-8"):
        m = json.loads(ln)
        cards[m["id"]] = m
    src = {}
    for q in ("top12_old", "top12_new"):
        for i in s[q]:
            src.setdefault(i, []).append(q[6:])
    ids = sorted(src)
    random.Random(20261121).shuffle(ids)
    (HERE / "review").mkdir(exist_ok=True)
    md = ["# evcard 审查材料（两榜前 12 条合并，打乱、隐去来源和名次）", "",
          "判断：完整线索（公共代码的依赖、架构条件改变保证的依据、同一对象到消费者的证据，且已排除最直接的合法解释）/ 未决 / 排除 / 未知。",
          "排除请写原因类别。行号前的 `>` 标出报告行。", ""]
    items = []
    for n, i in enumerate(ids, 1):
        m = cards[i]
        cd = m["card"]
        items.append({"n": n, "id": i})
        md.append(f"## [{n}] {m['engine']}（{m['check']}）`{m['file']}:{m['line']}` 函数 `{m['func']}`")
        md.append(f"- 原始特征：`{' ; '.join(m['sigs'])[:300]}`")
        md.append(f"- 卡片：消费位置 **{cd['consumer'][0]}**（{cd['consumer'][1]}）；编入 {cd['compiled']}；架构依据 **{cd['arch_basis'][0]}**（{cd['arch_basis'][1]}）；"
                  f"反证 **{cd['counter'][0]}**（{cd['counter'][1]}）")
        md.append("```c")
        md.append(excerpt(m["file"], m["line"] or 1))
        md.append("```")
        md.append("")
    (HERE / "review/packets.md").write_text("\n".join(md), encoding="utf-8")
    (HERE / "review/items.json").write_text(json.dumps(items, indent=1, ensure_ascii=False))
    (HERE / "review/source_map.json").write_text(json.dumps({it["n"]: src[it["id"]] for it in items}, indent=1))
    print("items", len(items))


if __name__ == "__main__":
    main()
