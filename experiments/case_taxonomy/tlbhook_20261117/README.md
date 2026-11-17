# TLB / 缓存钩子语义检查（tlbhook_20261117）

2026-11-17，Claude。用户：“TLB/缓存钩子语义”。来源：提交级留出集里出现次数最多的未覆盖类型（P2 刷缓存，P4 里的 TLB 语义），加上 depmine 的同类样本。
- 判据 `criteria.md` 写在写代码之前；修订 1（`criteria_amendment1.md`）写在第一次生成效果表之后、召回和当前版本统计之前；两者的 SHA 都在 `criteria_sha256.txt`。
- **本轮设计用到的留出集样本，此后算开发样本。**

统计行：模型调用 0；Codex 调用 1；构建 0；新确认缺陷 0；**新疑点 1**（riscv KASAN vmalloc 影子映射漏标记，静态判断）。

## 一句话结论

**历史样本 6/6 都能报出，当前版本 23 条候选里审出 1 个新疑点；但规则噪声大（23 条里 21 条不成立）。最有价值的发现是：钩子的效果会按地址区域变化，只看“调没调钩子”不够。**

| 指标 | 结果 | 参考线 |
|---|---|---|
| 横向效果表核对 | 5/6（mips 一项见下） | 6/6 ✗ |
| 历史样本召回（不含 T1b） | **5/5** | ≥4/5 ✓ |
| T1b 样本（上游已回退，单列） | 报出 | — |
| 当前版本候选 | 23 条（T1b 2、T2 20、T3 1、T4 0） | — |
| 两人审查（一致率 91%） | 可能 1、说不清 1、不可能 21 | 不设 |

## 这一类是什么（说人话）

公共代码改了页表或页内容之后，要调用一组“钩子”，让架构做 TLB 或缓存的维护：
- 新建用户映射后：`update_mmu_cache`；
- 新建内核映射后：`flush_cache_vmap`；
- 改用户映射前：`flush_cache_page`、`flush_cache_range`；
- 内核写了页内容后：`flush_dcache_page`。

这些钩子在 x86、arm64 上大多是空的，所以漏调了在这两个架构上没事。但 riscv 的 TLB 可能缓存无效项，需要 sfence；arm、mips、parisc 等缓存有别名，需要刷缓存。漏调或钩子实现得不够，就只在这些架构上出错。

## 做法

1. **横向：各架构钩子效果表**（`tlbhook.py table`，`table_df2908090cda.json`）。用词法读出 21 个架构上 9 个钩子的定义，转调的就向下追，再把效果归成：空、TLB 失效、只刷本地、TLB 预装、缓存、其他。词法方式在任何版本上都能做，所以历史样本也能用当时的代码。
2. **五条规则**：
   - **T1a**（架构侧）：同一架构里，`update_mmu_cache` 会做 TLB 失效，`flush_cache_vmap` 却为空，前后矛盾；
   - **T1b**（架构侧）：`update_mmu_cache` 只刷本地；
   - **T2**（公共侧）：建了内核映射，这个函数和它的调用者（向上 3 层）都没调刷新钩子；
   - **T3**（公共侧）：在 PMD 大页附近用了按页刷的 `flush_cache_page`，或者第 3 个参数不是页框号；
   - **T4**（公共侧）：内核写完页内容就映射给用户，没调 `flush_dcache_page`。
3. 自测 22 条全部通过。

## 结果

### 1. 横向效果表核对：5/6

- 第一次只有 4/6，查明有两个实现错误：mips 的头文件整体解析失败；转调钩子的包装被按名字误分类。按判据原文改正后变为 5/6。
- **riscv 一项是我判据里的预期写错了**：让 `update_mmu_cache` 通知其他 hart 的 4bd1d80efb5a 后来被 e921050022f1 回退，当前 riscv 的 `update_mmu_cache` 就是只刷本地，而且是有意为之。已写修订 1 更正。
- **mips 一项**：表里判成“TLB 失效 + 预装”，而我的预期是只有“预装”。查源码，mips 的 `__update_tlb` 在预装的同时会调 `flush_micro_tlb_vm` 刷微 TLB，按规则确实属于“TLB 失效”。所以表是对的，我的预期不够细。没有再改判据，如实记为 5/6。

### 2. 历史样本召回：5/5（另 T1b 1/1）

| 修复 | 规则 | 结果 |
|---|---|---|
| 7e3811521dc3 riscv 实现 flush_cache_vmap | T1a | 报出：修复前 riscv 的 `update_mmu_cache` 做 TLB 失效，`flush_cache_vmap` 为空 |
| d9807d60c145 riscv vmemmap 建好后刷 TLB | T2 | 报出 `vmemmap_pte_populate` |
| 7f9c9b607dc2 rmap THP 缓存刷新 | T3 | 报出 `page_mkclean_one` |
| 9add2cc22de6 migrate_device 大零页 PMD | T3 | 报出 `migrate_vma_insert_huge_pmd_page`（第 3 个参数传成了地址） |
| 19b482c29b6f shmem_mfill_atomic_pte 漏刷 | T4 | 报出 |
| 4bd1d80efb5a riscv 通知其他 hart（单列） | T1b | 报出；但这个修复后来被上游回退了 |

