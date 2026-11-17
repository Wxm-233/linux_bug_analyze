# 用调试信息展开内联，补上 KCOV 的内联盲区（kcov_inline_20261115）

2026-11-15，Claude。用户：“补内联盲区”。判据 `criteria.md` 写在构建和计算之前。修订 1 写在代码一致性核对之后、重跑和符号化之前。SHA 都在 `criteria_sha256.txt`。

统计行：模型调用 0；构建 4（全部成功）；QEMU 运行 12；新确认缺陷 0；新疑点 0。

## 先解释几个词

- **内联盲区**：编译器把小函数直接展开在调用者里，这个函数就没有独立的符号。上一轮按符号表把地址对到函数，展开后的代码只会算在调用者头上。所以 `do_anonymous_page`、`zap_pte_range` 等 128 项（当前版本）看起来“没执行”。
- **调试信息（DWARF）里的内联记录**：编译器开了调试信息后，会记下“这段机器码是从哪个函数内联来的”。`llvm-symbolizer --inlining` 能把一个地址展开成一条链，例如 `pud_none_or_clear_bad` ← `copy_pud_range` ← ……，链上每个函数都算执行过。

## 做了什么

1. **重建内核**：riscv、x86_64 各两个版本（当前版本、X1 修复前），配置和上一轮相同，只多开调试信息。这组设置和 arm64 defconfig 自带的一样（`DEBUG_INFO_REDUCED`）。arm64 上一轮的内核本来就有调试信息，不重建。
2. **代码一致性核对**（`nm_compare.txt`）：
   - 开了调试信息后，函数地址变了。riscv 还多出约 1.2 万个函数，开调试信息后编译方式不同。
   - 所以按判据，riscv、x86_64 用新内核重跑了 12 次。arm64 沿用上一轮的日志。写进了修订 1。
3. **符号化**：`symbolize_inline.py` 把每个地址减 1 后交给 `llvm-symbolizer-18 --inlining`，取内联链上所有函数，再并上同一内核符号表的结果。
   - 当前版本三个内核，各有约一半地址带内联帧（1466～1813 个）；
   - 无法解析的地址：当前版本 0 个，X1 修复前 riscv 有 3 个。
4. **分析**：`analyze_inline.py` 只读复用上一轮的 `analyze_kcov.py`，四项分析和上一轮完全相同，只是换成展开内联后的覆盖。

## 结果

### 回归：通过（`regression.txt`）

- riscv、x86_64 重跑的判定和上一轮一致：当前版本全部不违反；X1 修复前两个架构的 Z3 都违反。
- 但 x86 的 Z3 这次只有 2/3 次运行违反，有一次运行 8 次尝试都没命中。见下面“一个副产品”。

### 1. 手写表准确度：两条参考线都达到了

| 内核 | 手写表项数 | 上一轮测到 | 本轮测到 | 上一轮的内联盲区 | 本轮补回 |
|---|---|---|---|---|---|
| 当前版本 | 296 | 137（46%） | **231（78%）** | 128 | **94** |
| X1 修复前 | 296 | 123（42%） | 217（73%） | 131 | 91 |

- 参考线“内联盲区至少补回一半”：达到（94/128）。
- 参考线“原始准确度 ≥70%”：达到（78%）。
- 每个模板能对到的函数，从符号表的 151～407 个，增加到展开内联后的 481～1936 个。

### 2. 当前版本仍没测到的 65 项

- **所在文件没插桩，20 项**：`post_alloc_hook`（`mm/page_alloc.c`）16 项；x86 的 `flush_tlb_mm_range`、`flush_tlb_multi`（`arch/x86/mm/tlb.c`）4 项。展开内联对它们无效。
- **其他，45 项**。我按函数逐个看了一遍，分成四种（人工判断，第 4 种没有逐个核实）：

| 原因 | 项数 | 例子 |
|---|---|---|
| ① 这个名字在该架构或该版本上不存在。手写表把各架构的名字列在一起 | 15 | arm64 没有 `flush_tlb_mm_range`；`flush_tlb_multi` 只有 x86 有；x86 没有 `__flush_tlb_range`，它的 `flush_tlb_range` 是宏；当前版本 `tag_clear_highpage` 已改名为 `tag_clear_highpages` |
| ② 内联进了没插桩的 `page_alloc.c` | 5 | riscv、x86 上的 `tag_clear_highpages`；arm64、x86 的 4K 写缺页靠 `__GFP_ZERO` 在页分配时清零，所以 `clear_user_highpage` 不在缺页路径上 |
| ③ 手写表写错（上一轮已核对） | 11 | `flush_tlb_range`∈T2、`folio_zero_user`∈Z2、`shmem_fault`∈Z6 |
| ④ 没有逐个核实 | 14 | `clear_highpage`∈Z7、`flush_icache_pages`∈I1（多数架构上是空函数）、`madvise_dontneed_single_vma`∈Z5、x86 的 `vma_alloc_zeroed_movable_folio`、riscv 的 `shmem_alloc_folio`。可能原因：内联后没有自己的基本块（KCOV 按基本块记录），或者当前版本里已改名 |

明细见 `missing2.md`。

### 3. 实测覆盖下的流水线：X1 仍不能归因，和事先说明的一致

