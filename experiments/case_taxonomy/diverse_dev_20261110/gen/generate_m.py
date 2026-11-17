"""G0m / G2m / G3m with the case model C1-C3 (casemodel criteria 二、四, amendment 1).

    python generate_m.py <group>   (needs vocab_<group>.json and layouts_<group>.json in this directory)
        -> cases_<group>.json, cases_<group>_<arch>.txt, lists_<group>.json

Base values, classes, templates and the G3 hint rule come from base_generate.py (copy of rankprune's generator);
targets and hints are rankprune's pruned hints (../../rankprune_dev_20261110/gen/hints_<group>.json).
"""
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import base_generate as BG  # noqa: E402

B, SEEDS, ARCHS = 1000, (1, 2, 3), ("riscv", "arm64", "x86_64")
NEW_FDS = ["epoll", "timerfd", "signalfd", "inotify", "pidfd", "perfsw"]
BG.FDS.extend(NEW_FDS)  # C3: fd value table
RES = {"msqid": "x:msq", "semid": "x:sem", "shmid": "x:shm", "timer_id": "x:timer", "ctx_id": "x:aio",
       "ctx": "x:aio", "epfd": "f:epoll", "mqdes": "f:mq"}
LEN_RE = re.compile(r"(len|size|count)$")
PLAIN = 8192


class Builder:
    """C1 structured buffers for one case (logical, decided on the riscv layout)"""

    def __init__(self, rng, lay):
        self.rng, self.lay, self.bufs = rng, lay, []

    def ok(self, t):
        return all(t in self.lay[a] for a in ARCHS)

    def plain(self):
        self.bufs.append({"plain": [PLAIN, self.rng.choice("za"), self.rng.choice([0, 0, 1])]})
        return len(self.bufs) - 1

    def struct(self, t, depth):
        k = len(self.bufs)
        spec = {"type": t, "set": {}}
        self.bufs.append(spec)
        prev = None  # ("struct", j) | ("ptr", j) | None
        for f in self.lay["riscv"][t]["fields"]:
            if f["kind"] == "ptr":
                if f["pointee"] and depth < 2 and self.ok(f["pointee"]):
                    j = self.struct(f["pointee"], depth + 1)
                    prev = ("struct", j)
                else:
                    j = self.plain()
                    prev = ("ptr", j)
                spec["set"][f["name"]] = ["ptr", j]
                continue
            if f["kind"] == "scalar" and f["size"] in (1, 2, 4, 8):
                if prev and LEN_RE.search(f["name"]):
                    spec["set"][f["name"]] = ["one"] if prev[0] == "struct" else ["len", prev[1]]
                elif prev is None and f["name"] == "size":
                    spec["set"][f["name"]] = ["sizeof"]
            prev = None
        free = [f for f in self.lay["riscv"][t]["fields"]
                if f["kind"] == "scalar" and f["size"] in (1, 2, 4, 8) and f["name"] not in spec["set"]]
        for f in self.rng.sample(free, min(len(free), self.rng.choice([1, 2]))):
            ctype = "long" if f["size"] == 8 else "int"
            tok = BG.generic(self.rng, f["name"], ctype if f["signed"] else "unsigned " + ctype)
            if not tok.startswith("i:"):
                v = self.rng.choice(BG.GEN_INT)
                v = self.rng.randrange(256) if v == "small" else self.rng.getrandbits(64) if v == "rand64" else v
                tok = "i:%x" % (v & ((1 << (8 * f["size"])) - 1))
            spec["set"][f["name"]] = ["int", tok[2:]]
        return k


def serialize(bufs, lay, arch):
    defs = []
    for k, b in enumerate(bufs):
        if "plain" in b:
            size, fill, off = b["plain"]
            defs.append(f"{k}:{size}:{fill}:{off}")
            continue
        L = lay[arch][b["type"]]
        fields = {f["name"]: f for f in L["fields"]}
        parts = [f"{k}:{L['size']}:z:0"]
        for name, (kind, *a) in b["set"].items():
            f = fields.get(name)
            if f is None or f["off"] is None or f["size"] not in (1, 2, 4, 8):
                continue  # amendment 1.2: field absent on this architecture
            w = 8 if kind == "ptr" else f["size"]
            val = {"ptr": lambda: f"t{a[0]}", "len": lambda: f"l{a[0]}", "one": lambda: "i1",
                   "sizeof": lambda: "i%x" % L["size"], "int": lambda: "i" + a[0]}[kind]()
            parts.append(f"{f['off']}/{w}/{val}")
        defs.append(":".join(parts))
    return ";".join(defs)


def pointee(ptype):
    t = ptype.replace("const ", "").replace("volatile ", "").strip()
    if t.endswith("*"):
        b = t[:-1].strip()
        if b.startswith(("struct ", "union ")) and "*" not in b:
            return b
    return None


