"""Base cases and single-point mutation (mutate criteria 二、三). Shared by calib.py, bases.py, generate_s.py.

Logical case: {"sc", "args": [token...], "tmpl", "structs": [...]} as in casemodel; serialised with
generate_m.serialize (per-architecture layouts). Struct option marker in candidate args: "S:<type>".
"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import generate_m as GM  # noqa: E402  (extends the fd table with the 6 new kinds, as in casemodel)
BG = GM.BG
ARCHS = GM.ARCHS
SHALLOW = {"EBADF", "EFAULT", "EINVAL", "ENOTSOCK", "ENOTDIR", "ENOTTY", "ESPIPE", "EOPNOTSUPP"}
MAXSB = 16


class ValidBuilder(GM.Builder):
    """C1 structured buffer without random scalar mutation (criteria 二: base candidates)"""

    def struct(self, t, depth):
        k = len(self.bufs)
        spec = {"type": t, "set": {}}
        self.bufs.append(spec)
        prev = None
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
                if prev and GM.LEN_RE.search(f["name"]):
                    spec["set"][f["name"]] = ["one"] if prev[0] == "struct" else ["len", prev[1]]
                elif prev is None and f["name"] == "size":
                    spec["set"][f["name"]] = ["sizeof"]
            prev = None
        return k


def options(sc, i, pname, ptype, vocab, lay):
    """criteria 二 option table for one parameter (first option = default)"""
    cls = BG.pclass(pname, ptype)
    pt = GM.pointee(ptype)
    voc = vocab.get(sc, {}).get(str(i), {})
    eq4 = ["i:%x" % v for v in voc.get("eq", [])[:4]]
    if pt and all(pt in lay[a] for a in ARCHS):
        return ["S:" + pt, "b:z:0", "i:0"]
    if pname in GM.RES:
        return [GM.RES[pname], "i:0"]
    if cls == "ptr":
        return ["b:z:0", "b:a:0", "i:0"]
    if cls == "path":
        return ["p:f", "p:d", "p:nx"]
    if cls == "fd":
        return ["f:" + k for k in BG.FDS] + (["f:atcwd"] if "dfd" in pname or pname == "dirfd" else [])
    if cls == "size":
        return ["i:40", "i:1000", "i:10", "i:1", "i:0"]
    if cls == "flags":
        return ["i:0"] + [v for v in eq4 if v != "i:0"]
    if cls == "pid":
        return ["s:self", "i:0"]
    if cls == "uid":
        return ["i:0"]
    if cls == "addr":
        return ["i:0", "b:z:0", "i:40000000"]
    return ["i:0", "i:1", BG.hexv(-1, ptype)] + [v for v in eq4 if v not in ("i:0", "i:1")]


def realize(sc, args, lay, rng):
    """turn struct option markers into structured buffers; returns a logical case"""
    bld = ValidBuilder(rng, lay)
    out = []
    for a in args:
        if a.startswith("S:"):
            n0 = len(bld.bufs)
            k = bld.struct(a[2:], 0)
            if len(bld.bufs) > MAXSB or any(len(b.get("set", {})) > 40 for b in bld.bufs):
                del bld.bufs[n0:]
                out.append("b:z:0")
            else:
                out.append("t:%d" % k)
        else:
            out.append(a)
    c = {"sc": sc, "args": out, "tmpl": "none"}
    if bld.bufs:
        c["structs"] = bld.bufs
    return c


def candidates(sc, params, vocab, lay, rng, n=48):
    opts = [options(sc, i, pn, pt, vocab, lay) for i, (pn, pt) in enumerate(params)]
    out = [realize(sc, [o[0] for o in opts], lay, rng)]
    for _ in range(n - 1):
        out.append(realize(sc, [rng.choice(o) for o in opts], lay, rng))
    return out


def is_ok(r):
    return not (r.startswith("E") or r in ("timeout", "noresult", "setup_failed") or r.startswith("SIG"))


def scalar_fields(case, lay):
    pos = []
    for k, b in enumerate(case.get("structs", [])):
        if "type" not in b:
            continue
        for f in lay["riscv"][b["type"]]["fields"]:
            if f["kind"] == "scalar" and f["size"] in (1, 2, 4, 8):
                pos.append(("field", k, f["name"], f["size"], f["signed"]))
    return pos


def mutate(base, params, vocab, lay, rng, hints_p=None, use_hints=False):
    """criteria 三: change 1 (2/3) or 2 (1/3) positions of a copy of base"""
    c = copy.deepcopy(base)
    sc = c["sc"]
    pos = [("param", i) for i in range(len(params))] + scalar_fields(c, lay)
    if sc != "raw_nr":
        ai = next((i for i, (n, t) in enumerate(params) if BG.pclass(n, t) == "addr"), None)
        li = next((i for i, (n, t) in enumerate(params) if BG.pclass(n, t) == "size"), None)
        if ai is not None and li is not None:
            pos.append(("tmpl", ai, li))
    k = 1 if rng.random() < 2 / 3 else 2
    chosen = rng.sample(pos, min(k, len(pos)))
    for p in chosen:
        if p[0] == "tmpl":
            c["tmpl"] = rng.choice(["none", f"occ:{p[1]}:{p[2]}", f"adj:{p[1]}:{p[2]}"])
        elif p[0] == "field":
            _, kk, name, size, signed = p
            ctype = "long" if size == 8 else "int"
            tok = BG.generic(rng, name, ctype if signed else "unsigned " + ctype)
            if not tok.startswith("i:"):
                v = rng.choice(BG.GEN_INT)
                v = rng.randrange(256) if v == "small" else rng.getrandbits(64) if v == "rand64" else v
                tok = "i:%x" % (v & ((1 << (8 * size)) - 1))
            c["structs"][kk]["set"][name] = ["int", tok[2:]]
        else:
            i = p[1]
            pname, ptype = params[i]
            if use_hints and hints_p and hints_p.get(i) and rng.random() < 0.5:
                tok = rng.choice(sorted(hints_p[i]))
                c["args"][i] = BG.hint_token(rng, tok) if sc != "raw_nr" else tok
                continue
            if sc == "raw_nr":
                c["args"][i] = BG.make_case(rng, "raw_nr", params, None, False)["args"][i]
                continue
            srcs = ["generic"]
            voc = vocab.get(sc, {}).get(str(i))
            if voc:
                srcs.append("vocab")
            if pname in GM.RES:
                srcs.append("res")
            pt = GM.pointee(ptype)
            if pt and all(pt in lay[a] for a in ARCHS):
                srcs.append("struct")
            src = rng.choice(srcs)
            if src == "generic":
                c["args"][i] = BG.generic(rng, pname, ptype)
            elif src == "vocab":
                x = rng.choice(voc["eq"]) if voc["eq"] else 0
                for b in rng.sample(voc["bits"], min(len(voc["bits"]), rng.choice([0, 1, 2]))):
                    x |= b
                c["args"][i] = BG.hexv(x, ptype)
            elif src == "res":
                c["args"][i] = GM.RES[pname]
            else:
                bld = GM.Builder(rng, lay)
                bld.bufs = c.setdefault("structs", [])
                n0 = len(bld.bufs)
                kk = bld.struct(pt, 0)
                if len(bld.bufs) > MAXSB or any(len(b.get("set", {})) > 40 for b in bld.bufs):
                    del bld.bufs[n0:]
                    c["args"][i] = BG.generic(rng, pname, ptype)
                else:
                    c["args"][i] = "t:%d" % kk
    if not c.get("structs"):
        c.pop("structs", None)
    return c


def lines(cases, lay, nrt, NR):
    out = {a: [] for a in ARCHS}
    for c in cases:
        for a in ARCHS:
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
                line += " | " + GM.serialize(c["structs"], lay, a)
            out[a].append(line)
    return out
