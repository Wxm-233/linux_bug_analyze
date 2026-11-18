# TLB / 缓存钩子语义检查第二版：判据（写代码之前定下）

2026-11-17，Claude。用户：“继续你推荐的下一步改进”，即第一项“扩大覆盖面”。本轮先做 tlbhook 第二版。

来源是第一版（`tlbhook_20261117`）README 里“对分析器的启示”的四条：
1. 钩子效果要按地址区域判断；
2. T2 降噪；
3. 撤掉 T1b；
4. T3 改成同一分支。

本轮新用到的样本（503638e0babf、4edd70ee6a7d、8d6c8c40e733、Ali Tariq 的 KASAN 补丁）此后都算开发样本。

第一版代码只读导入（`tlbhook.py`），不修改。

## 一、按地址区域的钩子效果（新增）

### 1. 架构侧：`flush_cache_vmap` 对哪些区域生效

- 读取架构的 `flush_cache_vmap` 定义（取法同第一版）。如果函数体的全部非空效果都包在一个 `if (条件)` 里，就按条件里出现的记号确定生效区域：

  | 条件里的记号 | 区域 |
  |---|---|
  | `is_vmalloc_or_module_addr` | vmalloc、module |
  | `is_vmalloc_addr`、`VMALLOC_START`、`VMALLOC_END` | vmalloc |
  | `MODULES_VADDR`、`MODULES_END` | module |
  | `VMEMMAP_START`、`VMEMMAP_END` | vmemmap |
  | `KASAN_SHADOW_START`、`KASAN_SHADOW_END` | kasan |
  | `FIXADDR_START`、`FIXADDR_TOP` | fixmap |
  | `PKMAP_BASE` | pkmap |

- 没有包在 `if` 里，或者条件里一个记号都认不出，就记为“全部区域”。
- 函数体为空，记为“空”。这种情况第一版的 T1a 已经处理，本版不再处理。

### 2. 公共侧：调用 `flush_cache_vmap(start, end)` 的地方，映射的是哪个区域

按调用所在的文件和实参判断，规则依次匹配：

| 条件 | 区域 |
|---|---|
| 文件在 `mm/kasan/` 下 | kasan |
| 文件在 `mm/kmsan/` 下 | kmsan |
| 文件是 `mm/sparse-vmemmap.c`，或实参含 `vmemmap` | vmemmap |
| 文件是 `mm/vmalloc.c`、`mm/percpu-vm.c`、`mm/percpu.c`、`mm/ioremap.c`、`mm/execmem.c`、`kernel/bpf/arena.c` | vmalloc |
| 文件是 `mm/highmem.c` | pkmap |
| 其他 | 未知（不报，只计数） |

### 3. 配置可行性

区域对应的功能，该架构必须支持：
- kasan 要求 `arch/<架构>/Kconfig` 里有 `HAVE_ARCH_KASAN_VMALLOC`；
- kmsan 要求有 `HAVE_ARCH_KMSAN`；
- vmemmap 要求有 `SPARSEMEM_VMEMMAP_ENABLE`；
- 其他区域默认可行。

### 4. 规则 R1：区域没被覆盖

公共侧某个调用点的区域是 r（已知），某个架构的 `flush_cache_vmap` 生效区域是集合 S（不是“全部区域”），且 r 不在 S 里、配置可行，就报（架构，文件，函数，行，r，S）。

含义：调用方以为调了 `flush_cache_vmap` 就完成了刷新，但这个架构对 r 区域什么都不做。

### 5. 规则 T1c（架构侧，自身前后不一致）

