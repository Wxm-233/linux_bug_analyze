import gzip, json
from collections import Counter
E = json.load(gzip.open("/root/work/layerbound/funcs.json.gz", "rt"))
g2 = json.load(open("g2.json"))
print("strict(with macro)", g2["strict"], "strict direct-only", sum(1 for x in g2["items"] if x["strict_direct_only"] and x["evaluable"]), "/", g2["evaluable"])
print([ (x["id"], x["strict"], x["strict_direct_only"]) for x in g2["items"]])
un = [e for e in E if e["label"] == "未归因"]
print("unattr kinds", Counter(tuple(sorted({d[0].split(":")[0] for d in e["diffs"] if d[1] == "unattr"})) for e in un).most_common(4))
print("unattr top dirs", Counter("/".join(e["file"].split("/")[:2]) for e in un).most_common(10))
print("smaps defs", [(e["start"], e["label"], e["builds"]) for e in E if e["name"] == "smaps_pmd_entry"])
fn = [e for e in E if e["kind"] == "func"]
print("func labels", Counter(e["label"] for e in fn))
