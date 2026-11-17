"""kcov_inline criteria 四: same analyses as kcov_20261115/analyze_kcov.py, on inline-expanded coverage.

Reuses analyze_kcov.py read-only (its output dir is redirected to this directory).
    python analyze_inline.py [judge_head.json path]
        -> accuracy.json, pipeline_kcov_<tree>.json, report_kcov_<tree>.md, reach.json, missing2.json, missing2.md
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREV = HERE.parent / "kcov_20261115"
sys.path.insert(0, str(PREV))
import analyze_kcov as A  # noqa: E402
from classify_missing import ARCHDIR  # noqa: E402

A.HERE = HERE  # coverage_<tag>.json read from, outputs written to this directory


def notins(tag):
    files, dirs = set(), set()
    import re
    for line in (PREV / f"kcov_not_instrumented_{tag}.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"(.*/)?Makefile:\d+:\s*KCOV_INSTRUMENT(?:_([\w$().-]+)\.o)?\s*:=\s*n", line)
        if m:
            d = m.group(1) or ""
            (files.add(d + m.group(2) + ".c") if m.group(2) else dirs.add(d))
    return files, dirs


def missing(acc):
    defs = {}
    for line in (PREV / "funcinfo.txt").read_text(encoding="utf-8").splitlines():
        f, _, d = line.split("|")
        defs[f] = [x for x in d.split(",") if x]
    old = json.loads((PREV / "missing_classified.json").read_text(encoding="utf-8"))
    res, md = {}, ["# 展开内联后仍没测到的函数", ""]
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
        old_inl = {tuple(x) for x in old[tag]["items"]["inlined"]}
        still = {(a, t, f) for a, t, f in un + other}
        recovered = len(old_inl - still)
        res[tag] = {"listed": acc[tag]["listed"], "observed": acc[tag]["observed"], "uninstrumented": un, "other": other,
                    "old_inlined": len(old_inl), "old_inlined_recovered": recovered}
        md += [f"## {'当前版本' if tag == 'head' else 'X1 修复前'}", "",
               f"手写表 {acc[tag]['listed']} 项，测到 {acc[tag]['observed']} 项（{acc[tag]['observed'] / acc[tag]['listed']:.0%}）。"
               f"上一轮的 {len(old_inl)} 项内联盲区，本轮测到 {recovered} 项。仍没测到 {len(un) + len(other)} 项：所在文件没插桩 {len(un)}，其他 {len(other)}。", ""]
        for name, items in (("所在文件没插桩", un), ("其他", other)):
            by = {}
            for a, t, f in items:
                by.setdefault(f, []).append(f"{a}:{t}")
            md += [f"### {name}（{len(items)} 项）", ""] + ([f"- `{f}`：{'、'.join(sorted(v))}" for f, v in sorted(by.items())] or ["（无）"]) + [""]
    (HERE / "missing2.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    (HERE / "missing2.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return res


def merge_and_regress():
    """amendment 1.3: CUR verdicts = this round's riscv/x86_64 + previous round's arm64; regression of reruns."""
    L, merged = [], {}
    for tag in ("head", "x1pre"):
        new = A.load(HERE / f"judge_{tag}.json")
        old = A.load(PREV / f"judge_{tag}.json")
        diff = [(k, new[k]["violated"], old[k]["violated"]) for k in sorted(new)
                if k in old and bool(new[k]["violated"]) != bool(old[k]["violated"])]
        viol = sorted(k for k, v in new.items() if v["violated"])
        inval = sorted(k for k, v in new.items() if v["valid"] < v["runs"])
        L.append(f"{tag}：本轮重跑违反 {viol or '无'}；有无效运行 {inval or '无'}；与上一轮不一致 {len(diff)} 项 {diff}")
        if tag == "head":
            merged = {**{k: v for k, v in old.items() if k.startswith("arm64")}, **new}
    (HERE / "judge_head_merged.json").write_text(json.dumps(merged, indent=1), encoding="utf-8")
    (HERE / "regression.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    return L


def main():
    for line in merge_and_regress():
        print(line)
    jhead = HERE / "judge_head_merged.json"
    acc = A.accuracy()
    for tag, v in acc.items():
        print("accuracy", tag, v["observed"], "/", v["listed"], v["ratio"])
    st7 = A.CT / "effdep7_dev_20261113/out"
    for args in (("X1_pre", st7 / "X1.json", A.PV2 / "judge_x1.json", "_pre", "x1pre", "_x1pre", "X1 修复前（覆盖：X1 修复前 KCOV 内核，展开内联）"),
                 ("X1_fix", st7 / "X1.json", A.PV2 / "judge_x1.json", "_fix", "x1pre", "_x1pre", "X1 修复后对照（判错：修复后内核；覆盖：沿用修复前，展开内联）"),
                 ("CUR", st7 / "CUR_riscv.json", jhead, "_head", "head", "_head", "当前版本（KCOV 内核，展开内联）")):
        r = A.pipeline(*args)
        print("pipeline", r["tree"], r["counts"], "orphan", r["orphan_violations"])
    for k, v in A.reach().items():
        print("reach", k, v["fn_executed"], "/", v["candidates"], "fn or interface", v["fn_or_interface_executed"])
    for tag, v in missing(acc).items():
        print("missing", tag, "uninstrumented", len(v["uninstrumented"]), "other", len(v["other"]),
              "old inlined recovered", v["old_inlined_recovered"], "/", v["old_inlined"])


if __name__ == "__main__":
    main()
