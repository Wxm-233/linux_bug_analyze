"""Draw the manual-review sample from results/current.json (criteria section 6), written before the rerun finished.

    python3 review_sample.py        -> review_sample.json (all flags if <= 60, else random.Random(20261108).sample(flags, 40))

The flags are taken in file order; each sampled flag keeps its index so the draw can be reproduced.
"""
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    flags = json.loads((HERE / "results" / "current.json").read_text())["flags"]
    idx = list(range(len(flags))) if len(flags) <= 60 else sorted(random.Random(20261108).sample(range(len(flags)), 40))
    out = [{"index": i, **flags[i]} for i in idx]
    (HERE / "review_sample.json").write_text(json.dumps({"total_flags": len(flags), "seed": 20261108,
                                                          "sample": out}, ensure_ascii=False, indent=1))
    print(len(flags), "flags,", len(out), "sampled")


if __name__ == "__main__":
    main()
