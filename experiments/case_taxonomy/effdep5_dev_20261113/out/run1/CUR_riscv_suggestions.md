# 人工分析建议（纵向信号）：CUR_riscv

接口 9002 个；纵向候选 189 个，其中有横向差异的 14 个（只用于排序，不是判错依据）。以下为前 50 条。

## 1. `check_struct_ops_btf_id` 调用 `bpf_jit_supports_private_stack` 后跳过 `verbose`（kernel/bpf/verifier.c:19787）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`env` 在 `check_struct_ops_btf_id` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `bpf_jit_supports_private_stack` 后把 `i` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `env` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 19787 行调用 `bpf_jit_supports_private_stack` 后，第 19793 行把 `i` 设为 `0`；第 19800 行的 `verbose`（mem 类效果）受 `i` 控制
- 横向：`bpf_jit_supports_private_stack` 平凡定义的架构 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k；非平凡的 powerpc（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`bpf_jit_supports_private_stack` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 3.7856

## 2. `select_fallback_rq` 调用 `task_cpu_fallback_mask` 后跳过 `__printk_ratelimit`（kernel/sched/core.c:3595）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`（资源未识别）` 在 `select_fallback_rq` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `task_cpu_fallback_mask` 后把 `state` 设为 `fail`，不再自己保证
- 动态阶段可检查：后续使用 `该资源` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 3595 行调用 `task_cpu_fallback_mask` 后，第 3596 行把 `state` 设为 `fail`；第 3611 行的 `__printk_ratelimit`（mem 类效果）受 `state` 控制
- 横向：`task_cpu_fallback_mask` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`task_cpu_fallback_mask` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 3.0

## 3. `acpi_os_read_memory` 调用 `acpi_os_ioremap` 后跳过 `rcu_read_unlock`（drivers/acpi/osl.c:758）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`（资源未识别）` 在 `acpi_os_read_memory` 之后被使用或发布之前，必须写入已排序、已写入（清零或初始化）；公共层在调用 `acpi_os_ioremap` 后把 `unmap` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `该资源` 时，它是否写入已排序、已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 758 行调用 `acpi_os_ioremap` 后，第 761 行把 `unmap` 设为 `true`；第 773 行的 `rcu_read_unlock`（barrier+mem 类效果）受 `unmap` 控制
- 横向：`acpi_os_ioremap` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`acpi_os_ioremap` 是否产生了“写入已排序、已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 2.25

## 4. `acpi_os_write_memory` 调用 `acpi_os_ioremap` 后跳过 `rcu_read_unlock`（drivers/acpi/osl.c:789）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`（资源未识别）` 在 `acpi_os_write_memory` 之后被使用或发布之前，必须写入已排序、已写入（清零或初始化）；公共层在调用 `acpi_os_ioremap` 后把 `unmap` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `该资源` 时，它是否写入已排序、已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 789 行调用 `acpi_os_ioremap` 后，第 792 行把 `unmap` 设为 `true`；第 815 行的 `rcu_read_unlock`（barrier+mem 类效果）受 `unmap` 控制
- 横向：`acpi_os_ioremap` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`acpi_os_ioremap` 是否产生了“写入已排序、已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 2.25

## 5. `gen_kfunc_arg_proto` 调用 `bpf_jit_supports_stack_args` 后跳过 `is_kfunc_arg_prog_aux`（kernel/bpf/verifier.c:12075）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`args、btf` 在 `gen_kfunc_arg_proto` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `bpf_jit_supports_stack_args` 后把 `i` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `args、btf` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 12075 行调用 `bpf_jit_supports_stack_args` 后，第 12081 行把 `i` 设为 `0`；第 12082 行的 `is_kfunc_arg_prog_aux`（mem 类效果）受 `i` 控制
- 横向：`bpf_jit_supports_stack_args` 平凡定义的架构 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k；非平凡的 无
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`bpf_jit_supports_stack_args` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 1.8928

