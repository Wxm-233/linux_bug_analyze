"""Regression (fieldhint criteria 二.1): new facts minus the added "m" keys == old facts, for every function present
in the new file.   python3 facts_regress.py <new.json.gz> <old.json.gz> [--full]"""
import gzip, json, sys
new = json.load(gzip.open(sys.argv[1], "rt")); old = json.load(gzip.open(sys.argv[2], "rt"))
def strip(f):
    f = json.loads(json.dumps(f))
    for g in f.get("guards", []):
        for c in g["cmps"]:
            for s in c["sides"]:
                s.pop("m", None)
    for sw in f.get("switches", []):
        sw.pop("m", None)
    return f
only = sys.argv[sys.argv.index("--file") + 1] if "--file" in sys.argv else None  # subset runs: header inlines
keys = [k for k, f in new["functions"].items() if only is None or f["file"] == only]  # come from another unit
bad = [k for k in keys if old["functions"].get(k) != strip(new["functions"][k])]
nm = sum(1 for f in new["functions"].values() for g in f["guards"] for c in g["cmps"] for s in c["sides"] if s["m"])
print("functions", len(keys), "differ", len(bad), bad[:5], "sides with members", nm)
if "--full" in sys.argv:
    extra = {k: new[k] == old[k] for k in new if k not in ("functions", "seconds", "unit_status")}
    print("other keys equal", extra, "function sets equal", set(new["functions"]) == set(old["functions"]))
sys.exit(1 if bad else 0)
