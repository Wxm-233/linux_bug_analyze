# rvpud criteria2 amendment 1: rebuild R0, RF with STRICT_DEVMEM
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
KB="python3 $REPO/tools/kbuild/kbuild.py"
$KB get 65e4fd942f72 riscv pfnmapdbg --force || exit $?
$KB get 65e4fd942f72 riscv pfnmapdbg --mut rvpud.json:F --force || exit $?
for f in /root/work/kbuild/images/65e4fd942f72_riscv_pfnmapdbg_-.config /root/work/kbuild/images/65e4fd942f72_riscv_pfnmapdbg_rvpud-F.config; do echo "== $f"; grep -E "^CONFIG_(STRICT_DEVMEM|PAGE_TABLE_CHECK|PAGE_TABLE_CHECK_ENFORCED|DEBUG_VM_PGTABLE|VFIO_NOIOMMU)=" $f; done
df -h /root | tail -1
