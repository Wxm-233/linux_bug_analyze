# 判据修订 2：ppc64le 的运行时分支对账（swapsym_20261121）

2026-11-21，Claude。写于生成变体之前。

- 原因：ppc64le（powernv_defconfig）同时编入 radix 和 hash 两种页表，`pte_none` 等先问 `radix_enabled()`。符号求值已按两种取值分别证明（修订 1 后的第二版代码），但 clang 无法把运行时判断折叠成常数，33 个对账值里只有 14 个（编码本身和 3 个常量）能对，19 个记“无法对账”。
- 补充两个同一实现的配置变体，让 `radix_enabled()` 在编译期确定：
  - `ppc64le_radix`：powernv_defconfig 关掉 `PPC_64S_HASH_MMU`；
  - `ppc64le_hash`：powernv_defconfig 关掉 `PPC_RADIX_MMU`。
- 做法与修订 1 相同（`make prepare` + `mm/memory.o`），判定与对账规则不变。若某个选项关不掉（olddefconfig 又打开），记“变体不可用”，ppc64le 的结论就注明“运行时分支部分未与编译器对账”。
- ppc64le 本身的结果保留；两个变体的结果单独列出，不合并计数。
