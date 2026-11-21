"""scan3 criteria 一-四: whole-version scan mode. Input one kernel version, run the 8 frozen engines (checks3 grouping) on it,
output one candidate table grouped by the three checks. WSL.

    python3 scan3.py freeze                 -> frozen_sha256.txt (once)
    python3 scan3.py scan <rev> [N]         -> run missing engine jobs for <rev> (N parallel, default 8), then table
    python3 scan3.py table <rev>            -> tables/<rev12>.{csv,json,md} from the caches only
    python3 scan3.py verify                 -> criteria 二: per-engine counts on df2908090cda vs each round's head.json
    python3 scan3.py evaljobs | runall [H] [L] | stop | status    -> criteria 三/四: jobs for F^ of every fix in heldout2
    python3 scan3.py evalscore              -> analysis: eval_analysis.json (rows); sealed: summary only
The engines' own entry points (the same ones commit-level mode uses) write the shared caches; nothing in other rounds changes.
"""
import csv
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
H2 = CT / "heldout2_20261119"
sys.path.insert(0, str(CT / "checks3_20261119"))
import checks3 as C3  # noqa: E402

M, E, TLB, CE, WK, XA = C3.M, C3.E, C3.TLB, C3.CE, C3.WK, C3.XA
M.HERE = HERE
HEAD = "df2908090cda"
STOP, PIDF, LOG = HERE / "STOP", HERE / "runner.pid", HERE / "runall.log"
SETS = {"analysis": H2 / "set_analysis.json", "sealed": H2 / "set_sealed.json"}
CHECK_ORDER = list(C3.GROUPS)
ENGINE_ORDER = C3.ENGINES
SCRIPT = {"base": "commitmode_20261117/engines.py", "TLB": "commitmode_tlb_20261117/cmtlb.py", "CTX": "ctxeff3_20261118/ctxeff3.py",
          "WK": "weakov2_20261118/weakov2.py", "XA": "xvatom2_20261119/xvatom2.py"}


# ---------------------------------------------------------------- frozen code
def frozen_files():
    out = []
    for d in sorted(CT.iterdir()):
        if d.is_dir() and d.name[-8:] in ("20261115", "20261116", "20261117", "20261118", "20261119") and d.name != HERE.name:
            out += sorted(d.glob("*.py"))
    return out


def freeze():
    f = HERE / "frozen_sha256.txt"
    assert not f.exists(), "already frozen"
    f.write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(CT)}\n" for p in frozen_files()))
    print("frozen", len(frozen_files()), "files")


def check_frozen():
    want = dict(reversed(ln.split("  ", 1)) for ln in (HERE / "frozen_sha256.txt").read_text().splitlines() if ln)
    bad = [p for p, h in want.items() if not (CT / p).exists() or hashlib.sha256((CT / p).read_bytes()).hexdigest() != h]
    if bad:
        raise SystemExit(f"frozen code changed: {bad[:10]}")


# ---------------------------------------------------------------- jobs of one version
def rev_jobs(rev):
    rev = M.full(rev)
    out = [(e, rev, E.cache_path(e, rev, ()), [str(CT / SCRIPT["base"]), e, rev]) for e in ("P1", "XV", "ORD", "WT")]
    out.append(("TLB", rev, TLB.CACHE / f"{rev}.json", [str(CT / SCRIPT["TLB"]), "engine", rev]))
    out.append(("CTX", rev, CE.CACHE / f"{rev}.json", [str(CT / SCRIPT["CTX"]), "engine", rev]))
    out.append(("WK", rev, WK.CACHE / f"{rev}.json", [str(CT / SCRIPT["WK"]), "engine", rev]))
    out.append(("XA", rev, XA.CACHE / f"{rev}.json", [str(CT / SCRIPT["XA"]), "engine", rev]))
    return out


def cache_state(path):
    if not path.exists():
        return "todo"
    try:
        return "ok" if json.loads(path.read_text()).get("ok") else "error"
    except Exception:
        return "broken"


