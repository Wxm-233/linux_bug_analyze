"""kcov_pa criteria 四/五: same analyses as kcov_inline_20261115/analyze_inline.py, with page_alloc.o instrumented.

Reuses kcov_20261115/analyze_kcov.py read-only (output dir redirected here).
    python analyze_pa.py
        -> regression.txt, accuracy.json, pipeline_kcov_<tree>.json, report_kcov_<tree>.md, reach.json, missing3.json, missing3.md
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
K1 = HERE.parent / "kcov_20261115"
K2 = HERE.parent / "kcov_inline_20261115"
sys.path.insert(0, str(K1))
import analyze_kcov as A  # noqa: E402
from classify_missing import ARCHDIR  # noqa: E402

A.HERE = HERE


def notins(tag):  # previous list minus mm/page_alloc.c (criteria 四.4)
    files, dirs = set(), set()
    for line in (K1 / f"kcov_not_instrumented_{tag}.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"(.*/)?Makefile:\d+:\s*KCOV_INSTRUMENT(?:_([\w$().-]+)\.o)?\s*:=\s*n", line)
        if m:
            d = m.group(1) or ""
            (files.add(d + m.group(2) + ".c") if m.group(2) else dirs.add(d))
    files.discard("mm/page_alloc.c")
    return files, dirs


def regress():
    L = []
    for tag in ("head", "x1pre"):
        new, old = A.load(HERE / f"judge_{tag}.json"), A.load(K1 / f"judge_{tag}.json")
        diff = [(k, new.get(k, {}).get("violated"), old[k]["violated"]) for k in sorted(old)
                if k not in new or bool(new[k]["violated"]) != bool(old[k]["violated"])]
        viol = sorted(f"{k}={v['violated']}/{v['valid']}" for k, v in new.items() if v["violated"])
        inval = sorted(k for k, v in new.items() if v["valid"] < v["runs"])
        L.append(f"{tag}：本轮违反 {viol or '无'}；有无效运行 {inval or '无'}；与 kcov_20261115 不一致或缺失 {len(diff)} 项 {diff}")
    (HERE / "regression.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    return L


def missing(acc):
    defs = {}
    for line in (K1 / "funcinfo.txt").read_text(encoding="utf-8").splitlines():
        f, _, d = line.split("|")
        defs[f] = [x for x in d.split(",") if x]
    prev = json.loads((K2 / "missing2.json").read_text(encoding="utf-8"))
    res, md = {}, ["# 打开 page_alloc.o 插桩后仍没测到的函数", ""]
    for tag in ("head", "x1pre"):
        files, dirs = notins("HEAD" if tag == "head" else "x1pre")
        un, other = [], []
        for key, v in acc[tag]["per"].items():
            arch, t = key.split("|")
            base = arch.replace("（开 MTE）", "")
            for f in v["missing"]:
                ds = defs.get(f, [])
                cand = [d for d in ds if d.startswith(ARCHDIR[base])] or [d for d in ds if not d.startswith("arch/")]
                (un if cand and all(d in files or any(d.startswith(x) for x in dirs) for d in cand) else other).append([arch, t, f])
        before = {tuple(x) for x in prev[tag]["uninstrumented"] + prev[tag]["other"]}
        now = {tuple(x) for x in un + other}
        res[tag] = {"listed": acc[tag]["listed"], "observed": acc[tag]["observed"], "uninstrumented": un, "other": other,
                    "recovered_vs_inline_round": sorted(before - now), "newly_missing_vs_inline_round": sorted(now - before)}
        md += [f"## {'当前版本' if tag == 'head' else 'X1 修复前'}", "",
               f"手写表 {acc[tag]['listed']} 项，测到 {acc[tag]['observed']} 项（{acc[tag]['observed'] / acc[tag]['listed']:.0%}）。"
               f"与 kcov_inline 相比，新测到 {len(before - now)} 项，新没测到 {len(now - before)} 项。"
               f"仍没测到 {len(un) + len(other)} 项：所在文件没插桩 {len(un)}，其他 {len(other)}。", ""]
        for name, items in (("新测到（相对 kcov_inline）", sorted(before - now)), ("新没测到（相对 kcov_inline）", sorted(now - before)),
                            ("所在文件没插桩", un), ("其他", other)):
            by = {}
            for a, t, f in items:
                by.setdefault(f, []).append(f"{a}:{t}")
            md += [f"### {name}（{len(items)} 项）", ""] + ([f"- `{f}`：{'、'.join(sorted(v))}" for f, v in sorted(by.items())] or ["（无）"]) + [""]
    (HERE / "missing3.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    (HERE / "missing3.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return res


def main():
    for line in regress():
        print(line)
    acc = A.accuracy()
    for tag, v in acc.items():
        print("accuracy", tag, v["observed"], "/", v["listed"], v["ratio"])
    pah = {k: v["observed"] for k, v in acc["head"]["per"].items()}
    print("post_alloc_hook head:", {k: ("post_alloc_hook" not in v["missing"]) for k, v in acc["head"]["per"].items()
                                    if k.split("|")[1] in ("Z2", "Z3", "Z4", "Z7")})
    st7 = A.CT / "effdep7_dev_20261113/out"
    for args in (("X1_pre", st7 / "X1.json", A.PV2 / "judge_x1.json", "_pre", "x1pre", "_x1pre", "X1 修复前（覆盖：本轮 X1 修复前内核，page_alloc 插桩，展开内联）"),
                 ("X1_fix", st7 / "X1.json", A.PV2 / "judge_x1.json", "_fix", "x1pre", "_x1pre", "X1 修复后对照（判错：修复后内核；覆盖：沿用本轮修复前内核）"),
                 ("CUR", st7 / "CUR_riscv.json", HERE / "judge_head.json", "_head", "head", "_head", "当前版本（本轮内核）")):
        r = A.pipeline(*args)
        print("pipeline", r["tree"], r["counts"], "orphan", r["orphan_violations"])
    for k, v in A.reach().items():
        print("reach", k, v["fn_executed"], "/", v["candidates"], "fn or interface", v["fn_or_interface_executed"])
    for tag, v in missing(acc).items():
        print("missing", tag, "uninstrumented", len(v["uninstrumented"]), "other", len(v["other"]),
              "recovered", len(v["recovered_vs_inline_round"]), "newly missing", len(v["newly_missing_vs_inline_round"]))


if __name__ == "__main__":
    main()