| 树 | 动态确认 | 测过没事 | 部分架构测到 | 转人工 | 模板违反却无候选 |
|---|---|---|---|---|---|
| X1 修复前 | 0 | 0 | 1 | 6 | 2（riscv:Z3、x86_64:Z3） |
| X1 修复后 | 0 | 0 | 1 | 6 | 0 |
| 当前版本 | 0 | 0 | 0 | 6 | 0 |

和上一轮相同。判据里事先写明了原因：
- `post_alloc_hook` 在没插桩的 `page_alloc.c`；
- `tag_clear_highpage` 在 riscv、x86 上内联进了 `page_alloc.o`，那里没有任何 KCOV 回调。

展开内联也看不到它们。

### 4. 候选“测到 / 没测到”：有了第一批“测到”

| 候选集 | 个数 | 公共函数被执行到 | 函数或接口被执行到 |
|---|---|---|---|
| effdep5 纵向候选 | 32 | 2（上一轮 0） | 8（上一轮 0） |
| effdep7 候选 | 6 | 1（上一轮 0） | 1（上一轮 0） |

- 被执行到的公共函数是 `move_ptes`（两个候选都是它，分别调用 `pte_none` 和 `ptep_get`）。它被内联了，上一轮看不到。本轮看到 Z9（mremap）在三个架构上都执行了它，而且 Z9 都没有违反。
- 但它在流水线里仍然是“转人工”。它的共享资源叫 `new_ptep`，不在规则映射认的资源名（`page, folio, pte, vmf, vma, addr`）里，所以没有映射到任何规则。这里只记作观察，没有改映射规则。
- 另外 6 个候选只是接口被执行到，公共函数没执行到，例如 `ptep_get`、`set_bit` 这类通用函数。这不算“测到”。

## 一个副产品：开 KCOV 会降低 X1 的检出概率

X1 修复前的 Z3，逐次尝试的违反比例：

| 内核 | riscv | x86_64 |
|---|---|---|
| 不开 KCOV（`pipeline_v2`） | 17/24 | 19/24 |
| 开 KCOV（上一轮） | 4/24 | 9/24 |
| 开 KCOV + 调试信息（本轮） | 9/24 | 3/24 |

X1 能否被看到，取决于新分配的大零页是否恰好落在弄脏过的内存上。开 KCOV 后内核更大，第 1 次尝试还要映射 32MB 的 KCOV 缓冲区，这可能改变了空闲页的分布（推测，没有验证）。

**结论**：判错应继续用不开 KCOV 的内核。KCOV 内核只用来记录覆盖，不要用它的判定代替正式判定。

## 这一轮说明了什么

1. **展开内联把手写表的“可验证部分”从一半提到了四分之三以上**。剩下没测到的项有三类：没插桩的文件、名字在该架构不存在、手写表写错，只有少数原因不明。
2. **KCOV 已经可以基本替代手写表，只剩 `page_alloc.c` 一处关键盲区**。恰好 X1 就落在这里，所以 X1 仍然只能靠手写表兜底。要消除它，得给测试内核打开 `page_alloc.o` 的插桩。
3. **候选里第一次有了“测到了、性质也成立”的证据**（`move_ptes` 被 Z9 执行）。但流水线的规则映射只认 6 个资源名，没把它接上。这说明规则映射太窄，是下一处可以改进的地方。

## 局限

- arm64 沿用上一轮的日志，riscv、x86 是本轮重跑的。两者的地址都只对各自的内核符号化，没有混用。
- 第 2 节里 ①～④ 的分类是人工判断，第 ④ 种没有逐个核实。
- KCOV 只记录本线程和每个模板的第 1 次尝试，这两点和上一轮相同。

## 下一步建议（还没做）

1. **给测试内核打开 `page_alloc.o` 的插桩**：只在单独的测试内核上去掉 `mm/Makefile` 里的 `KCOV_INSTRUMENT_page_alloc.o := n`，看 `post_alloc_hook` 能否记到，X1 能否只靠实测覆盖归因。
2. **放宽规则映射的资源名**：例如把 `*ptep`、`*pte` 一类名字归到页表资源，让 `move_ptes` 这类候选能对上 R1、R2 规则。改之前先写判据。
3. **按候选补用例**：其余 30 个候选的公共函数都没被执行到，需要针对 swap、hugetlb、mincore 等路径写用例。

## 文件

- `criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`：判据和修订。
- `build.sh`、`build.log`、`nm_compare.txt`：构建和代码一致性核对。内核在 WSL `/root/work/kcov_inline/kernels/`（2.1G）。
- `propsuite3.c`、`run.sh`、`judge.py`（三者都从上一轮复制，`run.sh` 只改了目录）、`run_all.sh`、`runs/`、`judge_head.*`、`judge_x1pre.*`：重跑和判错。
- `symbolize_inline.py`、`symbolize_*.txt`、`symstats_*.json`、`coverage_*.json`：展开内联的符号化。
- `analyze_inline.py`、`judge_head_merged.json`、`regression.txt`、`accuracy.json`、`pipeline_kcov_*.json`、`report_kcov_*.md`、`reach.json`、`missing2.*`：分析结果。
