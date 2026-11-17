"""Copy a compile_commands.json without the -Wp,-MMD,<depfile> / -Wp,-MD,<depfile> argument (criteria section 2,
amendment 1: the arm64 compat vDSO uses -Wp,-MD)."""
import json, re, sys
rows = json.load(open(sys.argv[1]))
for r in rows:
    if "command" in r:
        r["command"] = re.sub(r"\s-Wp,-M{1,2}D,\S+", "", r["command"])
    else:
        r["arguments"] = [a for a in r["arguments"] if not re.match(r"-Wp,-M{1,2}D,", a)]
json.dump(rows, open(sys.argv[2], "w"))
