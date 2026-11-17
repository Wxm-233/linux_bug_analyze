# copy a compile_commands.json without the -Wp,-MMD,<depfile> argument (kernel depfile path is relative to the build dir)
import json, re, sys
rows = json.load(open(sys.argv[1]))
for r in rows:
    if "command" in r:
        r["command"] = re.sub(r"\s-Wp,-MMD,\S+", "", r["command"])
    else:
        r["arguments"] = [a for a in r["arguments"] if not a.startswith("-Wp,-MMD,")]
json.dump(rows, open(sys.argv[2], "w"))
print(len(rows))
