# 宏事实与跨架构采集：设计（实现前写定）

2026-10-28。动机：试点3两个候选均为跨架构宏可见性与取值（`MADV_*`、`CONFIG_MEMORY_FAILURE`下的`MADV_HWPOISON`/`MADV_SOFT_OFFLINE`），现有词表无宏事实与架构维度。

## 两层采集

1. **源码树层（全部`arch/*`，不需交叉编译器）**`kernel_facts.collect_tree`：
   - `kconfig`：`arch/<a>/Kconfig`中`select SYMBOL`行（含条件原文）；
   - `uapi`：对请求的UAPI头（如`asm/mman.h`），用宿主`gcc -E -dM -nostdinc`，包含路径`arch/<a>/include/uapi`、`include/uapi`；架构未提供该头时按`mandatory-y`语义改用`asm-generic/<头>`并记`generic_fallback`；记录请求宏是否定义及取值文本、可解析时的整数值、预处理错误。
2. **构建层（有交叉编译器的架构）**：沿用`collect`，对同一文件在各架构defconfig（加配置覆盖，如尝试打开`MEMORY_FAILURE`；实际值以`.config`为准）下编译，`build_ok`由构建返回码给出。

## 新查询（按架构上下文求值）

| 查询 | 值 | 边界 |
| --- | --- | --- |
| `kconfig_selects(symbol)` | bool | 只看本架构Kconfig顶层文件中的`select`，不展开`source`子文件与条件真值 |
| `uapi_defined(header, macro)` | bool | 用户态包含链终态（-dM），不是内核编译单元中使用点的状态 |
| `uapi_value(header, macro)` | int | 仅当宏体可解析为整数常量 |
| `build_ok(file)` | bool | 仅有交叉编译器的架构；失败原因另记 |

## 形式化与判定

事实名不带架构后缀，提示说明“同一关系按每个架构分别求值”；每个架构为一个独立上下文，交核心逐个判定，结果按架构列表汇总，即同用途跨架构对照（E3维度）。未采到的架构/事实不答，核心判不足。

## 不做

不安装新的交叉编译器（Alpha/MIPS/HPPA可经apt取得，Xtensa无，需用户另行批准）；不把用户态头终态当作内核编译单元的实际可见性；试点3已接触、不计评价。
