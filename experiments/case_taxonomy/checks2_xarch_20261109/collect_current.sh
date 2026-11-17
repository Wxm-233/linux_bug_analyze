# Current version (v7.3-rc2): riscv target, x86_64 and arm64 counterparts.
B=/root/work/boundary_build; O=/root/work/checks2/current
H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/checks2_xarch_20261109
bash $H/collect_build.sh riscv $B/riscv_defconfig riscv $O /root/repos/linux
bash $H/collect_build.sh x86 $B/x86_64_defconfig x86 $O /root/repos/linux
bash $H/collect_build.sh arm64 $B/arm64_defconfig arm64 $O /root/repos/linux
ls -la $O/*.json.gz
