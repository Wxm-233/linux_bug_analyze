source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/effzero_20261120
rm -f /root/work/effzero/facts_*.pkl.gz
printf '%s\n' "6829e274a623^ D1" "e89f5b370153^ D3" "dd65a941f6ba^ D4" "a1da439cc0d9^ D5" "5bebe8de1926^ X1" "6c2f761dad78^ K1" | \
  xargs -P 3 -L 1 bash runone.sh
echo ALLDONE
