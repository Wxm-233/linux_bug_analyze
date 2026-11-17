source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
KB="python3 $REPO/tools/kbuild/kbuild.py"
R=$REPO/experiments/case_taxonomy/s6dyn_20261116
img=$($KB get df2908090cda arm64 pg64k --mut s6dyn.json:F6 2>$R/kernels/build_F6_retry.err); echo "arm64 pg64k F6 rc=$? $img"
