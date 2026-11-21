"""effreplay criteria 二/三: run frozen E-ZERO, patchmatch and the 8-engine baseline on F^ and F of every sealed late
root cause; write everything to sealed_replay/; print counts only (never ids, files, functions). WSL.

    python3 replay.py run      -> sealed_replay/{runs,packets}/..., sealed_replay/mech.json, mech_summary.json (counts)
"""
import gzip
import hashlib
import json
import pickle
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
EZ = CT / "effzero_20261120"
SEALED_IN = CT / "effsupply_20261120/sealed_late"
OUT = HERE / "sealed_replay"
REPO = "/root/repos/linux"
sys.path.insert(0, str(EZ))
sys.path.insert(0, str(CT / "scan3_20261119"))


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def check_ez_frozen():
    for ln in (EZ / "frozen_sha256.txt").read_text().splitlines():
        h, name = ln.split(" ", 1)
        name = name.lstrip(" *")
        if name in ("effzero.py", "patchmatch.py") and hashlib.sha256((EZ / name).read_bytes()).hexdigest() != h:
            raise SystemExit("effzero frozen code changed")


def changed_funcs(fix, facts):
    out, cur = set(), None
    for ln in git("show", "--format=", "-U0", fix).split("\n"):
        if ln.startswith("--- a/"):
            cur = ln[6:]
        elif ln.startswith("--- "):
            cur = None
        elif ln.startswith("@@") and cur:
            m = re.match(r"@@ -(\d+)(?:,(\d+))?", ln)
            a = int(m.group(1))
            b = a + max(int(m.group(2) or 1), 1) - 1
            for d in facts["files"].get(cur, {}).get("fns", []):
                if d["l"] <= b and d["le"] >= a:
                    out.add((cur, d["n"]))
    return out


def top_dedup(keys, n=20):
    out, seen = [], set()
    for k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
        if len(out) >= n:
            break
    return out


