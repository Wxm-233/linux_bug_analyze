# 手写表里没测到的函数，按原因分类

- 内联：该内核里这个函数没有独立符号（被内联，或该版本里改名、不存在）；
- 没插桩：有符号，但定义它的 .c 文件编译时关掉了 KCOV（`KCOV_INSTRUMENT ... := n`）；
- 有插桩但没记到：有符号、文件也插桩了，模板执行时却没记到。

## 当前版本内核

手写表（模板 × 架构）共 296 项，实测执行到 137 项（46%）。没测到的 159 项中：内联 128，没插桩 20，有插桩但没记到 11。去掉 KCOV 本来就看不到的两类之后，可观测的 148 项里执行到 137 项（93%）。

### 没插桩（20 项，3 个函数）

- `flush_tlb_mm_range`：x86_64:T1、x86_64:T2、x86_64:T3
- `flush_tlb_multi`：x86_64:T3
- `post_alloc_hook`：arm64:Z2、arm64:Z3、arm64:Z4、arm64:Z7、arm64（开 MTE）:Z2、arm64（开 MTE）:Z3、arm64（开 MTE）:Z4、arm64（开 MTE）:Z7、riscv:Z2、riscv:Z3、riscv:Z4、riscv:Z7、x86_64:Z2、x86_64:Z3、x86_64:Z4、x86_64:Z7

### 有插桩但没记到（11 项，3 个函数）

- `flush_tlb_range`：arm64:T2、arm64（开 MTE）:T2、riscv:T2
- `folio_zero_user`：arm64:Z2、arm64（开 MTE）:Z2、riscv:Z2、x86_64:Z2
- `shmem_fault`：arm64:Z6、arm64（开 MTE）:Z6、riscv:Z6、x86_64:Z6

### 内联（128 项，26 个函数）

- `__do_huge_pmd_anonymous_page`：arm64:Z4、arm64（开 MTE）:Z4、riscv:Z4、x86_64:Z4
- `__flush_tlb_range`：x86_64:T3
- `alloc_anon_folio`：arm64:Z2、arm64（开 MTE）:Z2、riscv:Z2、x86_64:Z2
- `change_pte_range`：arm64:T2、arm64（开 MTE）:T2、riscv:T2、x86_64:T2
- `clear_highpage`：arm64:Z7、arm64（开 MTE）:Z7、riscv:Z7、x86_64:Z7
- `clear_user_highpage`：arm64:Z2、arm64（开 MTE）:Z2、riscv:Z2、x86_64:Z2
- `do_anonymous_page`：arm64:Z1、arm64:Z2、arm64:Z5、arm64:Z8、arm64:Z9、arm64（开 MTE）:Z1、arm64（开 MTE）:Z2、arm64（开 MTE）:Z5、arm64（开 MTE）:Z8、arm64（开 MTE）:Z9、riscv:Z1、riscv:Z2、riscv:Z5、riscv:Z8、riscv:Z9、x86_64:Z1、x86_64:Z2、x86_64:Z5、x86_64:Z8、x86_64:Z9
- `do_mprotect_pkey`：riscv:T2
- `do_mremap`：arm64:Z9、arm64（开 MTE）:Z9、riscv:Z9、x86_64:Z9
- `do_pte_missing`：arm64:Z1、arm64（开 MTE）:Z1、riscv:Z1、x86_64:Z1
- `flush_icache_pages`：arm64:I1、arm64（开 MTE）:I1、riscv:I1、x86_64:I1
- `flush_tlb_mm_range`：arm64:T1、arm64:T2、arm64:T3、arm64（开 MTE）:T1、arm64（开 MTE）:T2、arm64（开 MTE）:T3
- `flush_tlb_multi`：arm64:T3、arm64（开 MTE）:T3、riscv:T3
- `flush_tlb_range`：x86_64:T2
- `get_huge_zero_folio`：arm64:Z3、arm64（开 MTE）:Z3、riscv:Z3、x86_64:Z3
- `handle_pte_fault`：arm64:Z1、arm64（开 MTE）:Z1、riscv:Z1、x86_64:Z1
- `madvise_dontneed_single_vma`：arm64:Z5、arm64（开 MTE）:Z5、riscv:Z5、x86_64:Z5
- `move_ptes`：arm64:Z9、arm64（开 MTE）:Z9、riscv:Z9、x86_64:Z9
- `prot_commit_flush_ptes`：arm64:T2、arm64（开 MTE）:T2、riscv:T2、x86_64:T2
- `shmem_alloc_folio`：arm64:Z7、arm64（开 MTE）:Z7、riscv:Z7、x86_64:Z7
- `tag_clear_highpage`：arm64:Z3、arm64（开 MTE）:Z3、riscv:Z3、x86_64:Z3
- `tag_clear_highpages`：riscv:Z3、x86_64:Z3
- `vma_alloc_zeroed_movable_folio`：riscv:Z2、x86_64:Z2
- `zap_present_folio_ptes`：arm64:T1、arm64:T3、arm64:Z5、arm64（开 MTE）:T1、arm64（开 MTE）:T3、arm64（开 MTE）:Z5、riscv:T1、riscv:T3、riscv:Z5、x86_64:T1、x86_64:T3、x86_64:Z5
- `zap_present_ptes`：arm64:T1、arm64:Z5、arm64（开 MTE）:T1、arm64（开 MTE）:Z5、riscv:T1、riscv:Z5、x86_64:T1、x86_64:Z5
- `zap_pte_range`：arm64:T1、arm64:T3、arm64:Z5、arm64（开 MTE）:T1、arm64（开 MTE）:T3、arm64（开 MTE）:Z5、riscv:T1、riscv:T3、riscv:Z5、x86_64:T1、x86_64:T3、x86_64:Z5

## X1 修复前内核

