"""Compare self-test output with expected.json (criteria 三: must match exactly)."""
import gzip, json, sys
from pathlib import Path
W = Path(sys.argv[1]); HERE = Path(__file__).resolve().parent
exp = json.loads((HERE / "expected.json").read_text())
d = json.load(gzip.open(W / "facts.json.gz", "rt"))
F = {f["name"]: f for f in d["functions"].values()}
got = {}
got["functions"] = sorted(F)
regs = [r[:3] for f in F.values() for r in f["regs"]] + [r[:3] for r in d["global_regs"]]
got["regs"] = sorted(regs)
got["demo_calls"] = [[c[1], c[2]] for c in F["__do_sys_demo"]["calls"]]
got["demo_field_calls"] = [c[0] for c in F["__do_sys_demo"]["calls"] if c[0].startswith("field:")]
got["l6_guard_items"] = [sorted(x for x in g["items"] if x.lstrip("#") in ("arch_check", "ARCH_LIM")) for g in F["l6"]["guards"]]
got["l6_guard_consts"] = [next((s["const"] for c in g["cmps"] if c["op"] in (">", "==") for s in c["sides"] if s["const"] is not None), None) for g in F["l6"]["guards"]]
got["impl_op_guard_items"] = [sorted(x for x in g["items"] if x.lstrip("#") in ("arch_check", "ARCH_LIM")) for g in F["impl_op"]["guards"]]
got["macros"] = {n: {"fl": d["macros"][n]["fl"], "file": d["macros"][n]["file"]} for n in ("ARCH_LIM", "arch_check")}
got["macros"]["arch_check"]["body_has"] = "ARCH_LIM" if "ARCH_LIM" in d["macros"]["arch_check"]["body"] else None
ok = True
for k, v in exp["facts"].items():
    g = got.get(k)
    if k == "regs":
        v = sorted(v)
    if g != v:
        ok = False
        print("FACT MISMATCH", k, "expected", v, "got", g)
names = {"base": "base", "I1": "I1", "I2": "I2", "I4": "I4", "I1+I2": "I1,I2", "all": "I1,I2,I3,I4"}
for k, c in names.items():
    h = json.loads((W / f"hints_{c}.json").read_text())
    g = {sc: sorted([s["fn"], int(p), vs] for s in ss for p, vs in s["values"].items()) for sc, ss in h["sites"].items()}
    e = {sc: sorted(v) for sc, v in exp["hints"][k].items()}
    if g != e:
        ok = False
        print("HINT MISMATCH", k, "expected", e, "got", g)
    print(k, "stats", json.dumps({x: h["stats"][x] for x in ("sites", "T", "tree_boundary", "callbacks", "cb_edges_used")}))
print("SELFTEST", "PASS" if ok else "FAIL")
