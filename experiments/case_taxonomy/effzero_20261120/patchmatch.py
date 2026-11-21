"""Control 2 (criteria 二): lexical matching of design-side patch shapes P1..P5. Any revision, no build. WSL.

    python3 patchmatch.py <rev> [out.json]
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "p1check_20261115"))
import p1check as C  # noqa: E402

REPO = "/root/repos/linux"
EXCL = ("tools/", "scripts/", "samples/", "Documentation/", "usr/")
REQ = re.compile(r"^_*[A-Z0-9_]*(INIT|ZERO)[A-Z0-9_]*$")


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def grep_l(rev, pat):
    out = git("grep", "-l", "-E", pat, rev, "--", "*.c", "*.h")
    return sorted({ln.split(":", 1)[1] for ln in out.split("\n") if ":" in ln and not ln.split(":", 1)[1].startswith(EXCL)})


def funcs(src):
    t = C.tokenize(C.strip(src))
    for name, params, lo, hi in C.functions(t):
        yield name, [p[1] for p in params], t, lo, hi


def main(rev, outp=None):
    files = set()
    pats = {"P1": r"__GFP_ZERO", "P2": r"__GFP_ZERO", "P3": r"init\s*=\s*false", "P4": r"dma_common_contiguous_remap",
            "P5": r"[A-Z0-9_]*(INIT|ZERO)[A-Z0-9_]*"}
    byp = {k: grep_l(rev, v) for k, v in pats.items() if k != "P5"}
    byp["P5"] = sorted(set(grep_l(rev, r"\bflags\b")) & set(grep_l(rev, r"\b_*[A-Z0-9_]*(INIT|ZERO)[A-Z0-9_]*\b\s*[^ (A-Za-z0-9_]")))
    for v in byp.values():
        files |= set(v)
    blobs = C.cat_files(rev, sorted(files))
    cands = []
    for p, src in blobs.items():
        lines = C.strip(src).split("\n")
        for name, params, t, lo, hi in funcs(src):
            body = [x[0] for x in t[lo:hi + 1]]
            l0, l1 = t[lo][1], t[hi][1]
            seg = lines[l0 - 1:l1]
            hits = []
            if p in byp["P1"]:
                for i, ln in enumerate(seg):
                    if re.search(r"\bif\s*\(.*__GFP_ZERO", ln) and any("memset" in x for x in seg[i:i + 3]):
                        hits.append(("P1", l0 + i))
            if p in byp["P2"]:
                for i, ln in enumerate(seg):
                    if re.search(r"&=\s*~\s*\(?[^;]*__GFP_ZERO", ln):
                        hits.append(("P2", l0 + i))
            if p in byp["P3"]:
                for i, ln in enumerate(seg):
                    if re.search(r"\binit\s*=\s*false\s*;", ln) and any(re.search(r"\w*(clear|zero)\w*\s*\(", x) for x in seg[max(0, i - 3):i]):
                        hits.append(("P3", l0 + i))
            if p in byp["P4"]:
                if "dma_common_contiguous_remap" in body and "memset" not in body:
                    hits.append(("P4", l0))
            if p in byp["P5"] and "flags" in params:
                first = next((i for i, x in enumerate(body) if REQ.match(x) and (i + 1 >= len(body) or body[i + 1] != "(")), None)
                if first is not None and "return" in body[:first]:
                    hits.append(("P5", l0))
            for pat, line in hits:
                cands.append({"pattern": pat, "file": p, "line": line, "func": name})
    seen, out = set(), []
    for c in sorted(cands, key=lambda c: (c["pattern"], c["file"], c["line"])):
        k = (c["file"], c["func"])
        if k in seen:
            continue
        seen.add(k)
        out.append(c)
    res = {"rev": rev, "n": len(out), "by_pattern": {k: sum(1 for c in out if c["pattern"] == k) for k in ("P1", "P2", "P3", "P4", "P5")},
           "cands": out}
    if outp:
        Path(outp).write_text(json.dumps(res, indent=1, ensure_ascii=False))
    return res


if __name__ == "__main__":
    r = main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(r["n"], r["by_pattern"])
