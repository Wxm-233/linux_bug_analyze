# Full fact extraction for the listed trees (criteria 4.1-4.2).   extract_all.sh <tag>...   (tag: <ID>_pre | CUR)
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/semhint_dev_20261109/static
mkdir -p /root/work/semhint/facts
for t in "$@"; do
  if [ $t = CUR ]; then cc=/root/work/boundary_build/riscv_defconfig/compile_commands.json; root=/root/repos/linux
  else cc=/root/work/semhint/cc/$t.json; root=/root/work/difftest/src/$t; fi
  s=$(date +%s)
  python3 $H/extract.py $cc $root /root/work/semhint/facts/$t.json.gz --jobs ${JOBS:-8} 2>&1 | tail -3
  echo "$t rc=$? seconds=$(( $(date +%s) - s ))"
done
free -g | head -2; df -h / | tail -1
echo ALL_DONE
