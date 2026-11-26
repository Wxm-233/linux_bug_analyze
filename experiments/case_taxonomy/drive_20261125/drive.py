"""drive criteria 二: whole-version scan driver that checks every engine cache against the requested version, generates missing
caches with the engines' own commands (scan3 rev_jobs) or reports them missing, and never copies another version's result. WSL.

    python3 drive.py scan <rev> [-j N] [--no-generate]   -> out/<rev12>/{table.csv,table.json,table.md,manifest.json}
    python3 drive.py t1 | t2 | t3 | t4 | t5               -> criteria 三, results in checks/
Engines, scan3/scan4/scan11/scan12 and all caches are only read (caches are written only by the engines' own commands).
"""
import csv
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "scan3_20261119"))
sys.path.insert(0, str(CT / "ecscan_20261122"))
sys.path.insert(0, str(CT / "outfmt_20261124"))
import scan3 as S3  # noqa: E402
import scan4 as S4  # noqa: E402  (only its GROUPS / CHECK_OF / orders are used)
import outfmt  # noqa: E402

M = S3.M
EC_DIR = Path("/root/work/ec_cache/r10")
EC_SCRIPT = CT / "ecarm64_20261124" / "ec10.py"
COLS = [("no", "序号"), ("check", "检查类"), ("engine", "引擎"), ("prio", "优先级"), ("file", "文件"), ("line", "行"),
        ("func", "函数"), ("arch", "受影响架构"), ("sig", "特征"), ("resource", "关键资源"), ("prop", "要观察的性质"),
        ("ok_if", "不算失配的条件")]
DF = "df2908090cda"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def verify(path, full):
    """criteria 二.1: (state, detail, cache_rev)"""
    p = Path(path)
    if not p.exists():
        return "缺失", "没有缓存文件", None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as ex:              # noqa: BLE001
        return "错误", f"缓存无法解析：{ex}", None
    r = d.get("rev")
    if r != full:
        return "拒绝", f"缓存版本与目标版本不符（缓存里是 {r}）", r
    if not d.get("ok"):
        return "错误", f"引擎报错：{str(d.get('error', ''))[:200]}", r
    return "通过", "", r


