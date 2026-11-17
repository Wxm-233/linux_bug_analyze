# P1 静态检查：没查 present 就用只对 present 条目有定义的页表接口（p1check_20261115）

2026-11-15，Claude。用户：“把 P1 做成静态检查”，并要求需要第二人判断的地方调用 Codex。判据见 `criteria.md`、修订 1 `criteria_amendment1.md`，SHA 在 `criteria_sha256.txt`。

统计行：模型调用 0；Codex 调用 2（另一次用于 `depmine` 盲判）；构建 0；新确认缺陷 0；新疑点 2。

## 这一轮要回答什么

`depmine_20261115` 里最多的一类跨边界依赖缺失是 P1：公共层拿到一个页表项，没确认它 present（页在内存里），就调用了只对 present 条目有定义的架构接口。

举个例子。页表项不在内存里的时候（交换项、迁移项、device-private 项、uffd 标记），里面的位是另一套编码，各架构不同：

- loongarch 的 `pmd_leaf()` 只看 `_PAGE_HUGE` 位，交换项恰好总带这一位，于是被误判成大页（`26e7888a0c89`）；
- x86 上，交换项的软脏位和可写位是同一位，对交换项调 `pmd_write()` 就会把“软脏”读成“可写”（`43e7f189769c`）。

这一轮把它做成静态检查，回答三个问题：
- 能不能抓到历史上这类缺陷？
- 当前内核里报出多少条？
- 报出的条目里有没有真问题？

它属于**调用上下文检查**里的“对象是否就绪”：调用时传进去的页表项必须已经 present。

## 检查怎么做

1. **受限接口**（写死在判据里）：`pte_/pmd_/pud_` 加上 `write, dirty, young, special, leaf, pfn, page, soft_dirty, uffd_wp, protnone, devmap, exec` 等，共 30 个。
2. **present 守卫**：在同一函数里、调用之前，对同一个页表项做过 `p?d_present()` 或 `p?d_trans_huge()` 判断。认四种写法：
   - 调用在 `if (present(x))` 的分支里；
   - 前面有 `if (!present(x)) return/continue/goto`，包括 `if … else if …` 链每个分支都退出的情况；
   - 同一个表达式里 `present(x) && 调用`；
   - 循环条件里查过。

   另外，先把判断存进布尔变量（`present = pmd_present(…)`）的写法也认。守卫之后页表项变量被重新赋值，守卫作废。
3. **来源分级**：O1 是函数里直接从页表读出来的（`ptep_get`、`pmdp_get_lockless`、`pmdp_invalidate` 等）；O2 是函数参数；O3 是其他（结构体成员等）。
4. **实现**：不编译，只做词法和语句分析，源码直接从 git 对象读，所以任何历史版本都能马上跑。`#if` 各分支都当代码看。不跨函数。范围是 `mm/ fs/ kernel/ lib/` 的 `.c` 和 `include/linux/` 的 `.h`。

代码在 `p1check.py`，自测 32 例全部正确。

## 结果

### 1. 开发样本（参照它们设计，不算证据）

| 样本 | 父提交上报出 | 修复后消失 |
|---|---|---|
| `26e7888a0c89`（follow_pfnmap_start，pmd_leaf/pud_leaf 等） | 是 | 是 |
| `43e7f189769c`（set_pmd_migration_entry，pmd_write 等） | 是 | 是 |

第一次跑时两个样本都报出了，但修复后仍在报。原因是判据没覆盖 `if … else if …` 链、布尔变量和 `pmdp_invalidate()` 这类读法。我写了修订 1（在跑留出集和当前版本之前），改完后两个都达到。另外修了一处代码错误：给别名变量重新赋值时，把它原来指向的页表项的守卫也删掉了，这比判据规定的更严。

### 2. 机械留出集（检验）

- **选法**：在 v5.10 以来 13914 个带 `Fixes:` 的提交里，找新增了 present 判断、而且同一补丁块里随后调用了受限接口的修复，筛出 22 个。去掉开发样本和 `depmine` 读过的，剩 19 个。算分前我没读过它们。
- **结果：命中 11/19（58%），命中的 11 个修复后都消失了**，达到 50% 的参考线。
- **没命中的 8 个**（算分后读的）：
  - 6 个本身不是 P1 形态：修复时 present 判断和受限接口是一起新加的，父提交里没有“先用后查”，多是竞态修复或新功能。它们是 `3b89863c3fa4`、`9b25a6e3d243`（同一补丁出现两次）、`6fa1066fc5d0`、`71c186efc1b2`、`edb5d0cf5525`、`f5548c318d65`；
  - 2 个检查器其实报了，只是计分规则没算上：`3b77e8c8cde5` 父提交里报的是 `pmd_page`，修复后改成了 `pmd_pfn`；`1d4832becdc2` 真正没守卫的调用在被调函数 `get_pmd_pfn()` 里，检查器以 O2 报出。
  - 如果只算真正属于 P1 形态的 13 个，严格命中 11 个，算上上面 2 个是 13 个。

另外，Codex 在 `depmine` 复核时新指出了 3 个 P1 样本（不在留出集里，设计时也没参照过）。检查器在父提交上抓到其中 2 个（`bd1f2b2ace84`、`65529295607f`）。`3faa3ebc89c1` 用的是 `ptep_test_and_clear_young`，不在受限接口清单里（`extra_p1_codex.json`）。

### 3. 当前版本（`df2908090cda`）

