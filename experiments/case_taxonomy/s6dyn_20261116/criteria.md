# 判据：动态验证新疑点 S6（匿名 shmem 的 force 分支造出超过页缓存上限的 folio）（s6dyn_20261116）

2026-11-16，Claude。用户：“动态验证 S6”。本文件和 `predictions.json` 在构建、运行之前写定，SHA 存入 `criteria_sha256.txt`。

## 一、疑点

`orddom_20261116` 裁定的 S6：
- `mm/shmem.c:1865-1866` 的 `shmem_allowable_huge_orders()` 在 `shmem_huge == SHMEM_HUGE_FORCE` 时直接返回 `huge_shmem_orders_inherit`，没有和 `THP_ORDERS_ALL_FILE_DEFAULT` 求交；
- arm64 64K 上，这个变量默认是 `BIT(13)`，而 `MAX_PAGECACHE_ORDER` 是 11；
- 预期后果：匿名 shmem 缺页分配到 13 阶（512MB）的页缓存 folio。换出时 `shmem_writeout()` 必须先拆分（arm64 64K 没有 THP_SWAP），均匀拆分会调用 `xas_split_alloc(…, 13, …)`，在 `lib/xarray.c:1051` 报 `WARN_ON` 并失败。

## 二、内核（写死）

1. kbuild 新配置档 **`pg64k`**：arm64 defconfig + `ARM64_64K_PAGES` + `TRANSPARENT_HUGEPAGE` + `SWAP` + `ZRAM` + `ZSMALLOC` + `DEVTMPFS`。版本 `df2908090cda`。
2. 修复变异 **F6**（`tools/kbuild/mutations/s6dyn.json`）：force 分支改为 `return THP_ORDERS_ALL_FILE_DEFAULT & READ_ONCE(huge_shmem_orders_inherit);`。
3. 镜像：arm64 `pg64k` 的 plain 和 F6；对照用现有的 arm64 `dyn` plain 镜像（4K 页），不重新构建。

## 三、测试（写死）

测试程序 `s6.c`，作为 init 运行：
1. 挂载 proc、sys、devtmpfs；在 zram 上建交换区；
2. 从内核命令行读 `s6mode=force|always`，写入 `/sys/kernel/mm/transparent_hugepage/shmem_enabled`，再读回记录；
3. `mmap` 一段 `MAP_SHARED | MAP_ANONYMOUS` 的区域，大小是两个 PMD，取其中 PMD 对齐的一段（64K 页时 512MB，4K 页时 2MB），逐页写入已知内容；
4. 记录 folio 阶数的证据：用 pagemap 和 `/proc/kpageflags` 看这段第 0 页是不是 COMPOUND_HEAD、最后一页是不是 COMPOUND_TAIL（两者都满足，说明整个 PMD 是一个 folio）；同时记录 smaps 的 `ShmemPmdMapped`；
5. `madvise(MADV_PAGEOUT)` 这一段（触发换出）；
6. 再 `madvise(MADV_REMOVE)` 中间一页（触发打洞时的拆分，只作观察）；
7. 由 CPU 读回全部内容，核对；输出 JSON 后关机。

QEMU：`-M virt -cpu max -m 2048M -smp 2`，每次超时 300 秒。

运行矩阵（各 3 次）：
- `pg64k` plain，`s6mode=force`；
- `pg64k` plain，`s6mode=always`；
- `pg64k` F6，`s6mode=force`；
- `dyn`（4K）plain，`s6mode=force`；

共 12 次。冒烟测试另跑，不计入。

## 四、判定（写死）

- **有效**：交换区建成；`shmem_enabled` 读回的当前值和要求一致；`mmap` 和写入成功（能输出步骤 4 之后的记录）。
- **异常**：测试阶段的内核日志里，有 `lib/xarray.c` 的 WARNING，或任何 WARNING、`BUG:`、Oops；或者读回的内容不对。
- 另外记录：是否拿到整个 PMD 大小的 folio（第 4 步）、换出后 present 页数。
- 每格的结论：有效次数中异常 ≥2 记“复现”；异常 0 记“不复现”；其余记“不稳定”；有效次数 <2 记“无效”。

## 五、S6 成立的条件（写死）

同时满足：
1. `pg64k` plain force：复现，并且至少 2 次拿到了整个 PMD 大小的 folio；
2. `pg64k` F6 force：不复现；
3. `pg64k` plain always：不复现。

4K 对照只用来核对预测。

## 六、规则

- 不安装、不联网、不调用大模型；只读 `/root/repos/linux`，变异只打在构建树里；不对外报告。
- 新构建树保留作复用。