手写表（模板 × 架构）共 296 项，实测执行到 123 项（42%）。没测到的 173 项中：内联 131，没插桩 20，有插桩但没记到 22。去掉 KCOV 本来就看不到的两类之后，可观测的 145 项里执行到 123 项（85%）。

### 没插桩（20 项，3 个函数）

- `flush_tlb_mm_range`：x86_64:T1、x86_64:T2、x86_64:T3
- `flush_tlb_multi`：x86_64:T3
- `post_alloc_hook`：arm64:Z2、arm64:Z3、arm64:Z4、arm64:Z7、arm64（开 MTE）:Z2、arm64（开 MTE）:Z3、arm64（开 MTE）:Z4、arm64（开 MTE）:Z7、riscv:Z2、riscv:Z3、riscv:Z4、riscv:Z7、x86_64:Z2、x86_64:Z3、x86_64:Z4、x86_64:Z7

### 有插桩但没记到（22 项，6 个函数）

- `__flush_tlb_range`：arm64:T3、arm64（开 MTE）:T3
- `flush_tlb_range`：arm64:T2、arm64（开 MTE）:T2、riscv:T2
- `folio_zero_user`：arm64:Z2、arm64（开 MTE）:Z2、riscv:Z2、x86_64:Z2
- `prot_commit_flush_ptes`：x86_64:T2
- `shmem_fault`：arm64:Z6、arm64（开 MTE）:Z6、riscv:Z6、x86_64:Z6
- `unmap_region`：arm64:T1、arm64:T3、arm64（开 MTE）:T1、arm64（开 MTE）:T3、riscv:T1、riscv:T3、x86_64:T1、x86_64:T3

### 内联（131 项，27 个函数）

- `__do_huge_pmd_anonymous_page`：arm64:Z4、arm64（开 MTE）:Z4、riscv:Z4、x86_64:Z4
- `__flush_tlb_range`：x86_64:T3
- `alloc_anon_folio`：arm64:Z2、arm64（开 MTE）:Z2、riscv:Z2、x86_64:Z2
- `change_pte_range`：arm64:T2、arm64（开 MTE）:T2、riscv:T2、x86_64:T2
- `clear_highpage`：arm64:Z7、arm64（开 MTE）:Z7、riscv:Z7、x86_64:Z7
- `clear_user_highpage`：arm64:Z2、arm64（开 MTE）:Z2、riscv:Z2、x86_64:Z2
- `do_anonymous_page`：arm64:Z1、arm64:Z2、arm64:Z5、arm64:Z8、arm64:Z9、arm64（开 MTE）:Z1、arm64（开 MTE）:Z2、arm64（开 MTE）:Z5、arm64（开 MTE）:Z8、arm64（开 MTE）:Z9、riscv:Z1、riscv:Z2、riscv:Z5、riscv:Z8、riscv:Z9、x86_64:Z1、x86_64:Z2、x86_64:Z5、x86_64:Z8、x86_64:Z9
- `do_mprotect_pkey`：riscv:T2
- `do_mremap`：arm64:Z9、arm64（开 MTE）:Z9、riscv:Z9、x86_64:Z9
- `do_pte_missing`：arm64:Z1、arm64（开 MTE）:Z1、riscv:Z1、x86_64:Z1
- `flush_icache_pages`：arm64:I1、arm64（开 MTE）:I1、riscv:I1、x86_64:I1
- `flush_tlb_mm_range`：arm64:T1、arm64:T2、arm64:T3、arm64（开 MTE）:T1、arm64（开 MTE）:T2、arm64（开 MTE）:T3
- `flush_tlb_multi`：arm64:T3、arm64（开 MTE）:T3、riscv:T3
- `flush_tlb_range`：x86_64:T2
- `get_huge_zero_folio`：arm64:Z3、arm64（开 MTE）:Z3、riscv:Z3、x86_64:Z3
- `handle_pte_fault`：arm64:Z1、arm64（开 MTE）:Z1、riscv:Z1、x86_64:Z1
- `madvise_dontneed_single_vma`：arm64:Z5、arm64（开 MTE）:Z5、riscv:Z5、x86_64:Z5
- `move_ptes`：arm64:Z9、arm64（开 MTE）:Z9、riscv:Z9、x86_64:Z9
- `prot_commit_flush_ptes`：arm64:T2、arm64（开 MTE）:T2、riscv:T2
- `shmem_alloc_folio`：arm64:Z7、arm64（开 MTE）:Z7、riscv:Z7、x86_64:Z7
- `tag_clear_highpage`：riscv:Z3、x86_64:Z3
- `tag_clear_highpages`：arm64:Z3、arm64（开 MTE）:Z3、riscv:Z3、x86_64:Z3
- `vma_alloc_zeroed_movable_folio`：riscv:Z2、x86_64:Z2
- `zap_present_folio_ptes`：arm64:T1、arm64:T3、arm64:Z5、arm64（开 MTE）:T1、arm64（开 MTE）:T3、arm64（开 MTE）:Z5、riscv:T1、riscv:T3、riscv:Z5、x86_64:T1、x86_64:T3、x86_64:Z5
- `zap_present_ptes`：arm64:T1、arm64:Z5、arm64（开 MTE）:T1、arm64（开 MTE）:Z5、riscv:T1、riscv:Z5、x86_64:T1、x86_64:Z5
- `zap_pte_range`：arm64:T1、arm64:T3、arm64:Z5、arm64（开 MTE）:T1、arm64（开 MTE）:T3、arm64（开 MTE）:Z5、riscv:T1、riscv:T3、riscv:Z5、x86_64:T1、x86_64:T3、x86_64:Z5
- `zap_vma_range_batched`：arm64:Z5、arm64（开 MTE）:Z5、riscv:Z5、x86_64:Z5

