# 判据修订 1：再加两项工具链处理（ecbuild_20261122）

2026-11-22，Claude。写于在 v5.18、v5.10、v6.4 上试跑新脚本之后、9 个父版本正式重建和任何 EC 运行之前。

试跑结果（`logs/status_*.txt`）：v5.18 由 12 个构建增到 16 个，v5.10 由 3 个增到 13 个，v6.4 由 18 个增到 19 个。剩余失败：

| 构建 | 原因 | 处理 |
|---|---|---|
| s390（老版本） | 内联汇编（spinlock.h 的 ALTERNATIVE）clang 集成汇编器处理不了 | WSL 有 s390x 的 GNU as：s390 改用 `LLVM_IAS=0` |
| hexagon（v5.10） | clang 16 起把隐式函数声明默认当错误 | 所有构建加 `KCFLAGS=-Wno-error=implicit-function-declaration`（只把这一类错误降为警告） |
| ppc44x、ppc64e（及 v5.10 的 ppc64le） | `-Wa,-m440`、`-Wa,-me500`、`-Wa,-mpower4` 集成汇编器不认，WSL 没有 powerpc 的 GNU as | 不处理（不新装软件包），记为失败 |
| loongarch（v6.4 及以前） | 该版本 `scripts/Makefile.clang` 没有 loongarch 的 `--target` 映射（内核对 clang 构建 LoongArch 的支持从 v6.5 开始） | 不处理（要改源码副本，判据没有预先写），记为该版本不支持 |

其余规定不变。