# ---------------------------------------------------------------- candidate table (criteria 一)
def rows_of(rev):
    """all candidates of the 8 engines on rev, as table rows; engine status per engine"""
    rows, status = [], {}
    for e, r, path, _ in rev_jobs(rev):
        st = cache_state(path)
        status[e] = st
        if st != "ok":
            continue
        d = json.loads(path.read_text())
        # WK keeps its "alt" candidates in a separate list (weakov2 sigs(include_alt)); criteria 一 lists them with priority 2
        for x in d["cands"] + (d.get("cands_alt", []) if e == "WK" else []):
            if e == "CTX":
                site = x.get("site", "")
                loc = site.split(" ")[0]
                f, _, ln = loc.partition(":")
                row = {"file": f, "line": int(ln) if ln.isdigit() else 0, "func": x["hook"], "arch": x["arch"],
                       "sig": f"{x['hook']}|{x['arch']}|{x['effect']}|调用点 {site}", "prio": 1 if x.get("minority") else 2}
            else:
                sig = x["sig"]
                parts = sig.split("|")
                arch = parts[2] if e == "WK" and len(parts) > 2 else (parts[3] if e == "XA" and len(parts) > 3 else "")
                prio = 2 if (e == "WT" and sig.startswith("A|")) or (e == "WK" and x.get("alt")) else 1
                row = {"file": x["file"], "line": x.get("line", 0), "func": x["func"], "arch": arch, "sig": sig, "prio": prio}
            row.update(engine=e, check=C3.CHECK_OF[e])
            rows.append(row)
    # criteria amendment 2: priority first, then check class, engine, file, line
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
    (d / f"{tag}.json").write_text(json.dumps({"rev": rev, "info": info, "status": status, "rows": rows}, indent=1, ensure_ascii=False))
    L = [f"# 候选表汇总：{info}", "", f"引擎状态：{status}", "", "| 检查类 | 引擎 | 优先级一 | 优先级二 | 合计 |", "|---|---|---|---|---|"]
    for g in CHECK_ORDER:
        for e in C3.GROUPS[g]:
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
    check_frozen()
    todo = [j for j in rev_jobs(rev) if cache_state(j[2]) != "ok" and cache_state(j[2]) != "error"]
    for j in todo:
        if cache_state(j[2]) == "broken":
            j[2].unlink()
    running = []
    out = open(HERE / "engines_output.log", "a")
    while todo or running:
        running = [(j, pr) for j, pr in running if pr.poll() is None]
        while todo and len(running) < n:
            j = todo.pop(0)
            running.append((j, subprocess.Popen([sys.executable, *j[3]], stdout=out, stderr=subprocess.STDOUT)))
        time.sleep(3)
    return table(rev)


def verify():
    rows, status = rows_of(HEAD)
    got = {e: sum(1 for r in rows if r["engine"] == e) for e in ENGINE_ORDER}
    want = {"P1": 53, "XV": 56, "ORD": 59, "WT": 746, "TLB": 9, "CTX": 9, "WK": 5, "XA": 1}
    ctx_min = sum(1 for r in rows if r["engine"] == "CTX" and r["prio"] == 1)
    print("status", status)
    for e in ENGINE_ORDER:
        print(f"  {e:4s} got {got[e]:4d} want {want[e]:4d} {'OK' if got[e] == want[e] else 'MISMATCH'}")
    print(f"  CTX minority got {ctx_min} want 6 {'OK' if ctx_min == 6 else 'MISMATCH'}")


# ---------------------------------------------------------------- evaluation jobs (criteria 三) + pausable runner (criteria 四)
def eval_versions():
    out = []
    for p in SETS.values():
        for it in json.loads(p.read_text(encoding="utf-8"))["positives"]:
            for f in it["fixes"]:
                v = M.full(f + "^")
                if v and v not in out:
                    out.append(v)
    return out


def jobs():
    return [j for v in eval_versions() for j in rev_jobs(v)]


def alive(pid):
    try:
        return "scan3.py" in Path(f"/proc/{pid}/cmdline").read_text()
    except Exception:
        return False


