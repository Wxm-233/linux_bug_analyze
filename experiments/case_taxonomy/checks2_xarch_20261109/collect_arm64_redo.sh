# amendment 1: redo the current arm64 collect with the corrected nomd.py
O=/root/work/checks2/current
rm -rf $O/cdb_arm64 $O/scope_arm64.txt $O/facts_arm64.json $O/facts_arm64.json.gz $O/collect_arm64.log
bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/checks2_xarch_20261109/collect_build.sh arm64 /root/work/boundary_build/arm64_defconfig arm64 $O /root/repos/linux
ls -la $O/*.json.gz
