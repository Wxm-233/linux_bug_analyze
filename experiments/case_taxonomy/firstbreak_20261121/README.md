# 新评测集分析侧逐例登记“第一个断点”（firstbreak_20261121）

2026-11-21，Claude。用户：“开始逐例登记”。gpt-6.2-astra 第二次规划第三节“第 4～5 天，首轮未过线”。**只诊断，不写新规则。**

- 判据 `criteria.md`（4a572620…），写于收集和阅读之前；没有修订。
- 统计行：Codex 调用 2（第一次拒绝，第二次用改写后的提示完成；周额度 70% → 72%）；其他模型调用 0；构建 0。

## 第二标注：第一次被拒，改写提示后完成

- **第一次**（`codex_prompt.md`）：Codex 只核对了机械数字，回复说不能“逐例把修复前的代码位置、受影响架构和具体触发状态关联起来”，担心形成定向测试已知漏洞的清单，没写结果。
- 用户说明这类拒绝没有道理，可以改写提示重试（已记入记忆）。
- **第二次**（`codex_prompt_v2.md`）：
  - 开头写明这是防御性研究：给静态分析器的覆盖面打标签，样本都是已公开修复的上游提交，不需要写任何利用、复现或测试代码；
  - 去掉了“公共依赖、架构选择、必须观察的状态”三个描述字段（判据第三节本来只要求 Codex 判 S1、S3、S4 和第一个断点）；
  - 标签定义照抄判据，不变。
  - Codex 读了每例的补丁和父版本源码，完成了 21 例（`codex_registry.json`、`codex_notes.md`）。

**一致性**：第一个断点 15/21，κ = 0.61；自动化前提分类 14/21，κ = 0.51（Codex 的“其他”就是我单列的“只缺构建覆盖”，按同一类算）。

**裁定**（`adjudication.json`，最终结果 `final_registry.json`），6 条第一个断点不同：

| 样本 | 我 | Codex | 裁定 |
|---|---|---|---|
| hugetlb 启动参数（`b02019169284`） | S2 是 | S2 否 | **采纳 Codex**：能力实现所在的 powerpc 不在构建里。这和我对 sparc、LoongArch、powerpc SMT 用的是同一条规则，我在这条上没保持一致 |
| Xen PV 非叶 PMD（`4aaf269c768d`） | 断在 S4 | 断在 S3 | **维持我的**：实现能绑定；难点是“Xen 不能模拟对非叶 PMD 的写”在源码里看不出来 |
| KASAN HW_TAGS（`6c2f761dad78`） | S2 否 | S2 是 | **维持我的**：出错的实现 `mm/kasan/hw_tags.c` 在三个构建里都不编入 |
| ACPI CPPC（`09073396ea62`） | S1 否 | S1、S4 都是 | **采纳 Codex**：同一函数第 702 行已用 `cpc_supported_by_cpu()` 放行，灵活地址空间这处没有，属能力判断不一致；`cpc_supported_by_cpu` 是 `__weak` 默认加 x86 覆盖 |
| bpf fsession（`8798902f2b8b`） | S4 否 | S4 是 | **采纳 Codex**：父树 x86 trampoline 已有 `bpf_fsession_cnt()` 处理，arm64 没有，可以横向比较；我之前按大写 `FSESSION` 搜索，漏了小写写法 |
| perf 页大小（引入提交 `8d97e71811aa`） | S4 是 | S4 否 | **采纳 Codex**：这个引入提交的问题是无锁遍历没用 `READ_ONCE`，属内存模型；同一修复的另一个样本 `51b646b2d9f8` 是对特殊项调 `pte_page`，两者不同 |

另有 3 条只是阶段标签不同、第一个断点相同，维持我的（理由见 `adjudication.json`）。

## 结果（裁定后，`registry.md`、`summary.json`）

| 自动化前提 | 21 例 | 12 个干净 |
|---|---|---|
| 具备（S1～S4 都满足） | 7 | 3 |
| 具备，只缺构建覆盖（判据没写到这种情况，单列） | 7 | 4 |
| 只能人工核验 | 7 | 5 |
| 非跨架构可比 | 0 | 0 |

