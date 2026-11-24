# 复核判据修订 1：riscv 补开 STRICT_DEVMEM，让 PAGE_TABLE_CHECK 生效（rvpud_20261124）

2026-11-24，Claude。写于第二阶段镜像构建之后、任何试验运行之前。

**发现**：构建后核对配置，x86_64 镜像里 `PAGE_TABLE_CHECK`、`PAGE_TABLE_CHECK_ENFORCED` 都打开了，riscv 镜像里没有。原因是 `PAGE_TABLE_CHECK` 依赖 `EXCLUSIVE_SYSTEM_RAM`（`!DEVMEM || STRICT_DEVMEM`），riscv defconfig 打开了 `DEVMEM` 但没开 `STRICT_DEVMEM`；x86 defconfig 默认开了 `STRICT_DEVMEM`。

**修订**：配置档 `pfnmapdbg` 加 `STRICT_DEVMEM=y`，用 `--force` 重建 R0、RF 两个 riscv 镜像（X0 的配置里本来就有 `STRICT_DEVMEM`，不重建）。重建后核对两个 riscv 镜像都有 `PAGE_TABLE_CHECK=y`、`PAGE_TABLE_CHECK_ENFORCED=y`，才开始试验。`STRICT_DEVMEM` 只限制 `/dev/mem`，触发程序不用它，不影响试验。其他不变。
