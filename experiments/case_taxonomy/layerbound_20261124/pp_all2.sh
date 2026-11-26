source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd /root/work/layerbound && for f in lines_riscv lines_arm64 lines_x86_64; do [ -f $f.pkl.gz ] && [ ! -f ${f}_run1.pkl.gz ] && mv $f.pkl.gz ${f}_run1.pkl.gz; done
for f in funcs edges; do [ -f $f.json.gz ] && mv $f.json.gz ${f}_run1.json.gz; done
cd /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/layerbound_20261124
for b in riscv x86_64 arm64; do python3 pp.py $b -j 10 2>&1 | grep -E "done|Traceback|Error" ; done
ls -la /root/work/layerbound/*.pkl.gz
