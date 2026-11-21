"""incscan criteria 一～四. WSL.

    python3 incscan.py engines <new>   -> 8 engines on NEW (scan3 caches, frozen check) + EZ (ez_new.json)
    python3 incscan.py diff <new>      -> table_new.json, incr.jsonl, queues.csv, summary.json
    python3 incscan.py packets         -> review/packets.md, review/items.json, review/source_map.json
"""
import csv
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
for d in ("scan3_20261119", "effzero_20261120", "evcard_20261121"):
    sys.path.insert(0, str(CT / d))
import scan3 as S3  # noqa: E402
import effzero as EZ  # noqa: E402
import cards as CD  # noqa: E402

OLD = "df2908090cda"
CARDS_SHA = "6ce1a1626064f5ecfcbc32c5f90a6cdc9174d4177783f007941d7988dd45656d"  # evcard cards.py, recorded 11-20 before any run
WORK = "/root/work/incscan"
SRCN = WORK + "/src/"
ARCHS = ("riscv", "arm64", "x86_64")
BUILDN = {a: f"{WORK}/build/{a}_defconfig" for a in ARCHS}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check_frozen():
    S3.check_frozen()
    for ln in (CT / "effzero_20261120/frozen_sha256.txt").read_text().splitlines():
        h, name = ln.split(" *", 1)
        assert sha(CT / "effzero_20261120" / name) == h, f"effzero frozen file changed: {name}"
    assert sha(CT / "evcard_20261121/cards.py") == CARDS_SHA, "cards.py changed"


def full(rev):
    return subprocess.run(["git", "-C", CD.REPO, "rev-parse", rev], capture_output=True, text=True).stdout.strip()


def compiled_sets(c_only):
    out, status = {}, {}
    for a, d in BUILDN.items():
        st = (Path(d) / "status.txt").read_text().strip() if (Path(d) / "status.txt").exists() else "missing"
        status[a] = st
        if st != "success":
            out[a] = set()
            continue
        cc = json.load(open(d + "/compile_commands.json"))
        out[a] = {e["file"][len(SRCN):] for e in cc if e["file"].startswith(SRCN) and (e["file"].endswith(".c") or not c_only)}
    return out, status


# ---------------------------------------------------------------- engines
def engines(new, n=8, with_ez=True):
    check_frozen()
    new = full(new)
    todo = [j for j in S3.rev_jobs(new) if S3.cache_state(j[2]) not in ("ok", "error")]
    for j in todo:
        if S3.cache_state(j[2]) == "broken":
            j[2].unlink()
    out = open(HERE / "engines_output.log", "a")
    running = []
    t0 = time.time()
    while todo or running:
        running = [(j, pr) for j, pr in running if pr.poll() is None]
        while todo and len(running) < n:
            j = todo.pop(0)
            running.append((j, subprocess.Popen([sys.executable, *j[3]], stdout=out, stderr=subprocess.STDOUT)))
        time.sleep(3)
    print("8 engines", {e: S3.cache_state(p) for e, _, p, _ in S3.rev_jobs(new)}, round(time.time() - t0), "s")
    if not with_ez:
        return
    cs, st = compiled_sets(True)
    print("builds", st)
    res = EZ.run(new, str(HERE / "ez_new.json"), compiled=cs)
    print("EZ cands", len(res["cands"]), "secs", res["stats"].get("secs_total"))


# ---------------------------------------------------------------- diff + cards + queues
def nsig(s):
    return re.sub(r":\d+", "", s)


def raw_rows(tab_rows, ez_cands):
    raw = [{"engine": r["engine"], "file": r["file"], "line": r["line"], "func": r["func"], "arch": r["arch"], "sig": r["sig"],
            "prio": r["prio"], "old": i} for i, r in enumerate(tab_rows)]
    base = len(raw)
    for c in ez_cands:
        raw.append({"engine": "EZ", "file": c["file"], "line": c["line"], "func": c["func"], "arch": "",
                    "sig": f"{c['form']}|{c['group']}", "key_sig": f"{c['form']}|{c['group']}|{c.get('origin', '')}",
                    "prio": 1, "old": base + c["rank"], "ez_arch": c["arch"]})
    for r in raw:
        r["key"] = (r["engine"], r["file"], r["func"], r.get("key_sig") or nsig(r["sig"]))
    return raw


