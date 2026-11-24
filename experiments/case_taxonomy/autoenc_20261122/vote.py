"""autoenc criteria 二.5-二.6 and 三: majority vote over builds -> laws and deviations; clang reproduction of truncation witnesses;
G1 rediscovery check. WSL (clang reproduction), the rest runs anywhere.

    python3 vote.py vote        -> laws.json, deviations.json
    python3 vote.py repro       -> repro.json (clang -O2 folds the witness of every truncation deviation)
    python3 vote.py report      -> report.json, candidates.md, g1.json
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILDS = ["riscv64", "rv32_abi", "x86_64", "i386", "i386_pae", "arm64", "ppc64le", "ppc64le_hash", "ppc64e", "ppc32s", "ppc44x", "ppc8xx",
          "s390", "loongarch", "mips32", "mips32xpa", "mips64", "arm", "arm_lpae", "hexagon"]
NOVOTE = ("unsup", "domain-unknown", "runtime-dependent", "constants unknown", "imprecise", "not-applicable")


def norm(beh):
    """the vote compares behaviour classes; for a truncation the class is 'idlow:<param>' (k kept for the report)"""
    return ":".join(beh.split(":")[:2]) if beh.startswith("idlow:") else beh


def load():
    out = {}
    for b in BUILDS:
        p = HERE / f"beh_{b}.json"
        if p.exists():
            out[b] = json.loads(p.read_text(encoding="utf-8"))
    return out


def vote():
    beh = load()
    per = defaultdict(dict)
    for b, d in beh.items():
        for k, v in d["laws"].items():
            per[k][b] = v
    laws, devs = {}, []
    for k, bv in per.items():
        votes = {b: norm(v["beh"]) for b, v in bv.items() if v["beh"] not in NOVOTE}
        if len(votes) < 3:
            continue
        top, n = Counter(votes.values()).most_common(1)[0]
        if n * 2 <= len(votes):
            continue
        laws[k] = {"majority": top, "n_major": n, "n_comparable": len(votes), "n_builds": len(bv)}
        for b, cls in votes.items():
            if cls != top:
                v = bv[b]
                fam = k.split("|")[0]
                obs = k.split("|")[-1].split(">")[-1]
                trunc = v["beh"].startswith("idlow:") and top.startswith("id:") and top.split(":")[1] == v["beh"].split(":")[1]
                classif = fam == "SW" and (obs.endswith("_present") or obs.endswith("_none"))
                fallback = str(v.get("dom", "")).startswith("回退")
                prio = 1 if (classif or (trunc and not fallback)) else 2
                devs.append({"key": k, "build": b, "majority": top, "deviant": v["beh"], "prio": prio, "truncation": trunc,
                             "classification": classif, "dom": v.get("dom"), "nbits": v.get("nbits"), "kind": v.get("kind")})
    (HERE / "laws.json").write_text(json.dumps(laws, indent=1, ensure_ascii=False), encoding="utf-8")
    (HERE / "deviations.json").write_text(json.dumps(devs, indent=1, ensure_ascii=False), encoding="utf-8")
    fam = Counter(k.split("|")[0] for k in laws)
    print(json.dumps({"law_keys_total": len(per), "laws": len(laws), "laws_by_family": fam, "deviations": len(devs),
                      "deviations_by_prio": Counter(d["prio"] for d in devs), "truncations": sum(d["truncation"] for d in devs)},
                     ensure_ascii=False))


def c_expr(key, arg):
    """the C expression of a law key, with the constructor's offset/pfn argument = arg (type argument = 1)"""
    p = key.split("|")
    if p[0] == "SW":
        _, layer, cons, enc, mod, obs = p
        names = json.loads((HERE / "names.json").read_text(encoding="utf-8"))["names"]
        npar = len(names.get(cons, {}).get("params") or [])
        e = f"{cons}(1UL, {arg}UL)" if npar == 2 else f"{cons}({arg}UL)"
        x = f"{enc}({e})"
        if mod != "-":
            x = f"{mod}({x})"
        if ">" in obs:
            dec, o = obs.split(">")
            return f"(unsigned long long){o}({dec}({x}))"
        return f"(unsigned long long){obs}({x})"
    _, cons, prot, mod, obs = p
    x = f"{cons}({arg}UL, {prot})"
    if mod != "-":
        x = f"{mod}({x})"
    return f"(unsigned long long){obs}({x})"