## 6. `vmemmap_split_pmd` 调用 `pte_alloc_one_kernel` 后跳过 `set_ptes`（mm/hugetlb_vmemmap.c:60）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`addr、entry、init_mm、pte` 在 `vmemmap_split_pmd` 之后被使用或发布之前，必须写入已排序、缓存已同步、已写入（清零或初始化）、页表项已设置；公共层在调用 `pte_alloc_one_kernel` 后把 `i` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `addr、entry、init_mm、pte` 时，它是否写入已排序、缓存已同步、已写入（清零或初始化）、页表项已设置（各架构分别检查性质，不比较架构间差异）
- 依据：第 60 行调用 `pte_alloc_one_kernel` 后，第 66 行把 `i` 设为 `0`；第 72 行的 `set_ptes`（barrier+cache+mem+pgtable 类效果）受 `i` 控制
- 横向：`pte_alloc_one_kernel` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`pte_alloc_one_kernel` 是否产生了“写入已排序、缓存已同步、已写入（清零或初始化）、页表项已设置”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 1.8928

## 7. `hugetlb_fault` 调用 `update_mmu_cache` 后跳过 `vma_end_read`（mm/hugetlb.c:6132）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`vma` 在 `hugetlb_fault` 之后被使用或发布之前，必须写入已排序；公共层在调用 `update_mmu_cache` 后把 `ret` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `vma` 时，它是否写入已排序（各架构分别检查性质，不比较架构间差异）
- 依据：第 6132 行调用 `update_mmu_cache` 后，第 6135 行把 `ret` 设为 `0`；第 6213 行的 `vma_end_read`（barrier 类效果）受 `ret` 控制
- 横向：`update_mmu_cache` 平凡定义的架构 alpha、s390、um、x86；非平凡的 arc、arm、arm64、csky、hexagon、loongarch、m68k、microblaze（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`update_mmu_cache` 是否产生了“写入已排序”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 1.5759

## 8. `efi_earlycon_setup` 调用 `memset32` 后跳过 `efi_earlycon_scroll_up`（drivers/firmware/efi/earlycon.c:260）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`si` 在 `efi_earlycon_setup` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `memset32` 后把 `i` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `si` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 260 行调用 `memset32` 后，第 268 行把 `i` 设为 `0`；第 269 行的 `efi_earlycon_scroll_up`（mem 类效果）受 `i` 控制
- 横向：`memset32` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`memset32` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 1.5

## 9. `clear_highpages_kasan_tagged` 调用 `clear_pages` 后跳过 `clear_highpage_kasan_tagged`（mm/page_alloc.c:1225）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`page` 在 `clear_highpages_kasan_tagged` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `clear_pages` 后把 `i` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `page` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 1225 行调用 `clear_pages` 后，第 1229 行把 `i` 设为 `0`；第 1230 行的 `clear_highpage_kasan_tagged`（mem 类效果）受 `i` 控制
- 横向：`clear_pages` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`clear_pages` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 1.5

## 10. `hugetlb_fault` 调用 `update_mmu_cache_range` 后跳过 `vma_end_read`（mm/hugetlb.c:6132）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`vma` 在 `hugetlb_fault` 之后被使用或发布之前，必须写入已排序；公共层在调用 `update_mmu_cache_range` 后把 `ret` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `vma` 时，它是否写入已排序（各架构分别检查性质，不比较架构间差异）
- 依据：第 6132 行调用 `update_mmu_cache_range` 后，第 6135 行把 `ret` 设为 `0`；第 6213 行的 `vma_end_read`（barrier 类效果）受 `ret` 控制
- 横向：`update_mmu_cache_range` 平凡定义的架构 alpha、arm64、hexagon、m68k、microblaze、s390、um、x86；非平凡的 arc、arm、csky、loongarch、mips、nios2、openrisc、parisc（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`update_mmu_cache_range` 是否产生了“写入已排序”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 1.3086

## 11. `vmemmap_split_pmd` 调用 `pmd_populate_kernel` 后跳过 `set_ptes`（mm/hugetlb_vmemmap.c:64）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`addr、entry、init_mm、pte` 在 `vmemmap_split_pmd` 之后被使用或发布之前，必须写入已排序、缓存已同步、已写入（清零或初始化）、页表项已设置；公共层在调用 `pmd_populate_kernel` 后把 `i` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `addr、entry、init_mm、pte` 时，它是否写入已排序、缓存已同步、已写入（清零或初始化）、页表项已设置（各架构分别检查性质，不比较架构间差异）
- 依据：第 64 行调用 `pmd_populate_kernel` 后，第 66 行把 `i` 设为 `0`；第 72 行的 `set_ptes`（barrier+cache+mem+pgtable 类效果）受 `i` 控制
- 横向：`pmd_populate_kernel` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`pmd_populate_kernel` 是否产生了“写入已排序、缓存已同步、已写入（清零或初始化）、页表项已设置”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 1.292

