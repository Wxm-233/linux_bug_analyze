# 效果依赖线扩到新接口族：页大小派生的阶数 × 页缓存上限（orddom_20261116）

2026-11-16，Claude。用户：“先扩接口族”。属于 `xvdom_20261116/design.md` 第四节第 2 步。判据 `criteria.md`、召回样本 `samples.md`，都在写代码之前定下，SHA 在 `criteria_sha256.txt`。判据第二节标题里“写写死”是笔误，SHA 已经记下，没有改。

统计行：模型调用 0；Codex 调用 1；构建 0（只新建了 7 个 `modules_prepare` 目录）；新确认缺陷 0；**新疑点 1（S6）**。

## 一句话结论

**参考线全部达到，并找到一个新疑点 S6。** 横向常量表算对了：arm64 64K 的 `HPAGE_PMD_ORDER` 是 13，页缓存上限是 11。召回 4/5（80%）。

当前版本候选 59 条，审了前 30 条：
- 我判 30 条全部“不可能”；
- Codex 判 3 条“可能”，读源码后裁定 Codex 对：**匿名共享内存在 force 模式下没有按页缓存上限过滤**。在 arm64 64K 上会造出 13 阶的页缓存 folio，之后一拆分就会报 2024 年 9fd154ba 修过的那个 WARN。

这是 b66b1b71 修复时漏掉的一处，形态和 B-2 一样，属于“同类修复漏掉的位置”。

## 这一族是什么（说人话）

页缓存用 xarray 存放文件内容的 folio。xarray 能拆分的多索引项有上限 `MAX_XAS_ORDER`（11 阶），所以页缓存 folio 的阶数上限 `MAX_PAGECACHE_ORDER` 取它和 `HPAGE_PMD_ORDER` 中的小者。

“一个 PMD 能映射多大”随页大小变化：
- 4KB 页时是 2MB，9 阶；
- 64KB 页时是 512MB，13 阶，超过了上限。

公共代码如果拿 `HPAGE_PMD_ORDER` 直接去分配页缓存 folio，在 4KB 页的机器上一切正常，换到 64KB 页的 arm64 就会出错。这正是师兄文档里 9fd154ba 的例子，也是文档说的“值依赖”。

## 做法

1. **横向**（`probe_ord.py`）：沿用 encrank 的探针方法，新建 7 个页大小变体目录（arm64 16K/64K、loongarch 4K/64K、powerpc 4K、mips 16K/64K），在 15 个“架构 × 页大小”组合上算 8 个常量，结果见 `consts.md`。算不出常量的格子记为“未知”。
2. **纵向**（`orddom.py`，词法规则）：
   - 函数在“页缓存语境”里用到了大阶数来源（`HPAGE_PMD_ORDER`、`PMD_ORDER`、`PUD_ORDER`，以及宏体里递归含有它们的宏）；
   - 并且整个函数没出现任何页缓存上限守卫（`MAX_PAGECACHE_ORDER`、`mapping_max_folio_order`、`THP_ORDERS_ALL_FILE_DEFAULT` 等）；
   - 符合这两条就是候选。

## 结果

### 1. 常量表（`consts.md`）

| 组合 | HPAGE_PMD_ORDER | MAX_PAGECACHE_ORDER | 越界？ |
|---|---|---|---|
| x86_64、riscv、arm64、loongarch、mips 的 4K | 9 | 9 | 否 |
| s390 4K | 8 | 8 | 否 |
| arm64、loongarch、mips 的 16K | 11 | 11 | 否 |
| **arm64、loongarch、mips 的 64K** | **13** | **11** | **是** |
| arm 4K（没有 THP） | 未知 | 8 | `PMD_ORDER` 9 > 8 |
| powerpc 4K / 64K | 未知（运行时变量） | 未知 | 未知 |

另外几点：
- `PUD_ORDER` 在所有组合上都超过上限，不是跨架构差异；
- `MAX_PAGE_ORDER`（伙伴系统最大阶）在 arm64 64K 上是 13，在 loongarch 64K 上是 11，在 mips 64K 上是 10。所以后两者即便越过了页缓存上限，13 阶也分配不出来，会回退。

### 2. 召回（`recall.json`）：4/5 = 80%

| 样本 | 结果 | 名次 |
|---|---|---|
| 9fd154ba（shmem） | 命中 | 第 20 名 |
| 3390916aca7a（`do_sync_mmap_readahead`） | 命中 | 第 11 名 |
| 1f789a45c3f1（`page_cache_ra_order`） | **漏**，事先在 `samples.md` 里就预计会漏：它和上限比较了，只是写错了，词法规则看不出来 | — |
| d659b715e94a（`__thp_vma_allowable_orders`，经宏） | 命中 | 第 3 名 |
| b66b1b71d7ff（`shmem_allowable_huge_orders`） | 命中 | 第 8 名 |

### 3. 当前版本（`head.json`）

