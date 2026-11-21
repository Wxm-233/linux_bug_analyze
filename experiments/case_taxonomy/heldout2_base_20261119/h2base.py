"""heldout2_base criteria 一-五: baseline of the frozen 8-engine analyzer (checks3 grouping) on the new evaluation set. WSL.

    python3 h2base.py freeze            -> frozen_sha256.txt (once, before the first run)
    python3 h2base.py jobs              -> job counts per engine (no engine run)
    python3 h2base.py runall [H] [L]    -> run missing jobs, H heavy (P1/XV) + L other in parallel; runall.log; stops on STOP
    python3 h2base.py stop              -> pause: running jobs are killed, half-written caches removed; waits until all gone
    python3 h2base.py status            -> done / error / todo, runner alive?
    python3 h2base.py score             -> analysis: results_analysis.json (rows); sealed: summary only (criteria 三.5)
Engines are run with their own entry points, exactly as checks3.ensure() does; nothing in other rounds is modified.
"""
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
H2 = CT / "heldout2_20261119"
sys.path.insert(0, str(CT / "checks3_20261119"))
import checks3 as C3  # noqa: E402

M, E, TLB, CE, WK, XA = C3.M, C3.E, C3.TLB, C3.CE, C3.WK, C3.XA
M.HERE = HERE                       # check() writes report/ here (analysis) or into a temp dir (sealed), never into checks3
C3.set_variant("heldout")           # criteria 二.2
STOP, PIDF, LOG = HERE / "STOP", HERE / "runner.pid", HERE / "runall.log"
SETS = {"analysis": H2 / "set_analysis.json", "sealed": H2 / "set_sealed.json"}
SCRIPTS = ("commitmode_20261117/engines.py", "commitmode_tlb_20261117/cmtlb.py", "ctxeff3_20261118/ctxeff3.py",
           "weakov2_20261118/weakov2.py", "xvatom2_20261119/xvatom2.py")


# ---------------------------------------------------------------- frozen code (criteria 一)
def frozen_files():
    out = []
    for d in sorted(CT.iterdir()):
        if d.is_dir() and d.name[-8:] in ("20261115", "20261116", "20261117", "20261118", "20261119") and d.name != HERE.name:
            out += sorted(d.glob("*.py"))
    return out


