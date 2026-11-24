# 判据修订 1：试求函数体时编译期断言当空操作（ecpud_20261123）

2026-11-23，Claude。写于第一次 df 运行中途停下之后、正式运行之前。

第一次 df 运行（`logs/df.log`，挖掘做完、表决前停下，结果不用）发现修改 3 没有生效：ppc64le_hash 仍把 `radix_enabled()` 当运行时判断，行为文件与 ppc64le 相同。单独调试（`dbg_radix.py`）：函数体已经加载，但求值时遇到 `__compiletime_assert_8`（`BUILD_BUG_ON`/`compiletime_assert` 展开出的函数，只有声明、带 error 属性，没有函数体），求值器报“没有函数体”而放弃。

修订：**在修改 3 的试求过程中**，(1) 对 `__compiletime_assert_<数字>` 的调用当空操作。理由：这类函数一旦真被调用，内核就编译不过；能编译成功的构建里它们永远不会执行。(2) 修好 (1) 后又卡在 `__builtin_popcountl`（`mmu_has_feature` 的检查里），所以 `__builtin_popcount/ctz/clz/ffs`（含 `l`、`ll` 后缀）在实参为常量时按定义求值，非常量或 `ctz/clz(0)` 仍算求不出。两项都只用在试求函数体的过程中，其余求值不变。

其余规定不变。第一次运行的日志改名为 `logs/df_run1_stopped.log` 保留。