- 如果某架构的 `flush_cache_vmap` 在区域条件下调用的是一个辅助函数 M，而不是 TLB 失效函数（例如 riscv 的 `mark_new_valid_map`），说明这个架构靠 M 来处理“新出现的有效映射”。
- 在该架构的 `arch/<架构>/include/asm/**/*.h` 和 `arch/<架构>/mm/*.c` 里，找把内核页表项改成有效的函数：
  - 写法是 `set_pte(…, … | _PAGE_PRESENT …)`、`set_pte(…, pte_mkpresent(…))`、`set_pte(…, pte_mkvalid(…))`；
  - 这样的函数如果只调用了 `local_` 开头的 TLB 刷新，没有调用 M，也没有调用 `flush_tlb_kernel_range` 或 `flush_tlb_all`，就报。

## 二、第一版规则的改动

- **T1a**：不变。
- **T1b 撤掉**：上游认为 riscv 的 `update_mmu_cache` 只刷本地可以接受，4bd1d80efb5a 已被回退。
- **T2 降噪**，其余同第一版：
  1. 只认真正建映射的 `_noflush` 函数：被调用的名字以 `_noflush` 结尾，并且含 `vmap`、`map_pages`、`pages_range`、`populate`、`_pte`、`ioremap` 之一。`simple_fsync_noflush`、`set_direct_map_*_noflush` 等不再算。
  2. 回调：函数 G 的名字以“非调用”的形式（后面不跟 `(`）出现在函数 H 里，H 就算 G 的调用者，例如 `apply_to_page_range(…, G, …)`、`.pte_entry = G`。
  3. 刷新包装函数：名字含 `flush`、本身调用了刷新函数的函数（传递 3 层）也算刷新函数，例如 percpu 的 `pcpu_post_map_flush`。
  4. 调用链向上追到 8 层，原来是 3 层。超过 8 层仍未见刷新，按“没刷新”处理。
- **T3 改成同一分支**：PMD 写法要出现在 `flush_cache_page` 所在的最内层 `{ … }` 块里，或者这个块前面的条件头里（`if (…)`、`else if (…)`），不再按 ±15 行。实参不是页框号的条件 (a) 不变。
- **T4**：不变。

## 三、评估

1. **自测**：每条新规则、每项改动正反各至少 1 例。
2. **第一版样本的召回不降**：T1a 7e3811521dc3、T2 d9807d60c145、T3 7f9c9b607dc2 和 9add2cc22de6、T4 19b482c29b6f。参考线 5/5。
3. **新规则的样本**：

   | 样本 | 规则 | 期望 |
   |---|---|---|
   | 503638e0babf 引入区域过滤 | R1 提交级 | 在 503638e0babf 上报“riscv，mm/kasan/shadow.c，kasan”；在 503638e0babf^ 上不报。即这条候选是这个提交新引入的。这是 Ali Tariq KASAN 补丁的 `Fixes:` 目标 |
   | 4edd70ee6a7d 的反事实 | R1 | 在 4edd70ee6a7d^ 上只换入它的 `mm/sparse-vmemmap.c`（加了调用，但 riscv 还不认 vmemmap 区域），要报“riscv，sparse-vmemmap，vmemmap”；换入完整的 4edd70ee6a7d 则不报 |
   | 8d6c8c40e733 kfence | T1c | 在 8d6c8c40e733^ 上报 riscv `kfence_protect_page`；在 8d6c8c40e733 上不报 |

   参考线：3/3。

4. **当前版本（df2908090cda）**：
   - R1 必须报出“riscv，`mm/kasan/shadow.c` 的 `__kasan_populate_vmalloc`”（已由 Ali Tariq 在实机上证实，作为开发阳性）；
   - kmsan 在 riscv 上因配置不可行，不报；
   - vmalloc、percpu、bpf arena 的调用点不报；
   - T2 候选数相对第一版的 20 条，目标降到 10 条以下，同时第一版裁定为“可能”或“说不清”的不能丢；
   - 所有新出现的候选（第一版没审过的），由我和 Codex 盲判，然后裁定，报告精度。
5. 接进提交级模式、在留出集上重新测召回，留到下一轮。注意：留出集里用于本轮设计的样本已经变成开发样本，届时要剔除。
