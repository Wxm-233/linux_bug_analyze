"""Reproduce the book/drawer development matrix on the already-read f104 case.

This is deliberately development data, not an untouched holdout evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from contract_check_pilot_v1 import capability
from topology_contract_extract import from_git


FIX = "f1045056c726440469d89d23c13734bcd6c0d15b"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    extractor = here / "topology_contract_extract.py"
    cases = []
    for revision_label, revision in (("parent", FIX + "^"), ("fix", FIX)):
        for family in ("book", "drawer"):
            for arch, sched_topology in (("s390", True), ("s390", False),
                                         ("s390", None), ("x86", None)):
                facts = from_git(args.linux_dir, revision, arch, True, True,
                                 family, sched_topology)
                status, reason = capability(facts["records"][0])
                expected = "insufficient" if arch == "s390" and sched_topology is None else "normal"
                if status != expected:
                    raise AssertionError((revision_label, family, arch,
                                          sched_topology, status, expected))
                cases.append({"revision_label": revision_label,
                              "expected_status": expected, "status": status,
                              "reason": reason, "facts": facts})
    output = {"purpose": "post-read development check; not a holdout",
              "fix": FIX,
              "extractor_sha256": hashlib.sha256(extractor.read_bytes()).hexdigest(),
              "configuration": "SMP on, CPU topology sysfs built; SCHED_TOPOLOGY explicitly on/off/unknown for s390",
              "cases": cases}
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"records": len(cases),
                      "normal": sum(case["status"] == "normal" for case in cases),
                      "insufficient": sum(case["status"] == "insufficient" for case in cases)}))


if __name__ == "__main__":
    main()
