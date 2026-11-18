# 提交级模式加入第五个引擎 TLB（commitmode_tlb_20261117）

2026-11-17，Claude。用户：“接进提交级模式”。
- 判据 `criteria.md` 写在写代码之前，SHA 记在 `criteria_sha256.txt`，本轮没有修订。
- 只读导入 `commitmode_20261117`、`heldout_commit_20261117`、`tlbhook2_20261117`。

统计行：模型调用 0；Codex 调用 0；构建 0；TLB 引擎运行 273 次，出错 0，单次约 22 秒、1.6GB 内存。

## 一句话结论

**加入 TLB 引擎后误报没有增加，但召回和对位也没有提高。** 原因不在规则本身，而在“前后差分”这种比较方式：这一类缺陷大多是架构侧开始依赖某个性质，公共代码里的候选在引入提交前后完全一样，所以差分看不出来。

| 数据集 | 召回（判可疑） | 对位 | 误报 | TLB 单独 |
|---|---|---|---|---|
| 开发集（24 正 / 44 负） | 19 → 19 | 14 → 14 | 3 → 3 | 正样本 0，负样本 0 |
| 干净留出集（23 正 / 48 负） | 4 → 4 | 3 → 3 | 1 → 1 | 正样本 1（见下，不对位），负样本 0 |
| 被污染的 5 个留出正样本（单列） | 0 → 0 | 0 → 0 | — | 0/5 |

误报的参考线（每个数据集增加不超过 2）达到了：增加数为 0。召回不设参考线。

## 发现

### 1. TLB 在留出集上报出了一个真缺陷，但不能算留出成绩

- 留出正样本 `a30b48bf1b24`（mm/migrate_device：实现 zone device 页的 THP 迁移）上，TLB 新报出 T3 候选：`migrate_vma_insert_huge_pmd_page` 里的 `flush_cache_page(vma, addr, addr + HPAGE_PMD_SIZE)`，第 3 个参数是地址，不是页框号。
- 这是个真缺陷：上游修复 `9add2cc22de6` 的 `Fixes:` 标签正好指向 `a30b48bf1b24`。
- 不算对位：留出集给这个提交标注的是另一个修复 `bbcbf045d6c7`（P1 类）。一个提交可以同时引入多个缺陷，这里是两个。
- 不算留出成绩：`9add2cc22de6` 是 tlbhook 第一版的设计样本。

### 2. 被污染的 5 个样本都是 0，原因是结构性的

这 5 个引入提交的父版本和子版本上，TLB 的候选集合**完全相同**：

| 引入提交 | 实际问题 | 为什么差分看不出 |
|---|---|---|
| d95f1a542c3d RISC-V 实现 sparsemem | riscv 启用 vmemmap 后，建 vmemmap 映射没刷 TLB | T2 候选 `vmemmap_pte_populate` 原来就在；“riscv 开始用这段代码”不改变候选 |
| 7d3332be011e riscv 预分配 vmalloc 的 PGD | riscv 的 `flush_cache_vmap` 为空 | T1a（riscv）原来就在 |
| 65d4b9c53017 RISC-V ASID 分配器 | update_mmu_cache 只刷本地 | T1b 已撤掉；T1a 原来就在 |
| 7a92fc8b4d20 引入 `flush_cache_vmap_early` | 早期映射的刷新 | 没有对应规则 |
| 550a7d60bd5e mremap 支持 hugepage | 共享 PMD 的刷新范围 | tlbhook 不覆盖 |

前三个的共同点是：**缺陷由架构侧的变化引起**，比如启用一个功能、改变钩子的效果、开始依赖某个公共函数。公共侧的“可疑写法”早就存在，只是以前在这个架构上无害。签名里只有“文件、函数、写法”，不含“在哪些架构上有害”，所以前后签名一样。

## 对分析器的启示

1. **签名要带上受影响的架构集合**。例如 T2 候选签名加上“哪些架构需要这项维护、配置上可行”。这样：
   - riscv 启用 `SPARSEMEM_VMEMMAP`，会让 T2 的受影响架构多出 riscv，从而被识别为新引入；
   - riscv 把 `flush_cache_vmap` 改成按区域生效（503638e0babf），已经能被 R1 报出，因为 R1 签名本来就带架构。
   - 这一改动对其他引擎（P1、XV、ORD）同样适用：横纵两面的编码表本来就是按架构的，签名带上“会出错的架构”，就能抓到“架构改了编码”这一类引入。
2. **一个提交可能引入多个缺陷**：对位只看标注的那一个修复，会低估。可以改为“对位任一以该提交为 `Fixes:` 目标的修复”，查 `git log --grep "Fixes: <提交>"`。
3. TLB 在 44 + 48 个正常提交上没有一个误报，加进引擎组合没有代价，可以保留。

## 文件

- 判据：`criteria.md`、`criteria_sha256.txt`
- 代码：`cmtlb.py`、`run.sh`
- 结果：`results.json`、`score.log`、`report/`、`runall.log`；TLB 缓存在 WSL `/root/work/commitmode_cache/TLB/`
