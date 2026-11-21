"""caller-side #if context for the 12 sampled units (source + .config only). WSL."""
import json, re, subprocess, sys
from pathlib import Path
import expect_helper as H
HERE = Path(__file__).resolve().parent
for x in json.loads((HERE / (sys.argv[1] if len(sys.argv) > 1 else "binding_sample.json")).read_text(encoding="utf-8")):
    src = H.git("show", f"{H.REV}:{x['caller_file']}").split("\n")
    st = H.stack_at(src, x["line"])
    cf = sorted(set(re.findall(r"CONFIG_\w+", " ".join(s for _, s in st))))
    vals = " ".join(f"{c}={{{','.join(H.CFG[a].get(c, 'n') for a in H.CFG)}}}" for c in cf)
    print(x["callee"], x["caller_file"], x["line"], [s[:70] for _, s in st if "_H" not in s], vals)
