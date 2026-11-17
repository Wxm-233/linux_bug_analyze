# 判据修订 1（p1dyn_20261115）

2026-11-15，Claude。写在内核构建之后、**任何测试运行之前**。

## 一、更正：riscv 并非不可达

判据第二节说 riscv“不支持 THP 迁移，也不支持 `MEMORY_HOTREMOVE`”，这是错的。我当时 grep 的是旧的配置名 `ARCH_ENABLE_THP_MIGRATION`。当前版本里：

- `thp_migration_supported()` 看的是 `CONFIG_ARCH_HAS_PMD_SOFTLEAVES`，riscv、x86_64、arm64 都选了，三个 `dyn` 内核里都是 `=y`；
- riscv 的 `dyn` 内核里 `MEMORY_HOTREMOVE`、`ZONE_DEVICE`、`DEVICE_PRIVATE` 都是 `=y`，只有 `TEST_HMM` 没开上（原因未查明，可能是依赖顺序）。

所以 riscv 也纳入 S1、S2 的测试，不再只作对照。

## 二、补充 riscv 的预测（按当前源码 `arch/riscv/include/asm/pgtable.h` 的交换项格式）

riscv 交换项：第 6 位是 exclusive 标记（与 `_PAGE_ACCESSED` 同一位），第 7～11 位是类型，`_PAGE_DIRTY` 是第 7 位，即类型的第 0 位。

- riscv 的 `dyn` 内核没开 `MEMORY_FAILURE`，`MAX_SWAPFILES` 为 25。迁移项类型：读 25、读独占 26、写 27；device-exclusive 是 30。arm64 开了 `MEMORY_FAILURE`，值相同。
- **S1**：`MADV_FREE` 之后的 THP 仍可写，迁移项是“写”类型 27（二进制 11011），第 0 位为 1，所以 `pmd_dirty()` 读出真；迁移项不带 exclusive 标记，`pmd_young()` 读出假。**预测：riscv 上 LazyFree 被少算、Private_Dirty 被多算，Referenced 不变**。如果迁移项实际是类型 26，dirty 为假，就看不到异常。
- **S2**：device-exclusive 类型 30 的第 0 位为 0，而且不带 exclusive 标记，所以 `pte_young()` 读出假，riscv 的 `ptep_test_and_clear_young()` 会先查 young 再清。**预测：riscv 不受影响**。

同时补一处：arm64 上迁移项“写”类型 27，最高位为 1，与原预测一致（Referenced 被多算）。

## 三、内核

- riscv 的 `dyn` 树：用 `scripts/config -e TEST_HMM` 加 `olddefconfig` 补开 `TEST_HMM`，然后强制重建并重新登记。如果仍然开不上，riscv 的 S2 记为不适用。
- 变异 F1、F2 补上 riscv。
- **F1 预检规则改正**：arm64 的 `pmd_young` 是宏，预处理后名字就没了，原来的规则“找 `present && pmd_young`”必然找不到，arm64 F1 因此预检失败（rc=3）。改为在 `smaps_pmd_entry` 里找 `present &&`（原函数没有这个写法）。这是我写预检规则的错误，变异内容本身不变。

其余判据不变。
