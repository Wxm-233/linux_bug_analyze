# 召回样本（写代码之前定下）

从 v5.10 以来标题含 truncat 的修复里，逐个读改动，挑出“截断只在部分架构（32 位）上发生”的。

| 提交 | 形态 | 截断在哪 |
|---|---|---|
| bbc46b23af5b arch: copy_thread: pass clone_flags as u64 | A 窄化 | 各架构 `copy_thread()` 里 `unsigned long clone_flags = args->flags;`（`args->flags` 是 u64 字段） |
| 04ff48239f46 copy_sighand: Handle architectures where sizeof(unsigned long) < sizeof(u64) | A 窄化 | `copy_process()` 把 u64 的 `clone_flags` 传给 `copy_sighand(unsigned long clone_flags, …)` |
| 2d8c7edcb661 erofs: unify lcn as u64 for 32-bit platforms | A 窄化 | erofs 的 `lcn` 用 `unsigned long` 存放 64 位的逻辑簇号 |
| c99493ce409c erofs: fix offset truncation when shifting pgoff on 32-bit platforms | B 移位溢出 | `fpos = index << PAGE_SHIFT;`（`index` 是 `pgoff_t`） |
| c13094b894de iomap: avoid avoid truncating 64-bit offset to 32 bits | B 移位溢出 | `start_byte = folio_next_index(folio) << PAGE_SHIFT;` |
| f505e6c91e7a filemap: avoid truncating 64-bit offset to 32 bits | C 掩码截断 | `start = (start + bsz) & ~(bsz - 1);`（`start` 是 loff_t，`bsz` 是 size_t） |
| a63308ab426f ocfs2: fix readdir position truncation on 32-bit kernels | C 掩码截断 | `ctx->pos & ~(sb->s_blocksize - 1)`（`s_blocksize` 是 unsigned long） |
| a5a5ed23b134 udf: Fix i_lenExtents truncation on 32-bit kernels | C 掩码截断 | `… & ~(sb->s_blocksize - 1)` |

排除的：
- `660b982305ce`（ntfs）：窄的那一方是 `u32`，在所有架构上都会截断，不是跨架构缺陷；
- `7a4b21250bf7` 等 bpf 的三个：`roundup_pow_of_two` 在 32 位上溢出，属于“随位宽变化的算术溢出”，不在本轮规则范围；
- `f8cd9193b62e`（ucount）：`long` 传给 `int`，只在 64 位上截断（方向相反），本轮不做；
- `272b0d84b17f`、`616795d7db00`：`int` 和 `unsigned int` 的宽度在各架构上相同，不是跨架构。