## 12. `__pte_alloc_kernel` 调用 `pmd_populate_kernel` 后跳过 `pte_free_kernel`（mm/memory.c:472）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`init_mm` 在 `__pte_alloc_kernel` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `pmd_populate_kernel` 后把 `new` 设为 ``，不再自己保证
- 动态阶段可检查：后续使用 `init_mm` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 472 行调用 `pmd_populate_kernel` 后，第 473 行把 `new` 设为 ``；第 477 行的 `pte_free_kernel`（mem 类效果）受 `new` 控制
- 横向：`pmd_populate_kernel` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`pmd_populate_kernel` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 1.292

## 13. `do_swap_page` 调用 `pte_modify` 后跳过 `do_wp_page`（mm/memory.c:5175）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`vmf` 在 `do_swap_page` 之后被使用或发布之前，必须写入已排序、缓存已同步、已写入（清零或初始化）、页表项已设置、TLB 已刷新；公共层在调用 `pte_modify` 后把 `rwp_restore` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `vmf` 时，它是否写入已排序、缓存已同步、已写入（清零或初始化）、页表项已设置、TLB 已刷新（各架构分别检查性质，不比较架构间差异）
- 依据：第 5175 行调用 `pte_modify` 后，第 5176 行把 `rwp_restore` 设为 `true`；第 5256 行的 `do_wp_page`（barrier+cache+mem+pgtable+tlb 类效果）受 `rwp_restore` 控制
- 横向：`pte_modify` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`pte_modify` 是否产生了“写入已排序、缓存已同步、已写入（清零或初始化）、页表项已设置、TLB 已刷新”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 1.125

## 14. `iommu_get_default_domain_type` 调用 `static_assert` 后跳过 `___ratelimit`（drivers/iommu/iommu.c:1895）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`_rs` 在 `iommu_get_default_domain_type` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `static_assert` 后把 `driver_type` 设为 ``，不再自己保证
- 动态阶段可检查：后续使用 `_rs` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 1895 行调用 `static_assert` 后，第 1897 行把 `driver_type` 设为 ``；第 1929 行的 `___ratelimit`（mem 类效果）受 `driver_type` 控制
- 横向：`static_assert` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`static_assert` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 1.0686

## 15. `hugetlb_fault` 调用 `set_huge_pte_at` 后跳过 `vma_end_read`（mm/hugetlb.c:6130）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`vma` 在 `hugetlb_fault` 之后被使用或发布之前，必须写入已排序；公共层在调用 `set_huge_pte_at` 后把 `ret` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `vma` 时，它是否写入已排序（各架构分别检查性质，不比较架构间差异）
- 依据：第 6130 行调用 `set_huge_pte_at` 后，第 6135 行把 `ret` 设为 `0`；第 6213 行的 `vma_end_read`（barrier 类效果）受 `ret` 控制
- 横向：`set_huge_pte_at` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`set_huge_pte_at` 是否产生了“写入已排序”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.9815

## 16. `__irq_set_trigger` 调用 `mask_irq` 后跳过 `unmask_irq`（kernel/irq/manage.c:944）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`desc` 在 `__irq_set_trigger` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `mask_irq` 后把 `unmask` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `desc` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 944 行调用 `mask_irq` 后，第 946 行把 `unmask` 设为 `1`；第 977 行的 `unmask_irq`（mem 类效果）受 `unmask` 控制
- 横向：`mask_irq` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`mask_irq` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.9464

