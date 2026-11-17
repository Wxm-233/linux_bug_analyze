# Re-export the pre-fix trees and run extract3f.py on the 6 dev trees (fieldhint criteria 二.1, 二.2). Runs in WSL.
#   bash export_extract.sh [--only REGEX] <tree>...       trees: A101_pre ... B467_pre CUR
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
R=$REPO/experiments/case_taxonomy/fieldhint_dev_20261111; O=/root/work/fieldhint/facts; mkdir -p $O
declare -A FIX=([A101]=2116988d5372 [A310]=61119394631f [A171]=890ba5be6335 [A181]=1046791390af [B467]=c625154993d0)
only=""; [ "$1" = --only ] && { only="--only $2"; shift 2; }
for t in "$@"; do
  if [ $t = CUR ]; then cc=$KBUILD/riscv_defconfig/compile_commands.json; root=/root/repos/linux
  else id=${t%_pre}; root=/root/work/difftest/src/$t; cc=/root/work/semhint/cc/$t.json
       [ -f $root/Makefile ] || { mkdir -p $root; git -C $KSRC archive "${FIX[$id]}^" | tar -x -C $root; }; fi
  s=$(date +%s)
  PYTHONDONTWRITEBYTECODE=1 python3 $R/static/extract3f.py $cc $root $O/$t.json.gz --jobs 16 $only 2>&1 | tail -1
  echo "$t extract rc=$? $(( $(date +%s) - s ))s"
done
