"""Design-side regression scoring (criteria 三). WSL. Reads dev/<id>.json and the cached facts.

    python3 devcheck.py            -> devcheck.json + table
"""
import gzip
import json
import pickle
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = "/root/repos/linux"
DEV = {"D1": "6829e274a623", "D3": "e89f5b370153", "D4": "dd65a941f6ba", "D5": "a1da439cc0d9", "X1": "5bebe8de1926", "K1": "6c2f761dad78"}
NAMED = {"D3": ("arch/arc/", "arch/s390/")}          # fix message names the non-zeroing implementations
CEX = {"C1": ("D3", None, "dma_direct_alloc"), "C3": ("X1", "arch/arm64/mm/fault.c", "vma_alloc_zeroed_movable_folio"),
       "C4": ("X1", "mm/page_alloc.c", "kasan_unpoison_pages")}


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def changed_funcs(fix, facts):
    out = set()
    cur = None
    for ln in git("show", "--format=", "-U0", fix).split("\n"):
        if ln.startswith("--- a/"):
            cur = ln[6:]
        elif ln.startswith("--- "):
            cur = None
        elif ln.startswith("@@") and cur:
            m = re.match(r"@@ -(\d+)(?:,(\d+))?", ln)
            a = int(m.group(1))
            b = a + max(int(m.group(2) or 1), 1) - 1
            for d in facts["files"].get(cur, {}).get("fns", []):
                if d["l"] <= b and d["le"] >= a:
                    out.add((cur, d["n"]))
    return out


def main():
    rows = {}
    for k, fix in DEV.items():
        p = HERE / f"dev/{k}.json"
        if not p.exists():
            rows[k] = {"status": "not run"}
            continue
        res = json.loads(p.read_text())
        facts = pickle.load(gzip.open(f"/root/work/effzero/facts_{res['rev'][:12]}.pkl.gz"))
        ch = changed_funcs(fix, facts)
        hits = []
        for c in res["cands"]:
            if (c["file"], c["func"]) in ch or (c.get("origin") and (c["file"], c["origin"]) in ch):  # amendment 2.2
                hits.append((c["rank"], c["form"], c["file"], c["func"], c.get("origin"), "changed"))
            elif k in NAMED and c["file"].startswith(NAMED[k]) and c["form"] == "E1":
                hits.append((c["rank"], c["form"], c["file"], c["func"], c.get("origin"), "named-in-message"))
        cex = []
        for cid, (dk, f, fn) in CEX.items():
            if dk != k:
                continue
            bad = [c for c in res["cands"] if (c["func"] == fn and (f is None or c["file"] == f)) or
                   (cid == "C4" and c["form"] == "E2" and c["group"].endswith("/" + fn))]
            cex.append((cid, len(bad)))
        rows[k] = {"rev": res["rev"][:12], "n_cands": len(res["cands"]), "changed": sorted(ch), "hits": hits, "cex_reported": cex,
                   "stats": res["stats"]}
    Path(HERE / "devcheck.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    nh = sum(1 for r in rows.values() if r.get("hits"))
    for k, r in rows.items():
        print(k, r.get("rev"), "cands", r.get("n_cands"), "hits", r.get("hits", [])[:3], "cex", r.get("cex_reported"))
    cex_bad = sum(n for r in rows.values() for _, n in r.get("cex_reported", []))
    print(f"HIT {nh}/6  counterexamples reported {cex_bad}  -> gate {'PASS' if nh >= 4 and cex_bad == 0 else 'not yet'}")


if __name__ == "__main__":
    main()
