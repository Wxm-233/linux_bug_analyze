# 按被跳过的效果选规则（effrule_20261115）

2026-11-15，Claude。用户：“扩展规则映射”。判据见 `criteria.md`（SHA 在 `criteria_sha256.txt`，本轮没有修订）。

## 这一轮要回答什么

流水线要先把每个静态候选映射到一条性质规则（R1 清零、R2 旧翻译失效、R3 指令缓存一致、R4 搬移后内容保持），才能去看模板有没有测到它。旧映射（`r4_rule` + `rule_of`）看的是“被跳过的调用往下三层里出现过什么类别的效果”，再加上资源名的条件。本轮改成**只看离被跳过的调用最近的那一层做了哪种具体效果**：写页表项 → R4，清页 → R1，刷 TLB → R2，刷缓存 → R3，不再看资源名。

要回答的问题：这样映射是否更准？当前版本转人工的条目能不能变少？

举个例子。X1 里 `post_alloc_hook` 跳过的是 `kernel_init_pages`。它的名字看不出效果，往下一层是 `clear_highpage_kasan_tagged`，再下一层是 `clear_page`，所以最近效果在第 2 层，是“清页”，映射为 R1。

## 做了什么

1. `effects.py`（WSL）：按判据写死的四族函数名模式，在每棵树自己的事实文件上，从被跳过的调用往下找最近的效果层（最多第 2 层）。先跑自测，12 个手写例子全部正确。
2. `analyze.py`：
   - 静态统计：effdep7 的 13 棵树共 68 个候选，加 effdep5 当前版本的 32 个候选，比较新旧映射；
   - 流水线：当前版本（effdep7 的 6 个、effdep5 的 32 个）和 X1 修复前、修复后，新旧映射各跑一遍。只读导入 `kcov_20261115/analyze_kcov.py` 的 `pipeline`；覆盖用 `r4_20261115/coverage_kcov.json` 和 `kcov_pa_20261115/coverage_x1pre.json`，判错用 `r4_20261115/judge_neg.json` 和 `pipeline_v2_20261115/judge_x1.json`。
3. 规则变了的 9 个不同候选，逐条读 `/root/repos/linux` 的源码，判断是否合理（`judgement.json`）。

没有构建、没有运行内核。

## 结果

**静态**（`static.md`）。effdep7 13 棵树合计：旧映射 R1 7、R3 1、R4 7、无 53；新映射 R1 7、R2 8、R4 7、无 46。规则变了的不同候选共 9 个：

| # | 候选（函数 / 接口，被跳过的调用） | 旧 → 新 | 判断 |
|---|---|---|---|
| 1、2 | `kvm_get/clear_dirty_log_protect` / `kvm_arch_sync_dirty_log`，`kvm_flush_remote_tlbs_memslot` | 无 → R2 | 合理：写保护脏页后刷客户机 TLB |
| 3 | `convert_ctx_accesses` / `verbose`，`bpf_patch_insn_data` | R3 → 无 | 合理：改写的是校验器内部指令数组，与指令缓存无关 |
| 4 | `do_swap_page` / `pte_modify`，`do_wp_page` | R1 → R4 | **不合理**：跳过的是写升级/写时复制，不是“搬移后内容保持” |
| 5、6 | `do_swap_page` / `pte_same`、`ptep_get`，`swap_cache_del_folio` | R1 → 无 | 合理：只是从交换缓存摘掉 folio |
| 7 | `mincore_pte_range` / `ptep_get`，`pte_is_marker` | R1 → 无 | 合理：写的是 mincore 结果数组 |
| 8、9 | `_vm_unmap_aliases` / `max`、`min`，`flush_tlb_kernel_range` | 无 → R2 | 就规则而言合理：内核地址别名撤销后刷 TLB；但接口是通用宏，候选本身质量差 |

合理 8/9。其中新得到规则的 4 个全部合理，被去掉规则的 4 个全部合理（原来就是错的），改了规则的 1 个不合理。

**流水线**（`compare.md`，新映射 / 旧映射）：

| 树 | 动态确认 | 测过没事 | 部分架构测到 | 转人工 |
|---|---|---|---|---|
| 当前版本 effdep7（6 个） | 0 / 0 | 1 / 1 | 0 / 0 | **5 / 5** |
| 当前版本 effdep5（32 个） | 0 / 0 | 2 / 2 | 0 / 2 | **30 / 28** |
| X1 修复前（7 个） | 1 / 1 | 0 / 0 | 0 / 0 | 6 / 6 |
| X1 修复后（7 个） | 0 / 0 | 1 / 1 | 0 / 0 | 6 / 6 |

