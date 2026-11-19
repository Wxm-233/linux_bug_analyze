# 修订 2（看过开发样本 M18 没报出之后写下）

2026-11-19，Claude。

**问题**：判据二规定“在用”看 `arch/<a>/Kconfig` 里有没有 `select HAVE_ARCH_TRANSPARENT_HUGEPAGE(_PUD)`。powerpc 的这条 select 写在 `arch/powerpc/platforms/Kconfig.cputype` 里，不在 `arch/powerpc/Kconfig`，于是 powerpc 被当成“不用 THP”，M18 没报出。

**改动**：“在用”改为看 `arch/<a>/` 下所有名字以 `Kconfig` 开头的文件（任意子目录）。

**说明**：这是看到开发样本结果之后改的，开发样本本来就不算独立检验。主线、提交级误报都还没跑。规则 A 的开发样本 M6 不受影响（riscv 的 select 在 `arch/riscv/Kconfig`）。
