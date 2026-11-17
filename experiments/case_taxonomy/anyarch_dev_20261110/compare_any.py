"""Architecture-neutral comparison (anyarch criteria 二). Pure Python; reads gz or plain logs.

    python compare_any.py <kernels_<group>.json>  -> <out_dir>/compare_any.json

Config: {"group", "cases": <cases json>, "lists": <lists json or null>, "logs": <dir>, "out": <dir>,
         "kernels": [{"name", "arch", "build": <dir or null>}, ...]}   (paths relative to the config file)
Every kernel is checked against all kernels of the *other* architectures (a comparison set).  Verdict per
(checked kernel, case): unstable | excluded | same | odd_<arch> | split.  No architecture name is special.
"""
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "diverse_dev_20261110"))
import compare as C  # noqa: E402  (parse_log, KMSG, perf_needs_hw, is_hw_pmu; nothing runs on import)


def read_log(p):
    raw = gzip.open(p).read() if p.suffix == ".gz" else p.read_bytes()
    text, _ = C.KMSG.subn("", raw.replace(b"\x00", b"").decode("utf-8", "replace"))
    return C.parse_log(text)


def load(cfg_path):
    cfg_path = Path(cfg_path).resolve()
    cfg = json.loads(cfg_path.read_text(encoding="utf8"))
    base = cfg_path.parent
    cases = {str(c["id"]): c for c in json.loads((base / cfg["cases"]).read_text())["cases"]}
    logs = base / cfg["logs"]
    obs, hw, incomplete = {}, {}, []
    for k in cfg["kernels"]:
        runs = []
        for i in (1, 2, 3):
            p = logs / f"{k['name']}.run{i}.log"
            p = p if p.exists() else p.with_name(p.name + ".gz")
            r = read_log(p)
            if not r["complete"]:
                incomplete.append(p.name)
            runs.append(r)
        hw[k["name"]] = any(C.is_hw_pmu(n) for n in runs[0]["probe"].get("pmu_devices", []))
        obs[k["name"]] = [{cid: json.dumps(v) for cid, v in r["cases"].items()} for r in runs]
    assert not incomplete, incomplete
    stable, unstable = {}, set()
    for cid in cases:
        vals = {}
        for k in obs:
            vs = {o.get(cid, "missing") for o in obs[k]}
            if len(vs) != 1:
                unstable.add(cid)
                break
            vals[k] = vs.pop()
        else:
            stable[cid] = vals
    return cfg, base, cases, hw, stable, unstable


def sets(cfg):
    """checked kernel -> {arch: [kernels]} : itself plus every kernel of the other architectures"""
    arch = {k["name"]: k["arch"] for k in cfg["kernels"]}
    out = {}
    for k, a in arch.items():
        s = {a: [k]}
        for k2, a2 in arch.items():
            if a2 != a:
                s.setdefault(a2, []).append(k2)
        assert len(s) >= 3, "need at least 3 architectures"
        out[k] = s
    return out


def verdict(case, cset, hw, vals):
    members = [k for ks in cset.values() for k in ks]
    if C.perf_needs_hw(case) and not all(hw[k] for k in members):
        return "excluded"
    per = {a: {vals[k] for k in ks} for a, ks in cset.items()}
    if any(len(v) != 1 for v in per.values()):
        return "split"  # two kernels of one reference architecture disagree
    v = {a: next(iter(s)) for a, s in per.items()}
    distinct = set(v.values())
    if len(distinct) == 1:
        return "same"
    if len(distinct) == 2:
        odd = [a for a in v if sum(v[a] == v[b] for b in v) == 1]
        if len(odd) == 1:
            return "odd_" + odd[0]
    return "split"


def ckey(case, cset, vals, arch):
    r = json.loads(vals[cset[arch][0]])[0]
    ref = sorted({json.loads(vals[k])[0] for a, ks in cset.items() if a != arch for k in ks})
    return f"{case['sc']}|{r}|{'/'.join(ref)}"


def run(cfg_path):
    cfg, base, cases, hw, stable, unstable = load(cfg_path)
    out = {"group": cfg["group"], "kernels": {k["name"]: k["arch"] for k in cfg["kernels"]}, "hw_pmu": hw,
           "unstable": sorted(unstable, key=int), "sets": {}}
    for chk, cset in sets(cfg).items():
        vd, clusters = {}, {}
        for cid, c in cases.items():
            if cid in unstable:
                vd[cid] = "unstable"
                continue
            v = verdict(c, cset, hw, stable[cid])
            vd[cid] = v
            if v.startswith("odd_"):
                clusters.setdefault(v[4:], {}).setdefault(ckey(c, cset, stable[cid], v[4:]), []).append(cid)
        summary = {}
        for v in vd.values():
            summary[v] = summary.get(v, 0) + 1
        out["sets"][chk] = {"members": cset, "summary": dict(sorted(summary.items())),
                            "clusters": {a: {k: sorted(v, key=int) for k, v in sorted(cl.items())}
                                         for a, cl in sorted(clusters.items())},
                            "verdicts": {cid: v for cid, v in vd.items() if v != "same"}}
    out["values"] = {cid: stable[cid] for cid in stable
                     if any(s["verdicts"].get(cid, "same") not in ("same", "excluded") for s in out["sets"].values())}
    od = base / cfg["out"]
    od.mkdir(parents=True, exist_ok=True)
    (od / "compare_any.json").write_text(json.dumps(out, indent=0, ensure_ascii=False), encoding="utf8")
    for chk, s in out["sets"].items():
        print(cfg["group"], chk, json.dumps(s["summary"]), {a: len(c) for a, c in s["clusters"].items()})
    return out


if __name__ == "__main__":
    run(sys.argv[1])
