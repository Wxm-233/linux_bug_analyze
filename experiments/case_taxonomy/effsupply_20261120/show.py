"""Export design-side candidates for reading (criteria 五). WSL. Reads design.json only (never sealed_late/).

    python3 show.py > show_design.txt
Per commit: date, subject, Fixes, message body without trailers, and hunks (-U4) whose +/- lines match ZTOK.
"""
import json
import random
import re
import subprocess
from pathlib import Path

import mine as M

HERE = Path(__file__).resolve().parent


def main():
    d = json.loads((HERE / "design.json").read_text(encoding="utf-8"))
    if len(d) > 60:
        keep = set(c["commit"] for c in random.Random(20261120).sample(d, 60))
        d = [c for c in d if c["commit"] in keep]
    for c in sorted(d, key=lambda c: c["date"]):
        body = M.git("log", "-1", "--format=%B", c["commit"])
        text = "\n".join(ln for ln in body.split("\n")[1:] if not M.TRAILER.match(ln)).strip()
        print("=" * 100)
        print(f"{c['commit']} {c['date']} {c['subject']}")
        print(f"  fixes={c['fixes']} used={c['used']} analysis={c['analysis_set']} tokens={c['tokens']}")
        print("  " + text.replace("\n", "\n  ")[:1500])
        patch = M.git("show", "--format=", "--no-color", "-U4", c["commit"], "--", *M.PATHS)
        hunks, cur, fname = [], [], None
        for ln in patch.split("\n"):
            if ln.startswith("diff --git"):
                if cur:
                    hunks.append((fname, cur))
                cur, fname = [], ln.split(" b/")[-1]
            elif ln.startswith("@@"):
                if cur:
                    hunks.append((fname, cur))
                cur = [ln]
            elif cur:
                cur.append(ln)
        if cur:
            hunks.append((fname, cur))
        shown = 0
        for fname, h in hunks:
            if any(l.startswith(("+", "-")) and not l.startswith(("+++", "---")) and M.ZTOK.search(l) for l in h) and shown < 3:
                print(f"  --- {fname}")
                print("  " + "\n  ".join(h[:30]))
                shown += 1


if __name__ == "__main__":
    main()
