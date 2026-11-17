# 第二标注人盲判记录

日期：2026-11-17。标注人：Codex。

只读取本轮允许的 `review.txt`、`criteria.md`、`samples.md`、`widths.md`、`codex_blind/` 和必要的内核源码。未读取第一标注人或裁定文件、旧轮次判断、交接文档、进度日志、confirmed_bugs；未构建、联网、安装软件或调用其他模型。工作日志只在完成后追加，未读取原有内容。

源码均通过已有 `read_source.sh` 的 `show` / `grep64` 读取，固定版本为 `df2908090cda`。这里的判断依据为源码和整数语义，未进行运行时触发验证。

本次使用的既定判据 `../criteria.md` 的 SHA256：

`5E7CB578DE5330E60A8A9FA770472143485EA8B9A2A7A807D26959BAED1F10FD`

## 结果

共 30 条：可能 7 条（1、18、19、20、21、29、30）；不可能 22 条；说不清 1 条（28）。这些是逐条报告的判断，不是去重后的缺陷数量，也不是动态确认的缺陷数量。

## 容易误判的依据

- **2～7：巨页内偏移和对齐。** `include/linux/hugetlb.h:771-788` 定义巨页大小、掩码和移位；`mm/hugetlb.c:4200` 用 `~(huge_page_size(h)-1)` 初始化 `h->mask`。因此 `~huge_page_mask(h)` 恰好保留页内低位，清除文件偏移的高位符合这些语句的用途。
- **8：宏的真实展开。** `include/linux/mm.h:3175` 的 `offset_in_folio()` 是 `((unsigned long)(p) & (folio_size(folio)-1))`，并非完整的 64 位文件位置。`mm/filemap.c:3189` 对完整位置的更新已经把 `bsz` 转为 `u64`。
- **9、13～14、22～26：间接配置依赖。** `mm/Kconfig:514-519` 的 `MEMORY_HOTPLUG` 明确依赖 `64BIT`；`MEMORY_HOTREMOVE` 位于其 `if` 块中（522、582、590 行），`ZONE_DEVICE` 又依赖 `MEMORY_HOTREMOVE`（1225～1228 行）。`FS_DAX` 依赖 `ZONE_DEVICE`（`fs/Kconfig:58-63`），`FUSE_DAX` 依赖 `FS_DAX`（`fs/fuse/Kconfig:43-49`），`fs/fuse/Makefile:17` 仅在 `FUSE_DAX` 下加入 `dax.o`。
- **9 的调用可达性。** `unmap_and_kill()` 仅有 `mm/memory-failure.c:1814` 和 1855 两个调用点，分别来自 dev_pagemap 和 FS_DAX 路径。前一路径由 2418～2422 行的非空 `get_dev_pagemap()` 结果触发；未启用 `ZONE_DEVICE` 时该函数恒返回 NULL（`include/linux/memremap.h:282-285`）。普通 RAM 的故障处理不调用这个辅助函数，不能用普通文件缓存的高偏移作为该报告在 32 位上的触发证明。
- **10：跨度不同于物理地址。** `arch/arm/mm/init.c:75-80` 的 `find_limits()` 以 memblock 当前上限设置 `max_low_pfn`；`arch/arm/mm/mmu.c:1191-1219` 将低端映射上限裁到 `vmalloc_limit`。这里转换的是直接映射低端内存跨度，不是可能高于 4 GiB 的物理地址，也不包括 HIGHMEM 容量。
- **11～12、15～16：具体编译分支。** parisc 两条位于 `CONFIG_64BIT` 分支（213～240 行）；sparc 和 x86 的 Makefile 分别选择 `smp_$(BITS).o`、`init_$(BITS).o`。未把其他架构的 32 位类型宽度套到这些代码上。
- **17：不能只看 ext2 磁盘大小字段。** ext2 确实只为普通文件读取 `i_size_high`（`fs/ext2/inode.c:1412-1415`），但排除本行所用的更强依据是 `include/linux/pagemap.h:1593-1596`：`dir_pages()` 在右移前先转 `unsigned long`。32 位上的 `npages` 最大为 `ULONG_MAX>>PAGE_SHIFT`，而待判断语句只在 `n<npages` 的循环中执行；4 KiB 页下 `n` 最大为 1048574，左移仍不溢出。目录页数可能更早发生问题，此记录仅判断所报的第 292 行。
- **27：必须用块号的上界。** `fs/gfs2/quota.c:217-226` 的 `qd2index()` / `qd2offset()` 和 `include/linux/quota.h:65` 的 32 位 `qid_t` 给出位置上界；`include/uapi/linux/gfs2_ondisk.h:215-220` 的配额记录为 88 字节。最大记录末端为 `2^33*88=755914244096` 字节，即 704 GiB；`fs/gfs2/ops_fstype.c:169-176` 校验块大小至少 512 字节。最大配额文件逻辑块号是 1476395007（小于 `2^31`），本行从页号转块号不会溢出。

