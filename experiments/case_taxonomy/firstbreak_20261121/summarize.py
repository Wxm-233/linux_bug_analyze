"""firstbreak criteria 四: registry.md + summary.json from claude_registry.json + collected.json (Windows or WSL python)."""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
reg = json.loads((HERE / "final_registry.json").read_text(encoding="utf-8"))
col = {c["commit"]: c for c in json.loads((HERE / "collected.json").read_text(encoding="utf-8"))}


def dist(rows, key):
    return dict(Counter(r[key] for r in rows))


clean = [r for r in reg if not r["used"]]
by_fix = list({r["fix"]: r for r in reg}.values())
summ = {
    "annotators": "Claude + Codex（改写提示后重做），分歧已裁定，见 adjudication.json",
    "all_21": {"first_break": dist(reg, "first_break"), "auto": dist(reg, "auto")},
    "clean_12": {"first_break": dist(clean, "first_break"), "auto": dist(clean, "auto")},
    "by_fix_20": {"first_break": dist(by_fix, "first_break"), "auto": dist(by_fix, "auto")},
    "stage_no_counts_all": {s: sum(1 for r in reg if r[s][0] != "是") for s in ("S1", "S2", "S3", "S4")},
    "S5_yes": sum(1 for r in reg if col[r["commit"]]["S5"]),
    "first_break_ignoring_S2": dict(Counter(next((s for s in ("S1", "S3", "S4") if r[s][0] != "是"),
                                                 "S5/S6") for r in reg)),
}
(HERE / "summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False), encoding="utf-8")
L = ["# 新评测集分析侧：逐例第一个断点（firstbreak_20261121）", "",
     "| 正样本 | 修复 | 曾用 | 公共依赖 | 架构选择 | S1 | S2 | S3 | S4 | S5 | 第一个断点 | 自动化前提 |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
for r in reg:
    c = col[r["commit"]]
    L.append(f"| {r['commit']} | {r['fix']} | {'是' if r['used'] else ('EZ' if r.get('used_by_ez') else '否')} | {r['dep']} | {r['arch']} | "
             f"{r['S1'][0]} | {r['S2'][0]} | {r['S3'][0]} | {r['S4'][0]} | {'是' if c['S5'] else '否'} | {r['first_break']} | {r['auto']} |")
L += ["", "逐项证据见 `claude_registry.json`。"]
(HERE / "registry.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print(json.dumps(summ, indent=1, ensure_ascii=False))