- X1 结论不变（修复前动态确认，修复后测过没事）；`move_ptes` 仍是 R4、测过没事。
- effdep5 里旧映射的 2 个“部分架构测到”（`do_swap_page`/`ptep_get`、`mincore_pte_range`），是 R1 模板碰巧执行到这些函数，并不检查那里的性质。新映射把规则去掉后，它们回到转人工。
- 新映射下“规则对上了但没有模板执行到”的有 4 个：`_vm_unmap_aliases` ×2（R2，内核地址）、`do_swap_page`/`pte_modify`（R4，映射本身不合理）、`enable_instances`（R3，规则没变）。另有 KVM 的 2 个在 X1 树里同样如此。

## 对照参考线

- 自测全部正确：**达到**；
- X1 结论不变、`move_ptes` 不变：**达到**；
- 规则变了的候选中至少一半合理：**达到**（8/9）；
- 当前版本转人工至少减少 1 条：**没达到**。effdep7 是 5 → 5；effdep5 是 28 → 30，反而多了 2 条，就是上面两个虚的“部分架构测到”。

## 看出的几点

1. **按最近效果选规则，主要作用是去掉错的映射，而不是让更多候选被测到。** 旧映射下得到 R1 或 R3 的不同候选共 7 个，只有 X1 的 `post_alloc_hook` 是对的。新映射去掉了其中 4 个错的；1 个改成同样不对的 R4（`do_swap_page`/`pte_modify`）；1 个没变（`enable_instances`，仍是不对的 R3）。
2. **当前版本转人工减不下来，原因不在映射，而在候选本身。** effdep7 当前版本剩下的 5 个（`__irq_set_trigger`、`ring_buffer_read_page`、三个 BPF `verbose`），被跳过的调用在两层内都没有这四种效果。这些资源在内核内部，现有规则管不到。
3. **新得到规则的候选都落在现有模板测不到的资源上**：内核虚拟地址的 TLB（`flush_tlb_kernel_range`）、KVM 客户机的 TLB。要测它们，得补“内核地址范围的 R2”“客户机 TLB 的 R2”这类模板。前者也许能用 `vm_map_ram` 类路径从内核模块触发；后者要在 QEMU 里再跑一层虚拟化。两者都不是用户态检查程序能做的。
4. **“写页表项 → R4”太粗。** R4 只说页表搬移，写页表项的场合还有写时复制、写升级、改权限等，它们需要不同的性质（例如“写缺页后得到私有副本”）。同样，“刷缓存族”混了数据缓存别名（`flush_cache_vmap`）和指令缓存，而 R3 只管指令缓存（`enable_instances` 一例，规则没变，所以不计入评估）。刷 TLB 的名字模式还会误中查询函数 `mm_tlb_flush_pending`。

## 局限

- 判据写在看过候选列表之后：“最多到第 2 层”和刷 TLB 族里的 `flush_*tlbs*` 模式受看到的数据影响（判据第五节已写明）。这 13 棵树上的结果只算开发集结果。
- 合理性是我一个人读源码判断的，没有第二人复核。读源码用的是临时的 `sed` 命令，没有留脚本。
- 只按函数名判断效果，不看参数。`memset` 一律不算清页，所以 X1 那样“通过 memset 清页”的情形会漏掉。
- 当前版本的源码是 `df2908090cda`；KVM 两个候选在各样本树里的行号不同，我只读了当前版本的代码。

## 文件

- `criteria.md`、`criteria_sha256.txt`：判据；
- `effects.py`、`run_effects.sh`、`effects.log`、`effects.json`：最近效果的计算和自测；
- `analyze.py`、`static.{json,md}`、`compare.md`、`stats.json`：统计和对比；
- `pipeline_kcov_<树>[_old].json`、`report_kcov_<树>[_old].md`：新旧映射下的流水线报告，树为 CUR、E5CUR、X1_pre、X1_fix；
- `judgement.json`：9 条合理性判断。

## 下一步建议

- 把规则拆细，写时复制/写升级不再并入 R4：新增“写缺页后得到私有副本”（R5，用户态可测：fork 后子进程写、父进程看内容不变）；把 R3 限定为只认指令缓存函数。
- 或者转向另一头：上面第 2 点说明，当前版本转人工的瓶颈是候选本身，可以回到留出集或候选生成。

模型调用 0；构建 0；新确认缺陷 0；新疑点 0。
