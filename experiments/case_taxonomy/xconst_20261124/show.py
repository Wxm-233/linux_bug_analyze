import json
S = json.load(open("sample.json"))
for i, r in enumerate(S, 1):
    src = open("/root/repos/linux/" + r["file"]).read().split("\n")
    print(f'#{i} [{r["build"]}] {r["file"]}:{r["line"]} {r["F"]}  {r["name"]}')
    print("   src:", src[r["line"] - 1].strip()[:140])
    print("   chain:", " <- ".join(r["chain"]))
