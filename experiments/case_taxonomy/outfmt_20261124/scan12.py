"""outfmt criteria 三: whole-version scan table = ecarm64_20261124/scan11.py (scan3's 8 frozen engines + EC ec10) + three columns
(关键资源 / 要观察的性质 / 不算失配的条件) from outfmt.annotate. Engines and caches are only read. WSL.

    python3 scan12.py table <rev>   -> tables/<rev12>.{csv,json,md}
    python3 scan12.py check <rev>   -> criteria 四.1/四.2 against ecarm64_20261124/tables/<rev12>.csv
"""
import csv
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "ecarm64_20261124"))
import scan11  # noqa: E402  (sets scan4's EC cache to r10)
import outfmt  # noqa: E402

S4 = scan11.S4
M, GROUPS, CHECK_ORDER = S4.M, S4.GROUPS, S4.CHECK_ORDER
COLS = [("no", "序号"), ("check", "检查类"), ("engine", "引擎"), ("prio", "优先级"), ("file", "文件"), ("line", "行"),
        ("func", "函数"), ("arch", "受影响架构"), ("sig", "特征"), ("resource", "关键资源"), ("prop", "要观察的性质"),
        ("ok_if", "不算失配的条件")]


def table(rev):
    rev = M.full(rev)
    if not (scan11.R10 / f"{rev}.json").exists():
        shutil.copy(scan11.R10 / "df" / "df.json", scan11.R10 / f"{rev}.json")     # as scan11.py table
    rows, status = S4.rows_of(rev)
    for r in rows:
        r["resource"], r["prop"], r["ok_if"] = outfmt.annotate(r)
    tag = rev[:12]
    d = HERE / "tables"
    d.mkdir(exist_ok=True)
    with open(d / f"{tag}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([c[1] for c in COLS])
        for r in rows:
            w.writerow([("一" if r[k] == 1 else "二") if k == "prio" else r[k] for k, _ in COLS])
    info = M.git("log", "-1", "--format=%h|%cs|%s", rev).strip()
    (d / f"{tag}.json").write_text(json.dumps({"rev": rev, "info": info, "status": status, "rows": rows}, indent=1,
                                              ensure_ascii=False), encoding="utf-8")
    L = [f"# 候选表汇总：{info}", "", f"引擎状态：{status}", "", "| 检查类 | 引擎 | 优先级一 | 优先级二 | 合计 |", "|---|---|---|---|---|"]
    for g in CHECK_ORDER:
        for e in GROUPS[g]:
            a = sum(1 for r in rows if r["engine"] == e and r["prio"] == 1)
            b = sum(1 for r in rows if r["engine"] == e and r["prio"] == 2)
            L.append(f"| {g} | {e} | {a} | {b} | {a + b} |")
        a = sum(1 for r in rows if r["check"] == g and r["prio"] == 1)
        b = sum(1 for r in rows if r["check"] == g and r["prio"] == 2)
        L.append(f"| **{g}合计** | | **{a}** | **{b}** | **{a + b}** |")
    a = sum(1 for r in rows if r["prio"] == 1)
    L.append(f"| **全部** | | **{a}** | **{len(rows) - a}** | **{len(rows)}** |")
    L += ["", "## 各引擎示例（每个引擎第一行）", "", "| 引擎 | 点位 | 关键资源 | 要观察的性质 | 不算失配的条件 |", "|---|---|---|---|---|"]
    seen = set()
    for r in rows:
        if r["engine"] not in seen:
            seen.add(r["engine"])
            cell = lambda s: str(s).replace("|", "\\|")
            L.append(f"| {r['engine']} | {r['file']}:{r['line']} {r['func']} | {cell(r['resource'])} | {cell(r['prop'])} | {cell(r['ok_if'])} |")
    (d / f"{tag}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    undef = sum(1 for r in rows if r["resource"].startswith(outfmt.UNDEF))
    print(f"table: tables/{tag}.csv ({len(rows)} rows, undefined forms {undef})")
    return rows


def check(rev):
    tag = M.full(rev)[:12]
    old = list(csv.reader(open(CT / "ecarm64_20261124" / "tables" / f"{tag}.csv", encoding="utf-8-sig")))
    new = list(csv.reader(open(HERE / "tables" / f"{tag}.csv", encoding="utf-8-sig")))
    same = len(old) == len(new) and all(o == n[:9] for o, n in zip(old, new))
    empty = sum(1 for n in new[1:] if not all(x.strip() for x in n[9:12]))
    undef = sum(1 for n in new[1:] if n[9].startswith(outfmt.UNDEF))
    print(f"CHECK rows old {len(old) - 1} new {len(new) - 1}; first 9 columns identical: {same}; empty new cells: {empty}; "
          f"undefined forms: {undef}")
    return same and not empty and not undef


if __name__ == "__main__":
    {"table": table, "check": check}[sys.argv[1]](sys.argv[2])