## 17. `sha256_block_generic` 调用 `LOAD_OP` 后跳过 `BLEND_OP`（lib/crypto/sha256.c:94）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`W` 在 `sha256_block_generic` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `LOAD_OP` 后把 `i` 设为 `16`，不再自己保证
- 动态阶段可检查：后续使用 `W` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 94 行调用 `LOAD_OP` 后，第 102 行把 `i` 设为 `16`；第 103 行的 `BLEND_OP`（mem 类效果）受 `i` 控制
- 横向：`LOAD_OP` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`LOAD_OP` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.9464

## 18. `memtest` 调用 `__va` 后跳过 `reserve_bad_mem`（mm/memtest.c:48）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`last_bad、pattern` 在 `memtest` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `__va` 后把 `start_bad` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `last_bad、pattern` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 48 行调用 `__va` 后，第 50 行把 `start_bad` 设为 `0`；第 66 行的 `reserve_bad_mem`（mem 类效果）受 `start_bad` 控制
- 横向：`__va` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`__va` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.9031

## 19. `do_swap_page` 调用 `pte_same` 后跳过 `count_vm_event`（mm/memory.c:4980）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`（资源未识别）` 在 `do_swap_page` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `pte_same` 后把 `folio` 设为 ``，不再自己保证
- 动态阶段可检查：后续使用 `该资源` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 4980 行调用 `pte_same` 后，第 4983 行把 `folio` 设为 ``；第 4989 行的 `count_vm_event`（mem 类效果）受 `folio` 控制
- 横向：`pte_same` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`pte_same` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.8921

## 20. `handler_chain` 调用 `handler` 后跳过 `down_read`（kernel/events/uprobes.c:2562）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`uprobe` 在 `handler_chain` 之后被使用或发布之前，必须已写入（清零或初始化）、已登记；公共层在调用 `handler` 后把 `has_consumers` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `uprobe` 时，它是否已写入（清零或初始化）、已登记（各架构分别检查性质，不比较架构间差异）
- 依据：第 2562 行调用 `handler` 后，第 2568 行把 `has_consumers` 设为 `true`；第 2585 行的 `down_read`（mem+register 类效果）受 `has_consumers` 控制
- 横向：`handler` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`handler` 是否产生了“已写入（清零或初始化）、已登记”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.8107

## 21. `__slab_free` 调用 `spin_unlock_irqrestore` 后跳过 `slab_update_freelist`（mm/slub.c:5730）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`new、old、s、slab` 在 `__slab_free` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `spin_unlock_irqrestore` 后把 `n` 设为 ``，不再自己保证
- 动态阶段可检查：后续使用 `new、old、s、slab` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 5730 行调用 `spin_unlock_irqrestore` 后，第 5731 行把 `n` 设为 ``；第 5766 行的 `slab_update_freelist`（mem 类效果）受 `n` 控制
- 横向：`spin_unlock_irqrestore` 平凡定义的架构 parisc；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`spin_unlock_irqrestore` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.7778

## 22. `__calc_tpm2_event_size` 调用 `memcmp` 后跳过 `memcpy`（include/linux/tpm_eventlog.h:226）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`halg、halg_size、mapping` 在 `__calc_tpm2_event_size` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `memcmp` 后把 `i` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `halg、halg_size、mapping` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 226 行调用 `memcmp` 后，第 233 行把 `i` 设为 `0`；第 250 行的 `memcpy`（mem 类效果）受 `i` 控制
- 横向：`memcmp` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`memcmp` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.6662

## 23. `__rb_get_reader_page` 调用 `arch_spin_unlock` 后跳过 `smp_rmb`（kernel/trace/ring_buffer.c:6025）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`（资源未识别）` 在 `__rb_get_reader_page` 之后被使用或发布之前，必须写入已排序；公共层在调用 `arch_spin_unlock` 后把 `nr_loops` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `该资源` 时，它是否写入已排序（各架构分别检查性质，不比较架构间差异）
- 依据：第 6025 行调用 `arch_spin_unlock` 后，第 6033 行把 `nr_loops` 设为 `0`；第 6041 行的 `smp_rmb`（barrier 类效果）受 `nr_loops` 控制
- 横向：`arch_spin_unlock` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`arch_spin_unlock` 是否产生了“写入已排序”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.6543