本轮不覆盖、只记录的：3d0b95cd87b2（共享 PMD 的刷新范围）、f0293cd1f4fc（riscv 带地址的 sfence 只作用于叶子项）、depmine 里几个“说不清”的 arm64 TLB 样本。

### 3. 当前版本 23 条候选，两人审查（`review.txt`、`claude.json`、`codex_blind/`、`adjudication.json`）

**新疑点（可能）1 条：riscv 上 KASAN 的 vmalloc 影子映射漏了“新映射”标记**
- **位置**：`mm/kasan/shadow.c` 的 `__kasan_populate_vmalloc` 先给影子区建映射，然后调 `flush_cache_vmap(shadow_start, shadow_end)`。
- **问题**：
  - riscv 现在的 `flush_cache_vmap` 不直接刷 TLB，而是在地址属于 vmalloc、模块或 vmemmap 区时调 `mark_new_valid_map()`，设一个“本 CPU 有新映射”的标记；
  - 异常入口（`arch/riscv/kernel/entry.S`）遇到内核地址缺页，只要标记还在，就补一次 `sfence.vma` 再返回；
  - **KASAN 影子区不在这几个区内**，所以这次 `flush_cache_vmap` 在 riscv 上什么都没做。
- **后果**：如果硬件缓存了影子地址的旧无效项（riscv 规范允许，没有 Svvptc 扩展的实现可能这样做），访问新建的影子就会缺页。这个缺页既得不到补做的 sfence，`do_page_fault` 也不把它当作 vmalloc 地址处理，最后 Oops。
- **旁证**：上游已为同类问题修过一次：8d6c8c40e733 “riscv: kfence: Call mark_new_valid_map() for kfence_unprotect()”，kfence 的地址也不在这几个区里。
- **条件**：riscv64 + `CONFIG_KASAN_VMALLOC` + 会缓存无效项的硬件。QEMU 不缓存无效项，**无法动态验证**，只停在静态判断。
- **上游情况（2026-11-17 在 lore 上核对）**：已经有人报告并交了补丁。Ali Tariq《riscv: mm: Add KASAN shadow mapping to flush_cache_vmap()》（2026-11-02，Muchun Song 已 Ack，还没合入），修法和我们推断的一样；在实机 Orange Pi RV2 上，30 次启动崩了 2 次。更早还有 Shaoqing Qin 2026-08-12 的同类补丁。**所以这条静态判断是对的，但不是首次发现。**
- **谁发现的**：这条是 Codex 指出的。我原来判“不可能”，因为看到调用方调了 `flush_cache_vmap` 就以为刷过了，没想到 riscv 的实现会按地址区域过滤。

**说不清 1 条**：KASAN 早期影子（`zero_pte_populate`）。启动时由各架构 `kasan_init` 刷新；但内存热插拔（memmap_on_memory）时 `kasan_add_zero_shadow` 会在运行时再走这条路径，后面有没有及时刷新没有查清。

**不可能 21 条，原因都是规则太宽：**

| 原因 | 条数 |
|---|---|
| 名字带 `_noflush` 但和建映射无关（`simple_fsync_noflush`），或架构实现里其实刷了（riscv 的 `set_direct_map_*_noflush` 最后会 `flush_tlb_kernel_range`） | 6 |
| 回调函数（`apply_to_page_range`、遍历回调）没有直接调用者，刷新在注册回调的那一方 | 4 |
| 调用链超过 3 层（vmalloc、vmemmap） | 3 |
| 刷新被包在另一个函数里（percpu 的 `pcpu_post_map_flush`） | 2 |
| 设计如此（延迟清理、PKMAP 回收时已刷、kmap_local 由架构钩子处理） | 3 |
| T1b：riscv 是有意设计（已回退）；xtensa 是把单核配置的宏别名并进来造成的误判 | 2 |
| T3：`page_vma_mkclean_one` 的按页刷在 PTE 分支、参数也对，只是离 PMD 代码不到 15 行 | 1 |

## 对分析器的启示

1. **钩子效果要按地址区域判断**：riscv 的 `flush_cache_vmap` 只对 vmalloc、模块、vmemmap 生效。横向效果表应该从“这个钩子在这个架构上做了什么”，细化到“对哪些地址区域做了什么”，再和公共代码映射的区域（KASAN 影子、kfence、percpu、直接映射等）对照。新疑点就出在这里。
2. **T2 降噪**：
   - 只认真正建映射的 `_noflush` 函数；
   - 回调要找到注册它的地方，算到注册方的调用链上；
   - 刷新包装函数按传递关系识别；
   - 调用链追到入口，不设 3 层上限。
3. **T1b 应该撤掉，或者加条件**：上游认为“只刷本地”可以接受（靠 ASID 刷新和缺页修复）。
4. **T3 的窗口应改成“同一分支”**，不按行数。
5. 当前版本这几种写法基本都已修干净，这些规则更适合接进提交级模式，在新提交引入同类写法时报出来。

## 文件

- 判据：`criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`
- 分析器：`tlbhook.py`、`run.sh`
- 结果：`table.log`、`table_df2908090cda.json`、`head.json`、`head.log`、`recall.json`、`recall.log`
- 审查：`make_review.py`、`run_review.sh`、`review.txt`、`review.json`、`claude.json`、`codex_blind/`、`agree.py`、`agreement.json`、`adjudication.json`
