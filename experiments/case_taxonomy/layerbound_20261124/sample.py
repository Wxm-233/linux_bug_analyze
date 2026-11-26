import gzip, json, random
from collections import Counter
E = json.load(gzip.open("/root/work/layerbound/funcs.json.gz", "rt"))
D = json.load(gzip.open("/root/work/layerbound/edges.json.gz", "rt"))
random.seed(20261124)
print("A1 functions by dir", Counter("/".join(e["file"].split("/")[:2]) for e in E if e["label"] == "架构层A1" and e["kind"] == "func").most_common(8))
print("A1 attribution samples", Counter(d[0] for e in E if e["label"] == "架构层A1" for d in e["diffs"] if d[1] == "arch").most_common(10))
out = []
for kind in ("direct", "macro"):
    for k, c, b in random.sample(D[kind], 10):
        a, z = E[k], E[c]
        out.append({"kind": kind, "build": b, "caller": f'{a["file"]}:{a["start"]} {a["name"]} [{a["label"]}]',
                    "callee": f'{z["file"]}:{z["start"]} {z["name"]} [{z["label"]}/{z["kind"]}]'})
for o in out: print(o)
json.dump(out, open("edge_sample.json", "w"), ensure_ascii=False, indent=1)
