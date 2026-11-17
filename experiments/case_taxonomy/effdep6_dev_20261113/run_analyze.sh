cd /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/effdep6_dev_20261113
for t in "$@"; do echo "== $t"; python3 effdep6_analyze.py $t; done
