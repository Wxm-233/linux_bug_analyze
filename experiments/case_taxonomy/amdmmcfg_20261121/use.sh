cd /root/repos/linux; R=df2908090cda
echo "== pnp quirk guard and registration"; git show $R:drivers/pnp/quirks.c | grep -n "CONFIG_AMD_NB\|quirk_amd_mmconfig_area\|#if\|#endif" | head -20
echo "== amd_bus types and caller"; git show $R:arch/x86/pci/amd_bus.c | grep -n "u64 \|fam10h_mmconf\|static int __init\|early_root_info_init\|amd_postcore_init\|x86_init\|^postcore_initcall\|CONFIG_X86_64\|range\[" | head -40
echo "== mask defs"; git grep -n "FAM10H_MMIO_CONF" $R -- arch/x86/include/asm/msr-index.h
echo "== pnp_add_mem_resource sig"; git grep -n "pnp_add_mem_resource(struct" $R -- drivers/pnp include | head -3