## 24. `HUF_sort` 调用 `assert` 后跳过 `HUF_simpleQuickSort`（lib/zstd/compress/huf_compress.c:631）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`bucketSize、huffNode` 在 `HUF_sort` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `assert` 后把 `n` 设为 `192 typedef struct { huffNodeTable huffN`，不再自己保证
- 动态阶段可检查：后续使用 `bucketSize、huffNode` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 631 行调用 `assert` 后，第 637 行把 `n` 设为 `192 typedef struct { huffNodeTable huffN`；第 658 行的 `HUF_simpleQuickSort`（mem 类效果）受 `n` 控制
- 横向：`assert` 平凡定义的架构 mips；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`assert` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.6181

## 25. `ZSTD_copyBlockSequences` 调用 `assert` 后跳过 `ZSTD_updateRep`（lib/zstd/compress/zstd_compress.c:3358）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`inSeqs、repcodes` 在 `ZSTD_copyBlockSequences` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `assert` 后把 `i` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `inSeqs、repcodes` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 3358 行调用 `assert` 后，第 3365 行把 `i` 设为 `0`；第 3404 行的 `ZSTD_updateRep`（mem 类效果）受 `i` 控制
- 横向：`assert` 平凡定义的架构 mips；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`assert` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.6181

## 26. `ZSTD_compressBlock_splitBlock_internal` 调用 `assert` 后跳过 `ZSTD_deriveSeqStoreChunk`（lib/zstd/compress/zstd_compress.c:4223）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`nextSeqStore、partitions、zc` 在 `ZSTD_compressBlock_splitBlock_internal` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `assert` 后把 `i` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `nextSeqStore、partitions、zc` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 4223 行调用 `assert` 后，第 4229 行把 `i` 设为 `0`；第 4241 行的 `ZSTD_deriveSeqStoreChunk`（mem 类效果）受 `i` 控制
- 横向：`assert` 平凡定义的架构 mips；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`assert` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.6181

## 27. `ZSTD_compressStream_generic` 调用 `assert` 后跳过 `ZSTD_CCtx_reset`（lib/zstd/compress/zstd_compress.c:6149）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`zcs` 在 `ZSTD_compressStream_generic` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `assert` 后把 `someMoreWork` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `zcs` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 6149 行调用 `assert` 后，第 6150 行把 `someMoreWork` 设为 `0`；第 6157 行的 `ZSTD_CCtx_reset`（mem 类效果）受 `someMoreWork` 控制
- 横向：`assert` 平凡定义的架构 mips；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`assert` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.6181

## 28. `ZSTD_convertBlockSequences` 调用 `assert` 后跳过 `ZSTD_storeSeqOnly`（lib/zstd/compress/zstd_compress.c:7141）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`cctx、litLength、matchLength、offBase` 在 `ZSTD_convertBlockSequences` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `assert` 后把 `seqNb` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `cctx、litLength、matchLength、offBase` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 7141 行调用 `assert` 后，第 7147 行把 `seqNb` 设为 `0`；第 7154 行的 `ZSTD_storeSeqOnly`（mem 类效果）受 `seqNb` 控制
- 横向：`assert` 平凡定义的架构 mips；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`assert` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.6181

## 29. `ZSTD_compressSubBlock_multi` 调用 `assert` 后跳过 `ZSTD_compressSubBlock`（lib/zstd/compress/zstd_compress_superblock.c:536）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`bmi2、cctxParams、entropyMetadata、litEntropyWritten、litSize、llCodePtr、lp、mlCodePtr、nextCBlock、oend、ofCodePtr、op、seqCount、seqEntropyWritten、sp、writeLitEntropy、writeSeqEntropy` 在 `ZSTD_compressSubBlock_multi` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `assert` 后把 `n` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `bmi2、cctxParams、entropyMetadata、litEntropyWritten、litSize、llCodePtr、lp、mlCodePtr、nextCBlock、oend、ofCodePtr、op、seqCount、seqEntropyWritten、sp、writeLitEntropy、writeSeqEntropy` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 536 行调用 `assert` 后，第 537 行把 `n` 设为 `0`；第 551 行的 `ZSTD_compressSubBlock`（mem 类效果）受 `n` 控制
- 横向：`assert` 平凡定义的架构 mips；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`assert` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.6181

