"""ecscan criteria 一: whole-version scan = scan3's 8 frozen engines + EC (encoding consistency). WSL.

    python3 scan4.py scan <rev> [N]     -> run missing engine jobs (8 old engines via scan3's job list, then EC), then table
    python3 scan4.py table <rev>        -> tables/<rev12>.{csv,json,md} from the caches only
    python3 scan4.py verify             -> criteria 四 G2: the 8 old engines' counts on df2908090cda equal scan3's
scan3, checks3 and the old engines are imported, not modified; scan3's own tables are not touched.
"""
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "scan3_20261119"))
import scan3 as S3  # noqa: E402
C3, M = S3.C3, S3.M

GROUPS = {g: list(es) for g, es in C3.GROUPS.items()}
GROUPS["实现一致性检查"].append("EC")
CHECK_OF = {e: g for g, es in GROUPS.items() for e in es}
CHECK_ORDER = list(GROUPS)
ENGINE_ORDER = [e for es in GROUPS.values() for e in es]
EC_CACHE = Path("/root/work/ec_cache")


def ec_rows(rev):
    p = EC_CACHE / f"{rev}.json"
    if not p.exists():
        return [], "todo"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return [], "broken"
    if not d.get("ok"):
        return [], f"error: {d.get('error', '')}"
    rows = [{"file": c["file"], "line": c["line"], "func": c["func"], "arch": c["arch"], "sig": c["sig"], "prio": c["prio"],
             "engine": "EC", "check": CHECK_OF["EC"]} for c in d["cands"]]
    return rows, "ok"


def rows_of(rev):
    rev = M.full(rev)
    rows, status = S3.rows_of(rev)
    er, es = ec_rows(rev)
    rows = [dict(r) for r in rows] + er
    status = dict(status, EC=es)
    rows.sort(key=lambda r: (r["prio"], CHECK_ORDER.index(r["check"]), ENGINE_ORDER.index(r["engine"]), r["file"], r["line"]))
    for i, r in enumerate(rows, 1):
        r["no"] = i
    return rows, status


def table(rev):
    rev = M.full(rev)
    rows, status = rows_of(rev)
    tag = rev[:12]
    d = HERE / "tables"
    d.mkdir(exist_ok=True)
    cols = [("no", "序号"), ("check", "检查类"), ("engine", "引擎"), ("prio", "优先级"), ("file", "文件"), ("line", "行"),
            ("func", "函数"), ("arch", "受影响架构"), ("sig", "特征")]
    with open(d / f"{tag}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([c[1] for c in cols])
        for r in rows:
            w.writerow([("一" if r[k] == 1 else "二") if k == "prio" else r[k] for k, _ in cols])
    info = M.git("log", "-1", "--format=%h|%cs|%s", rev).strip()
    (d / f"{tag}.json").write_text(json.dumps({"rev": rev, "info": info, "status": status, "rows": rows}, indent=1, ensure_ascii=False),
                                   encoding="utf-8")
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
    (d / f"{tag}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"table: tables/{tag}.csv ({len(rows)} rows)")
    return rows, status


def scan(rev, n=8):
    S3.check_frozen()
    rev = M.full(rev)
    todo = [j for j in S3.rev_jobs(rev) if S3.cache_state(j[2]) not in ("ok", "error")]
    running = []
    out = open(HERE / "engines_output.log", "a")
    while todo or running:
        running = [(j, pr) for j, pr in running if pr.poll() is None]
        while todo and len(running) < n:
            j = todo.pop(0)
            running.append((j, subprocess.Popen([sys.executable, *j[3]], stdout=out, stderr=subprocess.STDOUT)))
        time.sleep(3)
    if ec_rows(rev)[1] in ("todo", "broken"):
        subprocess.run([sys.executable, str(HERE / "ec.py"), "engine", rev], stdout=out, stderr=subprocess.STDOUT)
    return table(rev)


def verify():
    rows, status = rows_of(S3.HEAD)
    want = {"P1": 53, "XV": 56, "ORD": 59, "WT": 746, "TLB": 9, "CTX": 9, "WK": 5, "XA": 1}
    print("status", status)
    ok = True
    for e in ENGINE_ORDER:
        got = sum(1 for r in rows if r["engine"] == e)
        if e in want:
            ok &= got == want[e]
            print(f"  {e:4s} got {got:4d} want {want[e]:4d} {'OK' if got == want[e] else 'MISMATCH'}")
        else:
            print(f"  {e:4s} got {got:4d} (new engine)")
    print("G2", "OK" if ok else "FAIL")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "scan":
        scan(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 8)
    elif cmd == "table":
        table(sys.argv[2])
    elif cmd == "verify":
        verify()
