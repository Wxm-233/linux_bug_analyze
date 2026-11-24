"""wtrange criteria 四 + amendment 1: frozen blind sample of 24, review packets without static results, reconciliation. WSL.

    python3 blind.py freeze                 -> frozen_sha256.txt (all .py in this dir)
    python3 blind.py sample                 -> blind_sample.json (seed 20261124) + review/packets.md, review/items.json
    python3 blind.py rng                    -> blind_rng.json (static results; open only after both reviews are in)
    python3 blind.py reconcile              -> reconcile.json (needs review/adjudication.json)
"""
import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(HERE))
import bind2 as B2  # noqa: E402
B = B2.B


def freeze():
    f = HERE / "frozen_sha256.txt"
    assert not f.exists(), "already frozen"
    f.write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in sorted(HERE.glob("*.py"))))
    print(f.read_text())


def check_frozen():
    for ln in (HERE / "frozen_sha256.txt").read_text().splitlines():
        h, name = ln.split("  ", 1)
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == h, f"frozen file changed: {name}"


def excluded():
    ex = set()
    for p in (CT / "wtrange_20261121/day1_sample.json", HERE / "day1_sample.json"):
        ex |= {r["id"] for r in json.loads(p.read_text(encoding="utf-8"))}
    ex |= {i["id"] for i in json.loads((CT / "evcard_20261121/review/items.json").read_text(encoding="utf-8")) if i["id"].startswith("WT:")}
    if (HERE / "calib_set.json").exists():
        ex |= {r["id"] for r in json.loads((HERE / "calib_set.json").read_text(encoding="utf-8"))}
    return ex


def excerpt(path, line, before=25, after=12):
    src = B2.git("show", f"{B.REV}:{path}").split("\n")
    i, j = max(0, line - 1 - before), min(len(src), line - 1 + after)
    return "\n".join(f"{k + 1:6d}{'>' if k + 1 == line else ' '} {src[k]}" for k in range(i, j))


def sample():
    check_frozen()
    ex = excluded()
    pool = [r for r in B.unreviewed() if r["id"] not in ex]
    pick = random.Random(20261124).sample(pool, 24)
    (HERE / "blind_sample.json").write_text(json.dumps(pick, indent=1, ensure_ascii=False))
    (HERE / "review").mkdir(exist_ok=True)
    md = ["# WT 盲审材料（wtrange2，24 条）", "",
          "每条回答两件事：(1) 在 32 位构建上，这次转换的值是否**一定放得下**（是 / 否 / 说不清）；(2) 它是不是完整线索（完整线索 / 未决 / 排除 / 未知，排除写原因类别）。",
          f"源码版本 `{B.REV}`，行号前的 `>` 标出报告行。“32 位构建”一栏列出编入了该文件的窄目标构建（rv32 有 MMU、rv32 无 MMU、i386 defconfig、i386 allmodconfig）。", ""]
    items = []
    for n, r in enumerate(pick, 1):
        us = B2.units(r["file"], r["func"])
        items.append({"n": n, "id": r["id"]})
        md.append(f"## [{n}] `{r['file']}:{r['line']}` 函数 `{r['func']}`")
        md.append(f"- 原始特征：`{' ; '.join(dict.fromkeys(r['sigs']))[:300]}`")
        md.append(f"- 32 位构建：{', '.join(sorted({b for b, _ in us})) or '无'}")
        md.append("```c")
        md.append(excerpt(r["file"], r["line"]))
        md.append("```")
        md.append("")
    (HERE / "review/packets.md").write_text("\n".join(md), encoding="utf-8")
    (HERE / "review/items.json").write_text(json.dumps(items, indent=1, ensure_ascii=False))
    print("pool", len(pool), "sampled", len(pick))


def rng():
    check_frozen()
    import rng as R
    rows = json.loads((HERE / "blind_sample.json").read_text(encoding="utf-8"))
    bound = [B2.bind_one(r) for r in rows]
    (HERE / "blind_bind.json").write_text(json.dumps(bound, indent=1, ensure_ascii=False))
    R.run("blind_bind.json", "blind_rng.json")


def reconcile():
    items = {i["n"]: i["id"] for i in json.loads((HERE / "review/items.json").read_text(encoding="utf-8"))}
    adj = {x["n"]: x for x in json.loads((HERE / "review/adjudication.json").read_text(encoding="utf-8"))}
    st = {r["id"]: r["overall"] for r in json.loads((HERE / "blind_rng.json").read_text(encoding="utf-8"))}
    rows, proven_ok, proven_bad = [], 0, 0
    for n, i in items.items():
        a = adj[n]
        s = st.get(i, "未绑定")
        ok = bad = False
        if s == "放得下":
            if a["fits"] == "是" and a["verdict"] == "排除":
                ok = True
            else:
                bad = True
        proven_ok += ok
        proven_bad += bad
        rows.append({"n": n, "id": i, "static": s, "fits": a["fits"], "verdict": a["verdict"], "proof_correct": ok, "proof_wrong": bad})
    harmless = sum(1 for r in rows if r["verdict"] == "排除")
    demoted_harmless = sum(1 for r in rows if r["static"] == "放得下" and r["verdict"] == "排除")
    summ = {"n": len(rows), "static_fits": sum(r["static"] == "放得下" for r in rows), "proof_correct": proven_ok, "proof_wrong": proven_bad,
            "harmless_adjudicated": harmless, "demoted_share_of_harmless": round(demoted_harmless / harmless, 3) if harmless else None,
            "status_counts": {k: sum(r["static"] == k for r in rows) for k in ("放得下", "可能超界", "未知", "未绑定")},
            "gate1_keep_evidence": proven_ok >= 6 and proven_bad == 0,
            "gate2_reorder": proven_ok >= 6 and proven_bad == 0 and harmless and demoted_harmless / harmless >= 0.25}
    (HERE / "reconcile.json").write_text(json.dumps({"summary": summ, "rows": rows}, indent=1, ensure_ascii=False))
    print(json.dumps(summ, ensure_ascii=False))


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    {"freeze": freeze, "sample": sample, "rng": rng, "reconcile": reconcile}[sys.argv[1]]()