- 页缓存语境里用到大阶数的函数有 68 个，其中 5 个有守卫，4 个横向不越界；**候选 59 条**（参考线是不超过 60 条）。
- **噪声**：其中 30 多条来自交换簇代码。`SWAPFILE_CLUSTER` 被定义成 `HPAGE_PMD_NR`，所以宏闭包把它算成了来源；文件名 `swapfile` 又含有 `file`，碰巧符合了语境规则。这是判据的语境规则写得太宽，如实保留。

### 4. 两人盲判前 30 条（`claude.json`、`codex_blind/`、`adjudication.json`）

| | 我 | Codex | 裁定 |
|---|---|---|---|
| 可能 | 0 | 3 | **3（S6）** |
| 不可能 | 30 | 27 | 27 |

原始一致率 90%。三处分歧都在 shmem（第 20、23、24 条），读源码后裁定 **Codex 对，我判错了**。

## 新疑点 S6：匿名共享内存在 force 模式下造出超过页缓存上限的 folio（arm64 64K）

- **位置**：`mm/shmem.c:1865-1866`，`shmem_allowable_huge_orders()`：

  ```c
  if (shmem_huge == SHMEM_HUGE_FORCE)
      return READ_ONCE(huge_shmem_orders_inherit);   /* 没有和 THP_ORDERS_ALL_FILE_DEFAULT 求交 */
  ...
  return THP_ORDERS_ALL_FILE_DEFAULT & mask;          /* 只有这里过滤了 */
  ```
- **为什么会越界**：arm64 64K 上，`huge_shmem_orders_inherit` 默认是 `BIT(HPAGE_PMD_ORDER)` = `BIT(13)`（`shmem_init`，第 5418 行）。而 `shmem_parse_huge` 在 force 模式下恰好要求它等于这个值。
- **路径**：
  1. 管理员把 `/sys/kernel/mm/transparent_hugepage/shmem_enabled` 设成 `force`；
  2. 进程用 `MAP_SHARED | MAP_ANONYMOUS` 映射 512MB 对齐的区域，触发缺页；
  3. `shmem_get_folio_gfp` → `shmem_allowable_huge_orders` 返回 `BIT(13)` → `shmem_alloc_and_add_folio` 按 13 阶分配。arm64 64K 的 `MAX_PAGE_ORDER` 也是 13，分得出来；
  4. 这个 folio 被加入页缓存，xarray 里是一个 13 阶的多索引项。
- **后果**：之后拆分这个 folio 时，`xas_split_alloc` 报 WARN（`lib/xarray.c`）并失败。会拆分的场景有截断、`MADV_REMOVE` 打洞、换出（arm64 64K 没有 THP_SWAP，换出前必须拆）。现象和 9fd154ba 当年报的一样，换出也会一直失败。
- **由来**：
  - force 分支由 `e7a2ab7b3bb5`（2024-06）引入；
  - 9fd154ba（2024-07）加的检查保留在 tmpfs 那条路径（第 632 行的 `maybe_pmd_order`）；
  - b66b1b71（2024-08）只给最后一个 return 加了过滤，**漏了 force 分支**。
- **架构**：只有 arm64 64K 会出事。loongarch 64K、mips 64K 的伙伴系统分不出 13 阶，会回退。
- **严重性**：force 主要用于测试，需要 root 设置；但触发的是一个已知会报 WARN、会让换出失败的状态。
- **状态**：只做了静态判断，没有动态验证，也没查上游（v7.3-rc2 之后）是否已修。

## 看出的几点

1. **新接口族同样能出结果。** 编码探针加上纵向规则，套到“取值域”这类值依赖上也成立，而且第一次就找到了一个修复漏掉的位置。
2. **函数级的“有守卫就不报”会漏掉分支级的问题。** S6 真正出错的那一行，所在函数别处出现了守卫词，被规则放过了，是 Codex 顺着候选的调用链找回来的。下一版应该改成按 return 或分支判断守卫，而不是按整个函数。
3. **语境规则要收紧。** 现在一半候选是交换簇的噪声。可以把“页缓存语境”从子串匹配改成看是否用到 `mapping`、`xas_*` 等对象，并排除交换簇的宏。

## 文件

- 判据：`criteria.md`、`samples.md`、`criteria_sha256.txt`
- 横向：`prepare.sh`、`prepare.log`、`probe_ord.py`、`run_probe.sh`、`probe.log`、`consts.json`、`consts.md`
- 纵向：`orddom.py`、`run.sh`、`head.json`、`head.log`、`recall.json`、`recall.log`
- 审查：`make_review.py`、`run_review.sh`、`review.txt`、`review.json`、`claude.json`、`codex_blind/`、`agree.py`、`agreement.json`、`adjudication.json`
- `stats.json`
- WSL 新建的探针目录：`/root/work/encprobe/{arm64_16k,arm64_64k,loongarch_4k,loongarch_64k,powerpc_4k,mips_16k,mips_64k}`（每个只做了 `modules_prepare`，保留作复用）
