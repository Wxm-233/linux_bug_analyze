# 判据修订 1（heldout_run_20261111）

2026-11-11，Claude。第一次试构建（L01 的修复前 LoongArch 内核）失败之后、任何候选的静态分析和运行之前写定。原判据不改。

## 原因

判据第四节写的 LoongArch 配置是 `loongson64_defconfig`。试构建发现较早的版本里没有这个文件：查了 10 个候选父提交的 `arch/loongarch/configs/` 目录（只看文件名），前 7 个只有 `loongson3_defconfig`，后 3 个和当前版本才有 `loongson64_defconfig`（另有 32 位的 `loongson32_defconfig`）。`loongson64_defconfig` 是 2025-12 加进来的，取代了 `loongson3_defconfig`。

## 修订

LoongArch 的配置取**该版本里的 64 位默认配置**：有 `loongson64_defconfig` 就用它，否则用 `loongson3_defconfig`。不用 32 位配置。其余不变。