def runner_pid():
    if PIDF.exists():
        pid = int(PIDF.read_text())
        if alive(pid):
            return pid
    return None


def log(msg):
    with open(LOG, "a") as f:
        print(time.strftime("%m-%d %H:%M:%S"), msg, file=f, flush=True)


def kill_group(pr):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pr.pid, sig)
        except ProcessLookupError:
            return
        for _ in range(50):
            if pr.poll() is not None:
                break
            time.sleep(0.1)


def runall(maxheavy=4, maxlight=4):
    if runner_pid():
        raise SystemExit(f"runner already running (pid {runner_pid()})")
    check_frozen()
    STOP.unlink(missing_ok=True)
    PIDF.write_text(str(os.getpid()))
    js = jobs()
    for j in js:
        if cache_state(j[2]) == "broken":
            log(f"removed broken cache {j[2]}")
            j[2].unlink()
    todo = [j for j in js if cache_state(j[2]) == "todo"]
    todo.sort(key=lambda j: j[0] not in M.HEAVY)
    log(f"start: {len(js)} jobs, {len(todo)} to run, heavy {maxheavy} + light {maxlight}")
    running, t0, last, finished = [], time.time(), 0, 0
    out = open(HERE / "engines_output.log", "a")
    while todo or running:
        if STOP.exists():
            for j, pr in running:
                kill_group(pr)
                if cache_state(j[2]) == "broken":
                    j[2].unlink()
                log(f"stopped {j[0]} {j[1][:12]} (will rerun)")
            log(f"paused after {round(time.time() - t0)}s: finished {finished}, left {len(todo) + len(running)}")
            STOP.unlink(missing_ok=True)
            PIDF.unlink(missing_ok=True)
            return
        still = []
        for j, pr in running:
            if pr.poll() is None:
                still.append((j, pr))
            else:
                finished += 1
                st = cache_state(j[2])
                if st != "ok":
                    log(f"{j[0]} {j[1][:12]} -> {st} (exit {pr.returncode})")
        running = still
        nh = sum(1 for j, _ in running if j[0] in M.HEAVY)
        nl = len(running) - nh
        for j in list(todo):
            heavy = j[0] in M.HEAVY
            if (heavy and nh < maxheavy) or (not heavy and nl < maxlight):
                pr = subprocess.Popen([sys.executable, *j[3]], stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
                running.append((j, pr))
                todo.remove(j)
                nh += heavy
                nl += not heavy
        if time.time() - last > 120:
            log(f"{round(time.time() - t0)}s finished={finished} running={len(running)} todo={len(todo)}")
            last = time.time()
        time.sleep(5)
    log(f"all done {round(time.time() - t0)}s, finished {finished}")
    PIDF.unlink(missing_ok=True)


def stop():
    pid = runner_pid()
    if not pid:
        print("runner not running")
    else:
        STOP.write_text("stop\n")
        for _ in range(240):
            if not alive(pid):
                break
            time.sleep(0.5)
        print("runner stopped" if not alive(pid) else "runner STILL ALIVE")
    pat = "|".join(s.split("/")[-1] for s in SCRIPT.values())
    ps = subprocess.run(["pgrep", "-af", pat], capture_output=True, text=True).stdout
    left = [ln for ln in ps.splitlines() if "pgrep" not in ln]
    print("engine processes left:", len(left))
    for ln in left:
        print("  ", ln[:160])


def status():
    js = jobs()
    st = {"todo": 0, "ok": 0, "error": 0, "broken": 0}
    by = {}
    for j in js:
        s = cache_state(j[2])
        st[s] += 1
        by.setdefault(j[0], {"todo": 0, "ok": 0, "error": 0, "broken": 0})[s] += 1
    print(f"{len(eval_versions())} versions, jobs {len(js)}: {st}; runner {'running pid ' + str(runner_pid()) if runner_pid() else 'not running'}")
    for e, v in by.items():
        print(f"  {e:4s} {v}")
    if LOG.exists():
        print("last log:", LOG.read_text().splitlines()[-1])


# ---------------------------------------------------------------- evaluation score (criteria 三)
def evalscore():
    check_frozen()
    import statistics
    out = {}
    for name, p in SETS.items():
        s = json.loads(p.read_text(encoding="utf-8"))
        per = []
        sizes, sizes1 = [], []
        for it in s["positives"]:
            names = {fn for _, fn in it.get("fix_funcs", [])}
            r = {"commit": it["commit"][:12], "used": bool(it.get("used")), "versions": [], "hit": False, "hit1": False,
                 "hit_engines": [], "hit_checks": [], "status_bad": []}
            for f in it["fixes"]:
                v = M.full(f + "^")
                rows, st = rows_of(v)
                sizes.append(len(rows))
                sizes1.append(sum(1 for x in rows if x["prio"] == 1))
                r["status_bad"] += [f"{e}:{x}" for e, x in st.items() if x != "ok"]
                hits = [x for x in rows if x["func"] in names]
                r["versions"].append(v[:12])
                if hits:
                    r["hit"] = True
                    r["hit1"] = r["hit1"] or any(x["prio"] == 1 for x in hits)
                    r["hit_engines"] = sorted(set(r["hit_engines"]) | {x["engine"] for x in hits})
                    r["hit_checks"] = sorted(set(r["hit_checks"]) | {x["check"] for x in hits})
                    if name == "analysis":
                        r.setdefault("hits", []).extend(f"{x['engine']} {x['file']}:{x['line']} {x['func']} {x['sig'][:80]}" for x in hits[:8])
            if name == "analysis":
                r["info"] = M.git("log", "-1", "--format=%h|%cs|%s", M.full(it["commit"])).strip()
            per.append(r)

        def summ(rs):
            return {"pos": len(rs), "hit": sum(r["hit"] for r in rs), "hit_prio1": sum(r["hit1"] for r in rs),
                    "by_check": {g: sum(g in r["hit_checks"] for r in rs) for g in CHECK_ORDER},
                    "by_engine": {e: sum(e in r["hit_engines"] for r in rs) for e in ENGINE_ORDER},
                    "engine_not_ok": sum(bool(r["status_bad"]) for r in rs)}
        res = {"all": summ(per), "clean": summ([r for r in per if not r["used"]]),
               "table_size": {"median": statistics.median(sizes), "max": max(sizes), "median_prio1": statistics.median(sizes1),
                              "max_prio1": max(sizes1), "versions": len(sizes)}}
        out[name] = res
        if name == "analysis":
            (HERE / "eval_analysis.json").write_text(json.dumps({"summary": res, "rows": per}, indent=1, ensure_ascii=False))
    (HERE / "eval_summary.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    for name, res in out.items():
        for part in ("clean", "all"):
            a = res[part]
            print(f"[{name}/{'去掉曾用' if part == 'clean' else '全部'}] pos {a['pos']} hit {a['hit']} (prio1 {a['hit_prio1']}) "
                  f"by check {a['by_check']} by engine {a['by_engine']} engine-not-ok {a['engine_not_ok']}")
        print(f"  table size {res['table_size']}")
    print("\n[analysis] rows:")
    for r in json.loads((HERE / "eval_analysis.json").read_text())["rows"]:
        print(f"  {'used ' if r['used'] else 'clean'} {'HIT ' if r['hit'] else '-   '} {r['info'][:70]} {r.get('hits', [])[:3]}")


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    cmd = sys.argv[1]
    if cmd == "freeze":
        freeze()
    elif cmd == "scan":
        scan(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 8)
    elif cmd == "table":
        table(sys.argv[2])
    elif cmd == "verify":
        verify()
    elif cmd == "evaljobs":
        status()
    elif cmd == "runall":
        runall(*(int(x) for x in sys.argv[2:4]))
    elif cmd == "stop":
        stop()
    elif cmd == "status":
        status()
    elif cmd == "evalscore":
        evalscore()
