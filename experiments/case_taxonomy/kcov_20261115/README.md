# 接入 KCOV：实测每个检查模板执行了哪些内核函数（kcov_20261115）

2026-11-15，Claude。用户：“先接入 KCOV”。判据 `criteria.md` 在构建和运行之前写定。修订 1（符号化时剔除非函数符号）写于符号化之前。两份文件的 SHA 都在 `criteria_sha256.txt`。

统计行：模型调用 0；构建 6（全部成功）；QEMU 运行 24；新确认缺陷 0；新疑点 0。

## 先解释几个词

- **KCOV**：内核自带的覆盖率记录功能。用户程序打开 `/sys/kernel/debug/kcov`，开启后，本线程在系统调用和缺页里执行过的内核代码地址会被记进一块共享内存。地址再对照内核符号表，就能知道执行过哪些函数。
- **手写覆盖表**：上一轮 `pipeline_v2` 里我手写的 `templates.json`，写明每个检查模板（Z1～Z9、T1～T3、I1）“应该会走到”哪些内核函数。流水线靠它判断：某个静态候选有没有被某个模板检查过。
- **KCOV 的盲区**：
  - 定义在关掉插桩的文件里的函数，KCOV 记不到。内核 `mm/Makefile` 对 `page_alloc.o`、`slub.o`、`memcontrol.o` 等写了 `KCOV_INSTRUMENT_xxx.o := n`；x86 的 `arch/x86/mm/tlb.o`、整个 `kernel/sched`、`kernel/locking` 也一样。
  - 被内联的函数没有独立符号，执行地址会算到调用者头上。

## 做了什么

1. 构建 6 个开 KCOV 的内核：当前版本（`df2908090cda`）和 X1 修复前（`e7c375b18160`），各有 riscv、x86_64、arm64。启动时加 `nokaslr`，保证地址固定。
2. `propsuite3.c` 在上一轮的检查程序 `propsuite2` 基础上只加了 KCOV 记录，判错逻辑一字未改。每个模板的第 1 次尝试打开 KCOV，结束后把去重的地址从串口打出。
3. 两套内核各跑 4 种配置（riscv、x86_64、arm64、arm64 开 MTE）× 3 次，共 24 次。当前版本内核上，每个模板记到 584～1806 个不同地址，对应 151～413 个函数；两套内核的缓冲区都没写满。
4. `symbolize.py` 把地址对到函数。`analyze_kcov.py` 按判据做四件事：和手写表对比、用实测覆盖重跑流水线、统计候选“测到 / 没测到”、回归检查。

## 结果（按判据）

### 1. 回归：通过

开了 KCOV 后，判定结果和之前完全一致（`regression.txt`）：
- X1 修复前：riscv、x86_64 的 Z3 违反（各 3/3），其余都不违反；
- 当前版本：全部不违反。

### 2. 手写表准不准：原始口径 46%，未达参考线；扣掉盲区后 93%

| 内核 | 手写表（模板×架构）项数 | 实测执行到 | 被内联 | 所在文件没插桩 | 有插桩但没记到 |
|---|---|---|---|---|---|
| 当前版本 | 296 | 137（46%） | 128 | 20 | 11 |
| X1 修复前 | 296 | 123（42%） | 131 | 20 | 22 |

- 按判据的原始口径，准确度 46% 和 42%，**没有达到 70% 的参考线**。
- 但没测到的绝大多数是 KCOV 本来就看不到的。例如 `do_anonymous_page`、`zap_pte_range` 被内联；`post_alloc_hook` 在没插桩的 `page_alloc.c` 里。
- 扣掉这两类之后，KCOV 能观测的项里，手写表准确度为 93%（当前版本，137/148）和 85%（X1 修复前，123/145）。
- “有插桩但没记到”的，在当前版本上只有 3 个函数，逐个核对，都是**手写表写错了**：
  - `flush_tlb_range` 写进了 T2。但 mprotect 走的是 mmu_gather，最后调的是 `flush_tlb_mm_range`。
  - `folio_zero_user` 写进了 Z2。但它只用于大页，4K 的写缺页走 `clear_user_highpage`。
  - `shmem_fault` 写进了 Z6。但 Z6 用 `read()` 读文件，不触发缺页。
- X1 修复前多出的 3 个（`unmap_region`、`__flush_tlb_range`、`prot_commit_flush_ptes`）没有逐个核对。手写表是照当前版本写的，推测是版本差异。

明细见 `missing_classified.md`。分类脚本 `classify_missing.py` 是看到准确度之后加的，只解释原因，不改变判据口径。

### 3. 实测覆盖下的流水线：X1 没能在 riscv、x86 上归因，未达参考线

| 树 | 动态确认 | 测过没事 | 部分架构测到 | 转人工 | 模板违反却无候选 |
|---|---|---|---|---|---|
| X1 修复前 | 0 | 0 | 1 | 6 | 2（riscv:Z3、x86_64:Z3） |
| X1 修复后 | 0 | 0 | 1 | 6 | 0 |
| 当前版本 | 0 | 0 | 0 | 6 | 0 |

原因是 X1 的两个名字在 riscv 和 x86 上 KCOV 都看不到：
- 公共函数 `post_alloc_hook` 在没插桩的 `mm/page_alloc.c` 里；
- 接口 `tag_clear_highpage` 在这两个架构上是通用头文件里的内联函数，也被编进了 `page_alloc.o`。

