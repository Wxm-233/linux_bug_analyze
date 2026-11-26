import gzip, json, pickle, zlib
E = json.load(gzip.open("/root/work/layerbound/funcs.json.gz", "rt"))
for e in E:
    if e["name"] == "writel_relaxed": print(e["file"], e["start"], e["kind"], e["label"], e["builds"])
d = pickle.load(gzip.open("/root/work/layerbound/lines_arm64.pkl.gz"))
bm = zlib.decompress(d["files"]["include/asm-generic/io.h"])
src = open("/root/repos/linux/include/asm-generic/io.h").read().split("\n")
for i in range(398, 412): print("*" if i < len(bm) and bm[i] else " ", i, src[i-1][:80])
