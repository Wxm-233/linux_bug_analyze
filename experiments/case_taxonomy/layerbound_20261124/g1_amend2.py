"""layerbound amendment 2: G1 over definitions compiled in at least one build"""
import gzip, json
E = json.load(gzip.open("/root/work/layerbound/funcs.json.gz", "rt"))
items = json.load(open("g1_funcs.json"))
ok, out = 0, []
for it in items:
    defs = [e for e in E if e["file"] == it["file"] and e["name"] == it["name"] and e["kind"] == "func" and e["builds"]]
    got = [e["label"] for e in defs]
    good = bool(got) and all(x in it["want"] for x in got)
    ok += good
    out.append(dict(it, got_compiled=got, ok_amend2=good))
    print("OK " if good else "BAD", it["file"], it["name"], got)
print("G1 functions (amendment 2)", ok, "/", len(items))
json.dump(out, open("g1_funcs_amend2.json", "w"), ensure_ascii=False, indent=1)