## “可能”条目的条件与限制

- **1：** `fs/ext4/ext4.h:3527-3535` 表明启用 `largedir` 后目录大小可使用高 32 位；还须确实进入线性 `ext4_readdir()` 并遇到目录版本变化。`fs/ext4/dir.c:147-160` 包含从索引读取回退到线性扫描的路径。
- **18～19：** `writeback_index` 为 `pgoff_t`；`mpd->start_pos/end_pos` 为 `loff_t`。后续 `mpage_prepare_extent_to_map()` 从这两个位置计算查找区间（`fs/ext4/inode.c:2613-2614`、2633～2635 行），所以影响扫描行为。两条属于同一函数中的同类转换，未视为两个独立根因；第 19 条使用 5 GiB 例子，避免把恰好 4 GiB 处无符号减一得到的正确终点误说成溢出错误。
- **20～21：** 调用入口只检查对齐及 `max_file_blocks()`（`fs/f2fs/file.c:3186-3192`），未限制为 32 位字节位置。后果直接体现为预写回区间错误；没有声称已经验证最终文件内容损坏。后续整理仍有逐页等待和写回，不能仅凭这两行就推导出必然数据损坏。
- **29：** `fs/nilfs2/page.c:518-578` 会跨 `folio_batch` 累计连续的延迟分配块，批次大小不是累计长度的上限。触发要求这些块的总字节数达到 4 GiB，需要有足够 HIGHMEM 及合适的脏页限制，不能只创建一个大稀疏文件。4 KiB 块下，1048576 块应为 4294967296 字节，而 32 位左移得到 0。
- **30：** `fs/nilfs2/recovery.c:36-44` 确认 `rb->blkoff` 为 `unsigned long`，381 行从日志逻辑块号赋值。用 1048576 这个本身可被 32 位保存的块号，就足以在 4 KiB 块下使第 543 行的字节位置从 4 GiB 回绕到 0；不需要依赖更早那次赋值的窄化。

## 保留的疑问

**28：** `simple_getattr()` 的确被 ramfs 使用（`fs/ramfs/file-mmu.c:52-55`），但其数据源是 `mapping->nrpages`，不是 `i_size` 或最高页号。首个溢出条件是至少 `2^(32-(PAGE_SHIFT-9))` 个驻留基础页，等价于 2 TiB 的实际缓存量，且还需要存放 `struct page`、页缓存索引等元数据。i386 PAE 的源码上界为 36 个物理地址位（`arch/x86/include/asm/sparsemem.h:19-25`），不能作为这样的触发平台；其他 32 位的大页、扩展物理地址及内核元数据容量组合未得到全面可达性证明。因此本条判“说不清”，保留给后续裁定。

## 验证

用整数运算复核了上述 5 GiB→1 GiB、4 GiB→0、配额文件块号上界及 ext2 循环变量上界。对输出进行了 JSON 解析、30 项数量、编号唯一且连续、位置与 `review.txt` 一致、字段集合和判定取值校验；运行时复现结果为 `null`。
