# 判据修订 2：试求遇到内联汇编或跳转即放弃（ecpud_20261123）

2026-11-23，Claude。写于修订 1 之后的 df 运行完成、核对 G2 时；在重跑受影响构建和任何父版本运行之前。

核对各构建遇到的运行时判断（`g2_runtime.py`，`results/g2_runtime_df.json`）：除了预期的 ppc64le_hash（`radix_enabled()` 求得假）之外，riscv64 的 `riscv_has_extension_likely(33)` 也被试求成了常量。它的函数体是 `asm goto(ALTERNATIVE(...))` 加 `l_no:` 标签，真实结果由启动时打补丁决定；求值器对内联汇编一律跳过、也不模拟 goto，于是直接走到 `return true`。这违反判据二.3 已写明的“求不出（内联汇编、跳转标签等）照旧枚举”，是实现错误。

修订：在修改 3 的试求过程中（包括它调用到的函数），遇到内联汇编语句（`GCCAsmStmt`/`MSAsmStmt`）、`goto`、标签语句或间接跳转，试求即告失败，该判断照旧按运行时枚举。试求之外的求值不变。

处理：只有 riscv64、riscv64_thp 受影响（其余构建的运行时判断列表与第三轮相同，ppc64le_hash 的结果经核对是正确的），这两个构建在 df 上重新挖掘，其余构建的行为文件沿用修订 1 后那次运行（备份在 `/root/work/ec_cache/v7/df_run2`）。父版本运行在此之后进行。
