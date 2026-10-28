# 已知跨架构缺陷回放2：shmem PMD页阶超过页缓存上限（设计，实现前写定）

2026-10-28。用户批准继续shmem回放，并批准安装alpha/mips/hppa交叉编译器（本轮使用）。目的：看die回放的断点（E1表述）是否重现，同时补“宏取值”与“函数优化后行为”两类事实。

## 案例与接触状态

修复`9fd154ba926b`（mm/shmem: disable PMD-sized page cache if needed），父版`3390916aca7a`。修复在`shmem_is_huge()`前加`if (HPAGE_PMD_ORDER > MAX_PAGECACHE_ORDER) return false;`。父版`MAX_PAGECACHE_ORDER = min(MAX_XAS_ORDER, PREFERRED_MAX_PAGECACHE_ORDER)`，`MAX_XAS_ORDER = XA_CHUNK_SHIFT*2-1`，THP下`PREFERRED…=HPAGE_PMD_ORDER`；ARM64 64K页`HPAGE_PMD_ORDER=13`而上限11。本案例已在`shmem_arch_contract_20261012`深度接触，本轮只计回放判别力。

## 输入

E1：冻结模板，修复触及的C/H文件在父版的完整内容（仅`mm/shmem.c`），不加提示。1次Kimi调用，无自动重试。

## 新事实（通用，可选开启）

- `macro_values`：对请求宏，在同一构建上下文以Kbuild保存的该文件编译命令编译探针（`#include`原源文件后追加`char __lba_probe_M[(M)+1];`），以`nm -S`读数组大小得整数值；不是整型常量表达式、为负或编译失败则不答。与架构无关，不解析汇编。
- `optimized_functions`：正常编译时加`-fdump-tree-optimized`，取请求函数的优化后GIMPLE记录；新查询`returns_only_zero(function)`：优化后函数体仅为`return 0;`（含`return false`）。函数被内联而无记录时不答。
- 桥接`tu_needs(trace_all=True)`：追踪候选文本与引用行中的全部标识符，采集后只为至少一个上下文中确为宏者生成`defined_*`/`arch_provides_*`；候选文本字段中的大写标识符（上限16）做取值探针，生成`value_*`；引用所在函数与候选文本中出现的源文件函数（上限12）生成`<fn>_returns_only_zero`。

## 上下文

父/修×9：x86_64、arm64（4K）、arm64（64K页）、s390、sparc64、riscv、alpha、mips、parisc，各defconfig并请求`TRANSPARENT_HUGEPAGE`、`SHMEM`、`TMPFS`为y（实际值以`.config`为准；不支持THP的架构会保持关闭）；64K上下文另设`ARM64_64K_PAGES=y`。构建失败如实记录、不重试。

## 判别标准（事先写定，依据shmem_arch_contract已核实事实）

父版arm64 64K应判violated，x86_64与arm64 4K不应判violated；修复版各上下文均不应判violated。达到即“可区分”。形式化值盲（只看父版事实名与类型），必要条件模式，逐上下文；同一形式化分别在父/修事实上判定。若E1候选未涉及页缓存上限，记为E1断点重现。研究者事后契约另列，不计链路检测。
