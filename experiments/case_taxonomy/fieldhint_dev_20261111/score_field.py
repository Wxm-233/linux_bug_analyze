"""(fieldhint_dev_20261111: copy of budget_dev_20261111/score_budget.py; groups + G3f, budget 2000, confirmations also
carried over from the budget round; field variants matched without their "of".) Scores (fieldhint criteria 四).

    python score_budget.py -> confirm.json (carried over + rule-confirmed), review_new.json (needs manual review),
                              stats.json
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
SAMPLES = ["A101", "A310", "A171", "A181", "B467"]
GROUPS = ["G0d", "G2d", "G3d", "G3c", "G3f"]
SEEDS = ["1", "2", "3"]
TIERS = [2000]
sys.path.insert(0, str(CT / "diverse_dev_20261110"))
import evaluate_d as E  # noqa: E402  (cond(): diagnosis conditions written 11-10)


def mod(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


SC = mod("tools_score", CT / "difftest_tools_20261111" / "score.py")
OTOK = re.compile(r"o:([zag]):52$")


def key(c):
    d = {k: v for k, v in c.items() if k not in ("id", "const_copy_of")}
    for f in ("rel", "fvar"):
        if f in d:
            d[f] = {k: v for k, v in d[f].items() if k != "of"}
    return json.dumps(d, sort_keys=True)


def effective(c, probes, kernel):
    """arguments as the kernel received them (relative cases are converted per kernel at output time)"""
    if "rel" not in c:
        return c
    m = int(probes[kernel]["values"]["mmap_top"], 16)
    args = list(c["args"])
    for j, d in c["rel"]["args"].items():
        args[int(j)] = "i:%x" % ((m + d) % 2**64)
    for j in c["rel"].get("obits", []):
        args[j] = "o:%s:%d" % (OTOK.match(args[j]).group(1), (m - 1).bit_length())
    return dict(c, args=args)


def main():
    probes = json.loads((CT / "rtprobe_dev_20261110" / "probes.json").read_text())
    oldc = SC.read_json(CT / "diverse_dev_20261110" / "confirm.json")
    mergec = SC.read_json(CT / "merge_dev_20261111" / "confirm.json")
    confirm, review, stats = {}, {}, {"tiers": {}, "cond": {}, "carried": {}, "rule": {}}
    for x in SAMPLES:
        # carry over: diverse ids -> content, merge ids -> content
        known = {}
        budc = SC.read_json(CT / "budget_dev_20261111" / "confirm.json")
        for src, conf in ((CT / "diverse_dev_20261110/gen" / f"cases_{x}.json", oldc),
                          (CT / "merge_dev_20261111/gen" / f"cases_{x}.json", mergec),
                          (CT / "budget_dev_20261111/run" / x / "cases.json", budc)):
            cs = {str(c["id"]): c for c in json.loads(src.read_text())["cases"]}
            for i, v in conf.get(x, {}).items():
                if i in cs:
                    known[key(cs[i])] = v
        cases = {str(c["id"]): c for c in json.loads((HERE / "run" / x / "cases.json").read_text())["cases"]}
        cmp_ = json.loads((HERE / "cmp" / x / "compare.json").read_text(encoding="utf8"))
        det = SC.detecting(cmp_, f"{x.lower()}_pre", f"{x.lower()}_fix")
        confirm[x], review[x] = {}, []
        nc = nr = 0
        for i in sorted(det, key=int):
            k = key(cases[i])
            if k in known:
                confirm[x][i] = known[k]
                nc += 1
            elif E.cond(x, effective(cases[i], probes, f"{x.lower()}_pre")):
                confirm[x][i] = {"ok": True, "why": "满足 diagnosis_conditions.md 中该样本的触发条件（规则确认）"}
                nr += 1
            else:
                review[x].append({"id": i, "sc": cases[i]["sc"], "args": cases[i]["args"], "rel": cases[i].get("rel"),
                                  "values": cmp_["values"].get(i)})
        stats["carried"][x], stats["rule"][x] = nc, nr
        lists = json.loads((HERE / "run" / x / "lists.json").read_text())
        stats["cond"][x] = {G: {str(n): [sum(1 for i in lists[G][s][:n]
                                          if E.cond(x, effective(cases[str(i)], probes, f"{x.lower()}_pre")))
                                          for s in SEEDS] for n in TIERS} for G in GROUPS}
    manual = HERE / "confirm_manual.json"
    if manual.exists():
        for x, d in json.loads(manual.read_text(encoding="utf8")).items():
            confirm[x].update(d)
            review[x] = [r for r in review[x] if r["id"] not in d]
    (HERE / "confirm.json").write_text(json.dumps(confirm, indent=1, ensure_ascii=False), encoding="utf8")
    (HERE / "review_new.json").write_text(json.dumps(review, indent=1, ensure_ascii=False), encoding="utf8")
    for n in TIERS:
        d = HERE / "tiers" / str(n)
        d.mkdir(parents=True, exist_ok=True)
        samples = {}
        for x in SAMPLES:
            lists = json.loads((HERE / "run" / x / "lists.json").read_text())
            (d / f"lists_{x}.json").write_text(json.dumps({G: {s: lists[G][s][:n] for s in SEEDS} for G in GROUPS}))
            samples[x] = {"compare": f"../../cmp/{x}/compare.json", "lists": f"lists_{x}.json",
                          "pre": f"{x.lower()}_pre", "fix": f"{x.lower()}_fix"}
        (d / "score_cfg.json").write_text(json.dumps({"groups": GROUPS, "seeds": SEEDS, "confirm": "../../confirm.json",
                                                      "out": "score.json", "samples": samples}, indent=1))
        print("== B =", n)
        stats["tiers"][str(n)] = SC.run(d / "score_cfg.json")["totals"]
    # current-version noise per tier
    cur = json.loads((HERE / "cmp" / "CUR" / "compare.json").read_text(encoding="utf8"))["checked"]["cur_riscv"]
    lists = json.loads((HERE / "run" / "CUR" / "lists.json").read_text())
    stats["current"] = {}
    for n in TIERS:
        row = {}
        for G in GROUPS:
            ids = {str(i) for s in SEEDS for i in lists[G][s][:n]}
            row[G] = {a: sum(1 for m in cl.values() if ids & set(m)) for a, cl in cur["clusters"].items()}
        stats["current"][str(n)] = row
    (HERE / "stats.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False), encoding="utf8")
    print("carried", stats["carried"], "rule-confirmed", stats["rule"],
          "to review", {x: len(v) for x, v in review.items()})
    print("current clusters", json.dumps(stats["current"]))
    for x in SAMPLES:
        print("cond", x, json.dumps(stats["cond"][x]))


if __name__ == "__main__":
    main()
