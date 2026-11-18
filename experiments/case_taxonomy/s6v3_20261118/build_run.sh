# s6v3: anchor check on 7.3-rc2, build pg64k+F6v3, run v3_force and plain_force x3, judge
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
R=$REPO/experiments/case_taxonomy/s6v3_20261118; mkdir -p $R/kernels
I=/root/work/kbuild/images/df2908090cda
python3 $REPO/tools/kbuild/kbuild.py get df2908090cda arm64 pg64k --mut s6v3.json:F6v3 > $R/kernels/pg64k_F6v3.path 2> $R/build.log
echo "build exit=$? image=$(cat $R/kernels/pg64k_F6v3.path)"; tail -n 3 $R/build.log
[ -s $R/kernels/pg64k_F6v3.path ] || exit 1
bash $R/run.sh main $(cat $R/kernels/pg64k_F6v3.path):v3_force:force ${I}_arm64_pg64k_-.img:plain_force:force > $R/run_main.log 2>&1
cd $R && python3 judge.py main