## 30. `ZSTD_ldm_generateSequences` 调用 `assert` 后跳过 `ZSTD_window_correctOverflow`（lib/zstd/compress/zstd_ldm.c:543）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`chunkStart、ldmState、maxDist` 在 `ZSTD_ldm_generateSequences` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `assert` 后把 `chunk` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `chunkStart、ldmState、maxDist` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 543 行调用 `assert` 后，第 549 行把 `chunk` 设为 `0`；第 562 行的 `ZSTD_window_correctOverflow`（mem 类效果）受 `chunk` 控制
- 横向：`assert` 平凡定义的架构 mips；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`assert` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.6181

## 31. `HUF_decompress4X1_usingDTable_internal_fast` 调用 `assert` 后跳过 `HUF_initRemainingDStream`（lib/zstd/decompress/huf_decompress.c:866）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`args、bit、segmentEnd` 在 `HUF_decompress4X1_usingDTable_internal_fast` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `assert` 后把 `i` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `args、bit、segmentEnd` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 866 行调用 `assert` 后，第 874 行把 `i` 设为 `0`；第 880 行的 `HUF_initRemainingDStream`（mem 类效果）受 `i` 控制
- 横向：`assert` 平凡定义的架构 mips；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`assert` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.6181

## 32. `HUF_decompress4X2_usingDTable_internal_fast` 调用 `assert` 后跳过 `HUF_initRemainingDStream`（lib/zstd/decompress/huf_decompress.c:1691）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`args、bit、segmentEnd` 在 `HUF_decompress4X2_usingDTable_internal_fast` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `assert` 后把 `i` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `args、bit、segmentEnd` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 1691 行调用 `assert` 后，第 1699 行把 `i` 设为 `0`；第 1705 行的 `HUF_initRemainingDStream`（mem 类效果）受 `i` 控制
- 横向：`assert` 平凡定义的架构 mips；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`assert` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.6181

## 33. `ZSTD_decompressStream` 调用 `assert` 后跳过 `ZSTD_decompressBegin_usingDDict`（lib/zstd/decompress/zstd_decompress.c:2088）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`zds` 在 `ZSTD_decompressStream` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `assert` 后把 `someMoreWork` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `zds` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 2088 行调用 `assert` 后，第 2093 行把 `someMoreWork` 设为 `0`；第 2107 行的 `ZSTD_decompressBegin_usingDDict`（mem 类效果）受 `someMoreWork` 控制
- 横向：`assert` 平凡定义的架构 mips；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`assert` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.6181

## 34. `alloc_thread_stack_node_from_cache` 调用 `numa_node_id` 后跳过 `arch_local_irq_save`（kernel/fork.c:229）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`（资源未识别）` 在 `alloc_thread_stack_node_from_cache` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `numa_node_id` 后把 `i` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `该资源` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 229 行调用 `numa_node_id` 后，第 232 行把 `i` 设为 `0`；第 233 行的 `arch_local_irq_save`（mem 类效果）受 `i` 控制
- 横向：`numa_node_id` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`numa_node_id` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.6175

## 35. `acpi_ut_get_expected_return_types` 调用 `strcpy` 后跳过 `strcat`（drivers/acpi/acpica/utpredef.c:117）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`buffer、ut_rtype_names` 在 `acpi_ut_get_expected_return_types` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `strcpy` 后把 `this_rtype` 设为 ``，不再自己保证
- 动态阶段可检查：后续使用 `buffer、ut_rtype_names` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 117 行调用 `strcpy` 后，第 123 行把 `this_rtype` 设为 ``；第 130 行的 `strcat`（mem 类效果）受 `this_rtype` 控制
- 横向：`strcpy` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`strcpy` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.5803

## 36. `__rb_validate_buffer` 调用 `local_set` 后跳过 `atomic_long_set`（kernel/trace/ring_buffer.c:2020）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`bpage` 在 `__rb_validate_buffer` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `local_set` 后把 `ret` 设为 `- 1`，不再自己保证
- 动态阶段可检查：后续使用 `bpage` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 2020 行调用 `local_set` 后，第 2022 行把 `ret` 设为 `- 1`；第 2024 行的 `atomic_long_set`（mem 类效果）受 `ret` 控制
- 横向：`local_set` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`local_set` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.5803

