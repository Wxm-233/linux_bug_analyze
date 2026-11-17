source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/commitmode_20261117
python3 - <<'PY' > rerun_jobs.txt
import sys; sys.path.insert(0,'.')
import commitmode as M, engines as E
for c in ['5bd2c0650a90','cb787f4ac0c2']:
    for j in M.jobs_of(c):
        if not E.cache_path(*j).exists(): print(j[0], j[1], *j[2])
PY
wc -l < rerun_jobs.txt
while read -r line; do /usr/bin/time -f "maxrss_kb=%M wall=%e" python3 engines.py $line 2>&1 | tail -2; done < rerun_jobs.txt
echo rerun-done
