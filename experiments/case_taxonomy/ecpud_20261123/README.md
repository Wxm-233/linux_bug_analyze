# 补可比的 PUD 构建（ecpud_20261123）

2026-11-23，Claude。用户：“下一步先加 PUD 构建吧”。接 `ecbuild_20261122`：规则 4（按保护值的形状规律）至少要 3 个构建可比，而 PUD 级只有 x86_64、arm64 两个，`144bb0aee33a`（x86 `pud_leaf`）因此漏报。

判据 `criteria.md`（1ca0d409…）写于实现之前，此前只做了只读诊断。之后有两条修订，都写于对应的正式运行之前：
- 修订 1：试求函数体时，编译期断言当空操作，位计数内建函数按常量求值；
- 修订 2：试求时遇到内联汇编或跳转即放弃。这是改实现上的一个错误，判据本身已写明这种情况照旧枚举。

判定规则不变：第三轮 EC 加第五轮规则 4、5。

## 结论

- **G1 部分通过**：
  - df 和 v7.1 上，PUD 级可比构建达到 3 个：x86_64、arm64，加新增的 riscv64_thp。
  - 召回样本 `144bb0aee33a` 的父版本 v6.11 上仍只有 2 个，v5.18、v5.16 上只有 x86_64 一个。
  - PMD 级可比构建从 6 个增到 7～8 个（加了 riscv64_thp）。
- **powerpc 补不上**：
  - book3s64 的层大小已经能求出来：radix 下 PMD_SHIFT 21、PUD_SHIFT 30，hash 下 24、34。
  - 但 `pfn_pmd`、`pfn_pud` 定义在 `arch/powerpc/mm/book3s64/pgtable.c`，不在头文件里，求值器拿不到函数体，所以 PMD/PUD 级的组合全部“求不出”。
  - riscv 的 PUD 大页（`HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD`）在 9 个父版本里只有 v7.1 有。
  - 所以在 v6.11 上，用这套“只看头文件”的办法，凑不出第三个 PUD 构建。
- **G2**：
  - 修改 3（运行时判断先求函数体）改正后，只让 ppc64le_hash 的 `radix_enabled()` 变成常量“假”，其他构建遇到的运行时判断与第三轮完全相同（`results/g2_runtime_df.json`）。
  - **ppc64le_hash 改正之后，行为仍和 ppc64le 一模一样**（df 上 15922 条，0 条不同）：能求值的 PTE 级接口在 radix 和 hash 下编码确实相同，powerpc 这两个构建投的就是同一票。这是事实，不是工具假象。
- **G3 开发集召回：父版本法 4/8**，与上一轮相同。
  - `144bb0aee33a` 仍未中，原因见 G1。
  - **疑似命中（按既定定义不计）**：`fba88ede6a31`（riscv “PAGE_PROT_NONE 符合 THP 语义”）。v5.16 上新增的 riscv64_thp 报出 `pmd_mkinvalid` 使 `pmd_present`“保持→改变”，打上修复后这一行消失。这正是这个缺陷的表现：修复前 `_PAGE_PROT_NONE` 就是 `_PAGE_READ`，`pmd_mkinvalid` 清掉它，大页失效后不再“存在”。但修复改的是 `_PAGE_PROT_NONE`/`PAGE_NONE` 宏，这一行指认的是 `pmd_mkinvalid`，不满足“报告行点到修复改动的接口”，不计入命中。
- **G4**：df 候选 22 行，与第五轮完全相同（偏离 295 条，按规则：第三轮 272、规则 5 23），新增 0 行，不需盲审。
- **G5**：`scan8.py verify` 显示 8 个旧引擎条数不变，整表 960 行。

## 一、修改（`ec7.py`、`mkvariants3.sh`）

| 修改 | 内容 | 结果 |
|---|---|---|
| 1 新构建 riscv64_thp | riscv defconfig + `TRANSPARENT_HUGEPAGE`；身份选项 `64BIT TRANSPARENT_HUGEPAGE` | df 和 8 个父版本建成；v5.10 的 riscv 不支持 THP，按身份核对排除 |
| 2 启动时赋值的层大小 | `__pte/__pmd/__pud/__pgd_index_size` 按 `radix_enabled()` 取 `RADIX_*`/`H_*` 常量 | powerpc 的 PMD/PUD 级不再是“定义域未知”，但构造函数在 .c 文件里，仍然求不出 |
| 3 运行时判断先求函数体 | 求得常量就用；修订 1、2 补了编译期断言、位计数内建函数、内联汇编和跳转的处理；新加载函数体里的枚举也折叠 | 只有 ppc64le_hash 的 `radix_enabled()` 变成“假” |

