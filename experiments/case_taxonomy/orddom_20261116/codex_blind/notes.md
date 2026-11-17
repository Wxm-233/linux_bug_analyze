# 第二标注人盲判记录

日期：2026-11-16。源码版本：`df2908090cda`。

我只读取了本轮允许的 `review.txt`、`criteria.md`、`samples.md`、`consts.md`、`codex_blind/read_source.sh` 及内核源码；没有读取其他标注人的结果、裁定文件、各轮 README、交接文档、进度日志或 confirmed_bugs。源码均通过给定的 `read_source.sh` 从固定版本读取，没有构建、联网、安装、修改源码或调用其他模型。

沿用已有判据，没有修改判据。`criteria.md` 的 SHA256 为：

`643ab513236c81cd51dd66aa6ff1668544019fe381aab8f4d42194c7b9612378`

`codex.json` 共 30 项：“可能”3 项（20、23、24），“不可能”27 项，“说不清”0 项。三个“可能”对应同一条可达的超限分配路径，不能据此计为三个独立缺陷。以下后果都是静态推导，运行复现次数和运行观察到的 WARN 次数均为 `null`。

## shmem force 路径

我找到的反例是 **arm64 × 64KB 页**，使用默认的 shmem 阶数继承设置，将全局 `shmem_enabled` 设置为 `force`，随后对满足 PMD 对齐和范围要求的匿名共享映射触发缺页。这里的匿名共享映射用 shmem 页缓存；它满足 `vma_is_anon_shmem()`，与 `do_huge_pmd_anonymous_page()` 处理的普通匿名 VMA 不同（`mm/shmem.c:284-291,5908-5918`）。

该组合在给定常量表中有：

| 常量 | 值 |
|---|---:|
| PAGE_SHIFT | 16 |
| HPAGE_PMD_ORDER | 13 |
| MAX_PAGECACHE_ORDER | 11 |
| XA_CHUNK_SHIFT | 6 |
| MAX_PAGE_ORDER | 13 |

PMD 大小为 `2^(16+13)` 字节，即 512 MiB。`arch/arm64/Kconfig:1739-1758` 也表明默认物理页分配上限为阶数 13，因此这条路径的分配并不会必然被 buddy 上限挡住；需要有足够的连续内存、记账额度及可用文件空间。缺页地址所在的 PMD 必须完全落在映射范围内，页缓存对应区间为空，THP 未被硬件或进程策略禁止。

具体数据流和控制流如下：

1. **来源，第 24 项。** `shmem_init()` 在未显式配置各阶数策略时把 `huge_shmem_orders_inherit` 设为 `BIT(HPAGE_PMD_ORDER)`（`mm/shmem.c:5413-5418`），此处得到 `BIT(13)`。
2. **策略入口，第 20 项。** `shmem_parse_huge()` 在继承掩码恰为 `BIT(HPAGE_PMD_ORDER)` 时允许 `force`（`672-703`）；`shmem_enabled_store()` 将其写入 `shmem_huge`（`5457-5479`）。这个比较的结果决定该策略能否进入后续超限分配路径，因此本项按可达路径判为“可能”。
3. **首次上限检查确实存在。** `shmem_huge_global_enabled()` 计算 `maybe_pmd_order`，当 13 大于 11 时返回 0，即使是 force 也如此（`627-641`）。因此我没有把普通 tmpfs 的 force 或正常 shmem 策略直接当作反例。
4. **检查结果被匿名共享内存的 force 分支绕过。** `shmem_allowable_huge_orders()` 先调用上述函数取得 `global_orders=0`（`1848-1849`），但对 `vma_is_anon_shmem(vma)` 不走 `1851-1852` 的提前返回；当 `shmem_huge == SHMEM_HUGE_FORCE` 时在 `1865-1866` 直接返回原始继承掩码。它没有经过 `1877` 的 `THP_ORDERS_ALL_FILE_DEFAULT & mask`。
5. **消费点，第 23 项。** `shmem_fault()` → `shmem_get_folio_gfp()` → `shmem_allowable_huge_orders()` → `shmem_alloc_and_add_folio()`（`2710-2735,2509-2528`）。`shmem_suitable_orders()` 只检查 VMA 对齐、大小和页缓存冲突（`1880-1914`）；其内部的 `thp_vma_suitable_orders()` 也只是对齐检查（`include/linux/huge_mm.h:214-296`），不会重新调用 allowable 过滤。
6. **超限项进入页缓存。** `shmem_alloc_and_add_folio()` 按阶数 13 分配（`1960-1965`），再调用 `shmem_add_to_page_cache()`（`2001`）。后者直接用 `folio_order(folio)` 构造 `XA_STATE_ORDER` 并执行 `xas_store()`（`892-948`），没有将阶数限制到 11。

这里的 `SHMEM_HUGE_FORCE` 是 sysfs 的分配策略；`TVA_FORCED_COLLAPSE` 是 MADV_COLLAPSE 等入口使用的合并检查类型。文件合并的后者仍受 `__thp_vma_allowable_orders()` 开头的文件阶数掩码限制，不能用这条反例把第 4、15、16 项也判为“可能”。

### 静态可证明的后果

我使用当前源码仍保留的**均匀拆分路径**建立后果，没有假定所有截断操作都会沿用历史样本的拆分方式。

