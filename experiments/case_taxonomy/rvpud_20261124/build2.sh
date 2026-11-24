# rvpud criteria2 二: R0, RF, X0 on 65e4fd942f72 (pfnmapdbg)
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
KB="python3 $REPO/tools/kbuild/kbuild.py"
$KB get 65e4fd942f72 riscv pfnmapdbg || exit $?
$KB get 65e4fd942f72 riscv pfnmapdbg --mut rvpud.json:F || exit $?
$KB get 65e4fd942f72 x86_64 pfnmapdbg || exit $?
for a in riscv x86_64; do echo "== $a"; grep -E "^CONFIG_(VFIO_NOIOMMU|VFIO_PCI|DEBUG_VM|DEBUG_VM_PGTABLE|PAGE_TABLE_CHECK|PAGE_TABLE_CHECK_ENFORCED|ARCH_SUPPORTS_PUD_PFNMAP|DYNAMIC_DEBUG)=" /root/work/kbuild/images/65e4fd942f72_${a}_pfnmapdbg_-.config; done
df -h /root | tail -1