调试中见过一次“字面量按位与在布尔上下文里算错”的现象，原因是调试脚本没有像挖掘时那样设置输入域（`S.DOM`）。正式挖掘不受影响，调试脚本已改正。

## 二、各版本 PUD/PMD 可比构建（`results/g12_*.json`）

| 版本 | PUD | PMD |
|---|---|---|
| df2908090cda | 3：x86_64、arm64、riscv64_thp | 7 |
| d4e58d2c21d9（v7.1） | 3：同上 | 7 |
| 4dd7724f02ab（v6.11） | 2：x86_64、arm64 | 8 |
| 0ff74a23e08f（v5.18） | 1：x86_64 | 7 |
| 8ee304396e2f（v5.16） | 1：x86_64 | 7 |

## 三、召回（`results/recall.json`）

| 样本 | 上一轮 | 本轮 | 说明 |
|---|---|---|---|
| `6f74c0ec2095` arm `__swp_entry` | 命中 | 命中 | — |
| `018e9828eb52` loongarch `wrprotect` | 命中 | 命中 | 规则 5 |
| `23bc8f69f0ec` arm64 `p?d_leaf` | 命中 | 命中 | 规则 4（偏离从 15 条变为 10 条：PMD 级多了 riscv64_thp 参加表决） |
| `ff1712f953e2` arm64 `pte_wrprotect` | 命中 | 命中 | 规则 5 |
| `144bb0aee33a` x86 `pud_leaf` | 未中 | 未中 | v6.11 上 PUD 级只有 2 个构建可比 |
| `fba88ede6a31` riscv `PAGE_PROT_NONE` | 未中 | 未中（疑似命中） | 见结论 |
| `e0fe5ab4192c`、`5d9cea8a552e` | 未中 | 未中 | 接口不在组合里 / 规则 1 |
| `ddc1729b07cc` | 无法评估 | 无法评估 | v6.4 的 loongarch 建不出来 |

## 四、下一步建议

1. **把 .c 里的页表构造函数也纳入求值**。powerpc book3s64 的 `pfn_pmd`/`pfn_pud`/`pmd_modify` 等在 `arch/powerpc/mm/book3s64/pgtable.c` 里，可以把这类文件里的函数体也提取出来。这是让 v6.11 的 PUD 级凑够 3 个构建的唯一现实途径，PMD 级也能多出 powerpc 一票。
2. **命中定义的局限**：`fba88ede6a31` 说明，修复改的是宏，而报告行指认的是用到它的函数，这种情况按现有定义算不上命中。如果要改定义，比如“修复改动的宏出现在报告行的求值路径上”，要先写判据，并说明它只对以后的样本生效。
3. 召回需要新的独立样本；规则 5 的输入覆盖条件还没做。

## 五、文件

- 判据：`criteria.md`、`criteria_amendment1.md`、`criteria_amendment2.md` 及各自的 SHA；代码 SHA：`code_sha256.txt`
- 代码：`ec7.py`、`mkvariants3.sh`、`thp_parents.sh`、`parents.sh`、`scan8.py`、`g12.py`、`g2_runtime.py`、`py.sh`；诊断与调试：`diag_pud.py`、`diag_ppc.py`、`dbg_*.py`
- 产出：`status_df.txt`、`logs/`（`df_run1_stopped.log` 第一次运行、中途停下；`df_run2.log` 修订 1 后的运行；`df.log` 修订 2 后只重挖 riscv 的两个构建）、`results/recall.json`、`results/g12_*.json`、`results/g2_runtime_df.json`、`tables/df2908090cda.*`
- WSL：
  - 变体 `/root/work/ecver/<版本>/cfg_*`（df 21 个，父版本加了 riscv64_thp；源码副本已删）
  - EC 缓存 `/root/work/ec_cache/v7`（352M，含修订 1 后的备份 `df_run2`）
  - 重新表决 `/root/work/ec_cache/r7`（312M）

统计：模型调用 0；构建：头文件变体 21 个（df）加 9 个（父版本 riscv64_thp，其中 1 个身份不符）；没有运行内核。完成后 WSL 剩 86G（共 196G）。
