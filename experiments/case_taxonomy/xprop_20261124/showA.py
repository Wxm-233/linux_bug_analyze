import json
S = json.load(open("sample_A.json"))
for i, r in enumerate(S, 1):
    src = open("/root/repos/linux/" + r["file"]).read().split("\n")
    line = src[r["line"] - 1].strip()
    print(f'#{i} [{r["build"]}] {r["file"]}:{r["line"]} {r["F"]} -> {r["G"]} ({r["G_kind"]}, {r["G_file"]})')
    print("   src:", line[:150])
    print("   ", {k: r.get(k) for k in ("role", "type", "expr", "origin", "use", "name", "cat", "alias_of", "impl") if r.get(k) not in (None, "")})
