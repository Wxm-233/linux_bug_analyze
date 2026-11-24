#!/bin/bash
# Regenerate and keep the header variants of the 9 parents after parent6.sh (which deleted them); drop only the source copies.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/ecbuild_20261122
for h in 018e9828eb52 6f74c0ec2095 144bb0aee33a e0fe5ab4192c 5d9cea8a552e ddc1729b07cc 23bc8f69f0ec fba88ede6a31 ff1712f953e2; do
  p=$(git -C $KSRC rev-parse --short=12 $h^)
  bash mkvariants2.sh $p > logs/keep_status_$p.txt 2>&1
  rm -rf /root/work/ecver/$p/src
  echo "$p builds $(grep -c ' ok ' logs/keep_status_$p.txt) same_as_run $(diff <(grep -E ' (ok|fail|skip|mismatch)' logs/status_$p.txt | awk '{print $1,$2}' | sort) <(grep -E ' (ok|fail|skip|mismatch)' logs/keep_status_$p.txt | awk '{print $1,$2}' | sort) >/dev/null && echo yes || echo NO)"
done
echo "space $(df -h / | awk 'NR==2{print $4" free of "$2}') ecver $(du -sh /root/work/ecver | cut -f1)"
