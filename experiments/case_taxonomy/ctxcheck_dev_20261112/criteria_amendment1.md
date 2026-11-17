# 判据修订 1（ctxcheck_dev_20261112）

2026-11-12，Claude。第一次构建在 riscv 配置阶段之后、任何内核编完和任何运行之前发现：A175 父提交里 `PREEMPT_RT` 依赖 `EXPERT`（`kernel/Kconfig.preempt`：`depends on EXPERT && ARCH_SUPPORTS_RT && !COMPILE_TEST`），默认配置没开 `EXPERT`，所以 `PREEMPT_RT` 没有生效（`config_check.txt` 中为 0）。

修订：配置里另开 `EXPERT`（只为满足依赖）；`build.sh` 在配置后检查 `PREEMPT_RT=y`，没生效就停止，不编译。其余不变。这次中断的构建（只完成了 riscv 的配置）作废，中间文件已删。
