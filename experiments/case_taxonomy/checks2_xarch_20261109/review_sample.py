"""Draw the manual-review sample from flags_current.json (criteria section 6), written before the current results existed.

    python3 review_sample.py   -> review_sample.json (all distinct flags if <= 60, else random.Random(20261109).sample(..., 40))

Each entry of flags_current.json["flags"] is one distinct flag (type, family, detail) with its counterparts merged;
entries are taken in file order and each sampled one keeps its index.
"""
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    flags = json.loads((HERE / "flags_current.json").read_text(encoding="utf-8"))["flags"]
    idx = list(range(len(flags))) if len(flags) <= 60 else sorted(random.Random(20261109).sample(range(len(flags)), 40))
    out = [{"index": i, **flags[i]} for i in idx]
    (HERE / "review_sample.json").write_text(json.dumps({"total_distinct": len(flags), "seed": 20261109, "sample": out},
                                                         ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(flags), "distinct flags,", len(out), "sampled")


if __name__ == "__main__":
    main()
