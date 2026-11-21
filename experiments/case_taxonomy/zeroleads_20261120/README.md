# 追 E-ZERO 的两条强疑点（zeroleads_20261120）

2026-11-20，Claude。用户：“追两条疑点”。疑点来自 `effzero_20261120` 在当前版本 `df2908090cda` 上的审查。

- 判据 `criteria.md`（115d993b…），写在上游检索和源码核对之后、构建和运行之前；没有修订。
- 统计行：模型调用 0；构建 2（arm32 修复前 1 次完整构建、打补丁后 1 次增量构建）；**动态确认 1**（arm32 原子池，属**已知但未合入**的问题，不是新缺陷）；疑点降级 1（Xen）。

## 结论

| 疑点 | 上游情况 | 实际影响 | 结论 |
|---|---|---|---|
| arm32 原子池块不清零 | 2018-07、2019-03、2022-12 三次有人提交过同一行补丁；Christoph Hellwig 两次回复“是对的”，Robin Murphy 也认可，一直没合入 | 所有非一致性设备上的原子 DMA 分配（不只 IOMMU 路径） | **QEMU 上确认**：修复前再分配读到上一次写入的全部 4096 字节，打补丁后为 0 |
| Xen grant DMA 分配不清零 | 没搜到相关报告 | 主要使用者 virtio 环自己带 `__GFP_ZERO`；不带的只找到 `virtio_rpmsg_bus` | **降为弱疑点**：违反 `518a2f1925c3` 的约定，但没找到实际依赖清零的使用者；需要 Xen 环境才能验证，这次没做 |

## arm32：源码和上游

- **路径**：arm32 有 MMU 时用 dma-direct。非一致性设备调 `arch_dma_alloc` → `__dma_alloc`；不能睡眠的分配（`GFP_ATOMIC`）走 `pool_allocator` → `__alloc_from_pool`，从 genalloc 原子池取块。块在 `__free_from_pool` 里只还给池，不清零。原子池 2012 年加入，2014 年改用 genalloc（`36d0fd2198da`），两种写法都没在再分配时清零。
- **约定**：`518a2f1925c3`（2018-12）定下“DMA 分配器返回的内存要能映射给用户态，分配时必须清零”。arm32 其他分配器经 `__dma_clear_buffer` 清零，通用池 `kernel/dma/pool.c` 第 318 行也清零；arm64 2015 年因同一问题修过（`6829e274a623`，E-ZERO 的开发样本 D1）。
- **上游**（lore.kernel.org）：
  - 2018-07：YueHaibing，“ARM: dma-mapping: always clear allocated buffers”，两版；
  - 2019-03：YueHaibing，“…always clear allocated buffers in __alloc_from_pool”，理由同样引用 `518a2f1925c3`；Christoph Hellwig 回复观察正确，希望 Russell King 也审；
  - 2022-12：Igor Klochko，“fix __alloc_from_pool returning a dirty buffer”，带 `Fixes: 36d0fd2198da`；Hellwig 认可；Russell King 担心会弄脏缓存行，Robin Murphy 解释池是非缓存映射、没有这个问题。线程停在 2023-01-03。
  - `df2908090cda`（2026-09）里仍没有这行。

## arm32：QEMU 验证

- 构建：`git archive` 出源码副本（不改仓库工作树），加开机自测 `zl_pooltest.c`（`late_initcall`），`ARCH=arm LLVM=1 multi_v7_defconfig`，只编 `zImage`，4 分 21 秒；打补丁后增量构建 16 秒。项目的 `tools/kbuild` 不支持 arm32，所以单独构建在 WSL `/root/work/zeroleads/`，构建目录已删，只留两个 `zImage`（共 25 MB）。
- 运行：`qemu-system-arm -M virt -cpu cortex-a15 -m 512`，不带根文件系统。
- 自测：注册一个非一致性平台设备（`coherent=0`），每轮分配 4 KiB、数非零字节、写满 `0xA5`、释放，共 8 轮；原子路径和 `GFP_KERNEL` 路径各一组。

| 内核 | 原子路径（`GFP_ATOMIC`） | 对照（`GFP_KERNEL`） |
|---|---|---|
| 修复前 | 第 0 轮 0；**第 1～7 轮都是 4096/4096 非零，首字节 `a5`**，且是同一地址 | 8 轮都是 0 |
| 打补丁后（`arm_pool_zero.diff`，即上游那一行） | 8 轮都是 0 | 8 轮都是 0 |

按判据第“判定”节：**确认**。

## 意义

- 对 E-ZERO 检查：这是检查在当前版本上**独立重新发现**的已知缺陷。它说明检查报的东西是真的，但不算新发现。
- 对上游：这个问题已有补丁和维护者认可，缺的是合入。我们的 QEMU 复现（两条日志对比）可以作为补充证据。**是否回复到上游线程、以谁的名义，由用户决定。**

## 文件

- `criteria.md`、`criteria_sha256.txt`
- `zl_pooltest.c`（开机自测）、`build_run.sh`（构建和运行）、`arm_pool_zero.diff`（补丁）
- `logs/`：`build_pre.log`、`build_patched.log`、`boot_pre.log`、`boot_patched.log`、`result_pre.txt`、`result_patched.txt`
- 镜像在 WSL `/root/work/zeroleads/zImage_pre`、`zImage_patched`
