"""effrule criteria 二: nearest skipped effect for every effdep candidate. Runs in WSL (needs the facts files).

    python3 effects.py selftest
    python3 effects.py            -> effects.json  (13 effdep7 trees + effdep5 CUR_riscv as "E5_CUR_riscv")
"""
import glob
import gzip
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
F5 = Path("/root/work/effdep5/facts")

FAMILIES = [  # (family, rule), in priority order R4 > R1 > R2 > R3 (criteria 二.4)
    ("pte_write", "R4", [r"(__)?set_(pte|pmd|pud|p4d)s?(_at)?", r"set_huge_pte_at", r"(pte|pmd|pud|p4d)_clear",
                         r"\w*ptep?_get_and_clear\w*", r"get_and_clear_ptes"]),
    ("page_clear", "R1", [r"(clear_page|clear_pages|clear_user_page|clear_huge_page|memzero_page)", r"\w*clear_\w*highpage\w*",
                          r"zero_user\w*", r"folio_zero\w*"]),
    ("tlb_flush", "R2", [r"\w*flush_tlb\w*", r"\w*tlb_flush\w*", r"\w*flush_\w*tlbs?(_\w+)?", r"sfence_vma\w*", r"\w*tlbi\w*",
                         r"arch_tlbbatch_\w+"]),
    ("cache_flush", "R3", [r"\w*flush_(dcache|icache|cache)\w*", r"\w*dcache_(clean|inval)\w*", r"\w*icache_inval\w*",
                           r"caches_clean_inval\w*", r"\w*sync_icache\w*"]),
]
FRX = [(f, r, re.compile("^(" + "|".join(p) + ")$")) for f, r, p in FAMILIES]
VALBIT = re.compile(r"^\w*_bits?$")
MAXD = 2


def fam_of(name):
    if VALBIT.match(name):
        return []
    return [f for f, _, rx in FRX if rx.match(name)]


def nearest(S, callees):
    """callees: name -> set of callee names, or None when the name has no definition in the facts.
    Returns dict(depth, families, hits, rule, also, unexpanded)."""
    seen = set(S)
    level = sorted(set(S))
    unexpanded = set()
    for d in range(MAXD + 1):
        hits = {}
        for n in level:
            for f in fam_of(n):
                hits.setdefault(f, []).append(n)
        if hits:
            fams = [f for f, _, _ in FRX if f in hits]
            rules = [r for f, r, _ in FRX if f in hits]
            return {"depth": d, "families": fams, "hits": {f: sorted(set(v)) for f, v in hits.items()}, "rule": rules[0],
                    "also": rules[1:], "unexpanded": sorted(unexpanded)}
        if d == MAXD:
            break
        nxt = set()
        for n in level:
            if VALBIT.match(n):
                continue
            cs = callees(n)
            if cs is None:
                unexpanded.add(n)
                continue
            nxt |= {c for c in cs if c not in seen}
        seen |= nxt
        level = sorted(nxt)
    return {"depth": None, "families": [], "hits": {}, "rule": None, "also": [], "unexpanded": sorted(unexpanded)}


def selftest():
    G = {"a": {"b"}, "b": {"c"}, "c": {"clear_page"}, "k": {"x"}, "x": {"clear_highpage_kasan_tagged"},
         "clear_highpage_kasan_tagged": {"clear_page"}, "m": {"set_ptes", "flush_tlb_range"}, "n": {"p"}, "p": {"flush_icache_range", "q"},
         "q": {"set_pte_at"}, "w": {"pte_bits", "memset"}}
    cb = lambda n: G.get(n)  # noqa: E731
    cases = [
        (["clear_page"], (0, "R1", ["page_clear"])),
        (["k"], (2, "R1", ["page_clear"])),               # like kernel_init_pages: depth 2
        (["a"], (None, None, [])),                       # clear_page only at depth 3
        (["m"], (1, "R4", ["pte_write", "tlb_flush"])),   # two families at depth 1: R4 wins
        (["n"], (2, "R3", ["cache_flush"])),             # depth 2 cache, depth 3 pte ignored
        (["p"], (1, "R3", ["cache_flush"])),             # nearest only: depth 1 cache, depth 2 pte not taken
        (["w"], (None, None, [])),                       # memset counts for nothing; *_bits skipped
        (["unknown_fn"], (None, None, [])),              # no definition: name only, recorded
        (["kvm_flush_remote_tlbs_range"], (0, "R2", ["tlb_flush"])),
        (["get_and_clear_ptes", "zz"], (0, "R4", ["pte_write"])),
        (["tag_clear_highpage"], (0, "R1", ["page_clear"])),
        (["set_bits"], (None, None, [])),
    ]
    bad = 0
    for S, (d, r, fams) in cases:
        got = nearest(S, cb)
        ok = (got["depth"], got["rule"], got["families"]) == (d, r, fams)
        bad += not ok
        print("ok " if ok else "BAD", S, got)
    assert nearest(["unknown_fn"], cb)["unexpanded"] == ["unknown_fn"]
    print("selftest", "PASS" if not bad else f"FAIL {bad}")
    return bad == 0


def load_facts(p):
    T = json.load(gzip.open(p, "rt"))
    cal = {}
    for f in T["functions"].values():
        cal.setdefault(f["name"], set()).update(c[2] for c in f["calls"])
    return lambda n: cal.get(n)


def run_tree(label, cand_path, facts_path):
    cb = load_facts(facts_path)
    rows = []
    for c in json.loads(Path(cand_path).read_text(encoding="utf-8"))["candidates_list"]:
        S = c.get("same_res_calls") or c.get("skipped_all") or []
        e = nearest(S, cb)
        rows.append({"fn": c["fn"], "interface": c["interface"], "call_line": c["call_line"], "skipped": c["skipped"], "S": S, **e})
    return rows


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(0 if selftest() else 1)
    if not selftest():
        sys.exit(1)
    out = {}
    for p in sorted(glob.glob(str(CT / "effdep7_dev_20261113/out/*.json"))):
        tid = Path(p).stem
        fp = F5 / ("CUR_riscv.json.gz" if tid == "CUR_riscv" else f"{tid}_pre.json.gz")
        out[tid] = run_tree(tid, p, fp)
        print(tid, len(out[tid]), flush=True)
    out["E5_CUR_riscv"] = run_tree("E5_CUR_riscv", CT / "effdep5_dev_20261113/out/CUR_riscv.json", F5 / "CUR_riscv.json.gz")
    print("E5_CUR_riscv", len(out["E5_CUR_riscv"]))
    (HERE / "effects.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