## 37. `rb_meta_validate_events` 调用 `local_set` 后跳过 `rb_inc_page`（kernel/trace/ring_buffer.c:2244）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`head_page` 在 `rb_meta_validate_events` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `local_set` 后把 `i` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `head_page` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 2244 行调用 `local_set` 后，第 2248 行把 `i` 设为 `0`；第 2248 行的 `rb_inc_page`（mem 类效果）受 `i` 控制
- 横向：`local_set` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`local_set` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.5803

## 38. `ring_buffer_read_page` 调用 `local_set` 后跳过 `rb_init_data_page`（kernel/trace/ring_buffer.c:7304）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`dpage` 在 `ring_buffer_read_page` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `local_set` 后把 `read` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `dpage` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 7304 行调用 `local_set` 后，第 7308 行把 `read` 设为 `0`；第 7315 行的 `rb_init_data_page`（mem 类效果）受 `read` 控制
- 横向：`local_set` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`local_set` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.5803

## 39. `efi_earlycon_setup` 调用 `ARRAY_SIZE` 后跳过 `efi_earlycon_scroll_up`（drivers/firmware/efi/earlycon.c:260）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`si` 在 `efi_earlycon_setup` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `ARRAY_SIZE` 后把 `i` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `si` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 260 行调用 `ARRAY_SIZE` 后，第 268 行把 `i` 设为 `0`；第 269 行的 `efi_earlycon_scroll_up`（mem 类效果）受 `i` 控制
- 横向：`ARRAY_SIZE` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`ARRAY_SIZE` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.5745

## 40. `efi_get_fdt_params` 调用 `ARRAY_SIZE` 后跳过 `efi_get_fdt_prop`（drivers/firmware/efi/fdtparams.c:100）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`fdt、name、node、pname、target` 在 `efi_get_fdt_params` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `ARRAY_SIZE` 后把 `i` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `fdt、name、node、pname、target` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 100 行调用 `ARRAY_SIZE` 后，第 106 行把 `i` 设为 `0`；第 118 行的 `efi_get_fdt_prop`（mem 类效果）受 `i` 控制
- 横向：`ARRAY_SIZE` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`ARRAY_SIZE` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.5745

## 41. `audit_set_feature` 调用 `ARRAY_SIZE` 后跳过 `audit_log_feature_change`（kernel/audit.c:1191）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`new_feature、new_lock、old_feature、old_lock` 在 `audit_set_feature` 之后被使用或发布之前，必须已写入（清零或初始化）、已登记；公共层在调用 `ARRAY_SIZE` 后把 `i` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `new_feature、new_lock、old_feature、old_lock` 时，它是否已写入（清零或初始化）、已登记（各架构分别检查性质，不比较架构间差异）
- 依据：第 1191 行调用 `ARRAY_SIZE` 后，第 1195 行把 `i` 设为 `0`；第 1210 行的 `audit_log_feature_change`（mem+register 类效果）受 `i` 控制
- 横向：`ARRAY_SIZE` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`ARRAY_SIZE` 是否产生了“已写入（清零或初始化）、已登记”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.5745

## 42. `rcu_init_one` 调用 `ARRAY_SIZE` 后跳过 `raw_spin_lock_init`（kernel/rcu/tree.c:4739）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`ACCESS_PRIVATE` 在 `rcu_init_one` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `ARRAY_SIZE` 后把 `i` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `ACCESS_PRIVATE` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 4739 行调用 `ARRAY_SIZE` 后，第 4747 行把 `i` 设为 `1`；第 4758 行的 `raw_spin_lock_init`（mem 类效果）受 `i` 控制
- 横向：`ARRAY_SIZE` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`ARRAY_SIZE` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.5745

## 43. `acpi_ns_externalize_name` 调用 `arch_local_save_flags` 后跳过 `acpi_ut_repair_name`（drivers/acpi/acpica/nsutils.c:473）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`converted_name` 在 `acpi_ns_externalize_name` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `arch_local_save_flags` 后把 `i` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `converted_name` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 473 行调用 `arch_local_save_flags` 后，第 480 行把 `i` 设为 `0`；第 494 行的 `acpi_ut_repair_name`（mem 类效果）受 `i` 控制
- 横向：`arch_local_save_flags` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`arch_local_save_flags` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.5637