def repro():
    sys.path.insert(0, str(HERE.parent / "swapsym_20261121"))
    import swaparch as A
    S = A.S
    devs = json.loads((HERE / "deviations.json").read_text(encoding="utf-8"))
    hdr = "#include <linux/mm.h>\n#include <linux/pgtable.h>\n#include <linux/swapops.h>\n#include <linux/leafops.h>\n"
    out = []
    byb = defaultdict(list)
    for i, d in enumerate(devs):
        if d["truncation"]:
            byb[d["build"]].append((i, d))
    for b, items in byb.items():
        if b in A.ARCHES or b == "ppc64le_hash":
            A.register(b)
        src, names = hdr, []
        for i, d in items:
            k = int(d["deviant"].split(":")[2])
            arg = 1 << k
            fn = f"RP_{i}"
            src += f"unsigned long long {fn}(void) {{ return {c_expr(d['key'], arg)}; }}\n"
            names.append((fn, i, d, arg))
        try:
            got = S.clang_consts(b, src, [n for n, *_ in names])
        except Exception as ex:
            for fn, i, d, arg in names:
                out.append({"i": i, "build": b, "key": d["key"], "status": f"编译失败 {str(ex)[:200]}"})
            continue
        for fn, i, d, arg in names:
            v = got.get(fn)
            st = "无法折叠" if v is None else ("复现（读回值不等于输入）" if v != arg else "不一致（读回值等于输入）")
            out.append({"i": i, "build": b, "key": d["key"], "input": hex(arg), "clang": None if v is None else hex(v), "status": st})
        print(b, Counter(o["status"] for o in out if o["build"] == b), flush=True)
    (HERE / "repro.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


G1 = {
    # obligation of rounds 3-5 -> the law-key pattern the automatic mining must contain (checked only after mining, criteria 三 G1)
    "O1 普通交换项编码后非有效": ("SW|public|swp_entry|swp_entry_to_pte|-|pte_present", "const:0"),
    "O1 普通交换项编码后非空": ("SW|public|swp_entry|swp_entry_to_pte|-|pte_none", "const:0"),
    "O2 编码不占独占位": ("SW|public|swp_entry|swp_entry_to_pte|-|pte_swp_exclusive", "const:0"),
    "O3 类型读回": ("SW|public|swp_entry|swp_entry_to_pte|-|softleaf_from_pte>swp_type", "id:type"),
    "O3 偏移读回": ("SW|public|swp_entry|swp_entry_to_pte|-|softleaf_from_pte>swp_offset", "id:offset"),
    "P1 迁移项编码后非有效": ("SW|public|make_writable_migration_entry|swp_entry_to_pte|-|pte_present", "const:0"),
    "P1 迁移项编码后非空": ("SW|public|make_writable_migration_entry|swp_entry_to_pte|-|pte_none", "const:0"),
    "P3 迁移项类型读回": ("SW|public|make_writable_migration_entry|swp_entry_to_pte|-|softleaf_from_pte>swp_type", "eq:type"),
    "P3 迁移项页帧号读回": ("SW|public|make_writable_migration_entry|swp_entry_to_pte|-|softleaf_from_pte>swp_offset", "id:offset"),
    "PMD O1 非有效": ("SW|public|swp_entry|swp_entry_to_pmd|-|pmd_present", "const:0"),
    "PMD O3 偏移读回": ("SW|public|swp_entry|swp_entry_to_pmd|-|softleaf_from_pmd>swp_offset", "id:offset"),
}
EXPECT_TRUNC = {"arm_lpae", "mips32xpa", "ppc44x", "mips64"}


def report():
    laws = json.loads((HERE / "laws.json").read_text(encoding="utf-8"))
    devs = json.loads((HERE / "deviations.json").read_text(encoding="utf-8"))
    rp = {(r["build"], r["key"]): r for r in json.loads((HERE / "repro.json").read_text(encoding="utf-8"))} if (HERE / "repro.json").exists() else {}
    g1 = {}
    for lab, (key, want) in G1.items():
        lw = laws.get(key)
        g1[lab] = {"key": key, "found": lw is not None and lw["majority"] == want, "law": lw,
                   "deviations": sorted(d["build"] for d in devs if d["key"] == key)}
    trunc_builds = sorted({d["build"] for d in devs if d["truncation"] and "migration" in d["key"] and d["key"].endswith(">swp_offset")})
    ord_dev = sorted({d["build"] for d in devs if "|swp_entry|" in d["key"] and d["key"].startswith("SW|public")})
    g1["页帧号截断自动出现在 arm_lpae/mips32xpa/ppc44x/mips64"] = {"found": EXPECT_TRUNC <= set(trunc_builds), "builds": trunc_builds}
    g1["普通交换项无偏离"] = {"found": not ord_dev, "builds": ord_dev}
    (HERE / "g1.json").write_text(json.dumps(g1, indent=1, ensure_ascii=False), encoding="utf-8")
    rows = []
    for d in sorted(devs, key=lambda d: (d["prio"], d["key"], d["build"])):
        r = rp.get((d["build"], d["key"]))
        rows.append(f"| {d['prio']} | {d['build']} | `{d['key']}` | {d['majority']} | {d['deviant']} | {d.get('dom') or ''} | {r['status'] if r else ''} |")
    (HERE / "candidates.md").write_text("| 优先级 | 构建 | 组合 | 多数行为 | 该构建行为 | 域来源 | clang 复现 |\n|---|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n",
                                        encoding="utf-8")
    rep = {"G1_all": all(v["found"] for v in g1.values()), "G1": {k: v["found"] for k, v in g1.items()},
           "G2_repro": Counter(r["status"] for r in rp.values()),
           "laws": len(laws), "deviations": len(devs), "prio": Counter(d["prio"] for d in devs),
           "deviations_by_family": Counter(d["key"].split("|")[0] for d in devs)}
    (HERE / "report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(rep, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    {"vote": vote, "repro": repro, "report": report}[sys.argv[1]]()
