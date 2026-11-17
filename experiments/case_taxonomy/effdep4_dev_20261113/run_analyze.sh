cd /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/effdep4_dev_20261113
for t in "$@"; do echo "== $t"; python3 effdep4_analyze.py $t; done