- 共报 **249 条**：O1 112、O2 51、O3 86；涉及 40 个文件、3758 个函数，解析失败 0。
- 集中在 `mm/debug_vm_pgtable.c`（59，测试代码）、`mm/memory.c`（31）、`mm/huge_memory.c`（30）、`mm/gup.c`（20）。
- O1 少于 300 条，专家读得完，达到参考线。

**O1 前 30 条（按文件、行号排序）由我和 Codex 各自盲判**：一致率 93%，κ = 0.75。2 条分歧都采纳了 Codex，第 6 条采纳前我核实了它给出的路径。裁定后：**可能 4、不可能 26**。

不可能的 26 条，原因分三类：
- 测试代码里条目是刚构造出来的（12 条）；
- 守卫在被调函数里（例如 `can_gather_numa_stats()`），检查器不跨函数；
- 调用约定保证 present（批处理 present PTE 的辅助函数、内核 arena 映射等）。

可能的 4 条：

| # | 位置 | 判断 |
|---|---|---|
| 1、2 | `fs/proc/task_mmu.c:1129` `smaps_pmd_entry` | **新疑点 1**：PMD 是 THP 迁移项（或 device-private 项）时，也会取到 page 并调用 `smaps_account(…, pmd_young(*pmd), pmd_dirty(*pmd), …)`。同文件的 PTE 路径只在 present 时才读这两个位，两条路径不一致。后果是 `/proc/<pid>/smaps` 里的 Referenced、脏页、lazyfree 统计会读到交换项编码里的位，结果取决于架构。两人独立都判为可能 |
| 6 | `include/linux/pgtable.h:534` 通用 `ptep_test_and_clear_young` | **新疑点 2**（Codex 提出，我部分核实）：回收路径 `folio_referenced_one()` 会拿到 device-exclusive 项，不查 present 就清 young 位。同一系列修过 `page_idle`、`try_to_unmap_one` 等相似路径，这里没修。没核实 device-exclusive 的 folio 是否真会进回收 |
| 29 | `mm/gup.c:656` `follow_huge_pud` | 加锁重读后，`pud_pfn` 在 present 判断之前就算了，但判断失败直接返回，值不被使用，无害 |

两个新疑点都只在本地记录，不对外报告。还没有动态验证。

### 4. 哪些架构不查 present（描述性）

`archs.json`：多数受限接口在多数架构上都不查 present，这正是“只对 present 有定义”的意思。有区别的是 `pmd_leaf`：arc、arm、loongarch、mips、powerpc、sparc、x86 的实现不查 present，arm64、riscv 查。这和 `26e7888a0c89` 只在 loongarch 上出错相符。另外这一项只按名字粗查，没有展开宏生成的定义。

## 看出的几点

1. **P1 可以做成一个短小、准确的静态检查**：不编译、不构建，任何历史版本都能直接跑；留出集上抓到 11/19（真正属于 P1 形态的 13 个里抓到 11 个），当前版本 O1 只有 112 条。
2. **它找到了当前内核里的疑点**，这是效果依赖这条线第一次在当前版本上报出两人都认为“可能”的条目（smaps）。
3. **主要的误报来源是不跨函数**：守卫写在被调函数里，或者调用约定保证了 present。下一步加一层跨函数（参数由所有调用者保证 present 就不报）能去掉不少 O2，以及部分 O1 误报。
4. **两人盲判很有用**：在 `depmine` 上，Codex 指出了我漏判的 3 个 P1 样本；在这里，又补出了一个我判“说不清”的疑点路径。

## 局限

- 词法分析，宏展开后的代码看不到；`#if` 里的守卫对所有配置都算数，会漏报“只在某些配置下才有守卫”的情况，这和判据“偏向不漏”的说法有出入。
- 不跨函数，O2（参数）是否由调用者保证没有追。
- 受限接口清单是手写的，`ptep_test_and_clear_young` 这类“修改型”接口不在里面（`3faa3ebc89c1` 因此漏掉）。
- 留出集的选法要求同一补丁块里新增 present 判断，跨补丁块的修复会漏掉；19 个样本，比例区间宽。
- 两个新疑点没有动态验证，严重程度未评估。

## 文件

- `criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`：判据；
- `p1check.py`（检查器和自测）、`run.sh`；
- `evaluate.py`、`run_eval.sh`：开发样本 `dev.json`、留出集 `heldout_set.json`/`heldout_score.json`、当前版本 `head.json`、架构 `archs.json`；
- `extra.py`、`run_extra.sh`、`extra_p1_codex.json`：Codex 新指出的 3 个 P1 样本；
- `make_review.py`、`run_review.sh`、`review_o1.txt`：O1 前 30 条的代码上下文；
- `review_o1_judgement.json`（我的判断）、`codex_blind/`（Codex 盲判的提示、`codex_o1.json`、笔记）、`adjudicate_o1.py`、`o1_adjudication.json`；
- `stats.json`。

## 下一步建议

1. **动态验证两个新疑点**：在 QEMU 里让 THP 迁移和读 `/proc/<pid>/smaps` 并发，比较不同架构上的 Referenced、脏页统计；device-exclusive 那条需要 HMM 测试模块（`lib/test_hmm`）。
2. **加一层跨函数**：参数（O2）在所有调用点都有 present 守卫，就不报。
3. 扩展受限接口清单到“修改型”接口（`ptep_test_and_clear_young`、`ptep_set_wrprotect` 等），再在留出池上检验。
