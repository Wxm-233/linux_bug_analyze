source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
O=/root/work/amdmmcfg/i386; mkdir -p $O
cd $KSRC && make -s O=$O ARCH=i386 LLVM=1 i386_defconfig >/dev/null 2>&1; echo rc=$?
for c in X86_32 X86_PAE HIGHMEM4G HIGHMEM64G PHYS_ADDR_T_64BIT AMD_NB AMD_NODE CPU_SUP_AMD PCI PNP PCI_MMCONFIG HIGHMEM; do printf "%s=%s\n" $c "$(grep -E "^CONFIG_$c=" $O/.config | cut -d= -f2)"; done
git -C $KSRC status --porcelain | wc -l
