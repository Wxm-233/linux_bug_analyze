# Re-score the diverse and relhint rounds with the normalised observations (stability criteria 三.4). Runs in WSL
# (the original compare.py reads the kernels' .config files there). No kernel is run.
#   bash rescore.sh      -> ev_diverse/, ev_relhint/ in this directory
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
CT=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy
R=$CT/stability_dev_20261111; W=/root/work/stab
for round in diverse relhint; do
  src=$CT/${round}_dev_20261110
  mkdir -p $R/ev_$round/gen
  cp $src/confirm.json $R/ev_$round/confirm.json
  for g in CUR A101 A310 A171 A181 B467; do
    cp $src/gen/cases_$g.json $src/gen/lists_$g.json $R/ev_$round/gen/
    mkdir -p $W/$round/runs/$g
    for f in $src/runs/$g/*.log.gz; do gzip -dc $f > $W/$round/runs/$g/$(basename ${f%.gz}); done
  done
  python3 - $round <<'PY'
import json, sys
from pathlib import Path
CT = Path("/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy")
R = CT / "stability_dev_20261111"
sys.path.insert(0, str(R))
import stable as S            # also puts the diverse round (compare, evaluate_d) on the path
import compare as C
import evaluate_d as E
rnd = sys.argv[1]
norm = S.normaliser()
orig = C.parse_log
CUR = {}
def parse_norm(text):
    p = orig(text)
    p["cases"] = {cid: norm(CUR[cid], v) if cid in CUR else v for cid, v in p["cases"].items()}
    return p
C.parse_log = parse_norm
C.HERE = R / f"ev_{rnd}"
C.W = Path(f"/root/work/stab/{rnd}")
for g in ["CUR", "A101", "A310", "A171", "A181", "B467"]:
    CUR.clear()
    CUR.update({str(c["id"]): c for c in json.loads((C.HERE / "gen" / f"cases_{g}.json").read_text())["cases"]})
    sys.argv = ["compare.py", g]
    C.main()
E.HERE = R / f"ev_{rnd}"
E.GROUPS = ["G0d", "G2d", "G3d"] if rnd == "diverse" else ["G3d", "G3r"]
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    E.main()
ev = json.loads((E.HERE / "evaluation.json").read_text())
print("SCORE", rnd, {G: (ev["totals"][G]["confirmed_total"], ev["totals"][G]["seeds_detecting"]) for G in E.GROUPS})
print("CURRENT", rnd, {G: {k: ev["current"][G][k] for k in ("odd_strong", "odd_weak", "clusters")} for G in E.GROUPS},
      "clusters_total", ev["current"]["clusters_total"], "unstable", ev["current"]["unstable"])
PY
done
rm -rf $W
