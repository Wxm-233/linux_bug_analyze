cd /root/repos/linux; R=df2908090cda
echo "== history of amd_get_mmconfig_range body"; git log -L '/^struct resource \*amd_get_mmconfig_range/,/^}/:arch/x86/kernel/amd_nb.c' --format='%h %cs %s' -s $R | head -12
echo "== introduced"; git log --format='%h %cs %s' -S'amd_get_mmconfig_range' $R | tail -3
echo "== FAM10H mask"; git grep -n "FAM10H_MMIO_CONF_BASE_MASK\|FAM10H_MMIO_CONF_BASE_SHIFT\|FAM10H_MMIO_CONF_BUSRANGE" $R -- arch/x86/include | head
echo "== amd_bus vars"; git show $R:arch/x86/pci/amd_bus.c | grep -n "fam10h_mmconf_start\|fam10h_mmconf_end\|fam10h_mmconf_res\|static.*fam10h" | head
echo "== resource_size_t"; git show $R:include/linux/types.h | grep -n -B2 -A3 "resource_size_t\|phys_addr_t;"
echo "== PHYS_ADDR_T_64BIT on x86"; git show $R:arch/x86/Kconfig | grep -n "PHYS_ADDR_T_64BIT"
git show $R:arch/x86/Kconfig | grep -n -A6 "^config AMD_NODE"
echo "== mmconf above 4G in 64-bit setup"; git grep -n "TOP_MEM2\|1ULL << 32\|4G" $R -- arch/x86/kernel/mmconf-fam10h_64.c | head
