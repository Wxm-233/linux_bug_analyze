# TLB / 缓存钩子语义检查：判据（写代码之前定下）

2026-11-17，Claude。用户：“TLB/缓存钩子语义”。来源：提交级留出集检验（`heldout_commit_20261117`）里出现次数最多的未覆盖类型（P2 刷缓存、P4 中的 TLB 语义），加上 depmine 的 P2、P4 样本。**这些样本用于本轮设计，此后算开发样本，不能再当留出集用。**

## 一、这一类缺陷是什么

公共代码修改页表或页内容之后，要调用一组钩子，让架构完成 TLB 或缓存的维护：
- `update_mmu_cache`：新建用户映射后调用；
- `flush_cache_vmap`、`flush_cache_vmap_early`：新建内核映射后调用；
- `flush_cache_page`、`flush_cache_range`：改用户映射前调用；
- `flush_dcache_page`、`flush_dcache_folio`：内核写过页内容后调用。

这些钩子在 x86_64、arm64 上多数是空函数。所以：
- 公共代码漏调钩子，在这些架构上不会出错，只在需要它的架构上出错（riscv 的 sfence，VIVT/VIPT 别名缓存的 arm、mips、parisc 等）；
- 反过来，架构实现的钩子效果不够，也只在那个架构上出错。

## 二、横向：各架构钩子效果表（词法，可在任意版本上做）

1. 范围：
   - 每个架构的 `arch/<架构>/include/asm/**/*.h`、`arch/<架构>/mm/*.c`；
   - 通用默认实现：`include/asm-generic/cacheflush.h`、`include/asm-generic/tlbflush.h`、`include/linux/pgtable.h`、`include/linux/cacheflush.h`。
2. 钩子：
   - `update_mmu_cache`、`update_mmu_cache_range`、`update_mmu_tlb`；
   - `flush_cache_vmap`、`flush_cache_vmap_early`；
   - `flush_cache_page`、`flush_cache_range`；
   - `flush_dcache_page`、`flush_dcache_folio`。
3. 取定义的方式：
   - 架构里的 `#define 名(参数) 内容`、`static inline` 函数、`.c` 里的函数定义；
   - 架构没定义，就用通用默认实现；
   - 宏或函数只是转调另一个钩子或另一个架构函数的，按名字向下追最多 3 层。
   - 同一架构有多份定义的（不同配置），取并集，标“多份”。
4. 每个钩子归成以下几类（可以兼有）：
   - **空**：没有任何调用、内联汇编或赋值；
   - **TLB 失效**：调用的函数名含 `tlb` 且含 `flush`、`inval` 或 `sfence`；或者内联汇编含 `sfence.vma`、`tlbi`、`invlpg`、`tlbie`；
   - **TLB 预装**：调用的函数名含 `tlb`，但不属于“TLB 失效”（例如 mips、loongarch 的 `__update_tlb`）；
   - **缓存**：调用的函数名含 `cache`、`dcache`、`icache`、`wbinv`；
   - **其他**。

   “TLB 失效”里，如果调用的失效函数名都以 `local_` 开头，或含 `_local`，再标“只刷本地”。

## 三、检查规则

**架构侧（a2c，架构自身前后不一致）**

- **T1a**：某架构的 `update_mmu_cache`（或 `update_mmu_cache_range`）属于“TLB 失效”，说明它在“无效 → 有效”之后需要 TLB 维护；但它的 `flush_cache_vmap` 是“空”。报（架构，`flush_cache_vmap`）。
- **T1b**：某架构的 `update_mmu_cache`（或 `update_mmu_cache_range`）属于“TLB 失效”且“只刷本地”。报（架构，`update_mmu_cache`）。

**公共侧（c2a，公共代码漏调或用错钩子）**

范围：`mm/`、`kernel/`、`lib/`、`fs/` 的 `.c`，以及 `include/linux/` 的 `.h`。架构代码只用来找调用者。