def main():
    group = sys.argv[1]
    h = json.loads((HERE.parents[1] / "rankprune_dev_20261110" / "gen" / f"hints_{group}.json").read_text())
    vocab = json.loads((HERE / f"vocab_{group}.json").read_text())["vocab"]
    lay = json.loads((HERE / f"layouts_{group}.json").read_text())
    nrt = json.loads((HERE / "nr_tables.json").read_text())
    vt = json.loads((HERE.parents[1] / "twostage_dev_20261109/version_tables.json").read_text())
    common = set.intersection(*[set(vt[k]) for k in BG.KERNELS[group]])
    U = sorted(sc for sc in common if sc not in BG.BLACK_EXACT and sc in h["entries"]
               and all(sc in nrt[a] for a in ARCHS)) + ["raw_nr"]
    T = [s for s in h["T"] if s in U]
    params = {sc: h["entries"][sc] for sc in U if sc != "raw_nr"}
    params["raw_nr"] = BG.RAW_PARAMS
    hints = {sc: [s["values"] for s in h["sites"].get(sc, [])] for sc in T if sc != "raw_nr"}
    if "raw_nr" in T:
        hints["raw_nr"] = [{"0": h["raw_nr"]["values"]}]
    NR = {a: (h["NR_syscalls"].get(a) if isinstance(h["NR_syscalls"].get(a), int) else max(nrt[a].values()) + 1)
          for a in ARCHS}
    use = {"C1": 0, "C3": 0, "C2": 0}

    def case(rng, sc, use_hints):
        c = BG.make_case(rng, sc, params[sc], hints.get(sc), use_hints)
        bld = Builder(rng, lay)
        if sc != "raw_nr":
            for i, (pname, ptype) in enumerate(params[sc]):
                pt = pointee(ptype)
                if pt and bld.ok(pt) and rng.random() < 0.5:
                    n0 = len(bld.bufs)
                    k = bld.struct(pt, 0)
                    if len(bld.bufs) > 16 or any(len(b.get("set", {})) > 40 for b in bld.bufs):
                        del bld.bufs[n0:]  # executor limits (MAXSB 16, MAXW 48): keep the original value
                        use.setdefault("C1_over_limit", 0)
                        use["C1_over_limit"] += 1
                    else:
                        c["args"][i] = "t:%d" % k
                        use["C1"] += 1
                elif pname in RES and rng.random() < 0.5:
                    c["args"][i] = RES[pname]
                    use["C3"] += 1
                elif vocab.get(sc, {}).get(str(i)) and rng.random() < 0.5:
                    v = vocab[sc][str(i)]
                    x = rng.choice(v["eq"]) if v["eq"] else 0
                    for b in rng.sample(v["bits"], min(len(v["bits"]), rng.choice([0, 1, 2]))):
                        x |= b
                    c["args"][i] = BG.hexv(x, ptype)
                    use["C2"] += 1
        if bld.bufs:
            c["structs"] = bld.bufs
        return c

    cases, key2id, lists = [], {}, {}
    for G in ("G0m", "G2m", "G3m"):
        lists[G] = {}
        for seed in SEEDS:
            rng = random.Random(f"{group}/{G}/{seed}")
            order_u = U[:]
            rng.shuffle(order_u)
            target = [] if G == "G0m" else T[:]
            rng.shuffle(target)
            ids, iu, it = [], 0, 0
            for i in range(B):
                if target and i % 5 != 4:
                    sc, it = target[it % len(target)], it + 1
                    uh = G == "G3m"
                else:
                    sc, iu = order_u[iu % len(order_u)], iu + 1
                    uh = False
                c = case(rng, sc, uh)
                key = json.dumps(c, sort_keys=True)
                if key not in key2id:
                    key2id[key] = len(cases) + 1
                    cases.append(dict(c, id=len(cases) + 1))
                ids.append(key2id[key])
            lists[G][str(seed)] = ids
    for a in ARCHS:
        lines = []
        for c in cases:
            args = list(c["args"])
            if c["sc"] == "raw_nr":
                t = args[0]
                nr = NR[a] + int(t[2:]) if t.startswith("r:") else int(t[2:], 16) - 2**64
                nr = (nr + 2**63) % 2**64 - 2**63
                args = args[1:]
            else:
                nr = nrt[a][c["sc"]]
            args = (args + ["i:0"] * 6)[:6]
            line = f"{c['id']} {nr} {c['tmpl']} " + " ".join(args)
            if c.get("structs"):
                line += " | " + serialize(c["structs"], lay, a)
            lines.append(line)
        (HERE / f"cases_{group}_{a}.txt").write_text("\n".join(lines) + "\n")
    meta = {"group": group, "B": B, "seeds": SEEDS, "U": U, "T": T, "NR_syscalls": NR, "params": params,
            "classes": {sc: [BG.pclass(n, t) for n, t in ps] for sc, ps in params.items()}, "use": use,
            "cases": cases}
    (HERE / f"cases_{group}.json").write_text(json.dumps(meta, indent=0))
    (HERE / f"lists_{group}.json").write_text(json.dumps(lists))
    print(group, "U", len(U), "T", len(T), "cases", len(cases), "use", use,
          "structured", sum(1 for c in cases if c.get("structs")))


if __name__ == "__main__":
    main()
