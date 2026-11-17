"""Summary for README (criteria section 8).   python make_stats.py -> stats.json"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
c = json.loads((HERE / "runs/all/compare2.json").read_text(encoding="utf-8"))
avm = json.loads((HERE / "auto_vs_manual.json").read_text(encoding="utf-8"))
truth = json.loads((HERE / "truth.json").read_text())
ev = c["evaluation"]
cells = ev["presence_matrix"]
out = {
    "round": "difftest_known_20261109",
    "kernels": {n: {"arch": truth["kernels"][n]["arch"], "commit": truth["kernels"][n]["commit"],
                    "bugs_present_by_truth": truth["present"].get(n)} for n in c["kernels"]},
    "runs_per_kernel": 3,
    "unstable_keys": {n: k["unstable"] for n, k in c["kernels"].items() if k["unstable"]},
    "capabilities": {n: k["capabilities"] for n, k in c["kernels"].items()},
    "per_sample": ev["per_sample"],
    "pass_count": ev["pass_count"], "samples": len(ev["per_sample"]),
    "presence_cells": len(cells), "presence_cells_detected": sum(1 for v in cells.values() if v),
    "outliers": len(ev["outliers"]), "outliers_strong": sum(1 for o in ev["outliers"] if o["strength"] == "强"),
    "false_outliers": ev["false_outliers"],
    "verdict_counts": ev["verdict_counts"],
    "auto_vs_manual": {"agree": avm["agree"], "total": avm["total"]},
    "taint_changed_any": any(k["taint_changed"] != ["False"] for k in c["kernels"].values()),
    "excluded_samples": {"A313": "用户态触发不了（修复前树里只有 WARN 分支和 bpf arena 能返回 VM_FAULT_SIGSEGV，该版本 riscv 不支持 arena）",
                         "A027": "saved_auxv 不会溢出，没有可观察症状"},
    "statline": "模型调用 0；构建 8；新确认缺陷 0；新疑点 0",
}
(HERE / "stats.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(out["pass_count"], out["presence_cells_detected"], out["presence_cells"], out["outliers"], out["outliers_strong"], len(out["false_outliers"]))
