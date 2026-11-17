"""Print, for each sampled commit, the diff hunk(s) containing the matched constant assignment (for the 是/不是 judgement)."""
import json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
for e in [e for e in json.load(open(HERE / "candidates.json", encoding="utf-8"))["commits"] if e["commit"][:12] in sys.argv[1:]]:
    print("########", e["commit"][:12], e["subject"])
    for m in e["matches"][:2]:
        d = subprocess.run(["git", "-C", "/root/repos/linux", "show", "-U6", "--format=", e["commit"], "--", m["file"]],
                           capture_output=True, text=True, errors="replace").stdout.split("\n")
        hunks, cur = [], []
        for l in d:
            if l.startswith("@@"):
                if cur: hunks.append(cur)
                cur = [l]
            elif cur:
                cur.append(l)
        if cur: hunks.append(cur)
        for h in hunks:
            if any(l.strip() == m["line"] or l.rstrip() == m["line"] for l in h) or any(l.startswith("-") and l[1:].strip() == m["line"][1:].strip() for l in h):
                print("  --", m["file"], "flag", m["flag"], "iface", m["interfaces"])
                print("\n".join("   " + x[:110] for x in h[:30]))
                break
