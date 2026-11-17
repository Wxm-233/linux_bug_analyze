# 判据修订 1（xvdom_20261116）

2026-11-16，Claude。写在看 S、MG、MS 三组任何结果之前；此前只看过“哪些输入类、哪些文件编得过”（`probe.log` 第一次运行）。

## 改什么

第二节“输入类”中，present 项的基础值由 `pfn_pte(P, PAGE_READONLY)`（PMD 为 `pmd_mkhuge(pfn_pmd(P, PAGE_READONLY))`）改为 **`pfn_pte(P, PAGE_SHARED)`**（PMD 同理）。其余变体照旧在这个基础值上构造。

## 为什么

第一次运行发现 `PAGE_READONLY` 在 riscv、s390、mips 上没有定义，present 类在这三个架构上全部编不过。按原判据会记为不可用，丢掉 riscv 这个主要检查对象。

`PAGE_SHARED`（用户态、可读写）在 8 个架构上都有定义。为了各架构可比，所有架构统一换成它，不按架构混用。

代价：基础值本身就带可写权限，所以 `pr.write` 变体和 `pr.plain` 可能相同，但不影响 S、MS 组“读出 1 / 改坏”的判断。