def ec_rows(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return [{"file": c["file"], "line": c["line"], "func": c["func"], "arch": c["arch"], "sig": c["sig"], "prio": c["prio"],
             "engine": "EC", "check": S4.CHECK_OF["EC"]} for c in d["cands"]]


def scan(rev, j=8, generate=True, out_root=None):
    t0 = time.time()
    full = M.full(rev)
    info = M.git("log", "-1", "--format=%h|%cs|%s", full).strip()
    S3.check_frozen()
    jobs = S3.rev_jobs(full)
    eng = {}
    gen = []
    for e, _, path, cmd in jobs:
        st, det, cr = verify(path, full)
        eng[e] = {"path": str(path), "state": st, "detail": det, "cache_rev": cr, "source": "已有缓存" if st == "通过" else None,
                  "script": cmd[0], "script_sha256": sha(cmd[0])}
        if st == "缺失" and generate:
            gen.append((e, path, cmd))
    if gen:                                                   # criteria 二.2: the engines' own commands, as scan4.scan
        log = open(HERE / "logs" / f"engines_{full[:12]}.log", "a")
        todo, running = list(gen), []
        while todo or running:
            running = [(x, pr) for x, pr in running if pr.poll() is None]
            while todo and len(running) < j:
                x = todo.pop(0)
                running.append((x, subprocess.Popen([sys.executable, *x[2]], stdout=log, stderr=subprocess.STDOUT)))
            time.sleep(3)
        for e, path, _ in gen:
            st, det, cr = verify(path, full)
            eng[e].update(state=st, detail=det or "原本没有缓存，本次已生成", cache_rev=cr,
                          source="本次生成" if st == "通过" else "生成失败")
    # EC: whole-version results exist only where ec10 wrote them; never copied
    ecp = EC_DIR / f"{full}.json"
    st, det, cr = verify(ecp, full)
    if st == "缺失":
        det = "该版本没有 EC 整版结果（EC 目前只能对 df2908090cda 自动生成整版结果）"
    eng["EC"] = {"path": str(ecp), "state": st, "detail": det, "cache_rev": cr, "source": "已有缓存" if st == "通过" else None,
                 "script": str(EC_SCRIPT), "script_sha256": sha(EC_SCRIPT)}
    for e, x in eng.items():
        x["sha256"] = sha(x["path"]) if Path(x["path"]).exists() else None
    okset = {e for e, x in eng.items() if x["state"] == "通过"}
    rows, _ = S3.rows_of(full)                                # reads the same files that were just verified
    rows = [dict(r) for r in rows if r["engine"] in okset]
    if "EC" in okset:
        rows += ec_rows(ecp)
    rows.sort(key=lambda r: (r["prio"], S4.CHECK_ORDER.index(r["check"]), S4.ENGINE_ORDER.index(r["engine"]), r["file"], r["line"]))
    for i, r in enumerate(rows, 1):
        r["no"] = i
        r["resource"], r["prop"], r["ok_if"] = outfmt.annotate(r)
    d = (out_root or HERE / "out") / full[:12]
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "table.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([c[1] for c in COLS])
        for r in rows:
            w.writerow([("一" if r[k] == 1 else "二") if k == "prio" else r[k] for k, _ in COLS])
    status = {e: x["state"] for e, x in eng.items()}
    (d / "table.json").write_text(json.dumps({"rev": full, "info": info, "status": status, "rows": rows}, indent=1, ensure_ascii=False),
                                  encoding="utf-8")
    L = [f"# 候选表：{info}", "", "| 引擎 | 状态 | 来源 | 说明 | 行数 |", "|---|---|---|---|---|"]
    cnt = Counter(r["engine"] for r in rows)
    for e in S4.ENGINE_ORDER:
        x = eng[e]
        L.append(f"| {e} | {x['state']} | {x['source'] or '—'} | {x['detail'] or '—'} | {cnt.get(e, 0)} |")
    complete = len(okset) == len(eng)
    L += ["", f"**{'完整' if complete else '不完整'}**：{len(okset)}/{len(eng)} 个引擎核对通过，共 {len(rows)} 行。"]
    (d / "table.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    man = {"rev": full, "info": info, "complete": complete, "engines": eng, "rows": len(rows), "rows_by_engine": dict(cnt),
           "wall_seconds": round(time.time() - t0), "driver_sha256": sha(__file__)}
    (d / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    print("\n".join(L))
    return man, rows


# ------------------------------------------------------------------ criteria 三
def save(name, obj):
    (HERE / "checks").mkdir(exist_ok=True)
    (HERE / "checks" / f"{name}.json").write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(name, "PASS" if obj.get("pass") else "FAIL", {k: v for k, v in obj.items() if k not in ("diff", "manifest")})


def fresh(tag):
    import shutil
    p = HERE / "out" / tag
    shutil.rmtree(p, ignore_errors=True)


def t1():
    fresh(DF)
    man, rows = scan(DF)
    ref = json.load(open(CT / "outfmt_20261124" / "tables" / f"{DF}.json", encoding="utf-8"))["rows"]
    keys = [c for c, _ in COLS]
    diff = [i for i, (a, b) in enumerate(zip(rows, ref)) if any(a[k] != b[k] for k in keys)]
    ok = len(rows) == len(ref) == 978 and not diff and man["complete"] and all(x["source"] == "已有缓存" for x in man["engines"].values())
    save("t1", {"pass": ok, "rows": len(rows), "ref_rows": len(ref), "field_diffs": len(diff), "diff": diff[:20],
                "complete": man["complete"], "manifest": man})


def t2(v="6617da8fb565"):
    full = M.full(v)
    before = (EC_DIR / f"{full}.json").exists()
    fresh(v)
    man, rows = scan(v)
    after = (EC_DIR / f"{full}.json").exists()
    old8 = [e for e in S4.ENGINE_ORDER if e != "EC"]
    ok = (all(man["engines"][e]["state"] == "通过" and man["engines"][e]["source"] == "已有缓存" for e in old8)
          and man["engines"]["EC"]["state"] == "缺失" and not any(r["engine"] == "EC" for r in rows) and not before and not after)
    save("t2", {"pass": ok, "rev": full, "rows": len(rows), "ec": man["engines"]["EC"], "ec_file_before": before,
                "ec_file_after": after, "manifest": man})


def t3(v="65e4fd942f72"):
    fresh(v)
    t0 = time.time()
    man, rows = scan(v)
    old8 = [e for e in S4.ENGINE_ORDER if e != "EC"]
    states = {e: (man["engines"][e]["state"], man["engines"][e]["source"]) for e in old8}
    explicit = all(s in ("通过", "错误", "拒绝") for s, _ in states.values())
    ok = explicit and man["engines"]["EC"]["state"] == "缺失" and not (EC_DIR / f"{M.full(v)}.json").exists()
    save("t3", {"pass": ok, "rev": M.full(v), "rows": len(rows), "states": states, "cold_seconds": round(time.time() - t0),
                "all_generated_ok": all(s == "通过" and src == "本次生成" for s, src in states.values()), "manifest": man})


def t4(v="6617da8fb565"):
    import shutil
    full = M.full(v)
    fake = EC_DIR / f"{full}.json"
    assert not fake.exists(), "a real EC file exists for this version; refusing to overwrite"
    shutil.copy(EC_DIR / "df" / "df.json", fake)               # exactly what scan11/scan12 table does
    try:
        fresh(v)
        man, rows = scan(v)
    finally:
        fake.unlink()
    gone = not fake.exists()
    ec = man["engines"]["EC"]
    ok = ec["state"] == "拒绝" and not any(r["engine"] == "EC" for r in rows) and gone
    save("t4", {"pass": ok, "ec": ec, "fake_removed": gone, "rows": len(rows), "manifest": man})


def t5(v="6617da8fb565"):
    full = M.full(v)
    ref, _ = S3.rows_of(full)
    got = json.load(open(HERE / "out" / full[:12] / "table.json", encoding="utf-8"))["rows"]
    k = lambda r: (r["engine"], r["file"], r["line"], r["func"], r["arch"], r["sig"], r["prio"])  # noqa: E731
    a, b = Counter(map(k, ref)), Counter(map(k, (r for r in got if r["engine"] != "EC")))
    ok = a == b
    save("t5", {"pass": ok, "scan3_rows": sum(a.values()), "driver_rows": sum(b.values()), "only_scan3": len(a - b),
                "only_driver": len(b - a)})


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    (HERE / "logs").mkdir(exist_ok=True)
    c = sys.argv[1]
    if c == "scan":
        scan(sys.argv[2], int(sys.argv[sys.argv.index("-j") + 1]) if "-j" in sys.argv else 8, "--no-generate" not in sys.argv)
    else:
        {"t1": t1, "t2": t2, "t3": t3, "t4": t4, "t5": t5}[c]()
