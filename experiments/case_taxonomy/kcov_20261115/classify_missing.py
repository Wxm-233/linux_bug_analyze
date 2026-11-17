"""Why did KCOV not see a hand-listed function? (explains criteria 四.2; added after the first look at accuracy.json)

    python classify_missing.py    (needs accuracy.json, funcinfo.txt, kcov_not_instrumented_<tag>.txt)
        -> missing_classified.json, missing_classified.md

Each (tag, arch, template, function) listed in templates.json but not observed falls into one class:
  inlined        the function has no text symbol in that kernel (inlined, or renamed / absent there)
  uninstrumented it has a symbol, but the .c file defining it is built with KCOV_INSTRUMENT := n
  not_observed   symbol present and file instrumented, yet not in the template's coverage
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARCHDIR = {"riscv": "arch/riscv/", "x86_64": "arch/x86/", "arm64": "arch/arm64/"}


def not_instrumented(tag):
    files, dirs = set(), set()
    for line in (HERE / f"kcov_not_instrumented_{tag}.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"(.*/)?Makefile:\d+:\s*KCOV_INSTRUMENT(?:_([\w$().-]+)\.o)?\s*:=\s*n", line)
        if not m:
            continue
        d = m.group(1) or ""
        if m.group(2):
            files.add(d + m.group(2) + ".c")
        else:
            dirs.add(d)
    return files, dirs


def main():
    acc = json.loads((HERE / "accuracy.json").read_text(encoding="utf-8"))
    info = {}
    for line in (HERE / "funcinfo.txt").read_text(encoding="utf-8").splitlines():
        f, nm, defs = line.split("|")
        info[f] = (set(nm.split()), [d for d in defs.split(",") if d])
    res, md = {}, ["# 手写表里没测到的函数，按原因分类", "",
                  "- 内联：该内核里这个函数没有独立符号（被内联，或该版本里改名、不存在）；",
                  "- 没插桩：有符号，但定义它的 .c 文件编译时关掉了 KCOV（`KCOV_INSTRUMENT ... := n`）；",
                  "- 有插桩但没记到：有符号、文件也插桩了，模板执行时却没记到。", ""]
    for tag, suffix in (("head", "_head"), ("x1pre", "_x1pre")):
        files, dirs = not_instrumented("HEAD" if tag == "head" else "x1pre")
        cls = {"inlined": [], "uninstrumented": [], "not_observed": []}
        listed = acc[tag]["listed"]
        for key, v in acc[tag]["per"].items():
            arch, t = key.split("|")
            base = arch.replace("（开 MTE）", "")
            for f in v["missing"]:
                nm, defs = info.get(f, (set(), []))
                if f"{base}{suffix}" not in nm:
                    cls["inlined"].append((arch, t, f))
                    continue
                own = [d for d in defs if d.startswith(ARCHDIR[base])]
                generic = [d for d in defs if not d.startswith("arch/")]
                cand = own or generic
                un = bool(cand) and all(d in files or any(d.startswith(x) for x in dirs) for d in cand)
                cls["uninstrumented" if un else "not_observed"].append((arch, t, f))
        obs = acc[tag]["observed"]
        observable = listed - len(cls["inlined"]) - len(cls["uninstrumented"])
        res[tag] = {"listed": listed, "observed": obs, **{k: len(x) for k, x in cls.items()},
                    "observable": observable, "ratio_observable": round(obs / observable, 3) if observable else None,
                    "items": {k: [list(x) for x in v] for k, v in cls.items()}}
        md += [f"## {'当前版本' if tag == 'head' else 'X1 修复前'}内核", "",
               f"手写表（模板 × 架构）共 {listed} 项，实测执行到 {obs} 项（{obs / listed:.0%}）。没测到的 {listed - obs} 项中："
               f"内联 {len(cls['inlined'])}，没插桩 {len(cls['uninstrumented'])}，有插桩但没记到 {len(cls['not_observed'])}。"
               f"去掉 KCOV 本来就看不到的两类之后，可观测的 {observable} 项里执行到 {obs} 项"
               f"（{obs / observable:.0%}）。" if observable else "", ""]
        for k, h in (("uninstrumented", "没插桩"), ("not_observed", "有插桩但没记到"), ("inlined", "内联")):
            by = {}
            for arch, t, f in cls[k]:
                by.setdefault(f, []).append(f"{arch}:{t}")
            md += [f"### {h}（{len(cls[k])} 项，{len(by)} 个函数）", ""]
            md += [f"- `{f}`：{'、'.join(sorted(v))}" for f, v in sorted(by.items())] or ["（无）"]
            md.append("")
    (HERE / "missing_classified.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    (HERE / "missing_classified.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    for tag, v in res.items():
        print(tag, {k: v[k] for k in ("listed", "observed", "inlined", "uninstrumented", "not_observed", "observable", "ratio_observable")})


if __name__ == "__main__":
    main()
