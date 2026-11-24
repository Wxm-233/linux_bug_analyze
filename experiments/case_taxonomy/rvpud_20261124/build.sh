# rvpud criteria 二/四: original + mutant F riscv pfnmap images
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
KB="python3 $REPO/tools/kbuild/kbuild.py"
$KB get df2908090cda riscv pfnmap || exit $?
$KB get df2908090cda riscv pfnmap --mut rvpud.json:F || exit $?
grep -E "VFIO|DYNAMIC_DEBUG=|PUD_PFNMAP|HUGEPAGE_PUD" /root/work/kbuild/images/df2908090cda_riscv_pfnmap_-.config
df -h /root | tail -1
