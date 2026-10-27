"""Replay previously read inputs only; never independent detection accuracy."""
import json
import subprocess
from pathlib import Path

import representation_producer_v5 as producer

HERE = Path(__file__).resolve().parent
OUT = HERE / "repr_v5_20260930" / "development"
REPO = Path("/root/repos/linux")
CASES = [
    ("mpt3sas", "494f401bcd07", "drivers/scsi/mpt3sas/mpt3sas_base.c"),
    ("hisi_sas", "47e66bec3edaebd7c52d8ee981065a4c83b3072f", "drivers/scsi/hisi_sas/hisi_sas_v3_hw.c"),
    ("dw_mmc", "541fe77cc4d77799ac1b869e2183e1bdd716a1f2", "drivers/mmc/host/dw_mmc.c"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {"scope": "previously read development replay; not independent or consumer/hardware validation", "cases": []}
    for name, short, source in CASES:
        fixed = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", short], text=True).strip()
        parent = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", fixed + "^"], text=True).strip()
        row = {"case": name, "source_path": source, "parent": parent, "fixed": fixed, "reports": []}
        for label, revision in (("parent", parent), ("fixed", fixed)):
            report = producer.analyze_revision(REPO, revision, source)
            dest = OUT / f"{name}_{label}.json"
            dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            row["reports"].append({"label": label, "path": dest.name,
                "v4_counts_before_shape_review": report["v4_counts_before_shape_review"],
                "counts": report["counts"], "filtered_pointer_count": report["filtered_pointer_count"],
                "filtered_pointer_sites": [{"line": item["line"], "original_lvalue": item["original_lvalue"], "rhs": item["rhs"]} for item in report["filtered_pointer_sites"]],
                "normal_sites": [{"line": item["line"], "original_lvalue": item.get("original_lvalue"), "rhs": item["rhs"]} for item in report["findings"] if item["status"] == "normal"],
                "candidate_sites": [{"line": item["line"], "original_lvalue": item.get("original_lvalue"), "rhs": item["rhs"]} for item in report["findings"] if item["status"] == "candidate"]})
        summary["cases"].append(row)
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"completed_development_inputs": 6, "summary_path": str(OUT / "summary.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
