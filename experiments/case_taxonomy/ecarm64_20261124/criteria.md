# 判据：编译期检查宏 `BUILD_BUG_ON_ZERO` 按 0 求值（ecarm64_20261124）

2026-11-24，Claude。用户：“接着做待办，先查 arm64 不精确”。接 `ecunreach_20261123`：v6.11（`4dd7724f02ab`）上 PUD 级已有 3 个可比构建，但 PAGE_NONE 下 `pfn_pud>pud_mkhuge` 的 `pud_leaf`，x86_64 修复前为假、修复后为真，ppc64le 为真，**arm64 为“不精确”**，只剩 2 个构建可比，`144bb0aee33a` 因此未中。写于修改之前，此前只做了调试（`dbg_arm64*.py`）。

## 一、诊断

- 直接求 `pud_leaf(pud_mkhuge(pfn_pud(x, PAGE_NONE)))`，在页号位宽较小时（30 位）得到确定值“真”；按挖掘的取值范围（`MAX_PHYSMEM_BITS` = 52，页号 40 位）求，PUD 值的第 0、2～6 位混进了未知位，`pud_present`/`pud_leaf` 随之不精确。PAGE_READONLY 等带有效位（第 0 位）的保护值不受影响，所以只有 PAGE_NONE 这一格坏了。
- 根源：arm64 52 位物理地址下 `__phys_to_pte_val(phys) = (phys | (phys >> 42)) & PHYS_TO_PTE_ADDR_MASK`，掩码是 `GENMASK_ULL(49, 8)`；`GENMASK_ULL` 展开后带 `GENMASK_INPUT_CHECK`，即 `BUILD_BUG_ON_ZERO(...)` = `(int)sizeof(struct { int:(-!!(e)); })`。求值器求不出匿名结构体的 `sizeof`，整个掩码变成全部未知，`phys >> 42` 移到低位的页号位于是没被清掉。语法树里这个 `sizeof` 的拼写位置是 `include/linux/build_bug.h` 第 16 行（`BUILD_BUG_ON_ZERO` 的定义）。

## 二、修改（基础设施；判定规则不变，前几轮 `ec7.py`～`ec9.py` 的修改保留）

**拼写位置在 `include/linux/build_bug.h` 里的 `sizeof` 表达式求值为 0**（宽度取表达式本身的类型）。理由：这个文件里的 `sizeof(struct { int:(-!!(e)); })` 是编译期检查的写法，条件为真时编译失败，能编译成功的构建里它恒为 0（GNU C 里只含零宽无名位域的结构体大小为 0）。只认这个文件，不按名字或结构猜别的 `sizeof`。

## 三、运行

- 代码 `ec10.py` = `ec9.py` + 上面一项；缓存 `/root/work/ec_cache/v10`，重新表决 `/root/work/ec_cache/r10`。
- **核对**：在 arm64（df 与 v6.11）上，`PHYS_TO_PTE_ADDR_MASK` 的求值结果必须等于 clang 实际编译算出的常量；不等就停，不做后面的运行。
- **df**：21 个构建全部重新挖掘（`GENMASK` 用得很广，任何构建都可能受影响）；报告每个构建行为变化的条数。
- **9 个父版本**：只重新挖掘 df 上行为变化的构建，其余复用 `v9`；变化的构建多就如实报告。重挖前删除目标构建的旧行为文件（同上一轮修订 1）。

## 四、门槛与报告

- **G1**：v6.11 与 df 上，arm64 的 PAGE_NONE `pfn_pud>pud_mkhuge` `pud_leaf` 有确定值；v6.11 上这一格可比构建 ≥3。
- **G2 影响范围**：每个构建行为变化的条数、变化方向（如“不精确→确定”）；对确定值之间的翻转（如真变假）逐类说明。
- **G3 开发集召回**：9 个样本，父版本法，命中定义同第五轮。重点 `144bb0aee33a`。仍是开发集。
- **G4 df 噪声**：与上一轮 df 的 42 行比较，新增行不超过 30 行时，我先封存结论，再请 Codex 新会话盲审；超过 30 行只报分类统计。
- **G5 整版扫描**：`scan11.py`；8 个旧引擎条数不变，报告整表行数。

## 五、其他

不新装软件包、不联网；不运行内核；不读封存材料；源码副本用完即删，报告剩余空间。
