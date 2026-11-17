# Run G3d+G3r cases of the listed groups on their kernels, 3 times each; one case list per kernel (relhint 三).
#   bash run_rel.sh <group>...    logs -> /root/work/relhint/runs/<group>/ ; then compare (original compare.py
#   functions, paths patched) ; gz logs + compare.json copied to runs/<group>/ in this directory
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
CT=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy
R=$CT/relhint_dev_20261110; W=/root/work/relhint
mkdir -p $W/initramfs; jobs=$W/jobs.txt; : > $jobs
declare -A IMG ARCH
while read name arch img; do [ -n "$name" ] && { IMG[$name]=$img; ARCH[$name]=$arch; }; done < <(tr -d '\r' < $CT/rtprobe_dev_20261110/kernels_all.txt)
for g in "$@"; do
  mkdir -p $W/runs/$g
  l=$(echo $g | tr A-Z a-z)
  if [ $g = CUR ]; then ks="cur_riscv cur_arm64 cur_x86_64"; else ks="${l}_pre ${l}_fix ${l}_ref_arm64 ${l}_ref_x86_64"; fi
  for k in $ks; do
    bash $CT/mix_dev_20261110/harness/mk_initramfs.sh ${ARCH[$k]} $R/gen/cases_${g}_$k.txt $W/initramfs/${g}_$k.cpio >/dev/null || exit 1
    for i in 1 2 3; do echo "${ARCH[$k]} ${IMG[$k]} $W/initramfs/${g}_$k.cpio $W/runs/$g/$k.run$i.log" >> $jobs; done
  done
done
echo "jobs: $(wc -l < $jobs)  start $(date +%T)"
xargs -P ${PAR:-10} -L 1 bash $CT/casemodel_dev_20261110/harness/run_qemu.sh < $jobs > $W/xargs.log 2>&1
echo "done $(date +%T)  ok=$(grep -c 'exit=0' $W/xargs.log) of $(wc -l < $jobs)"
python3 - "$@" <<'PY'
import sys
from pathlib import Path
CT = Path("/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy")
sys.path.insert(0, str(CT / "diverse_dev_20261110"))
import compare as C
C.HERE = CT / "relhint_dev_20261110"      # gen/cases_<g>.json in, runs/<g>/compare.json out
C.W = Path("/root/work/relhint")          # runs/<g>/<kernel>.run<i>.log
sys.argv = ["compare.py"] + sys.argv[1:]
C.main()
PY
for g in "$@"; do for f in $W/runs/$g/*.log; do grep -aq '^@@SH END' $f || echo "INCOMPLETE $f"; gzip -c $f > $R/runs/$g/$(basename $f).gz; done; done
