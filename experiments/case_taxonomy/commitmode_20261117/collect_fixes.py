"""commitmode: gather historical fix commits used by each check line, read their Fixes: tags. WSL. -> fixes_raw.json"""
import json, re, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
CT = HERE.parent
KSRC = "/root/repos/linux"
def git(*a):
    return subprocess.run(["git", "-C", KSRC, *a], capture_output=True, text=True).stdout
fixes = []   # (line, fix_commit)
ho = json.loads((CT / "p1check_20261115/heldout_score.json").read_text())
dev = json.loads((CT / "p1check_20261115/dev.json").read_text())
ex = json.loads((CT / "p1check_20261115/extra_p1_codex.json").read_text())
for r in ho["rows"]:
    if r["hit"]: fixes.append(("P1", r["commit"]))
for c in dev: fixes.append(("P1", c))
for c, rows in ex.items():
    if any(h["hit"] for h in rows): fixes.append(("P1", c))
fixes.append(("xvdom", "8f34f1eac382"))
fixes.append(("xvlift", "3faa3ebc89c1"))
for c in ["9fd154ba926b", "3390916aca7a", "1f789a45c3f1", "d659b715e94a", "b66b1b71d7ff"]: fixes.append(("orddom", c))
for c in ["bbc46b23af5b", "04ff48239f46", "2d8c7edcb661", "c99493ce409c", "c13094b894de", "f505e6c91e7a", "a63308ab426f", "a5a5ed23b134"]:
    fixes.append(("widthtrunc", c))
out = []
for line, c in fixes:
    full = git("rev-parse", "--verify", "-q", c + "^{commit}").strip()
    msg = git("log", "-1", "--format=%s%n%cs%n%B", c)
    subj, date = msg.split("\n")[0], msg.split("\n")[1]
    tags = []
    for m in re.finditer(r"^\s*Fixes:\s*([0-9a-fA-F]{8,40})\b(.*)$", msg, re.M):
        h = git("rev-parse", "--verify", "-q", m.group(1) + "^{commit}").strip()
        info = git("log", "-1", "--format=%h|%cs|%s", h).strip() if h else ""
        tags.append({"tag": m.group(1), "resolved": h, "info": info})
    out.append({"line": line, "fix": c, "fix_full": full, "subject": subj, "date": date, "fixes": tags})
    print(line, c, date, subj[:60], "|", [t["info"][:70] or ("UNRESOLVED " + t["tag"]) for t in tags], flush=True)
(HERE / "fixes_raw.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
