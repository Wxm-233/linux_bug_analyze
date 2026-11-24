# 复核材料：交换项编解码（8 条）

内核版本 `df2908090cda`（v7.3-rc2）。读源码：

```
wsl -u root -- git -C /root/repos/linux show df2908090cda:<路径>
```

各构建的 `.config`（只生成了头文件的配置变体，没有完整编译）：

| 构建 | 配置来源 | `.config` 路径 |
|---|---|---|
| arm_lpae | `multi_v7_defconfig` + `CONFIG_ARM_LPAE=y` | `/root/work/swapsym/cfg_arm_lpae/.config` |
| arm | `multi_v7_defconfig` | `/root/work/swapsym/cfg_arm/.config` |
| mips32xpa | `maltaup_xpa_defconfig` | `/root/work/swapsym/cfg_mips32xpa/.config` |
| mips64 | `64r6el_defconfig` | `/root/work/swapsym/cfg_mips64/.config` |
| ppc44x | `ppc44x_defconfig` | `/root/work/swapsym/cfg_ppc44x/.config` |
| i386_pae | `i386_defconfig` + `CONFIG_X86_PAE=y` | `/root/work/swapsym/cfg_i386_pae/.config` |
| x86_64 | `x86_64_defconfig` | `/root/work/boundary_build/x86_64_defconfig/.config` |
| loongarch | `loongarch` 的 `defconfig` | `/root/work/swapsym/cfg_loongarch/.config` |

## 共同背景（公共层）

- `include/linux/swapops.h`：交换项的公共表示（`swp_entry`、`swp_type`、`swp_offset`，约 28-121 行）；`SWP_PFN_BITS`、`SWP_PFN_MASK`（约 31-43 行）；`swp_entry_to_pte`（约 115-121 行）；迁移项等的构造（约 137-261 行）。
- `include/linux/leafops.h`：`softleaf_from_pte`（约 55-65 行）、`softleaf_type`（约 160-200 行）、`softleaf_has_pfn`、`softleaf_to_pfn`（约 355-384 行）、`softleaf_from_pmd` / `pmd_is_valid_softleaf`（约 85-110、643-657 行）。
- 迁移项的使用者举例：`mm/migrate.c` 的 `remove_migration_pte`、`mm/page_vma_mapped.c` 的 `check_pte`、`mm/memory.c` 的 `do_swap_page`→`migration_entry_wait`、`fs/proc/task_mmu.c` 的 pagemap。
- 4K 页时，物理地址 = 页帧号 × 4096。

## R1～R6：PFN 类交换项（迁移项、hwpoison、设备私有项）的页帧号能否被各架构的交换项编码保持

对每个构建回答：
1. 该配置下 `SWP_PFN_BITS` 是多少（看 `MAX_PHYSMEM_BITS` 是否定义、`phys_addr_t` 的宽度、`PAGE_SHIFT`）；
2. 架构把公共交换项编码进页表项（`__swp_entry`、`__swp_entry_to_pte`）再解码（`__pte_to_swp_entry`、`__swp_type`、`__swp_offset`）后，偏移能原样保持多少位；
3. 如果 2 小于 1：会被截断的页帧号对应的物理地址，在这个配置/这类平台上能否真的存在内存（例如架构允许的物理地址位宽、内存模型 flatmem/sparsemem 对可用内存的限制、已知平台）；
4. 截断如果发生，对使用者有什么后果。

| 编号 | 构建 | 架构交换项编码的位置（约） |
|---|---|---|
| R1 | arm_lpae | `arch/arm/include/asm/pgtable.h` 270-293 行；另看 `arch/arm/include/asm/sparsemem.h`、`arch/arm/mm/Kconfig` 的 `ARM_LPAE`、`arch/arm/Kconfig` 的内存模型选项 |
| R2 | mips32xpa | `arch/mips/include/asm/pgtable-32.h` 约 222-250 行（`CONFIG_XPA` 分支）；另看 `arch/mips/include/asm/sparsemem.h` |
| R3 | ppc44x | `arch/powerpc/include/asm/nohash/32/pgtable.h` 约 185-200 行；物理地址宽度看 `CONFIG_PHYS_64BIT`、44x 的说明 |
| R4 | mips64 | `arch/mips/include/asm/pgtable-64.h` 约 330-350 行 |
| R5 | i386_pae | `arch/x86/include/asm/pgtable-3level.h` 约 164-205 行 |
| R6 | arm | 同 R1 的编码位置，但不开 LPAE |

## R7：x86_64 上原生测试的输入

`mm/debug_vm_pgtable.c` 1228-1233 行在 `init_args` 里构造所有交换项测试共用的输入（注释说要探出最大偏移）。请判断：在 `x86_64_defconfig` 下，这里得到的 `max_swap_offset` 实际是多少？是否是它想测的最大偏移？对照 `mm/swapfile.c` 的 `generic_max_swapfile_size()`（约 3449-3462 行）和 x86_64 的编码（`arch/x86/include/asm/pgtable_64.h` 约 180-238 行）、`pte_none`/`pte_present` 的定义。若有问题，是什么时候引入的（可以用 `git log -L`）。

## R8：loongarch 上原生 PMD 测试

`mm/debug_vm_pgtable.c` 的 `pmd_softleaf_tests`（约 822-840 行）用 `args->leaf_entry = make_writable_migration_entry(~0UL)`（约 1233 行）作输入，检查 `pmd_is_valid_softleaf(softleaf_to_pmd(...))`。请判断：在 loongarch `defconfig`（16K 页、3 级页表）下这条断言是否成立？如果不成立，原因是什么？这个输入在真实使用中是否合法？对照 `arch/loongarch/include/asm/pgtable.h`（约 248-275、329-350 行）和 `arch/loongarch/include/asm/pgtable-bits.h`。若有问题，是什么时候引入的。
