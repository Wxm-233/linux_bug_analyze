# kbuild_reuse criteria 三: acceptance tests A1-A8 (A7 = QEMU runs). WSL.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
R=$REPO/experiments/case_taxonomy/kbuild_reuse_20261115
KB="python3 $REPO/tools/kbuild/kbuild.py"
LOG=$R/accept.log; : > $LOG
step() {  # step <id> <expect rc> <kbuild args...>
  local id=$1 want=$2; shift 2
  local t0=$(date +%s) out rc
  out=$($KB "$@" 2>>$R/kbuild_stderr.log); rc=$?
  echo "$id rc=$rc want=$want secs=$(( $(date +%s) - t0 )) out=$out args=$*" | tee -a $LOG
  eval "IMG_$id=\$out"
}
REV=df2908090cda
step A1 0 get $REV riscv plain --tag a1
step A2 0 get $REV riscv plain --tag a1
step A3 3 get $REV riscv plain --mut r4.json:R4a_bad
step A4 0 get $REV riscv plain --mut r4.json:R4a
step A5 0 get $REV riscv plain --mut r4.json:R4b
step A8 0 get $REV riscv plain --mut n2.json:N2
step A6 0 get $REV riscv plain --tag a6
T=/root/work/kbuild/trees/${REV}_riscv_plain
echo "src vs pristine after all reverts: $(diff -rq /root/work/kbuild/pristine/$REV $T/src | grep -v '\.complete' | wc -l) differing files" | tee -a $LOG
grep -h "BUILD OK\|PRECHECK\|precheck ok\|reverted\|FAILED" $R/kbuild_stderr.log | tee -a $LOG
echo "disk: pristine $(du -sh /root/work/kbuild/pristine | cut -f1), trees $(du -sh /root/work/kbuild/trees | cut -f1), images $(du -sh /root/work/kbuild/images | cut -f1), registry entries $($KB list | wc -l)" | tee -a $LOG
K=/root/work/kbuild_accept/k; rm -rf $K; mkdir -p $K
ln -s $IMG_A4 $K/riscv_R4a.img; ln -s $IMG_A5 $K/riscv_R4b.img; ln -s $IMG_A6 $K/riscv_a6.img
bash $R/run.sh a7 $K riscv_R4a:riscv:plain riscv_R4b:riscv:plain riscv_a6:riscv:plain
echo "accept end $(date '+%T')" | tee -a $LOG