- **T2 建内核映射后没刷新**：
  - 函数 F 里有内核映射写入：`set_pte_at(&init_mm, …)`、`set_ptes(&init_mm, …)`，或调用名字以 `_noflush` 结尾的建映射函数；F 自己的名字不以 `_noflush` 结尾。
  - 刷新：F 里调用了 `flush_cache_vmap`、`flush_cache_vmap_early`、`flush_tlb_kernel_range`、`local_flush_tlb_kernel_range` 或 `flush_tlb_all`，就算刷新过。
  - 否则看 F 的调用者（在 `mm/`、`kernel/`、`lib/`、`fs/` 和 `arch/*/mm` 里按名字找），向上最多 3 层：所有调用链上都有刷新，才算刷新过。
  - 一个调用者都找不到，或者存在一条没有刷新的调用链，就报 F。
- **T3 大页上用了按页刷**：
  - 函数里调用了 `flush_cache_page(vma, addr, X)`，并满足以下任一条：
    - (a) 第 3 个实参看起来是地址而不是页框号：含 `addr`、`address` 或 `_SIZE`，且不含 `pfn`；
    - (b) 这次调用前后 15 行内出现 PMD 级的写法：`HPAGE_PMD_SIZE`、`HPAGE_PMD_NR`、`pvmw.pmd`、`set_pmd_at`、`pmdp_`、`pmd_trans_huge`、`PMD_SIZE`。
  - 满足就报。
- **T4 写完页内容就映射给用户，没刷数据缓存**：
  - 同一函数里，同时有：
    - **内核写页**：`copy_from_user`、`memcpy`、`memset`、`clear_highpage`、`copy_highpage`、`memcpy_to_page`、`copy_mc_to_kernel` 中任一，且函数里出现 `kmap`、`kmap_local_page`、`kmap_local_folio`、`page_address` 或 `folio_address`；
    - **映射给用户**：`set_pte_at`（第一个实参不是 `&init_mm`）、`set_ptes`、`mfill_atomic_install_pte`、`folio_add_new_anon_rmap` 中任一。
  - 并且没有：`flush_dcache_page`、`flush_dcache_folio`、`clear_user_highpage`、`copy_user_highpage`、`folio_zero_user`。
  - 满足就报。

每条公共侧候选都附“受影响的架构”：对应钩子在横向表里不为空的架构。T2 看 `flush_cache_vmap`，或 `update_mmu_cache` 属于“TLB 失效”；T3 看 `flush_cache_page`；T4 看 `flush_dcache_page`。

## 四、评估

1. **自测**：每条规则正反各至少 1 例；横向表在构造的头文件上分类正确。
2. **横向表核对**：在当前版本上核对 6 个已知事实：
   - x86 的 `flush_cache_vmap` 为空；
   - riscv 的 `flush_cache_vmap` 是 TLB 失效；
   - arm 的 `flush_cache_vmap` 不为空；
   - x86 的 `update_mmu_cache` 为空；
   - riscv 的 `update_mmu_cache` 是 TLB 失效，且不是只刷本地；
   - mips 的 `update_mmu_cache` 是 TLB 预装。

   参考线：6/6。
3. **召回**：在修复前的版本上运行，看对应规则是否报出修复改动的位置（架构侧看架构和钩子；公共侧看文件和函数）：

   | 样本 | 规则 |
   |---|---|
   | 7e3811521dc3 riscv 实现 flush_cache_vmap | T1a |
   | 4bd1d80efb5a riscv update_mmu_cache 通知其他 hart | T1b |
   | d9807d60c145 riscv vmemmap 建好后刷 TLB | T2（报 `mm/sparse-vmemmap.c` 里写 init_mm 的函数） |
   | 7f9c9b607dc2 rmap THP 的缓存刷新 | T3 |
   | 9add2cc22de6 migrate_device 大零页 PMD 的缓存刷新 | T3 |
   | 19b482c29b6f shmem_mfill_atomic_pte 漏刷 | T4 |

   参考线：≥4/6。本轮明确不覆盖、只记录的：3d0b95cd87b2（共享 PMD 的刷新范围）、f0293cd1f4fc（riscv 带地址的 sfence 只作用于叶子项）、depmine 里几个“说不清”的 arm64 TLB 样本。
4. **当前版本**：报告各规则的候选数。候选不超过 40 条时全审，否则审每条规则排在前面的、合计 40 条。我和 Codex 盲判（可能、不可能、说不清，定义同前几轮：在某个架构上确实会因为缺这个 TLB 或缓存维护而出错），然后裁定。报告精度，不设参考线。
5. 不做提交级评测：本轮是新增检查，接进提交级模式留到之后。
