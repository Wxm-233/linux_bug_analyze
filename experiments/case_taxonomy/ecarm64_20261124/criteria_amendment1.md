# 判据修订 1：新版内核里 `BUILD_BUG_ON_ZERO` 换了写法（ecarm64_20261124）

2026-11-24，Claude。写于第三节“核对”之后、任何挖掘运行之前。

**核对结果**：v6.11（`4dd7724f02ab`）上 arm64 的 `PHYS_TO_PTE_ADDR_MASK` 求值为 0x3ffffffffff00，与 clang 一致；df2908090cda 上仍是全部未知，不一致，按判据停下。

**原因**：df 上 `BUILD_BUG_ON_ZERO(e)` 改为调用 `include/linux/compiler.h` 里的 `__BUILD_BUG_ON_ZERO_MSG(e, msg, ...)`，写法是 `((int)sizeof(struct {_Static_assert(!(e), msg);}))`，`sizeof` 的拼写位置在 `compiler.h` 第 200 行，不在 `build_bug.h`。

**修订**：第二节的规则改为——**匿名结构体的 `sizeof`，拼写位置落在 `include/linux/build_bug.h` 或 `include/linux/compiler.h` 里、名字含 `BUILD_BUG_ON_ZERO` 的宏定义之内，求值为 0**。判断方法：按拼写位置的文件和行号，向上找到所在宏定义的 `#define` 行（处理续行），看宏名。两种写法（`int:(-!!(e))` 无名位域、`_Static_assert`）在能编译成功时结构体都为空，GNU C 中大小为 0。其他 `sizeof` 不变。

核对要求不变：两个版本都要与 clang 一致才继续。
