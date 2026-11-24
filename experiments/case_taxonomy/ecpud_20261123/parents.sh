#!/bin/bash
# ecpud 三: parents (re-mine riscv64_thp / ppc64le / ppc64le_hash, reuse the rest from v6) and fixed runs, then recall.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/ecpud_20261123
mkdir -p logs
for h in 018e9828eb52 6f74c0ec2095 144bb0aee33a e0fe5ab4192c 5d9cea8a552e ddc1729b07cc 23bc8f69f0ec fba88ede6a31 ff1712f953e2; do
  p=$(git -C $KSRC rev-parse --short=12 $h^)
  bash ../ecbuild_20261122/ensure_src.sh $p > /dev/null
  python3 ec7.py parent $h > logs/parent_$h.log 2>&1
  rm -rf /root/work/ecver/$p/src
  echo "$h parent $p $(grep -a 'EC4 '$p' ' logs/parent_$h.log | grep -o '"laws": [0-9]*, "deviations": [0-9]*') $(grep -a 'EC4 '$h'-fixed' logs/parent_$h.log | grep -o '"deviations": [0-9]*')"
done
python3 ec7.py recall > logs/recall.log 2>&1
grep -a RECALL7 logs/recall.log | cut -c1-300
echo "space $(df -h / | awk 'NR==2{print $4" free of "$2}')"