def sha_map():
    return {str(p.relative_to(CT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in frozen_files()}


def freeze():
    f = HERE / "frozen_sha256.txt"
    assert not f.exists(), "already frozen"
    f.write_text("".join(f"{h}  {p}\n" for p, h in sha_map().items()))
    print("frozen", len(sha_map()), "files")


def check_frozen():
    want = dict(reversed(ln.split("  ", 1)) for ln in (HERE / "frozen_sha256.txt").read_text().splitlines() if ln)
    # only the files listed at freeze time are compared; .py files of rounds created later are not frozen code
    # (fixed 11-19 16:50 before any resume: the first version also flagged new files, e.g. scan3_20261119/*.py)
    bad = [p for p, h in want.items() if not (CT / p).exists() or hashlib.sha256((CT / p).read_bytes()).hexdigest() != h]
    if bad:
        raise SystemExit(f"frozen code changed: {bad[:10]}")


# ---------------------------------------------------------------- jobs (criteria 二)
def commits():
    out = []
    for name, p in SETS.items():
        s = json.loads(p.read_text(encoding="utf-8"))
        for it in s["positives"] + s["negatives"]:
            c = M.full(it["commit"])
            if c not in out:
                out.append(c)
    return out


def jobs():
    """[(engine, rev, extra, cache_path, argv)] in the order checks3.ensure() would run them"""
    out, seen = [], set()

    def add(eng, rev, extra, path, argv):
        if (eng, rev, extra) not in seen:
            seen.add((eng, rev, extra))
            out.append((eng, rev, extra, path, argv))

    for c in commits():
        for e, rev, x in M.jobs_of(c):
            add(e, rev, x, E.cache_path(e, rev, x), [str(CT / SCRIPTS[0]), e, rev, *x])
        revs = (M.full(c + "^"), c)
        for rev in revs:
            if TLB.touches(c):
                add("TLB", rev, (), TLB.CACHE / f"{rev}.json", [str(CT / SCRIPTS[1]), "engine", rev])
            if CE.TL.touches(c):
                add("CTX", rev, (), CE.CACHE / f"{rev}.json", [str(CT / SCRIPTS[2]), "engine", rev])
            if WK.touches(c):
                add("WK", rev, (), WK.CACHE / f"{rev}.json", [str(CT / SCRIPTS[3]), "engine", rev])
            if XA.touches(c):
                add("XA", rev, (), XA.CACHE / f"{rev}.json", [str(CT / SCRIPTS[4]), "engine", rev])
    return out


def cache_state(path):
    if not path.exists():
        return "todo"
    try:
        return "ok" if json.loads(path.read_text()).get("ok") else "error"
    except Exception:
        return "broken"


def cmd_jobs():
    js = jobs()
    by = {}
    for e, _, _, p, _ in js:
        by.setdefault(e, {"todo": 0, "ok": 0, "error": 0, "broken": 0})[cache_state(p)] += 1
    print(len(commits()), "commits,", len(js), "jobs")
    for e, v in by.items():
        print(f"  {e:4s} {v}")
    return js


# ---------------------------------------------------------------- runner with pause (criteria 五)
def alive(pid):
    try:
        return "h2base.py" in Path(f"/proc/{pid}/cmdline").read_text()
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
    for e, rev, x, p, _ in js:
        if cache_state(p) == "broken":
            log(f"removed broken cache {p}")
            p.unlink()
    todo = [j for j in js if cache_state(j[3]) == "todo"]
    todo.sort(key=lambda j: j[0] not in M.HEAVY)          # heavy jobs first, as in the earlier runall()
    log(f"start: {len(js)} jobs, {len(todo)} to run, heavy {maxheavy} + light {maxlight}")
    running, t0, last, finished = [], time.time(), 0, 0
    out = open(HERE / "engines_output.log", "a")
    while todo or running:
        if STOP.exists():
            for j, pr in running:
                kill_group(pr)
                if cache_state(j[3]) == "broken":
                    j[3].unlink()
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
                st = cache_state(j[3])
                if st != "ok":
                    log(f"{j[0]} {j[1][:12]} -> {st} (exit {pr.returncode})")
        running = still
        nh = sum(1 for j, _ in running if j[0] in M.HEAVY)
        nl = len(running) - nh
        for j in list(todo):
            heavy = j[0] in M.HEAVY
            if (heavy and nh < maxheavy) or (not heavy and nl < maxlight):
                pr = subprocess.Popen([sys.executable, *j[4]], stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
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
    ps = subprocess.run(["pgrep", "-af", "|".join(s.split("/")[-1] for s in SCRIPTS)], capture_output=True, text=True).stdout
    left = [ln for ln in ps.splitlines() if "pgrep" not in ln]
    print("engine processes left:", len(left))
    for ln in left:
        print("  ", ln[:160])


def status():
    js = jobs()
    st = {"todo": 0, "ok": 0, "error": 0, "broken": 0}
    for j in js:
        st[cache_state(j[3])] += 1
    print(f"jobs {len(js)}: {st}; runner {'running pid ' + str(runner_pid()) if runner_pid() else 'not running'}")
    if LOG.exists():
        print("last log:", LOG.read_text().splitlines()[-1])


# ---------------------------------------------------------------- score (criteria 三)
def score():
    check_frozen()
    out = {}
    for name, p in SETS.items():
        s = json.loads(p.read_text(encoding="utf-8"))
        tmp = None
        if name == "sealed":
            tmp = tempfile.mkdtemp(prefix="h2sealed_")
            M.HERE = Path(tmp)
        else:
            M.HERE = HERE
        rows = []
        for kind, items in (("pos", s["positives"]), ("neg", s["negatives"])):
            for it in items:
                names = {fn for _, fn in it.get("fix_funcs", [])}
                r = C3.grouped(it["commit"], kind, names)
                r["used"] = bool(it.get("used")) if kind == "pos" else False
                r["no_scan"] = kind == "pos" and not it.get("files")
                rows.append(r)
        clean = [r for r in rows if not r["used"]]
        summ = {"all": C3.summarize(rows), "clean": C3.summarize(clean),
                "no_scan_pos": {"all": sum(r["no_scan"] for r in rows), "clean": sum(r["no_scan"] for r in clean)},
                "status": {e: {st: sum(r["_eng"][e]["status"] == st for r in rows) for st in ("ok", "skip", "error", "未评估")}
                           for e in C3.ENGINES}}
        out[name] = summ
        if tmp:
            subprocess.run(["rm", "-rf", tmp])
        else:
            keep = [{k: v for k, v in r.items() if k != "_eng"} | {"info": M.git("log", "-1", "--format=%h|%cs|%s", M.full(r["commit"])).strip()}
                    for r in rows]
            (HERE / "results_analysis.json").write_text(json.dumps({"summary": summ, "rows": keep}, indent=1, ensure_ascii=False))
    M.HERE = HERE
    (HERE / "summary.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    for name, summ in out.items():
        for part in ("clean", "all"):
            s = summ[part]
            a = s["all"]
            print(f"\n[{name}/{'去掉曾用' if part == 'clean' else '全部'}] pos {a['pos']} flagged {a['pos_flag']} aligned {a['pos_aligned']}"
                  f" | neg {a['neg']} flagged {a['neg_flag']} | no-scan pos {summ['no_scan_pos'][part]}")
            for g in C3.GROUPS:
                x = s[g]
                print(f"  {g}: pos {x['pos_flag']}/{x['pos_aligned']} neg {x['neg_flag']}  " +
                      "  ".join(f"{e}={y['pos_flag']}/{y['pos_aligned']}/{y['neg_flag']}" for e, y in x["engines"].items()))
        print("  status", summ["status"])
    a = out["analysis"]
    print("\n[analysis] positives (clean first):")
    rows = json.loads((HERE / "results_analysis.json").read_text())["rows"]
    for r in sorted(rows, key=lambda r: (r["kind"], r["used"])):
        if r["kind"] == "pos" or r["flag"]:
            hit = [f"{x['engine']}:{x['func']}" for g in r["checks"].values() for x in g["cands"]][:6]
            print(f"  {r['kind']} {'used' if r['used'] else 'clean'} {'ALIGN' if r['aligned'] else ('flag ' if r['flag'] else '-    ')} "
                  f"{r['info'][:70]} {hit}")


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    cmd = sys.argv[1]
    if cmd == "freeze":
        freeze()
    elif cmd == "jobs":
        cmd_jobs()
    elif cmd == "runall":
        runall(*(int(x) for x in sys.argv[2:4]))
    elif cmd == "stop":
        stop()
    elif cmd == "status":
        status()
    elif cmd == "score":
        score()
