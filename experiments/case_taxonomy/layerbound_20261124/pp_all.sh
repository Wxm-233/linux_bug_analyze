source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/layerbound_20261124
for b in riscv x86_64 arm64; do python3 pp.py $b -j 10 2>&1 | grep -E "done|000 /" ; done
ls -la /root/work/layerbound/; df -h /root | tail -1
