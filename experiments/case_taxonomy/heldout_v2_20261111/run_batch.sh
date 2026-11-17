# (heldout_v2: copy of heldout_run_20261111/run_batch.sh; field vocabulary + gen_holdout2 replace gen_adapter/combine)
# First batch of the holdout (criteria 四): every candidate, every step. Runs in WSL. Resumable: a step whose marker
# logs/<group>.<step>.done exists is skipped; a failed step marks the candidate failed (logs/<group>.FAILED) and the
# batch moves on (criteria: no retry with other settings, no replacement).
#   bash run_batch.sh <group>:<parent>:<fix> ...
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
R=$REPO/experiments/case_taxonomy/heldout_v2_20261111
T=$REPO/experiments/case_taxonomy/difftest_tools_20261111
export PYTHONDONTWRITEBYTECODE=1
cd $R
step() {  # step <group> <name> <command...>
  local g=$1 n=$2; shift 2
  [ -f logs/$g.$n.done ] && return 0
  local t0=$(date +%s)
  if "$@" >> logs/$g.batch.log 2>&1; then
    echo "$(date '+%F %T') $g $n OK $(( $(date +%s)-t0 ))s" | tee -a logs/batch.log; touch logs/$g.$n.done
  else
    echo "$(date '+%F %T') $g $n FAILED $(( $(date +%s)-t0 ))s" | tee -a logs/batch.log; touch logs/$g.FAILED; return 1
  fi
}
for spec in "$@"; do
  spec=$(printf %s "$spec" | tr -d '\015'); IFS=: read g parent fix <<< "$spec";  # 11-12: batch1.txt has a CRLF ending (broke L10)
  p=$(echo $g | tr A-Z a-z); W=/root/work/heldout_run/$g; K=/root/work/heldout_run/kernels/$g
  [ -f logs/$g.FAILED ] && { echo "$g skipped (failed before)" | tee -a logs/batch.log; continue; }
  echo "$(date '+%F %T') == $g $parent $fix" | tee -a logs/batch.log
  python3 check_manifest.py | tee -a logs/batch.log | grep -q OK || { echo "MANIFEST CHANGED, stop" | tee -a logs/batch.log; exit 3; }
  for st in src la cc arm64 x86 save keep; do step $g $st bash build_cand.sh $g $parent $fix $st || continue 2; done
  step $g builds python3 -c "
import json; p='data/builds.json'; b=json.load(open(p))
b['loongarch']['$g']={'loongarch':'$W/b_la','arm64':'$W/b_arm64','x86_64':'$W/b_x86'}
json.dump(b,open(p,'w'),indent=1)" || continue
  step $g tables python3 prep_tables.py $g $parent $fix || continue
  cutoff=$(git -C $KSRC log -1 --format=%at $fix)
  step $g static bash static_group.sh $g $W/compile_commands.json $cutoff $W/src || continue
  step $g fix bash build_cand.sh $g $parent $fix fix || continue
  printf "%s loongarch %s\n%s loongarch %s\n%s arm64 %s\n%s x86_64 %s\n" ${p}_pre $K/${p}_pre.efi ${p}_fix $K/${p}_fix.efi \
     ${p}_ref_arm64 $K/${p}_ref_arm64.Image ${p}_ref_x86_64 $K/${p}_ref_x86_64.bzImage > data/kernels_$g.txt
  step $g probe bash probe.sh data/kernels_$g.txt runs/probe || continue
  step $g probetable python3 probe_table.py runs/probe data/kernels_$g.txt data/probes.json || continue
  step $g clean bash build_cand.sh $g $parent $fix clean || continue
  step $g ws python3 prep_ws.py $g || continue
  step $g fvocab env TARGET=loongarch python3 static/fieldvocab2.py static/$g/facts.json.gz ws/$g/diverse_dev_20261110/gen/layouts_$g.json ws/$g/fieldvocab.json || continue
  step $g gen bash -c "python3 gen_holdout2.py ws/$g $g \"\$(cat ws/$g/S.txt)\" ws/$g/fieldvocab.json --slot-name loongarch" || continue
  step $g cfg python3 -c "
import json
ks=[l.split() for l in open('data/kernels_$g.txt') if l.strip()]
json.dump({'group':'$g','cases':'ws/$g/run/cases.json','cases_txt':'ws/$g/run/cases_{name}.txt','logs':'runs/$g','out':'cmp/$g',
 'volatile':'../stability_dev_20261111/volatile.json','kernels':[{'name':n,'arch':a,'image':i} for n,a,i in ks]},open('kernels_$g.json','w'),indent=1)" || continue
  step $g run env PAR=12 bash $T/run.sh $R/kernels_$g.json || continue
  step $g compare python3 $T/compare.py kernels_$g.json || continue
  step $g warnings python3 $T/warnings.py runs/$g || continue
  echo "$(date '+%F %T') $g DONE" | tee -a logs/batch.log
done
echo "$(date '+%F %T') batch end; $(df -h /root | tail -1)" | tee -a logs/batch.log
