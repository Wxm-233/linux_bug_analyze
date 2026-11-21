source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/linmap2_20261119
python3 linmap2.py selftest | tail -1
mkdir -p /root/work/lm2check && cp diag/011.json /root/work/lm2check/011.old.json
rm -f diag/011.json
/usr/bin/time -v python3 linmap2.py diag 11 > diag_11b.log 2> time_11b.log
echo rc=$?
grep -E "Maximum resident|Elapsed" time_11b.log
python3 - <<'PY'
import json
a=json.load(open('/root/work/lm2check/011.old.json')); b=json.load(open('diag/011.json'))
print('old', a['param_cands'], a['info']['param_summaries'], a['v1_hit'], a['v2_hit'])
print('new', b['param_cands'], b['info']['param_summaries'], b['v1_hit'], b['v2_hit'])
print('sinks same', a['sinks_in_fix_funcs']==b['sinks_in_fix_funcs'])
PY
