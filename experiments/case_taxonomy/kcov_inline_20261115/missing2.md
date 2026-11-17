# 展开内联后仍没测到的函数

## 当前版本

手写表 296 项，测到 231 项（78%）。上一轮的 128 项内联盲区，本轮测到 94 项。仍没测到 65 项：所在文件没插桩 20，其他 45。

### 所在文件没插桩（20 项）

- `flush_tlb_mm_range`：x86_64:T1、x86_64:T2、x86_64:T3
- `flush_tlb_multi`：x86_64:T3
- `post_alloc_hook`：arm64:Z2、arm64:Z3、arm64:Z4、arm64:Z7、arm64（开 MTE）:Z2、arm64（开 MTE）:Z3、arm64（开 MTE）:Z4、arm64（开 MTE）:Z7、riscv:Z2、riscv:Z3、riscv:Z4、riscv:Z7、x86_64:Z2、x86_64:Z3、x86_64:Z4、x86_64:Z7

### 其他（45 项）

- `__flush_tlb_range`：x86_64:T3
- `clear_highpage`：arm64:Z7、arm64（开 MTE）:Z7、riscv:Z7、x86_64:Z7
- `clear_user_highpage`：arm64:Z2、arm64（开 MTE）:Z2、x86_64:Z2
- `flush_icache_pages`：arm64:I1、arm64（开 MTE）:I1、riscv:I1、x86_64:I1
- `flush_tlb_mm_range`：arm64:T1、arm64:T2、arm64:T3、arm64（开 MTE）:T1、arm64（开 MTE）:T2、arm64（开 MTE）:T3
- `flush_tlb_multi`：arm64:T3、arm64（开 MTE）:T3、riscv:T3
- `flush_tlb_range`：arm64:T2、arm64（开 MTE）:T2、riscv:T2、x86_64:T2
- `folio_zero_user`：arm64:Z2、arm64（开 MTE）:Z2、riscv:Z2、x86_64:Z2
- `madvise_dontneed_single_vma`：arm64:Z5、arm64（开 MTE）:Z5、riscv:Z5、x86_64:Z5
- `shmem_alloc_folio`：riscv:Z7
- `shmem_fault`：arm64:Z6、arm64（开 MTE）:Z6、riscv:Z6、x86_64:Z6
- `tag_clear_highpage`：arm64:Z3、arm64（开 MTE）:Z3、riscv:Z3、x86_64:Z3
- `tag_clear_highpages`：riscv:Z3、x86_64:Z3
- `vma_alloc_zeroed_movable_folio`：x86_64:Z2

## X1 修复前

手写表 296 项，测到 217 项（73%）。上一轮的 131 项内联盲区，本轮测到 91 项。仍没测到 79 项：所在文件没插桩 20，其他 59。

### 所在文件没插桩（20 项）

- `flush_tlb_mm_range`：x86_64:T1、x86_64:T2、x86_64:T3
- `flush_tlb_multi`：x86_64:T3
- `post_alloc_hook`：arm64:Z2、arm64:Z3、arm64:Z4、arm64:Z7、arm64（开 MTE）:Z2、arm64（开 MTE）:Z3、arm64（开 MTE）:Z4、arm64（开 MTE）:Z7、riscv:Z2、riscv:Z3、riscv:Z4、riscv:Z7、x86_64:Z2、x86_64:Z3、x86_64:Z4、x86_64:Z7

### 其他（59 项）

- `__flush_tlb_range`：x86_64:T3
- `clear_highpage`：arm64:Z7、arm64（开 MTE）:Z7、riscv:Z7、x86_64:Z7
- `clear_user_highpage`：arm64:Z2、arm64（开 MTE）:Z2、x86_64:Z2
- `flush_icache_pages`：arm64:I1、arm64（开 MTE）:I1、riscv:I1、x86_64:I1
- `flush_tlb_mm_range`：arm64:T1、arm64:T2、arm64:T3、arm64（开 MTE）:T1、arm64（开 MTE）:T2、arm64（开 MTE）:T3
- `flush_tlb_multi`：arm64:T3、arm64（开 MTE）:T3、riscv:T3
- `flush_tlb_range`：arm64:T2、arm64（开 MTE）:T2、riscv:T2、x86_64:T2
- `folio_zero_user`：arm64:Z2、arm64（开 MTE）:Z2、riscv:Z2、x86_64:Z2
- `madvise_dontneed_single_vma`：arm64:Z5、arm64（开 MTE）:Z5、riscv:Z5、x86_64:Z5
- `prot_commit_flush_ptes`：arm64:T2、arm64（开 MTE）:T2
- `shmem_alloc_folio`：riscv:Z7
- `shmem_fault`：arm64:Z6、arm64（开 MTE）:Z6、riscv:Z6、x86_64:Z6
- `tag_clear_highpage`：riscv:Z3、x86_64:Z3
- `tag_clear_highpages`：arm64:Z3、arm64（开 MTE）:Z3、riscv:Z3、x86_64:Z3
- `unmap_region`：arm64:T1、arm64:T3、arm64（开 MTE）:T1、arm64（开 MTE）:T3、riscv:T1、riscv:T3、x86_64:T1、x86_64:T3
- `vma_alloc_zeroed_movable_folio`：x86_64:Z2
- `zap_vma_range_batched`：arm64:Z5、arm64（开 MTE）:Z5、riscv:Z5、x86_64:Z5

