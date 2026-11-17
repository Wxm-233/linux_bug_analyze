"""Default comparison from 2026-11-11 on: architecture-neutral (anyarch round) + volatile-output normalisation
(stability round). Pure Python; reads plain or gz logs.

    python compare.py <kernels.json> [--raw] [--no-timeout-class]   -> <out>/compare.json
    python compare.py learn <kernels.json>... -o volatile.json

Config (paths relative to the config file):
  {"group", "cases": <cases json>, "logs": <dir>, "out": <dir>,
   "volatile": <volatile.json or null>,              # null / missing / --raw: no normalisation
   "kernels": [{"name", "arch"}, ...]}

Verdict per (checked kernel, case).  "others" = kernels of the other architectures that are not capability-excluded
for this case.
  unstable   the 3 runs of some kernel differ (after normalisation)
  timeout    the checked kernel hit the executor's per-case time limit (kernels that timed out are also left out
             of "others"); --no-timeout-class restores the old behaviour (a timeout is an ordinary result)
  excluded   the checked kernel lacks a capability the case needs
  no_ref     no other architecture is left to compare with
  split      two kernels of one other architecture disagree, or more than one architecture stands apart
  same       all agree                         (at least 2 other architectures)
  odd_<a>    architecture <a> alone differs    (at least 2 other architectures)
  weak_same / weak_diff   only 1 other architecture is left: equal / different, cannot tell which side is odd
Mapping to the riscv-only verdicts of the earlier rounds (for a riscv checked kernel): consistent = same|weak_same,
odd_strong = odd_riscv, odd_weak = weak_diff, ref_split = odd_<other>|split, excluded_* = excluded.
"""
import glob
import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
import importlib.util  # noqa: E402

# log parser and the PMU capability rule, reused read-only; loaded by path because that file is also called compare.py
_spec = importlib.util.spec_from_file_location("compare_diverse", CT / "diverse_dev_20261110" / "compare.py")
C0 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C0)

ERRNO = re.compile(r"^E[A-Z0-9]+$")
KMSG_ANY = re.compile(r"\[\s*\d+\.\d{6}\][^\n]*\n")
THRESHOLD = 2  # distinct cases that must show the variation (stability criteria 二)


# ---------- reading ----------
def read_log(p):
    raw = gzip.open(p).read() if p.suffix == ".gz" else p.read_bytes()
    # Kernel messages can interrupt an executor line, several lines at a time (seen once warning-level messages are
    # shown).  Remove every timestamped kernel message up to its newline, wherever it starts; the pieces of the
    # interrupted line then join again.  (The earlier rule only removed one message that started mid-line.)
    text = KMSG_ANY.sub("", raw.replace(b"\x00", b"").decode("utf-8", "replace"))
    return C0.parse_log(text)


def load(cfg_path):
    cfg_path = Path(cfg_path).resolve()
    cfg = json.loads(cfg_path.read_text(encoding="utf8"))
    base = cfg_path.parent
    cases = {str(c["id"]): c for c in json.loads((base / cfg["cases"]).read_text())["cases"]}
    runs = {}
    for k in cfg["kernels"]:
        runs[k["name"]] = []
        for i in (1, 2, 3):
            p = base / cfg["logs"] / f"{k['name']}.run{i}.log"
            p = p if p.exists() else p.with_name(p.name + ".gz")
            r = read_log(p)
            assert r["complete"], p
            runs[k["name"]].append(r)
    return cfg, base, cases, runs


# ---------- volatile outputs ----------
def slots(case, v):
    sc, out = case["sc"], []
    for ai, n, h in v[2] or []:
        out.append(((sc, "b", str(ai)), (n, h)))
    if v[3] and v[3] != [None, None]:
        out.append(((sc, "pool", ""), tuple(v[3])))
    if len(v) > 4 and v[4]:
        S = case.get("structs", [])
        for k, n, h in v[4]:
            out.append(((sc, "s", S[k].get("type", "plain") if k < len(S) else "plain"), (n, h)))
    return out


def learn(cfg_paths, out_path):
    vs, vr = {}, {}
    for cp in cfg_paths:
        cfg, _, cases, runs = load(cp)
        g = cfg["group"]
        for k, rs in runs.items():
            for cid, c in cases.items():
                o = [r["cases"].get(cid) for r in rs]
                if None in o:
                    continue
                if len({x[0] for x in o}) > 1:
                    vr.setdefault(c["sc"], set()).add(f"{g}/{cid}")
                if len({(x[0], x[1]) for x in o}) > 1:
                    continue
                per = {}
                for x in o:
                    d = {}
                    for key, val in slots(c, x):
                        d.setdefault(key, []).append(val)
                    for key, val in d.items():
                        per.setdefault(key, set()).add(tuple(val))
                for key, vals in per.items():
                    if len(vals) > 1:
                        vs.setdefault(key, set()).add(f"{g}/{cid}")
    out = {"threshold": THRESHOLD, "learned_from": [str(p) for p in cfg_paths],
           "slots": sorted(["|".join(k), len(v)] for k, v in vs.items() if len(v) >= THRESHOLD),
           "slots_below_threshold": sorted(["|".join(k), len(v)] for k, v in vs.items() if len(v) < THRESHOLD),
           "returns": sorted([sc, len(v)] for sc, v in vr.items() if len(v) >= THRESHOLD),
           "returns_below_threshold": sorted([sc, len(v)] for sc, v in vr.items() if len(v) < THRESHOLD)}
    Path(out_path).write_text(json.dumps(out, indent=1))
    print("volatile slots", len(out["slots"]), "returns", len(out["returns"]))
    return out


