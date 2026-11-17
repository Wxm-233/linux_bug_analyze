# 修订 1：更正第三节对修复范围的描述

2026-11-09 19:10，Claude。写于判据定稿（SHA `d124fd00…`）两分钟后，此时**没有生成任何用例、没有运行任何测试**。

## 原文

第三节：“这 5 个修复都只改 `arch/riscv/`（修复前后的 diff 可核对）”。

## 核对结果（`git show --stat`）

| 样本 | 修复提交 | 改动的文件 |
| --- | --- | --- |
| A101 | `2116988d5372` | `arch/riscv/include/asm/processor.h` |
| A310 | `61119394631f` | `arch/riscv/kernel/traps.c` |
| A171 | `890ba5be6335` | `arch/riscv/include/asm/pgtable.h` |
| A181 | `1046791390af` | `arch/riscv/include/asm/uaccess.h` |
| B467 | `c625154993d0` | `drivers/perf/riscv_pmu_legacy.c`、`drivers/perf/riscv_pmu_sbi.c` |

## 更正

原文改为：“这 5 个修复只改 riscv 专用的代码：4 个在 `arch/riscv/` 下，B467 在 `drivers/perf/riscv_pmu_*.c`（只在 riscv 上编译）。所以修复提交的 arm64、x86 与修复前的公共代码相同。”

结论（参照取修复提交的版本可行）不变。第 4.1 节的抽取范围不含 `drivers/`，B467 的修复位置因此不在静态范围内；这一点按原规则保留，在分环节诊断里如实记为“候选覆盖”未覆盖，不为它扩大范围。
