"""commitmode: preliminary look at commits whose 8 engine runs are all cached (does not write results.json)."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import commitmode as M
import engines as E
ds = json.loads((HERE / "dataset.json").read_text())
done = lambda c: all(E.cache_path(*j).exists() for j in M.jobs_of(c))
for kind, items in (("P", ds["positives"]), ("N", ds["negatives"])):
    ok = [it for it in items if done(it["commit"])]
    fl = al = 0
    for it in ok:
        r = M.check(it["commit"], run_missing=False)
        names = {fn for _, fn in it.get("fix_funcs", [])}
        a = any(x["func"] in names for x in r["new"]) if kind == "P" else False
        fl += r["flag_all"]; al += a
        eng = {e: v.get("new", v["status"]) for e, v in r["engines"].items()}
        print(kind, "ALIGN" if a else ("flag " if r["flag_all"] else "-    "), "noA" if r["flag_noA"] else "   ", r["info"][:58], eng)
    print(f"== {kind}: done {len(ok)}/{len(items)}  flagged {fl}" + (f"  aligned {al}" if kind == "P" else ""))