def normaliser(volatile_path):
    v = json.loads(Path(volatile_path).read_text())
    VS = {tuple(s[0].split("|")) for s in v["slots"]}
    VR = {s[0] for s in v["returns"]}

    def norm(case, o):
        sc, o = case["sc"], list(o)
        if sc in VR and not ERRNO.match(o[0]):
            o[0] = "val"
        if o[2]:
            o[2] = [[ai, int(n > 0)] if (sc, "b", str(ai)) in VS else [ai, n, h] for ai, n, h in o[2]]
        if o[3] and o[3] != [None, None] and (sc, "pool", "") in VS:
            o[3] = [int(o[3][0] > 0)]
        if len(o) > 4 and o[4]:
            S = case.get("structs", [])
            o[4] = [[k, int(n > 0)] if (sc, "s", S[k].get("type", "plain") if k < len(S) else "plain") in VS
                    else [k, n, h] for k, n, h in o[4]]
        return o
    return norm


# ---------- verdicts ----------
def timed_out(v):
    return json.loads(v)[0] == "timeout"


def verdict(case, chk, arch, hw, vals, tclass=True):
    need = C0.perf_needs_hw(case)
    if need and not hw[chk]:
        return "excluded"
    if tclass and timed_out(vals[chk]):
        return "timeout"
    others = {}
    for k, a in arch.items():
        if a != arch[chk] and not (need and not hw[k]) and not (tclass and timed_out(vals[k])):
            others.setdefault(a, set()).add(vals[k])
    if not others:
        return "no_ref"
    if any(len(v) != 1 for v in others.values()):
        return "split"
    v = {a: next(iter(s)) for a, s in others.items()}
    mine = vals[chk]
    if len(v) == 1:
        return "weak_same" if next(iter(v.values())) == mine else "weak_diff"
    v[arch[chk]] = mine
    distinct = set(v.values())
    if len(distinct) == 1:
        return "same"
    if len(distinct) == 2:
        odd = [a for a in v if sum(v[a] == v[b] for b in v) == 1]
        if len(odd) == 1:
            return "odd_" + odd[0]
    return "split"


def ckey(case, chk, arch, vals, odd):
    r = json.loads(next(vals[k] for k in arch if arch[k] == odd and (odd != arch[chk] or k == chk)))[0]
    ref = sorted({json.loads(vals[k])[0] for k in arch if arch[k] != odd and (arch[k] != arch[chk] or k == chk)})
    return f"{case['sc']}|{r}|{'/'.join(ref)}"


def run(cfg_path, raw=False, tclass=True):
    cfg, base, cases, runs = load(cfg_path)
    vol = None if raw else cfg.get("volatile")
    norm = normaliser(base / vol) if vol else None
    arch = {k["name"]: k["arch"] for k in cfg["kernels"]}
    hw = {k: any(C0.is_hw_pmu(n) for n in runs[k][0]["probe"].get("pmu_devices", [])) for k in arch}
    stable, unstable = {}, []
    for cid, c in cases.items():
        vals = {}
        for k in arch:
            s = {json.dumps(norm(c, x) if norm and x is not None else x) for x in (r["cases"].get(cid) for r in runs[k])}
            if len(s) != 1:
                unstable.append(cid)
                break
            vals[k] = s.pop()
        else:
            stable[cid] = vals
    us = set(unstable)
    out = {"group": cfg["group"], "kernels": arch, "normalised": bool(norm), "volatile": vol, "hw_pmu": hw,
           "timeout_class": tclass,
           "unstable": unstable, "checked": {}}
    for chk in arch:
        vd, cl = {}, {}
        for cid, c in cases.items():
            if cid in us:
                vd[cid] = "unstable"
                continue
            v = verdict(c, chk, arch, hw, stable[cid], tclass)
            vd[cid] = v
            if v.startswith("odd_"):
                cl.setdefault(v[4:], {}).setdefault(ckey(c, chk, arch, stable[cid], v[4:]), []).append(cid)
        summ = {}
        for v in vd.values():
            summ[v] = summ.get(v, 0) + 1
        out["checked"][chk] = {"summary": dict(sorted(summ.items())),
                               "clusters": {a: dict(sorted(x.items())) for a, x in sorted(cl.items())},
                               "verdicts": {cid: v for cid, v in vd.items() if v != "same"}}
    keep = {cid for s in out["checked"].values() for cid, v in s["verdicts"].items()
            if v not in ("excluded", "unstable", "weak_same", "timeout")}
    out["values"] = {cid: stable[cid] for cid in sorted(keep & set(stable), key=int)}
    od = base / cfg["out"]
    od.mkdir(parents=True, exist_ok=True)
    (od / "compare.json").write_text(json.dumps(out, indent=0, ensure_ascii=False), encoding="utf8")
    for chk, s in out["checked"].items():
        print(cfg["group"], chk, "norm" if norm else "raw", json.dumps(s["summary"]),
              {a: len(x) for a, x in s["clusters"].items()})
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "learn":
        o = a[a.index("-o") + 1]
        learn([x for x in a[1:a.index("-o")]], o)
    else:
        run(a[0], raw="--raw" in a, tclass="--no-timeout-class" not in a)