def main():
    t0 = time.time()
    check_ez_frozen()
    import scan3 as S  # noqa: E402
    S.check_frozen()
    import patchmatch as PM  # noqa: E402
    jud = json.loads((SEALED_IN / "scorer_judgement.json").read_text(encoding="utf-8"))
    fixes = [git("rev-parse", j["commit"]).strip() for j in jud if j["verdict"] == "是"]
    print("late yes commits:", len(fixes), flush=True)
    (OUT / "runs").mkdir(parents=True, exist_ok=True)
    (OUT / "packets").mkdir(exist_ok=True)
    revs = []
    for i, f in enumerate(fixes):
        revs += [(i, "pre", git("rev-parse", f + "^").strip()), (i, "post", f)]
    log = open(OUT / "runs/engines.log", "a")
    # E-ZERO (3 parallel) and baseline engines (6 parallel), all detached from the console
    ez_jobs = [(i, ph, r, [sys.executable, str(EZ / "effzero.py"), "run", r, str(OUT / f"runs/ez_{i}_{ph}.json")]) for i, ph, r in revs]
    base_jobs = []
    for i, ph, r in revs:
        for e, rr, path, argv in S.rev_jobs(r):
            if S.cache_state(path) in ("todo", "broken"):
                if S.cache_state(path) == "broken":
                    path.unlink()
                base_jobs.append([sys.executable, *argv])
    print("jobs: effzero", len(ez_jobs), "baseline engines to run", len(base_jobs), flush=True)
    todo = [("ez", j[3]) for j in ez_jobs if not (OUT / f"runs/ez_{j[0]}_{j[1]}.json").exists()] + [("b", a) for a in base_jobs]
    running = []
    done = 0
    while todo or running:
        still = []
        for kind, pr in running:
            if pr.poll() is None:
                still.append((kind, pr))
            else:
                done += 1
                print(f"  finished {done} (rc {pr.returncode}) {round(time.time() - t0)}s", flush=True)
        running = still
        nez = sum(1 for k, _ in running if k == "ez")
        nb = sum(1 for k, _ in running if k == "b")
        for x in list(todo):
            kind, argv = x
            if (kind == "ez" and nez < 3) or (kind == "b" and nb < 4):
                todo.remove(x)
                running.append((kind, subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT)))
                nez += kind == "ez"
                nb += kind == "b"
        time.sleep(5)
    # collect, score mechanically
    mech = []
    for i, f in enumerate(fixes):
        pre = git("rev-parse", f + "^").strip()
        facts = pickle.load(gzip.open(f"/root/work/effzero/facts_{pre[:12]}.pkl.gz"))
        ch = changed_funcs(f, facts)
        row = {"rc": i, "fix": f[:12], "changed": sorted(ch)}
        lists = {}
        for ph, r in (("pre", pre), ("post", f)):
            ez = json.loads((OUT / f"runs/ez_{i}_{ph}.json").read_text())
            pm = PM.main(r, str(OUT / f"runs/pm_{i}_{ph}.json"))
            rows, status = S.rows_of(r)
            (OUT / f"runs/base_{i}_{ph}.json").write_text(json.dumps({"status": status, "rows": rows}, ensure_ascii=False))
            lists[ph] = {"ez": ez["cands"], "pm": pm["cands"], "base": rows, "base_status": status}
        for m in ("ez", "pm", "base"):
            pre_c = lists["pre"][m]
            keys = [(c["file"], c["func"]) for c in pre_c]
            top = top_dedup(keys)
            hit_any = [k for k in dict.fromkeys(keys) if k in ch] + \
                ([(c["file"], c["origin"]) for c in pre_c if m == "ez" and c.get("origin") and (c["file"], c["origin"]) in ch])
            hit_top = [k for k in top if k in ch] + \
                ([(c["file"], c["origin"]) for c in pre_c if m == "ez" and c.get("origin") and (c["file"], c["func"]) in top
                  and (c["file"], c["origin"]) in ch])
            post_keys = {(c["file"], c["func"]) for c in lists["post"][m]} | \
                ({(c["file"], c.get("origin")) for c in lists["post"][m]} if m == "ez" else set())
            row[m] = {"n_pre": len(pre_c), "n_post": len(lists["post"][m]), "hit_top20": bool(hit_top), "hit_any": bool(hit_any),
                      "cleared_after_fix": bool(hit_any) and not any(k in post_keys for k in hit_any)}
        row["base_status"] = lists["pre"]["base_status"]
        mech.append(row)
        # scorer packet: fix id + top-20 of each method on F^
        pk = {"rc": i, "fix": f[:12],
              "effzero_top20": [c for c in lists["pre"]["ez"] if (c["file"], c["func"]) in set(top_dedup([(x["file"], x["func"]) for x in lists["pre"]["ez"]]))][:40],
              "patchmatch_top20": [lists["pre"]["pm"][k] for k in range(min(20, len(lists["pre"]["pm"])))],
              "baseline_top20": []}
        seen = set()
        for r in lists["pre"]["base"]:
            k = (r["file"], r["func"])
            if k in seen:
                continue
            seen.add(k)
            pk["baseline_top20"].append(r)
            if len(pk["baseline_top20"]) >= 20:
                break
        (OUT / f"packets/rc_{i}.json").write_text(json.dumps(pk, indent=1, ensure_ascii=False))
    (OUT / "mech.json").write_text(json.dumps(mech, indent=1, ensure_ascii=False))
    summ = {"root_causes": len(mech), "secs": round(time.time() - t0),
            "baseline_engine_status_not_ok": sum(1 for r in mech for v in r["base_status"].values() if v != "ok")}
    for m in ("ez", "pm", "base"):
        summ[m] = {"hit_top20": sum(r[m]["hit_top20"] for r in mech), "hit_any": sum(r[m]["hit_any"] for r in mech),
                   "cleared_after_fix": sum(r[m]["cleared_after_fix"] for r in mech),
                   "median_cands_pre": sorted(r[m]["n_pre"] for r in mech)[len(mech) // 2] if mech else None}
    summ["ez_new_vs_base_top20"] = sum(1 for r in mech if r["ez"]["hit_top20"] and not r["base"]["hit_top20"])
    (HERE / "mech_summary.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    if sys.argv[1] == "run":
        main()