- 第一个断点（21 例）：S2 构建覆盖 9、S5 未生成 6、S4 性质表示不了 4、S3 绑定 1、S6 名次 1（CTX 第 332 名）。
- **不看 S2 时，14 例都走到了 S5 或之后**，也就是“检查写得出来，只是现在没有，或者排得太后”。

### 有自动化前提的 14 例，形态很分散

| 形态 | 例子 | 归哪类检查 |
|---|---|---|
| 地址类别 | btf 对内核镜像符号用 `virt_to_phys` | 类型一致性 |
| 用户 ABI 位宽 | `move_pages` 按本机指针宽度读 compat 指针数组 | 类型一致性 |
| 能力判断不一致 | hugetlb 启动参数没查 `hugepages_supported`；secretmem 没查 `can_set_direct_map`；CPPC 一处没用 `cpc_supported_by_cpu` 放行 | 实现一致性 |
| 架构能力的横向比较 | bpf fsession：x86 trampoline 支持，arm64 不支持，校验器没拦 | 实现一致性 |
| 指令可见性效果 | riscv 早期 ftrace 改写、riscv uprobes XOL 都没刷 icache | 实现一致性（效果） |
| 清零效果 | KASAN HW_TAGS 提前返回（K1） | 实现一致性（E-ZERO） |
| 同族函数只覆盖了一部分 | LoongArch 覆盖了 5 个大页辅助函数，没覆盖 `huge_pte_clear` | 实现一致性 |
| 访问函数的架构副作用 | sparc64 `pte_mkdirty` 同时设写位 | 实现一致性 |
| 上下文约束 | x86 poly1305 去掉 SIMD 可用性检查；riscv `__kernel_map_pages` 在原子上下文里拿信号量 | 调用上下文 |
| 非普通页表项 | perf 对 hugetlb 特殊项调 `pte_page`（`51b646b2d9f8`） | 类型 / 实现一致性 |

14 例分属约 10 种形态，最多的“能力判断不一致”也只有 3 例。每一种都写得出检查，但要一种一种地写。**召回低的主要原因是覆盖的形态太少**，不是绑定或性质表示不了。

### 只能人工核验的 7 例

| 原因 | 例子 |
|---|---|
| 并发或内存模型 | arm64 远端 TLBI 完成（DSB 不够）；快速 GUP 与 THP 合并竞争；perf 无锁遍历没用 `READ_ONCE` |
| 运行时环境 | Xen PV 不能写非叶 PMD |
| 经 ops 回调或运行时分派 | PEBS 缓冲排空时机；zswap 经 zpool 驱动返回的地址 |
| 需要修复才引入的钩子 | powerpc `topology_is_core_online` |

### 构建覆盖（S2）是最大的断点

9 例的根因所在的代码或架构不在当前三个 defconfig 里：
- 功能没开：BTF sysfs、zswap、riscv ftrace、KASAN HW_TAGS；
- 架构不在：sparc64、LoongArch、powerpc（2 例）；
- 文件已改名：poly1305。

所以依赖编译数据库的分析（按构建绑定），覆盖面受构建配置限制；词法检查不受这个限制。

## 这对下一步的含义（只是观察，不据此写规则）

1. 召回的瓶颈是**形态数量**：可自动化的漏报分散在约 10 种形态里，每种 1～3 例。继续“每次补一种规则”，每种只多覆盖一两例，而且未必能迁移（前几轮的独立样本结果都是 0）。
2. 若要用编译信息，三个 defconfig 不够：需要更多配置（例如功能全开的配置）和更多架构的构建。
3. 并发、内存模型、运行时环境、ops 分派这几类，静态检查做不出来，只能交给动态测试或人工。

## 文件

- `criteria.md`、`criteria_sha256.txt`
- `collect.py`、`collected.json`、`show.sh`、`show_used1.txt`、`show_used2.txt`
- `claude_registry.json`（我的原始登记，记了 SHA）、`codex_prompt.md`（第一次，被拒）、`codex_prompt_v2.md`（第二次）、`codex_registry.json`、`codex_notes.md`、`adjudication.json`、`final_registry.json`（裁定后）
- `summarize.py`、`registry.md`、`summary.json`
