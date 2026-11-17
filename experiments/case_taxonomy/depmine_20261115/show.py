"""Dump the sampled commits for reading (criteria 五). WSL, read-only.

    python3 show.py   -> show_sample.txt  (each distinct sampled commit once: message without trailers, matched hunks)
"""
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = "/root/repos/linux"
TRAILER = re.compile(r"^\s*(Signed-off-by|Reviewed-by|Acked-by|Tested-by|Cc|Link|Reported-by|Closes|Suggested-by|Co-developed-by|"
                     r"Reported-and-tested-by|Message-ID|Message-Id|Debugged-by|Analyzed-by)\s*:", re.I)


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def hunks(commit, files, needles):
    out = []
    for f in files:
        txt = git("show", "-U8", "--format=", commit, "--", f)
        cur = []
        for line in txt.splitlines():
            if line.startswith("@@"):
                if cur:
                    out.append((f, cur))
                cur = [line]
            elif cur:
                cur.append(line)
        if cur:
            out.append((f, cur))
    keep = [(f, h) for f, h in out if any(n in "\n".join(h) for n in needles)]
    return keep[:3]


def main():
    cand = json.loads((HERE / "candidates.json").read_text(encoding="utf-8"))
    samp = json.loads((HERE / "sample.json").read_text(encoding="utf-8"))
    byc = {c["commit"]: c for c in cand["commits"]}
    order, forms_of = [], {}
    for f in "ABC":
        for h in samp[f]:
            if h not in forms_of:
                order.append(h)
            forms_of.setdefault(h, []).append(f)
    L = []
    for k, h in enumerate(order, 1):
        c = byc[h]
        msg = git("log", "-1", "--format=%B", h)
        body = [x for x in msg.splitlines() if not TRAILER.match(x)]
        while body and not body[-1].strip():
            body.pop()
        files = sorted({m["file"] for f in c["forms"] for m in c["forms"][f]})
        needles = sorted({m["line"][:60] for f in c["forms"] for m in c["forms"][f]})
        L += ["=" * 100, f"[{k}] {h[:12]}  forms={','.join(forms_of[h])}  {c['subject']}", "-- matches:"]
        for f in c["forms"]:
            for m in c["forms"][f][:4]:
                L.append(f"   {f} {m.get('sub', '')} {m['file']} I={m.get('I')} E={m.get('E')} func={m.get('func')} | {m['line'][:120]}")
        L += ["-- message:"] + ["   " + x for x in body[:40]] + (["   …"] if len(body) > 40 else [])
        for f, hk in hunks(h, files, [n.strip()[:40] for n in needles]):
            L.append(f"-- hunk {f}:")
            L += ["   " + x for x in hk[:45]] + (["   …"] if len(hk) > 45 else [])
    (HERE / "show_sample.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("distinct sampled commits", len(order))


if __name__ == "__main__":
    main()
