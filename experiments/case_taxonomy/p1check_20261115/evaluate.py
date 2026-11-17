"""p1check criteria 四: dev samples, mechanical held-out set, HEAD scan, per-arch definitions. WSL.

    python3 evaluate.py dev | heldout_mine | heldout_score | head | archs
"""
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p1check as C  # noqa: E402

HERE = Path(__file__).resolve().parent
CT = HERE.parent
HEAD = "df2908090cda"
DEV = ["26e7888a0c89", "43e7f189769c"]
PRES_RX = re.compile(r"\b(" + "|".join(sorted(C.PRESENT - {"pmd_trans_huge", "pud_trans_huge"} | {"pmd_trans_huge", "pud_trans_huge"})) + r")\s*\(")


def git(*a):
    return C.git(*a)


def hunks(commit, path, ctx=8):
    """[(old_start, old_len, new_start, new_len, lines[(tag,text)])] of commit vs parent for one file"""
    out, cur = [], None
    for line in git("show", f"-U{ctx}", "--format=", commit, "--", path).split("\n"):
        m = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if m:
            cur = [int(m.group(1)), int(m.group(2) or 1), int(m.group(3)), int(m.group(4) or 1), []]
            out.append(cur)
        elif cur is not None and line[:1] in (" ", "+", "-"):
            cur[4].append((line[0], line[1:]))
    return out


def funcs_at(spans, lo, hi):
    return {n for n, a, b in spans if a <= hi and b >= lo}


def analyze_rev(rev, path):
    src = git("show", f"{rev}:{path}")
    if not src:
        return [], []
    f, _, _, sp = C.analyze_source(src, path)
    return f, sp


def score_hunk(commit, path, h, accs):
    """function-level hit (criteria 四.3) and disappearance after the fix"""
    os_, ol, ns, nl, _ = h
    pf, psp = analyze_rev(f"{commit}^", path)
    ff, fsp = analyze_rev(commit, path)
    pfun = funcs_at(psp, os_, os_ + max(ol, 1) - 1)
    ffun = funcs_at(fsp, ns, ns + max(nl, 1) - 1)
    pm = [x for x in pf if x["func"] in pfun and x["accessor"] in accs]
    fm = [x for x in ff if x["func"] in ffun and x["accessor"] in accs]
    pc = Counter((x["func"], x["accessor"]) for x in pm)
    fc = Counter((x["func"], x["accessor"]) for x in fm)
    gone = bool(pm) and all(fc[k] < v for k, v in pc.items())
    return {"funcs_parent": sorted(pfun), "hit": bool(pm), "parent_findings": pm, "fix_findings": fm, "gone_after_fix": gone}


def dev():
    res = {}
    for c in DEV:
        files = [p for p in git("show", "--name-only", "--format=", c).split("\n") if p and C.in_scope(p)]
        rows = []
        for p in files:
            for h in hunks(c, p):
                accs = {m.group(1) for _, t in h[4] for m in C.ACC_RX.finditer(t)}
                if not accs:
                    continue
                rows.append({"file": p, "old": h[:2], "new": h[2:4], "accessors": sorted(accs), **score_hunk(c, p, h, accs)})
        res[c] = rows
    (HERE / "dev.json").write_text(json.dumps(res, indent=1))
    for c, rows in res.items():
        print(c, [(r["file"], r["accessors"], r["funcs_parent"], "hit" if r["hit"] else "MISS",
                   "gone" if r["gone_after_fix"] else "still") for r in rows])


def last_ident(s):
    ids = re.findall(r"[A-Za-z_]\w*", s)
    return ids[-1] if ids else None


def call_args(text, name):
    out = []
    for m in re.finditer(rf"\b{name}\s*\(", text):
        i, d = m.end(), 1
        j = i
        while j < len(text) and d:
            d += {"(": 1, ")": -1}.get(text[j], 0)
            j += 1
        out.append(text[i:j - 1])
    return out


def heldout_mine():
    read = set(DEV)
    samp = json.loads((CT / "depmine_20261115/sample.json").read_text())
    read |= {h[:12] for f in samp for h in samp[f]}
    cmd = ["git", "-C", C.REPO, "log", "v5.10..HEAD", "--no-merges", "--grep=^Fixes:", "-U8", "-p", "--format=COMMIT %H %s", "--",
           *C.SCOPE_C, *C.SCOPE_H]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, errors="replace")
    sel, n = {}, 0
    cur = fname = None
    hk = None

    def flush():
        if not (cur and fname and hk and C.in_scope(fname)):
            return
        lines = hk[4]
        plus = [t for g, t in lines if g == "+"]
        minus = [t for g, t in lines if g == "-"]
        post = [(g, t) for g, t in lines if g in " +"]
        accs = set()
        for i, (g, t) in enumerate(post):
            if g != "+":
                continue
            for m in PRES_RX.finditer(t):
                pn = m.group(1)
                if len(re.findall(rf"\b{pn}\s*\(", "\n".join(plus))) <= len(re.findall(rf"\b{pn}\s*\(", "\n".join(minus))):
                    continue
                ids = {last_ident(a) for a in call_args(t, pn)}
                for g2, t2 in post[i:]:
                    for a in C.ACCESSORS:
                        for arg in call_args(t2, a):
                            if last_ident(arg) in ids:
                                accs.add(a)
        if accs:
            e = sel.setdefault(cur[0], {"commit": cur[0], "subject": cur[1], "hunks": []})
            e["hunks"].append({"file": fname, "old": hk[:2], "new": hk[2:4], "accessors": sorted(accs)})
    for raw in proc.stdout:
        line = raw.rstrip("\n")
        if line.startswith("COMMIT "):
            flush()
            hk = None
            n += 1
            h, _, s = line[7:].partition(" ")
            cur, fname = (h, s), None
            continue
        if line.startswith("diff --git"):
            flush()
            hk, fname = None, None
            continue
        if line.startswith("+++ "):
            fname = line[6:] if line.startswith("+++ b/") else None
            continue
        if line.startswith(("--- ", "index ")):
            continue
        m = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if m:
            flush()
            hk = [int(m.group(1)), int(m.group(2) or 1), int(m.group(3)), int(m.group(4) or 1), []]
            continue
        if hk is not None and line[:1] in (" ", "+", "-"):
            hk[4].append((line[0], line[1:]))
    flush()
    proc.wait()
    allc = sorted(sel.values(), key=lambda e: e["commit"])
    held = [e for e in allc if e["commit"][:12] not in read]
    (HERE / "heldout_set.json").write_text(json.dumps({"scanned": n, "selected": len(allc), "excluded_read": len(allc) - len(held),
                                                       "heldout": held}, indent=1))
    print("scanned", n, "selected", len(allc), "heldout", len(held))


