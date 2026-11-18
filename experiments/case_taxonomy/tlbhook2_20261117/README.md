# TLB / 缓存钩子语义检查第二版（tlbhook2_20261117）

2026-11-17，Claude。用户：“继续你推荐的下一步改进”（第一项：扩大覆盖面，先做 tlbhook 第二版）。
- 判据 `criteria.md` 写在写代码之前，SHA 记在 `criteria_sha256.txt`，本轮没有修订。
- 第一版代码只读导入。
- 本轮新用的样本（503638e0babf、4edd70ee6a7d、8d6c8c40e733、Ali Tariq 的 KASAN 补丁）此后都算开发样本。

统计行：模型调用 0；Codex 调用 1（2 条盲判，新会话）；构建 0；新确认缺陷 0；新疑点 0。

## 一句话结论

**新增“按地址区域”的规则后，召回全部达标（第一版样本 5/5，新样本 3/3），并能在提交级检出 KASAN 缺陷的引入提交；当前版本的候选从 23 条降到 9 条，真问题一个没丢。**

| 指标 | 第一版 | 第二版 | 参考线 |
|---|---|---|---|
| 第一版样本召回 | 5/5（另 T1b 1/1） | **5/5** | 5/5 ✓ |
| 新样本召回（R1 两个、T1c 一个） | 不支持 | **3/3** | 3/3 ✓ |
| 当前版本候选数 | 23 | **9** | T2 ≤10 ✓（T2 为 7） |
| 其中“可能” / “说不清” / “不可能” | 1 / 1 / 21 | 1 / 1 / 7 | — |
| 两人一致率（新候选） | 91% | 2/2 | — |

## 改了什么

1. **新规则 R1：按地址区域判断 `flush_cache_vmap`**
   - 架构侧：从 `flush_cache_vmap` 的 `if` 条件读出它对哪些区域生效。当前只有 riscv 是按区域生效的，覆盖 vmalloc、module、vmemmap 三个区域。
   - 公共侧：按调用所在的文件，判断每处 `flush_cache_vmap(start, end)` 映射的是哪个区域。当前版本共 15 处调用：vmalloc 5 处、kasan 1 处、kmsan 8 处、vmemmap 1 处。
   - 区域不在覆盖范围内，并且这个架构在配置上支持该功能，就报。kmsan 在 riscv 上不支持（没有 `HAVE_ARCH_KMSAN`），所以不报。
2. **新规则 T1c**：架构的 `flush_cache_vmap` 靠一个标记函数（riscv 的 `mark_new_valid_map`）处理“新出现的有效映射”，但架构里另有把内核页表项改成有效的函数，只做了本地刷新，也没调这个标记函数，就报。
3. **撤掉 T1b**：riscv 的 `update_mmu_cache` 只刷本地是有意的设计。
4. **T2 降噪**：
   - 只认真正建映射的 `_noflush` 函数；
   - 回调函数算到注册它的函数头上；
   - 名字含 `flush` 的刷新包装函数也算刷新；
   - 调用链向上追到 8 层（原来 3 层）。
5. **T3 改成同一分支**：PMD 写法必须出现在 `flush_cache_page` 所在的最内层块或它的条件头里，不再按 ±15 行判断。

## 结果

### 1. 召回（`recall.json`）

| 样本 | 规则 | 结果 |
|---|---|---|
| 7e3811521dc3、d9807d60c145、7f9c9b607dc2、9add2cc22de6、19b482c29b6f | T1a、T2、T3、T3、T4 | 5/5 全部保持 |
| **503638e0babf**（riscv 开始按区域过滤 `flush_cache_vmap`） | R1 提交级 | 在这个提交上报出“riscv，kasan 影子区”，在它的父版本上不报。**这正是 Ali Tariq KASAN 补丁 `Fixes:` 标签指向的引入提交** |
| 4edd70ee6a7d 反事实 | R1 | 只换入 `mm/sparse-vmemmap.c`（加了调用，但 riscv 还不认 vmemmap 区域）时报；换入完整提交后不报 |
| 8d6c8c40e733 kfence | T1c | 修复前报 riscv 的 `kfence_protect_page`，修复后不报 |

### 2. 当前版本（`head.json`、`new_vs_v1.json`）

9 条候选：R1 1 条、T2 7 条、T3 1 条。

- **R1：riscv，`mm/kasan/shadow.c` 的 `__kasan_populate_vmalloc`**：裁定“可能”。这就是第一版里的新疑点，现在报在调用 `flush_cache_vmap` 的地方，比第一版报在回调 `kasan_populate_vmalloc_pte` 上更准。上游已经有人在实机上证实并提交了补丁。
- **T2 7 条**：都是第一版审过的。`zero_pte_populate` 仍是“说不清”，其余 6 条是“不可能”。
- **T3 `mm/ksm.c` 的 `replace_page`**：新候选，两人都判“不可能”。函数开头已经排除了大页。被报出来，是因为调用写在函数顶层，“同一分支”退化成了整个函数。

第一版有、第二版去掉的 16 条里，15 条在第一版裁定为“不可能”；剩下 1 条是 KASAN，已经改由 R1 报出。**所以降噪没有丢掉真问题。**

## 不足与下一步

1. **R1 的区域判断靠文件名**：没有归属的调用点算“未知”，不报；当前版本里所有调用点都有归属。新出现的映射区域（例如新的 sanitizer）要手工加进表里。
2. **R1 只对“按区域生效”的架构有用**：目前只有 riscv。它的价值在于新提交改了区域条件、或者新增了调用点时，能马上发现。所以适合接进提交级模式。
3. **T3 的一个漏洞**：调用写在函数顶层时，“同一分支”等于整个函数。可以改成“同一个基本块，或从函数开头到调用之间没有提前退出”。
4. **T2 仍有 6 条不成立**：hugetlb vmemmap 的重映射、kmap_local 的切换，属于“架构有别的机制”或“调用链上的刷新包得更深”。
5. **下一步**：把 R1、T1c、T2、T3、T4 作为第五个引擎（TLB）接进提交级模式，再在留出集上重测召回。注意：留出集里已经用于 tlbhook 设计的样本要剔除。

## 文件

- 判据：`criteria.md`、`criteria_sha256.txt`
- 分析器：`tlbhook2.py`、`run.sh`
- 结果：`head.json`、`head.log`、`new_vs_v1.json`、`recall.json`、`recall.log`
- 审查：`make_review.py`、`run_review.sh`、`review.txt`、`review.json`、`claude.json`、`codex_blind/`、`adjudication.json`
