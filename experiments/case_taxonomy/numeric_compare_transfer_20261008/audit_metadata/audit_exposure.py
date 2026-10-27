"""Read only prior study manifests/reviews; never read new source or patches."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


OUT = Path(__file__).resolve().parent
BASE = OUT.parents[1]
STAGE = OUT.parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    pool_path = STAGE / "metadata_pool.json"
    pool = json.loads(pool_path.read_text(encoding="utf-8"))["records"]
    assert len(pool) == 16
    searched = []
    hits = []
    for path in sorted(BASE.rglob("*")):
        if not path.is_file() or path.suffix not in (".json", ".md", ".tsv"):
            continue
        rel = path.relative_to(BASE).as_posix()
        if "numeric_compare_transfer_20261008" in rel or "__pycache__" in rel:
            continue
        name = path.name.lower()
        allowed = (
            ("manifest" in name and any(x in name for x in ("source", "raw", "development", "unseal")))
            or "source" in name
            or "review" in name
            or "card" in name
            or name in ("pilot_500_20260926.tsv", "legacy_13_dimensions.tsv")
        )
        if not allowed:
            continue
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        searched.append({"path": rel, "sha256": hashlib.sha256(raw).hexdigest()})
        for record in pool:
            if re.search(re.escape(record["commit"][:8]), text, re.I):
                hits.append({"pool_order": record["pool_order"], "commit": record["commit"], "path": rel})

    # The prior review maps this abbreviated output filename to the full fix SHA.
    # Inspect only provenance fields of its successful old-source extraction.
    report_path = BASE / "producer_holdout_457b_macsec_raw.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    evidence = {key: report[key] for key in ("source_file", "source_sha256", "revision", "files_read", "counts")}
    assert evidence["source_file"] == "include/net/macsec.h"
    assert evidence["revision"] == "5fe71fda89745fc3cd95f70d06e9162b595c3702"
    known_hit = next(record for record in pool if record["commit"].startswith("457bb797"))
    assert any(hit["pool_order"] == known_hit["pool_order"] and hit["path"] == "endian_producer_holdout_review.md" for hit in hits)

    result = {
        "scope": "Prior case_taxonomy source/development/raw manifests, source reports/evidence, reviews/cards and two basic TSVs selected by recorded filename predicate; new stage and analysis_out excluded.",
        "metadata_pool_sha256": digest(pool_path),
        "pool_count": len(pool),
        "searched_files": searched,
        "matching_references": hits,
        "confirmed_prior_source_exposure": [{
            "pool_order": known_hit["pool_order"],
            "commit": known_hit["commit"],
            "review_path": "endian_producer_holdout_review.md",
            "review_evidence": "The old-source output table explicitly maps 457bb797 to include/net/macsec.h and the subsequent section records unsealed source review; this is not a metadata-only selection mention.",
            "successful_extraction_path": report_path.relative_to(BASE).as_posix(),
            "successful_extraction_sha256": digest(report_path),
            "source_provenance_fields": evidence,
        }],
        "records": [{
            "pool_order": record["pool_order"],
            "commit": record["commit"],
            "status": "prior_source_review_exposure" if record["commit"] == known_hit["commit"] else "no_evidence_in_defined_scope",
        } for record in pool],
        "limitations": [
            "The absence of a matching reference is bounded by the searched artifacts and does not establish global, human or model blindness.",
            "Metadata-only selections, pools and protocol mentions are not treated as prior source exposure.",
            "Only provenance fields of one previously successful extraction were inspected; no C source or patch text was opened in this audit.",
            "No new Git command, model result or raw response was read; no candidate was selected by this audit.",
        ],
    }
    (OUT / "exposure_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pool_count": len(pool), "searched_file_count": len(searched), "confirmed_source_exposure_count": 1, "no_evidence_count": 15, "new_source_or_patch_read": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
