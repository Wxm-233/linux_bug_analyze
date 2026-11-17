# 召回样本（写代码之前定下）

都是 2024 年“arm64 64KB 页时，PMD 阶数超过页缓存上限”这一组修复。逐个读过改动，确认属于“大阶数没和上限比较”。

| 提交 | 修复改动的函数 | 大阶数怎么进来的 |
|---|---|---|
| 9fd154ba926b mm/shmem: disable PMD-sized page cache if needed | `shmem_is_huge`（新加的包装） | shmem 直接按 `HPAGE_PMD_ORDER` 分配 |
| 3390916aca7a mm/filemap: skip to create PMD-sized page cache if needed | `do_sync_mmap_readahead` | 直接用 `HPAGE_PMD_ORDER` |
| 1f789a45c3f1 mm/readahead: limit page cache size in page_cache_ra_order() | `page_cache_ra_order` | 和上限比较了，但写错了（本判据的词法规则预计漏掉它） |
| d659b715e94a mm/huge_memory: avoid PMD-size page cache if needed | `__thp_vma_allowable_orders` 及 `huge_mm.h` 里的宏 | 经宏 `THP_ORDERS_ALL_FILE`（含 `PMD_ORDER`、`PUD_ORDER`） |
| b66b1b71d7ff mm: shmem: avoid allocating huge pages larger than MAX_PAGECACHE_ORDER for shmem | `shmem_allowable_huge_orders` | `BIT(PMD_ORDER + 1) - 1` |

排除的：
- `8732e14b7191`：性能改进，不是缺陷修复；
- `099d90642a71`：改的是上限本身的定义，没有消费者位置。