def heldout_score():
    hs = json.loads((HERE / "heldout_set.json").read_text())["heldout"]
    rows = []
    for e in hs:
        hits, gone, per = False, False, []
        for h in e["hunks"]:
            hh = [h["old"][0], h["old"][1], h["new"][0], h["new"][1], []]
            r = score_hunk(e["commit"], h["file"], hh, set(h["accessors"]))
            per.append({**h, **{k: r[k] for k in ("funcs_parent", "hit", "gone_after_fix")},
                        "parent_findings": [(x["func"], x["line"], x["accessor"], x["origin"]) for x in r["parent_findings"]]})
            hits |= r["hit"]
            gone |= r["gone_after_fix"]
        rows.append({"commit": e["commit"][:12], "subject": e["subject"], "hit": hits, "gone_after_fix": gone, "hunks": per})
    nh = sum(r["hit"] for r in rows)
    ng = sum(r["gone_after_fix"] for r in rows)
    (HERE / "heldout_score.json").write_text(json.dumps({"n": len(rows), "hit": nh, "gone_after_fix": ng, "rows": rows}, indent=1))
    print("heldout", len(rows), "hit", nh, "gone_after_fix", ng)


def head():
    res, _ = C.scan(HEAD)
    f = res["findings"]
    res["by_origin"] = dict(Counter(x["origin"] for x in f))
    res["by_accessor"] = dict(Counter(x["accessor"] for x in f).most_common())
    res["by_dir"] = dict(Counter(x["file"].split("/")[0] + "/" + (x["file"].split("/")[1] if x["file"].count("/") > 1 else "") for x in f).most_common())
    o1 = sorted((x for x in f if x["origin"] == "O1"), key=lambda x: (x["file"], x["line"]))
    res["o1_top30"] = o1[:30]
    (HERE / "head.json").write_text(json.dumps(res, indent=1))
    print("findings", len(f), "by_origin", res["by_origin"], "files", res["files_with_accessors"], "functions", res["functions"],
          "parse_errors", res["parse_errors"])
    print("by_accessor", res["by_accessor"])
    print("by_dir", res["by_dir"])


def archs():
    out = {}
    files = [p for p in git("ls-tree", "-r", "--name-only", HEAD, "--", "arch/").split("\n") if re.match(r"^arch/[^/]+/include/asm/.*\.h$", p)]
    blobs = C.cat_files(HEAD, files)
    defs = {}
    for p, src in blobs.items():
        a = p.split("/")[1]
        s = C.strip(src) if False else src
        for name in C.ACCESSORS:
            for m in re.finditer(rf"^\s*#\s*define\s+{name}\s*\(([^\n\\]|\\\n)*", s, re.M):
                defs.setdefault((a, name), []).append(m.group(0))
            for m in re.finditer(rf"static\s+(?:__always_)?inline[^;{{(]*\b{name}\s*\([^)]*\)\s*\{{", s):
                i, d = m.end(), 1
                j = i
                while j < len(s) and d:
                    d += {"{": 1, "}": -1}.get(s[j], 0)
                    j += 1
                defs.setdefault((a, name), []).append(s[m.start():j])
    RX_P = re.compile(r"PRESENT|VALID|_present\s*\(|pte_present|pmd_present|pud_present")
    for (a, name), bodies in defs.items():
        body = "\n".join(bodies)
        checks = bool(RX_P.search(body))
        dele = sorted({x for x in C.ACCESSORS if x != name and re.search(rf"\b{x}\s*\(", body)})
        out.setdefault(name, {})[a] = {"checks_present": checks, "delegates_to": dele, "n_defs": len(bodies)}
    for name, per in out.items():  # one-level delegation
        for a, v in per.items():
            if not v["checks_present"] and v["delegates_to"]:
                v["checks_present_via_delegate"] = any(out.get(d, {}).get(a, {}).get("checks_present") for d in v["delegates_to"])
    summary = {name: sorted(a for a, v in per.items() if not v["checks_present"] and not v.get("checks_present_via_delegate"))
               for name, per in sorted(out.items())}
    (HERE / "archs.json").write_text(json.dumps({"per_accessor": out, "no_present_check": summary}, indent=1))
    for k, v in summary.items():
        print(k, "defined_by", len(out[k]), "no_present_check:", v)


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    {"dev": dev, "heldout_mine": heldout_mine, "heldout_score": heldout_score, "head": head, "archs": archs}[sys.argv[1]]()