def reviewed_index():  # evcard rule + amendment 1; only this directory excluded (criteria 二)
    texts = []
    for root, dirs, fs in os.walk(CT):
        if HERE.name in root or "sealed" in root or "__pycache__" in root:
            continue
        for fn in fs:
            hit = CD.REVIEW_PAT.search(fn) or fn == "README.md" or "packet" in fn.lower() or "packets" in root
            if hit and fn.endswith((".json", ".md", ".csv", ".txt")) and "sealed" not in fn:
                try:
                    texts.append(open(os.path.join(root, fn), encoding="utf-8", errors="ignore").read())
                except Exception:
                    pass
    return texts


_CACHES = {}


def at_rev(rev):
    CD.REV = rev
    CD._SRC = _CACHES.setdefault(rev, {})


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def diff(new):
    check_frozen()
    new = full(new)
    rows_new, status = S3.rows_of(new)
    assert all(v == "ok" for v in status.values()), status
    ez_new = json.loads((HERE / "ez_new.json").read_text())["cands"]
    tab_old = json.loads((CT / "scan3_20261119/tables/df2908090cda.json").read_text(encoding="utf-8"))["rows"]
    ez_old = json.loads((CT / "effzero_20261120/cur/effzero.json").read_text())["cands"]
    (HERE / "table_new.json").write_text(json.dumps({"rev": new, "status": status, "rows": rows_new, "ez": ez_new}, indent=1,
                                                     ensure_ascii=False))
    raw_new, raw_old = raw_rows(rows_new, ez_new), raw_rows(tab_old, ez_old)
    kold, knew = {r["key"] for r in raw_old}, {r["key"] for r in raw_new}
    added = [r for r in raw_new if r["key"] not in kold]
    vanished = [r for r in raw_old if r["key"] not in knew]
    merged = {}
    for r in added:
        k = (r["file"], r["func"], r["engine"])
        m = merged.setdefault(k, {**{x: r[x] for x in ("engine", "file", "line", "func", "arch", "prio", "old")}, "sigs": [],
                                  "ez_arch": r.get("ez_arch")})
        m["sigs"].append(r["sig"])
        m["old"] = min(m["old"], r["old"])
    texts = reviewed_index()
    cs, bstat = compiled_sets(False)
    inv, pool = [], []
    for m in merged.values():
        fnre = re.compile(r"\b" + re.escape(m["func"]) + r"\b")
        m["reviewed"] = any(m["file"] in t and fnre.search(t) for t in texts)
        at_rev(new)
        m["card"] = CD.card(m, cs)
        for a in ARCHS:  # criteria 一: failed build -> compiled unknown
            if bstat[a] != "success":
                m["card"]["compiled"] += f"（{a} 构建失败，编入未知）"
        m["tier"] = CD.tier(m["card"])
        m["check"] = CD.CHECK_OF[m["engine"]]
        m["id"] = f"{m['engine']}:{m['file']}:{m['func']}"
        fb_new = CD.func_body(m["file"], m["func"], m["line"])
        at_rev(OLD)
        fb_old = CD.func_body(m["file"], m["func"], 0)
        m["diag"] = {"func_in_old": fb_old is not None,
                     "body_changed": None if fb_old is None or fb_new is None else norm(fb_old[1]) != norm(fb_new[1])}
        inv.append(m)
        if not m["reviewed"]:
            pool.append(m)
    at_rev(new)
    old_q = sorted(pool, key=lambda m: m["old"])
    card_q = sorted(pool, key=lambda m: (m["tier"], m["old"]))
    with open(HERE / "incr.jsonl", "w", encoding="utf-8") as f:
        for m in sorted(inv, key=lambda m: m["old"]):
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    with open(HERE / "queues.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "old_queue", "card_queue"])
        for i in range(len(pool)):
            w.writerow([i + 1, old_q[i]["id"], card_q[i]["id"]])
    info = subprocess.run(["git", "-C", CD.REPO, "log", "-1", "--format=%h|%cs|%s", new], capture_output=True, text=True).stdout.strip()
    summ = {"new": new, "new_info": info, "builds": bstat,
            "rows_new": len(rows_new), "ez_new": len(ez_new), "rows_old": len(tab_old), "ez_old": len(ez_old),
            "added_rows": len(added), "added_rows_by_engine": dict(Counter(r["engine"] for r in added)),
            "vanished_rows": len(vanished), "vanished_rows_by_engine": dict(Counter(r["engine"] for r in vanished)),
            "incr_merged": len(inv), "reviewed": sum(m["reviewed"] for m in inv), "pool": len(pool),
            "pool_by_engine": dict(Counter(m["engine"] for m in pool)), "pool_by_tier": dict(Counter(m["tier"] for m in pool)),
            "pool_func_new": sum(not m["diag"]["func_in_old"] for m in pool),
            "pool_body_changed": sum(bool(m["diag"]["body_changed"]) for m in pool),
            "pool_body_same": sum(m["diag"]["body_changed"] is False for m in pool),
            "top12_old": [m["id"] for m in old_q[:12]], "top12_card": [m["id"] for m in card_q[:12]],
            "overlap_top12": len({m["id"] for m in old_q[:12]} & {m["id"] for m in card_q[:12]})}
    (HERE / "summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in summ.items() if not k.startswith("top12")}, indent=1, ensure_ascii=False))


# ---------------------------------------------------------------- review packets (criteria 四)
def excerpt(rev, path, line, before=25, after=20):
    src = subprocess.run(["git", "-C", CD.REPO, "show", f"{rev}:{path}"], capture_output=True, text=True, errors="replace").stdout.split("\n")
    i, j = max(0, line - 1 - before), min(len(src), line - 1 + after)
    return "\n".join(f"{k + 1:6d}{'>' if k + 1 == line else ' '} {src[k]}" for k in range(i, j))


def packets():
    s = json.loads((HERE / "summary.json").read_text(encoding="utf-8"))
    cards = {}
    for ln in open(HERE / "incr.jsonl", encoding="utf-8"):
        m = json.loads(ln)
        cards[m["id"]] = m
    pool = [i for i, m in cards.items() if not m["reviewed"]]
    src = {}
    if len(pool) <= 24:
        for i in pool:
            src.setdefault(i, []).append("all")
    else:
        for q in ("top12_old", "top12_card"):
            for i in s[q]:
                src.setdefault(i, []).append(q[6:])
    ids = sorted(src)
    random.Random(20261120).shuffle(ids)
    (HERE / "review").mkdir(exist_ok=True)
    md = [f"# incscan 审查材料（新版本 {s['new_info']}；两榜前 12 条合并，打乱、隐去来源和名次）", "",
          "判断：完整线索（公共代码的依赖、架构条件改变保证的依据、同一对象到消费者的证据，且已排除最直接的合法解释）/ 未决 / 排除 / 未知。",
          f"排除请写原因类别。行号前的 `>` 标出报告行。源码是新版本 `{s['new'][:12]}`。", ""]
    items = []
    for n, i in enumerate(ids, 1):
        m = cards[i]
        cd = m["card"]
        items.append({"n": n, "id": i})
        md.append(f"## [{n}] {m['engine']}（{m['check']}）`{m['file']}:{m['line']}` 函数 `{m['func']}`")
        md.append(f"- 原始特征：`{' ; '.join(m['sigs'])[:300]}`")
        md.append(f"- 卡片：消费位置 **{cd['consumer'][0]}**（{cd['consumer'][1]}）；编入 {cd['compiled']}；架构依据 **{cd['arch_basis'][0]}**（{cd['arch_basis'][1]}）；"
                  f"反证 **{cd['counter'][0]}**（{cd['counter'][1]}）")
        md.append(f"- 函数在旧版本 {OLD} 里：{'有' if m['diag']['func_in_old'] else '没有（新函数）'}"
                  + ("" if m["diag"]["body_changed"] is None else f"；函数体{'改过' if m['diag']['body_changed'] else '没改'}"))
        md.append("```c")
        md.append(excerpt(s["new"], m["file"], m["line"] or 1))
        md.append("```")
        md.append("")
    (HERE / "review/packets.md").write_text("\n".join(md), encoding="utf-8")
    (HERE / "review/items.json").write_text(json.dumps(items, indent=1, ensure_ascii=False))
    (HERE / "review/source_map.json").write_text(json.dumps({it["n"]: src[it["id"]] for it in items}, indent=1))
    print("items", len(items))


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    cmd = sys.argv[1]
    if cmd == "engines":
        engines(sys.argv[2])
    elif cmd == "engines8":  # 8 engines only (no build needed), n parallel
        engines(sys.argv[2], int(sys.argv[3]), with_ez=False)
    elif cmd == "diff":
        diff(sys.argv[2])
    elif cmd == "packets":
        packets()
