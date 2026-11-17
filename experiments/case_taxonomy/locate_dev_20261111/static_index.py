"""Static index for the localisation report (locate criteria 二). Runs in WSL, read-only.

    TARGET=riscv PYTHONPATH=<heldout pipeline> python3 static_index.py <group> <facts.json.gz> <values.json> \
        <fieldvocab.json> <out.json>

For every syscall: all hint sites of hints4 (I1-I4) with the score, the boundary item chosen for the score and its
evidence level (rank.score_sites, patch evidence with the same cutoff as the ranking); the raw syscall-number checks;
for every struct member in the field vocabulary, the functions that compare it (file, line, in target-arch code?);
the per-architecture values of every boundary item that was chosen for a score.
"""
import gzip
import json
import re
import sys

import hints4
import rank

DRV = re.compile(r"^drivers/.*(riscv|sifive|-sbi)")


def main():
    g, fp, vp, fvp, out = sys.argv[1:6]
    facts = json.load(gzip.open(fp, "rt"))
    vals = json.load(open(vp))
    h = hints4.run(facts, vals, {"I1", "I2", "I3", "I4"})
    pnames, cutoff = rank.patch_names(g)
    scored, _ = rank.score_sites(h, facts, vals, pnames)
    idx = h["functions_index"]
    sites = {}
    items = set()
    for sc, ss in scored.items():
        sites[sc] = []
        for s in ss:
            f = idx.get(s["fn"], [None, None, None])
            sites[sc].append({"fn": s["fn"], "file": f[0], "fn_line": f[1], "line": s["line"], "depth": s["depth"],
                              "cb_hops": s.get("cb_hops", 0), "score": round(s["score"], 4), "e_item": s["e_item"],
                              "e": s["e"], "P": s["P"], "items": sorted(s["items"])[:30], "values": s["values"]})
            if s["e_item"]:
                items.add(s["e_item"])
    fv = json.load(open(fvp))["vocab"]
    members = {m for d in fv.values() for m in d}
    fields = {}
    for f in facts["functions"].values():
        hit = set()
        for gd in f["guards"]:
            for c in gd["cmps"]:
                for side in c["sides"]:
                    hit.update(m for m in side.get("m", []) if m in members)
        for sw in f.get("switches", []):
            hit.update(m for m in sw.get("m", []) if m in members)
        for m in hit:
            arch = f["file"].startswith("arch/riscv/") or bool(DRV.search(f["file"]))
            fields.setdefault(m, []).append([f["name"], f["file"], f["line"], arch])
    res = {"group": g, "patch_cutoff": cutoff, "sites": sites, "raw_nr": h["raw_nr"],
           "fields": {m: sorted(v, key=lambda x: (not x[3], x[1], x[2]))[:40] for m, v in fields.items()},
           "macro_values": {i: {a: vals[a].get(i) for a in ("riscv", "arm64", "x86_64")}
                            for i in sorted(items | {"TASK_SIZE_MAX", "TASK_SIZE", "NR_syscalls"})}}
    json.dump(res, open(out, "w"), indent=0)
    print(g, "syscalls with sites", len(sites), "sites", sum(len(v) for v in sites.values()), "fields", len(fields),
          "items", len(items))


if __name__ == "__main__":
    main()
