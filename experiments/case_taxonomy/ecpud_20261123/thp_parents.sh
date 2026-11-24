#!/bin/bash
# ecpud 三: add the riscv64_thp variant to the 9 parents (other variants were kept by ecbuild); drop the source copy afterwards.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/ecpud_20261123
mkdir -p logs
for h in 018e9828eb52 6f74c0ec2095 144bb0aee33a e0fe5ab4192c 5d9cea8a552e ddc1729b07cc 23bc8f69f0ec fba88ede6a31 ff1712f953e2; do
  p=$(git -C $KSRC rev-parse --short=12 $h^)
  bash mkvariants3.sh $p riscv64_thp > logs/thp_$p.txt 2>&1
  rm -rf /root/work/ecver/$p/src
  echo "$p $(grep '^riscv64_thp' /root/work/ecver/$p/status.txt | tail -1) pudthp=$(grep -c 'HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD=y' /root/work/ecver/$p/cfg_riscv64_thp/.config 2>/dev/null)"
done
echo "space $(df -h / | awk 'NR==2{print $4" free of "$2}') ecver $(du -sh /root/work/ecver | cut -f1)"