arm64 上 `tag_clear_highpage` 是 `arch/arm64/mm/fault.c` 里的独立函数，有插桩，所以 Z3 在 arm64 上记到了它。

于是 riscv、x86 上 Z3 明明违反了，流水线却找不到对应候选。**参考线“X1 仍在 riscv、x86_64 上被确认”没有达到。**

### 4. 候选“测到 / 没测到”：0/32、0/6

按判据，effdep5 的 32 个纵向候选、effdep7 的 6 个候选，**没有一个**的公共函数被任何模板执行到。

## 事后补充分析（`supplement.md`，不替代上面的结果）

看到上面的结果后，我加了“看得到 / 看不到”的区分：
- 函数在该内核里没有符号，或定义它的文件关掉了插桩，就算“看不到”。

**混合归因**：某个架构上候选的函数和接口都看不到时，退回用手写表，否则用实测覆盖。

| 树 | 动态确认 | 测过没事 | 部分架构测到 | 转人工 | 模板违反却无候选 |
|---|---|---|---|---|---|
| X1 修复前 | 1 | 0 | 0 | 6 | 0 |
| X1 修复后 | 0 | 1 | 0 | 6 | 0 |
| 当前版本 | 0 | 0 | 0 | 6 | 0 |

X1 回到了“修复前确认、修复后通过”，和 `pipeline_v2` 一致。其中 arm64 的判断来自实测，riscv 和 x86 来自手写表兜底。

**候选三分类**（当前版本）：

| 候选集 | 个数 | 执行到 | 看得到但没执行到 | 看不到 |
|---|---|---|---|---|
| effdep5 纵向候选 | 32 | 0 | 26 | 6 |
| effdep7 候选 | 6 | 0 | 3 | 3 |

- 看得到但没执行到的 26 个，涉及 swap（`do_swap_page`）、hugetlb、中断、tracing、ACPI、BPF、cgroup、audit 等路径。现有 13 个模板只测匿名内存、THP、tmpfs/memfd、brk、mremap、munmap、mprotect，**确实走不到这些地方**。
- 看不到的 6 个：`move_ptes` 被内联；`try_charge_memcg` 在没插桩的 `memcontrol.c`；`print_instance`、`arg_track_log`、`audit_add_to_parent` 没有独立符号。

## 这一轮说明了什么

1. **KCOV 能把“没测到”说实**。以前流水线只能说“手写表里没有它”。现在对 26 个候选可以明确说：这些模板运行时根本没进过这个函数。这就是“转人工”和“测过没事”之间缺的那条证据。
2. **当前版本上，“测过没事”这一类仍然填不上**。原因不是记录不到，而是现有模板没有一个走到候选路径。要填上，得按候选生成用例（例如让 `do_swap_page` 被执行：开 swap 再换出换入），而不是只靠固定的 13 个模板。
3. **单靠 KCOV 不能替代手写表**。内存管理里最关键的几个函数恰好在盲区：`page_alloc.c` 不插桩，大量 `static` 函数被内联，x86 的 TLB 刷新文件也不插桩。用“实测为主、盲区退回手写表”的混合归因，才能保持 X1 的结果。
4. **手写表本身有 3 处写错**（见上），KCOV 帮着找出来了。

## 局限

- KCOV 只记录本线程。T3 的另一线程、中断里的 TLB 刷新，都看不到。
- 只记录每个模板的第 1 次尝试；8 次尝试走的路径可能略有不同。
- “看不到”的判断用 `git grep` 找定义文件，只认 `.c` 文件，再对照 Makefile 里的 `KCOV_INSTRUMENT ... := n`。这是近似判断：同名函数、宏生成的函数可能判断错。
- X1 修复后这棵树的覆盖，沿用了修复前 KCOV 内核的覆盖（判据如此规定）。

## 下一步建议（还没做）

1. **补上内联盲区**：开 `DEBUG_INFO` 重建这 6 个内核，用 `llvm-symbolizer --inlining` 把地址展开到内联链。这样 `do_anonymous_page`、`move_ptes` 这类函数就能看到。这一项预计能消掉 128 项盲区中的大部分。
2. **补上没插桩的盲区**：只给测试内核去掉 `mm/page_alloc.o` 的 `KCOV_INSTRUMENT := n`（不改正式结论用的内核），看 `post_alloc_hook` 是否能被记到。
3. **按候选生成用例**：对“看得到但没执行到”的候选，按它所在的路径补用例（swap、hugetlb、mincore 等），再用 KCOV 确认确实走到了。

## 文件

- `criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`：判据和修订。
- `build.sh`、`build.log`：构建（内核在 WSL `/root/work/kcov/kernels/`，1.3G）。
- `propsuite3.c`、`run.sh`、`run_all.sh`、`runs/`：检查程序和 24 次运行日志。
- `judge.py`、`judge_head.*`、`judge_x1pre.*`、`regression.txt`：判错和回归。
- `symbolize.py`、`symbolize_*.txt`、`coverage_*.json`：地址到函数。
- `analyze_kcov.py`、`accuracy.json`、`pipeline_kcov_*.json`、`report_kcov_*.md`、`reach.json`：按判据的分析。
- `classify_missing.py`、`funcinfo.txt`、`kcov_not_instrumented_*.txt`、`missing_classified.*`：没测到的原因。
- `supplement.py`、`candinfo.txt`、`supplement.*`：事后补充分析。