## 44. `move_ptes` 调用 `pte_none` 后跳过 `mremap_folio_pte_batch`（mm/mremap.c:267）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`max_nr_ptes、old_addr、old_pte、old_ptep、vma` 在 `move_ptes` 之后被使用或发布之前，必须已写入（清零或初始化）、页表项已设置；公共层在调用 `pte_none` 后把 `nr_ptes` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `max_nr_ptes、old_addr、old_pte、old_ptep、vma` 时，它是否已写入（清零或初始化）、页表项已设置（各架构分别检查性质，不比较架构间差异）
- 依据：第 267 行调用 `pte_none` 后，第 269 行把 `nr_ptes` 设为 `1`；第 287 行的 `mremap_folio_pte_batch`（mem+pgtable 类效果）受 `nr_ptes` 控制
- 横向：`pte_none` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`pte_none` 是否产生了“已写入（清零或初始化）、页表项已设置”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.5637

## 45. `generic_map_delete_batch` 调用 `__untagged_addr_remote` 后跳过 `copy_from_user`（kernel/bpf/syscall.c:2030）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`key、keys、map` 在 `generic_map_delete_batch` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `__untagged_addr_remote` 后把 `cp` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `key、keys、map` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 2030 行调用 `__untagged_addr_remote` 后，第 2037 行把 `cp` 设为 `0`；第 2039 行的 `copy_from_user`（mem 类效果）受 `cp` 控制
- 横向：`__untagged_addr_remote` 平凡定义的架构 无；非平凡的 riscv、x86
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`__untagged_addr_remote` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.5598

## 46. `map_write` 调用 `strchr` 后跳过 `simple_strtoul`（kernel/user_namespace.c:995）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`pos` 在 `map_write` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `strchr` 后把 `next_line` 设为 ``，不再自己保证
- 动态阶段可检查：后续使用 `pos` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 995 行调用 `strchr` 后，第 1000 行把 `next_line` 设为 ``；第 1004 行的 `simple_strtoul`（mem 类效果）受 `next_line` 控制
- 横向：`strchr` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`strchr` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.5238

## 47. `do_initcalls` 调用 `panic` 后跳过 `strcpy`（init/main.c:1430）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`command_line、saved_command_line` 在 `do_initcalls` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `panic` 后把 `level` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `command_line、saved_command_line` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 1430 行调用 `panic` 后，第 1432 行把 `level` 设为 `0`；第 1434 行的 `strcpy`（mem 类效果）受 `level` 控制
- 横向：`panic` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`panic` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.4963

## 48. `rcu_init_one` 调用 `panic` 后跳过 `raw_spin_lock_init`（kernel/rcu/tree.c:4743）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`ACCESS_PRIVATE` 在 `rcu_init_one` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `panic` 后把 `i` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `ACCESS_PRIVATE` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 4743 行调用 `panic` 后，第 4747 行把 `i` 设为 `1`；第 4758 行的 `raw_spin_lock_init`（mem 类效果）受 `i` 控制
- 横向：`panic` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`panic` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.4963

## 49. `__pte_alloc_kernel` 调用 `smp_wmb` 后跳过 `pte_free_kernel`（mm/memory.c:471）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`init_mm` 在 `__pte_alloc_kernel` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `smp_wmb` 后把 `new` 设为 ``，不再自己保证
- 动态阶段可检查：后续使用 `init_mm` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 471 行调用 `smp_wmb` 后，第 473 行把 `new` 设为 ``；第 477 行的 `pte_free_kernel`（mem 类效果）受 `new` 控制
- 横向：`smp_wmb` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`smp_wmb` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.4963

## 50. `string_get_size` 调用 `do_div` 后跳过 `snprintf`（lib/string_helpers.c:98）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`remainder、tmp` 在 `string_get_size` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `do_div` 后把 `j` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `remainder、tmp` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 98 行调用 `do_div` 后，第 105 行把 `j` 设为 `0`；第 125 行的 `snprintf`（mem 类效果）受 `j` 控制
- 横向：`do_div` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`do_div` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.4878

