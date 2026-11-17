source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd /root/repos/linux
echo "== x86 access_ok"; grep -n "valid_user_address\|USER_PTR_MAX" arch/x86/include/asm/uaccess_64.h | head -12
echo "== arm64 fcntl"; grep -n "O_DIRECT\|O_DIRECTORY" arch/arm64/include/uapi/asm/fcntl.h include/uapi/asm-generic/fcntl.h
echo "== arm64 prot"; grep -n "PROT_BTI\|PROT_MTE" arch/arm64/include/uapi/asm/mman.h
echo "== prctl"; grep -n "PR_SME_SET_VL\b\|PR_SME_GET_VL\b\|PR_SVE_SET_VL\b" include/uapi/linux/prctl.h
echo "== mincore"; grep -n "access_ok\|untagged_addr\|ENOMEM\|EFAULT\|EINVAL" mm/mincore.c | tail -12
echo "== listmount"; grep -n "access_ok\|E2BIG\|copy_mnt_id_req\|EFAULT" fs/namespace.c | sed -n 1,40p
echo "== riscv syscall nr"; sed -n 330,350p arch/riscv/kernel/traps.c
echo "== arm64 scno"; grep -n "scno" arch/arm64/kernel/syscall.c | head -12
echo "== cfg"; grep -n "CONFIG_ARM64_VA_BITS=\|CONFIG_ARM64_TAGGED_ADDR_ABI\|CONFIG_ARM64_SME=\|CONFIG_ARM64_BTI=" /root/work/boundary_build/arm64_defconfig/.config
