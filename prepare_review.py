"""从现有报告建立复核清单；旧模型标签不作为人工真值。"""
import argparse
import csv
import json
import random
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, default=Path("analysis_out"))
    parser.add_argument("--outdir", type=Path, default=Path("analysis_out/review-pilot"))
    args = parser.parse_args()
    if args.outdir.exists():
        parser.error("输出目录已存在；请选择新目录，避免覆盖人工标注")
    positive, negative = [], []
    for path in sorted(args.reports.glob("*.meta.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("status") != "success":
            continue
        relevance = data["classification"]["relevance"]
        row = {"hash": data["commit_hash"], "subject": data["subject"],
            "previous_model_label": relevance, "human_label": "", "human_evidence": "",
            "report": str((args.reports / data["report_file"]).resolve())}
        (negative if relevance == "unrelated" else positive).append(row)
    rows = positive + random.Random(20260908).sample(negative, min(20, len(negative)))
    args.outdir.mkdir(parents=True)
    with (args.outdir / "review.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["hash", "subject", "previous_model_label", "human_label", "human_evidence", "report"])
        writer.writeheader()
        writer.writerows(rows)
    (args.outdir / "hashes.txt").write_text("".join(r["hash"] + "\n" for r in rows), encoding="utf-8")
    (args.outdir / "README.md").write_text(
        "# 人工复核样本\n\n包含现有相关、不确定项，以及固定随机种子抽取的最多 20 条不相关项。\n"
        "previous_model_label 仅是旧模型判断，不是人工真值。human_label 和 human_evidence 留空等待复核。\n"
        "核对补丁及其父版本，记录支持、反证与缺失证据；human_label 填 related/unrelated/uncertain。\n"
        "比较短判定时优先检查人工相关项被判 unrelated 的漏检。标签分层抽样不能用于直接估算全量相关率。\n"
        "此清单不包含被原规则排除的提交，因此尚不能衡量原规则召回率。\n", encoding="utf-8")
    print(f"已生成 {len(rows)} 条复核清单：{args.outdir}")


if __name__ == "__main__":
    main()