- `arch/arm64/Kconfig:99` 只在 4KB 页时选择 `ARCH_WANTS_THP_SWAP`，而 `mm/Kconfig:971-979` 中 `THP_SWAP` 依赖该选项，所以 arm64-64k 的 `THP_SWAP=n`。
- 启用 swap、使上述页变脏并进入回收，在无额外固定引用等阻碍时，`shrink_folio_list()` 的 `pageout()` 调用 `shmem_writeout()`（`mm/vmscan.c:618-658`）。
- `shmem_writeout()` 因 `!IS_ENABLED(CONFIG_THP_SWAP)` 要求拆分，调用 `split_folio_to_list()`（`mm/shmem.c:1624-1648`）。它经 `split_huge_page_to_list_to_order(..., 0)` 进入 `SPLIT_TYPE_UNIFORM`（`mm/huge_memory.c:4388-4394,4455-4457`）。
- `__folio_split()` 设置目标阶数为 0 后，调用 `xas_split_alloc(&xas, folio, old_order, gfp)`（`4183-4188`）。此时 `old_order=13`、`xa_shift=0`，满足 `0 + 2 * 6 <= 13`。
- `lib/xarray.c:1050-1052` 因而执行 `WARN_ON`，并在 `1072-1074` 设置 `-ENOMEM`，拆分失败；`shmem_writeout()` 返回 redirty 路径。无需声称存在数据结构损坏即可满足题目的后果要求。

这也解释了为什么“插入成功”和“超过页缓存上限”能同时发生：当前 `MAX_XAS_ORDER` 所针对的是 `xas_split_alloc()` 的拆分能力，`xas_store()` 并没有相同的硬上限（`include/linux/pagemap.h:369-387`）。第 21 项处的 `HPAGE_PMD_ORDER` 本身只用于拆分成功后的统计；坏输入在它前面的拆分调用处暴露，不是该统计比较制造了大阶数。

## 其余报告的主要排除依据

| 报告 | 核查结果及关键源码 |
|---|---|
| 1、2 | DAX 是明确例外：`include/linux/huge_mm.h:81-89`；`fs/dax.c:687-770` 对零/空项降级时删除原项，真实 DAX 项保留，不调用 `xas_split_alloc()`。arm-4k 的常量虽越过 8，但给定组合 THP=n，`FS_DAX_PMD` 也因 `fs/Kconfig:90-95` 的依赖关闭。 |
| 3、17 | 普通匿名内存，不创建文件页缓存项；分别核对 `mm/memory.c:6379-6385` 和 `mm/migrate_device.c:995-1015` 的调用者。 |
| 4、15、16 | 合并入口调用 `collapse_possible()`，经 `collapse_possible_orders()` → `thp_vma_allowable_orders()` → `__thp_vma_allowable_orders()`，先与 `THP_ORDERS_ALL_FILE_DEFAULT` 相交；位置为 `mm/khugepaged.c:568-585,1887,2887,3195`，以及 `mm/huge_memory.c:131-141`。强制合并不会跳过这一步。 |
| 5、7、8、10、11、12、13、19 | 已有 folio 的页表、反向映射、引用或 RSS 操作；没有用命中常量创建超限页缓存项。第 13 项拆的是 PMD 映射，不能与第 23 项后果中的页缓存项拆分混同。 |
| 9 | 页表自测的内存；`debug_vm_pgtable_alloc_huge_page()` 已比较 `MAX_PAGE_ORDER`，必要时尝试连续页分配，失败有跳过/回退（`mm/debug_vm_pgtable.c:1045-1064,1235-1265`）。 |
| 14、21 | 阈值只决定 THP 统计类别；实际拆分目标来自输入，未用该常量生成新的大项。 |
| 22 | 仅决定 khugepaged 是否需要运行（`mm/khugepaged.c:515-529`），实际文件合并另有上述掩码过滤。 |
| 6、18、25—30 | 当前 swap cache 用每簇平面数组，非同阶数 xarray 项；见下述说明。 |

### swap cache 与普通页缓存的区别

`mm/swap_table.h:9-19` 声明 `entries[SWAPFILE_CLUSTER]`；分配器按该结构大小分配，恰好等于一页时分配阶数 0 页（`mm/swapfile.c:449-469,3946-3949`）。`__swap_cache_do_add_folio()` 将一个大 folio 逐槽写入此数组（`mm/swap_state.c:209-230`），源码 `376` 行还明确说明它保存 N 个条目，而非一个高阶条目。

`swap_cache_alloc_folio()` 的 525-527 行已拒绝超过簇大小的请求，分配失败按输入允许的阶数退回（529-539）。因此不能把对 `SWAPFILE_CLUSTER` 的比较误读成“拿 PMD 大阶数作为 xarray 项的阶数”。另外，`SWAPFILE_CLUSTER` 只有在 `CONFIG_THP_SWAP=y` 时才等于 `HPAGE_PMD_NR`，否则固定为 256（`mm/swap.h:31-37`）；这在 arm64-64k 上进一步挡住了阶数 13 的 swap cache 请求。

## 核查方式和未验证事项

使用给定脚本的 `show` 与 `grep64` 读取固定版本源码，重点命令例如：

```text
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/orddom_20261116/codex_blind/read_source.sh show mm/shmem.c 627:703 1818:2041 2509:2528 5376:5419 5457:5479
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/orddom_20261116/codex_blind/read_source.sh show mm/huge_memory.c 121:151 4103:4189 4388:4395 4455:4458
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/orddom_20261116/codex_blind/read_source.sh show lib/xarray.c 1032:1075
```

没有运行内核、调整 sysfs、分配测试页或观察真实 WARN。没有重新测量常量表，也没有把 powerpc 的未知常量当作“不越界”；相应报告的排除依据是用途或调用链与该页缓存阶数限制无关。JSON 的结构、编号、枚举和报告位置另做文件格式核对，不属于运行复现。
