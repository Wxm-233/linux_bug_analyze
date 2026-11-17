# Run each listed kernel 3 times (criteria section 3).
#   run_set2.sh <run tag> <name>=<arch>:<image> ...
set -uo pipefail
H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/difftest_known_20261109/harness
tag=$1; shift
O=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/difftest_known_20261109/runs/$tag
mkdir -p $O
for spec in "$@"; do
  name=${spec%%=*}; rest=${spec#*=}; arch=${rest%%:*}; img=${rest#*:}
  for i in 1 2 3; do bash $H/run_qemu2.sh $arch $img $O/$name.run$i.log; done
done
