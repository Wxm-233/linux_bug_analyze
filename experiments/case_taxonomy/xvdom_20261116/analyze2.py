"""xvdom criteria 二 features + 四.1 probe checks.  python analyze2.py -> check_probe.json, table2.json, table2.md"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
ENC2 = json.loads((HERE / "encoding2.json").read_text())
ENC1 = json.loads((CT / "encrank_20261115/encoding.json").read_text())
ARCHS = list(ENC2)
SELF = {("pte", "swp_soft_dirty"): "sd", ("pte", "swp_exclusive"): "ex", ("pte", "swp_uffd"): "uf",
        ("pmd", "swp_soft_dirty"): "sd", ("pmd", "swp_uffd"): "uf"}


def cell(arch, lv, grp, acc):
    return {k: v for k, v in ENC2[arch].get(lv, {}).get(grp, {}).get(acc, {}).items() if not k.startswith("_")}


def check_probe():
    """四.1: (a) old cells identical to encrank; (b) self checks"""
    same, diff, missing = 0, [], 0
    for a in ARCHS:
        for lv, accs in ENC1[a].items():
            for acc, mods in accs.items():
                grp, acc2 = ("MG", "mkold") if acc == "MKOLD" else ("R", acc)
                new = cell(a, lv, grp, acc2)
                if not isinstance(mods, dict):
                    continue
                for mod, kinds in mods.items():
                    if not isinstance(kinds, dict):
                        continue
                    for k, v in kinds.items():
                        nv = new.get(f"np.{k}.{mod}", "absent")
                        if nv == "absent":
                            missing += 1
                            diff.append((a, lv, acc, mod, k, v, nv))
                        elif nv == v:
                            same += 1
                        else:
                            diff.append((a, lv, acc, mod, k, v, nv))
    selfok, selfbad, selfunk = 0, [], 0
    for a in ARCHS:
        for (lv, acc), mod in SELF.items():
            for c, v in cell(a, lv, "S", acc).items():
                if c.startswith("np.") and c.endswith("." + mod):
                    if v == "unknown":
                        selfunk += 1
                    elif v == 1:
                        selfok += 1
                    else:
                        selfbad.append((a, lv, acc, c, v))
        for lv in ("pte", "pmd"):
            for acc, cs in ENC2[a].get(lv, {}).get("RT", {}).items():
                for c, v in cs.items():
                    if c.startswith("_"):
                        continue
                    if v == "unknown":
                        selfunk += 1
                    elif v == 1:
                        selfok += 1
                    else:
                        selfbad.append((a, lv, acc, c, v))
    return {"encrank_cells_same": same, "encrank_cells_diff": diff, "encrank_cells_missing": missing,
            "self_ok": selfok, "self_bad": selfbad, "self_unknown": selfunk}


def out_classes(grp):
    return ("np.", "none") if grp in ("R", "MG") else ("pr.", "none")


def features(lv, grp, acc):
    """criteria 二 末: M = archs that misread/corrupt on some out-of-domain class"""
    M, avail, detail, unknown = [], [], {}, {}
    pref = out_classes(grp)
    for a in ARCHS:
        cs = {c: v for c, v in cell(a, lv, grp, acc).items() if c.startswith(pref)}
        known = {c: v for c, v in cs.items() if v != "unknown"}
        if grp == "R" and acc == "pfn":
            hits = [c for c, v in known.items() if v == 0]
        else:
            hits = [c for c, v in known.items() if v == 1]
        if cs and len(known) < len(cs):
            unknown[a] = len(cs) - len(known)
        if not known:
            continue
        avail.append(a)
        if hits:
            M.append(a)
            detail[a] = sorted(hits)
    partial = bool(M) and len(M) < len(avail)
    return {"group": grp, "M": M, "avail": avail, "partial": partial, "latent": partial and "x86_64" not in M, "n": len(M),
            "detail": detail, "unknown": unknown}


def main():
    chk = check_probe()
    (HERE / "check_probe.json").write_text(json.dumps(chk, indent=1))
    print("encrank same", chk["encrank_cells_same"], "diff", len(chk["encrank_cells_diff"]), "missing", chk["encrank_cells_missing"],
          "| self ok", chk["self_ok"], "bad", len(chk["self_bad"]), "unknown", chk["self_unknown"])
    table = {}
    for lv in ("pte", "pmd"):
        accs = {(g, x) for a in ARCHS for g, d in ENC2[a].get(lv, {}).items() if g != "RT" for x in d}
        for g, x in sorted(accs):
            table[f"{lv}_{x}"] = features(lv, g, x)
    (HERE / "table2.json").write_text(json.dumps({"archs": ARCHS, "table": table}, indent=1))
    L = ["# 编码表第二版（R 组加空项；S、MG、MS 三组新增）", "", "出错：R、S 读出 1（pfn 读不出 P）；MG、MS 改变了值。只统计定义域外的输入类。", "",
         "| 接口 | 组 | 出错架构 | 有结果的架构 | 跨架构不一致 | x86_64 不出错（潜伏） |", "|---|---|---|---|---|---|"]
    for name, f in sorted(table.items(), key=lambda kv: (kv[1]["group"], kv[0])):
        L.append(f"| `{name}` | {f['group']} | {', '.join(f['M']) or '—'} | {len(f['avail'])} | {'是' if f['partial'] else ''} | {'是' if f['latent'] else ''} |")
    (HERE / "table2.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
