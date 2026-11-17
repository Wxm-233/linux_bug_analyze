# 动态验证新疑点 S6：匿名 shmem 在 force 模式下造出超过页缓存上限的 folio（s6dyn_20261116）

2026-11-16，Claude。用户：“动态验证 S6”。判据 `criteria.md` 和预测 `predictions.json` 在构建前写定；修订 1 `criteria_amendment1.md` 写在正式运行之前（改 QEMU 的 CPU 型号和内存大小）。SHA 都在 `criteria_sha256.txt`。

统计行：模型调用 0；Codex 调用 0；构建 2（全量 1、变异 1）；**新确认缺陷 1**（用户 11-16 确认，登记为 `../../confirmed_bugs.md` 的 B-2026-11-16-3，只在本地记录、不对外报告）；新疑点 0。

## 一句话结论

**S6 动态成立，判据第五节三个条件全部满足，4 格预测全部命中，12 次运行全部有效。**

在 arm64 64K 页内核上：
1. 把 `shmem_enabled` 设成 `force`；
2. 匿名共享内存缺页，拿到了一个整块 512MB（13 阶）的页缓存 folio；
3. 换出时每次都报 `WARNING: lib/xarray.c:1051 at xas_split_alloc`，这正是 2024 年 9fd154ba 当年修过的那个 WARN。

只要修复变异 F6（force 分支也按页缓存上限过滤），或者换成 always 模式，就拿不到 512MB 的 folio，也不报 WARN。4K 页内核拿到的是 2MB 的 folio，拆分正常。

## 疑点回顾（说人话）

页缓存（xarray）能拆分的 folio 最多 11 阶。64K 页时一个 PMD 是 13 阶（512MB）。

2024 年的几个修复给共享内存加了“超过上限就不用 PMD 大页”的过滤，但 `shmem_allowable_huge_orders()` 的 force 分支（`mm/shmem.c:1865-1866`）直接返回默认掩码 `BIT(13)`，漏掉了这层过滤。于是共享内存仍然会造出 13 阶的页缓存 folio。

之后要拆分它的时候（arm64 64K 没有 THP_SWAP，换出前必须拆），`xas_split_alloc` 发现阶数太大，报 WARN 并返回失败，拆分不了。

这个疑点由 `orddom_20261116`（新接口族“页大小派生阶数 × 页缓存上限”）找到。我起初判“不可能”，是 Codex 盲判时指出的，我读源码后裁定为“可能”。

## 做法

1. **内核**：kbuild 新配置档 `pg64k`（arm64 defconfig + 64K 页 + THP + zram 交换）。
   - 构建 plain 和修复变异 F6。F6 把 force 分支改成 `THP_ORDERS_ALL_FILE_DEFAULT & huge_shmem_orders_inherit`。
   - F6 第一次构建时预检失败：`shmem.i` 里同名函数先出现在头文件声明处，`region_start` 匹配错了地方。改为全文搜唯一标记后重建成功。
   - 4K 对照用现有的 `dyn` 镜像。
2. **测试程序 `s6.c`**：
   1. 写 `shmem_enabled`，读回确认；
   2. `MAP_SHARED | MAP_ANONYMOUS` 映射，取 PMD 对齐的一段，逐页写入；
   3. 用 kpageflags 确认首页是复合页的头、末页是复合页的尾（说明是整块 PMD 大小的 folio），并记录 smaps 的 `ShmemPmdMapped`；
   4. `MADV_PAGEOUT` 触发换出，`MADV_REMOVE` 打洞一页；
   5. 读回核对。
3. **修订 1**（调试中发现）：
   - 64K 内核用 QEMU `-cpu max` 启动时，initcall 全部完成后进不了 `/init`，改用 `cortex-a72`；
   - 内存 2GB 时找不到空闲的 512MB 连续块，13 阶分配会回退，改用 4GB。

## 结果（`judge_main.txt`、`judge_main.json`）

| 内核与模式 | 结论 | 拿到整块 PMD folio | 现象 |
|---|---|---|---|
| 64K plain，force | **复现 3/3** | 3/3（512MB，`ShmemPmdMapped` 524288 kB） | 3 次都是 `WARNING: lib/xarray.c:1051 at xas_split_alloc+0xf0/0x134` |
| 64K F6，force | 不复现 0/3 | 0/3 | 只用小页，无告警 |
| 64K plain，always | 不复现 0/3 | 0/3 | 非 force 分支按上限过滤，只用小页 |
| 4K plain，force（对照） | 不复现 0/3 | 3/3（2MB） | 拆分正常，页被换出 |

预测 4/4 命中。读回内容在所有运行里都正确：拆分失败后页仍在页缓存里，数据没有丢。打洞（非均匀拆分）没有额外告警。

## 看出的几点

1. **新接口族的第一个疑点就动态成立了**：“页大小派生阶数 × 页缓存上限”这一族，从常量表、纵向规则、两人盲判到动态验证，一条线走通。
2. **又是同类修复漏掉的位置**：b66b1b71 修了同一个函数的另一个 return，漏了 force 分支。这和 B-2（device-exclusive 那一系列修复漏了 `folio_referenced_one`）是同一种形态。“找修复漏掉的兄弟位置”值得作为固定策略。
3. **触发条件**：需要 root 把 `shmem_enabled` 设成 force（主要用于测试），而且机器上要有空闲的 512MB 连续内存。后果是内核 WARN、大页换不出去；数据不丢。
4. **只有 arm64 64K 受影响**。loongarch 64K、mips 64K 也越过了页缓存上限，但它们的伙伴系统最大阶小于 13，分配会回退，所以是潜伏的。
5. 只测了 v7.3-rc2；上游 v7.3-rc2 之后有没有修，没有查（需要联网）。

## 文件

- 判据：`criteria.md`、`predictions.json`、`criteria_amendment1.md`、`criteria_sha256.txt`
- 构建：`build.sh`、`build.log`、`build_f6.sh`、`build_f6.log`、`kernels/`
- 测试程序与调试：`s6.c`、`cc_check.sh`、`dbg_boot.sh`～`dbg_boot4.sh`
- 运行与判定：`run.sh`、`run_all.sh`、`smoke.sh`、`run_main.log`、`runs/`、`judge.py`、`judge_smoke.*`、`judge_main.*`、`stats.json`
- kbuild：`profiles.json` 加了 `pg64k` 档；`mutations/s6dyn.json`（F6）。WSL 新树 `df2908090cda_arm64_pg64k`，保留作复用。
