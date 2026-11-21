# 判据：追 E-ZERO 的两条强疑点（zeroleads_20261120）

2026-11-20，Claude。用户：“追两条疑点”。疑点来自 `effzero_20261120`：arm32 原子池块不清零、Xen grant DMA 分配不清零。

## 已查到的（写判据之前）

- **上游检索**（lore.kernel.org，内置浏览器）：
  - arm32：同一问题 2018-07（YueHaibing，两版）、2019-03（YueHaibing）、2022-12（Igor Klochko）共三次提交过一行补丁（在 `__alloc_from_pool` 里 `memset`）。2019 年那次的理由同样引用 `518a2f1925c3`；Christoph Hellwig 两次都回复“看起来是对的”。2022 年那次 Russell King 担心会弄脏缓存行，Robin Murphy 解释池是非缓存映射，没问题。之后没有下文，`df2908090cda` 里仍没有这行。
  - Xen grant DMA：按函数名和文件名都没搜到有关清零的报告。
- **源码**（`df2908090cda`）：
  - arm32 有 MMU 时用 dma-direct，非一致性设备调 `arch_dma_alloc` → `__dma_alloc`；不能睡眠的分配走 `pool_allocator` → `__alloc_from_pool`。所以影响面是**所有非一致性设备上的原子 DMA 分配**，不只 IOMMU 路径。池自 2012 年加入以来，块被再分配时从没清零过。
  - Xen：`xen_grant_dma_alloc` 不清零，但最主要的使用者 virtio 环（`virtio_ring.c` 1306、1321 行和 packed 环）自己带 `__GFP_ZERO`；其他直接在 virtio 设备上分配、且不带清零的使用者只找到 `virtio_rpmsg_bus`。

## 这一步做什么

**arm32 动态验证**（Xen 不做：需要 Xen 环境，且没找到实际依赖清零的使用者，降为弱疑点）：
- 版本 `df2908090cda`；`ARCH=arm`、`LLVM=1`、`multi_v7_defconfig`，只编 `zImage`。项目的 `tools/kbuild` 不支持 arm32，这次单独构建在 WSL `/root/work/zeroleads/`，源码是 `git archive` 的副本，在副本里加一个开机自测文件 `lib/zl_pooltest.c`（`late_initcall`，`obj-y`），不改仓库工作树。
- QEMU：`qemu-system-arm -M virt -cpu cortex-a15 -m 512`，不带根文件系统，自测打印结果后内核找不到 init 而停下，属正常。
- 自测内容：注册一个平台设备，设 32 位 DMA 掩码（不设一致性，即非一致性设备）：
  1. **原子路径**：`dma_alloc_coherent(GFP_ATOMIC)` 4 KiB，数非零字节，写满 `0xA5`，释放；同样大小再分配，数非零字节。重复 8 轮。
  2. **对照**：`GFP_KERNEL` 分配（走 remap 或 CMA，有 `__dma_clear_buffer`），先写满再释放、再分配，数非零字节。
- 再做一次**打补丁后**的构建：在副本的 `__alloc_from_pool` 里加上游补丁那一行 `memset(ptr, 0, size);`，增量构建，同样运行。

## 判定（事先写定）

- **确认**：修复前，原子路径从第 2 轮起至少有一轮读到非零（预期是上一轮写的 `0xA5`），且对照路径读到 0；打补丁后原子路径各轮都读到 0。
- 修复前原子路径各轮都是 0：疑点不成立（或这个配置走不到池），如实记录，查原因。
- 构建或启动失败：记录失败原因，不改判定。

## 其他

- 不上报、不联系任何人；是否把结果补充到上游线程由用户决定。
- 构建目录用完删除，只留两个 `zImage` 和日志。
- 统计行：模型调用 0；构建 2（修复前、打补丁后增量）。
