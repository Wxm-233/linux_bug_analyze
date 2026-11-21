"""Diagnose dev misses (design side only): which operations did each fix put under the new capability, and what did inference A/B see in fix^.

    python3 diag.py   -> diag_run1.json + printed table
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import capcheck as K  # noqa: E402
import dev as D  # noqa: E402


def stats(files):
    n, g = Counter(), defaultdict(Counter)
    for f in files:
        for fn in f["funcs"]:
            for line, nm, keys, gs in fn["sites"]:
                for k in keys:
                    n[k] += 1
                    for c in gs:
                        g[k][c] += 1
    return n, g


def main():
    run1 = json.loads((HERE / "dev_run1.json").read_text(encoding="utf-8"))
    out = []
    for r in run1["roots"]:
        fix, tg = r["fix"], {tuple(x) for x in r["targets"]}
        new_f = [f for f in K._work((K.full(fix), sorted({p for p, _ in tg})))]
        newly = []
        for f in new_f:
            for fn in f["funcs"]:
                if (f["path"], fn["name"]) in tg:
                    for line, nm, keys, gs in fn["sites"]:
                        if gs:
                            newly.append((f["path"], fn["name"], line, keys, gs))
        par = K.facts(K.full(fix + "^"))
        n, g = stats(par)
        ent = [(f["path"], kind, name) for f in par for kind, name in f["regs"] if (f["path"], name) in tg]
        rows = []
        for p, fn, line, keys, gs in newly:
            for k in keys:
                for c in gs:
                    rows.append({"op": k, "cap": c, "n": n[k], "g_cap": g[k][c], "best": g[k].most_common(1)[0] if g[k] else None})
        out.append({"root": r["root"], "fix": fix, "family": r["family"], "guarded_ops_in_fix": rows[:8], "target_is_entry": ent})
        print(r["root"], r["family"], "entry" if ent else "", "|", "; ".join(f"{x['op']} cap={x['cap']} n={x['n']} g={x['g_cap']} best={x['best']}"
                                                                        for x in rows[:4]), flush=True)
    (HERE / "diag_run1.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    main()
