# 动态验证新疑点 S5：调试构建下 folio_pte_batch 拿到 device-exclusive 项（s5dyn_20261116）

2026-11-16，Claude。用户：“验证 S5”。判据 `criteria.md` 和预测 `predictions.json` 在构建前写定；修订 1 `criteria_amendment1.md` 写在第一次正式运行之后，修订 2 `criteria_amendment2.md` 写在第二次之后。SHA 都在 `criteria_sha256.txt`。

统计行：模型调用 0；Codex 调用 0；构建 6（全量 3、变异 3）；新确认缺陷 0（S5 与 B-2 同根，上游已修）；新疑点 0。

## 一句话结论

**S5 在 riscv 上完全成立，在 arm64 上也复现了，而且后果比预测的严重；x86_64 的回收始终扫不到测试用的大页，没法判定。** 判据第五节要求 x86_64 和 riscv 都满足，所以按判据只能算“部分成立”。

在开 `CONFIG_DEBUG_VM` 的内核上，riscv 和 arm64 每次都是：
1. 先在 `mm/internal.h:420` 报 `VM_WARN_ON_FOLIO(!pte_present(pte))`；
2. 接着在 422 行对读错的 pfn 取 `struct page`，发生**内核 Oops**（访问没有映射的 `vmemmap` 地址），回收的进程挂掉，系统卡住。

加修复变异 F5（只对 present 项做批处理），或者不开 DEBUG_VM，都不再出现。

**这个问题上游已经修了**：`f3c493d2f42b`（2026-11-02 合入主线）。它的提交说明写了 “folio_pte_batch() will VM_WARN_ON_FOLIO”，修法是批处理前先查 present。

## 疑点（说人话）

内存回收时，`folio_referenced_one()` 遇到大页 folio，会调用 `folio_pte_batch()`，把一串连续的页表项当一批处理。`folio_pte_batch` 要求第一项是 present 的。开了调试选项时，它会检查这一点：
- 第 420 行检查 present；
- 第 422 行用 `pte_pfn` 取出页框号，再用 `pfn_to_page` 取到 `struct page`，核对它属于这个 folio。

驱动把大页中的某一页设成 device-exclusive 后，这一项不 present。`folio_referenced_one` 只查了“是不是大页”，就把它交了进去：
- 420 行先报 WARNING；
- 422 行再对这一项调 `pte_pfn`。device-exclusive 项的位布局和 present 项不一样，读出的页框号是错的，`pfn_to_page` 指到一块没有映射的地址，就 Oops 了。

这些检查只在 `CONFIG_DEBUG_VM` 打开时才编进内核，所以只影响调试构建。但很多测试、模糊测试用的内核（例如 syzbot）都开着它。

## 做法

1. **内核**：kbuild 新配置档 `dbgvm`（= `dyn` + `DEBUG_KERNEL` + `DEBUG_VM`，MGLRU 关）。
   - 三个架构各编 plain 和 F5。F5 把 `rmap.c:969` 的条件加上 `pte_present(ptep_get(pvmw.pte))`。
   - F5 第一次构建三个都失败（rc=3），原因是我写的预检正则没考虑换行。变异本身打上了，改了正则后重建成功。
   - 对照用现有的 `dyn` 内核（不开 DEBUG_VM）。
2. **测试程序 `s5.c`**（由 `s4.c` 改来）：
   - 映射 2MB 对齐的匿名区，`MADV_HUGEPAGE`，确认拿到了 THP；
   - 修订 2：先 `MADV_COLD`；
   - 用 `lib/test_hmm` 把第 8～15 页设成 device-exclusive。PMD 会被拆成 PTE，folio 仍是大页，用 kpageflags 确认；
   - 修订 1：先输出回收前的证据，再 `memory.reclaim` 最多 20 次，扫到这个大页就停；
   - 最后核对类型和内容，30 秒看门狗。
3. **规模**：冒烟 2 次。正式运行做了三次，每次 24 次，只有第三次（修订 2 之后）计入结论；前两次的日志和判定保留在 `runs_first/`、`runs_second/`。

## 结果（第三次正式运行，`judge_main.txt`、`judge_main.json`）

| 内核 | 结论 | 说明 |
|---|---|---|
| riscv `dbgvm` plain | **复现 3/3** | 每次都是 420 行 WARNING，随后 Oops（`Unable to handle kernel paging request at ff1c…`），系统卡住 |
| riscv `dbgvm` F5 | 不复现 0/3 | 第 1 次回收就扫到，大页正常换出到 zram |
| riscv `dyn` plain（无 DEBUG_VM） | 不复现 0/3 | 同上 |
| arm64 `dbgvm` plain | **复现 3/3** | 420 行 WARNING，随后 Oops（`fffff1ffc0000208`） |
| arm64 `dbgvm` F5 | 表上记“复现 2/3”，**但不是 S5** | 没有 S5 的 WARNING。异常来自 B-2：8 个 device-exclusive 项被改成类型 14，`Bad swap file entry`，进程退出时 `BUG: Bad rss-counter`。判据的异常定义把 `BUG:` 也算进去了 |
| x86_64 `dbgvm` plain、F5、`dyn` plain | **无效** | 9 次里 8 次，20 次回收都没扫到这个大页（加了 `MADV_COLD` 也没用）；唯一扫到的那次（F5）没有异常，但因为回收前的证据不全，判为无效 |

判据第五节的条件：
- riscv 三条全部满足；
- x86_64 三格都无效，没法判定。

按判据，S5 只能算“部分成立”。

### 与预测对照（`predictions.json`）

| 预测 | 结果 |
|---|---|
| riscv plain：复现，只有 420 行 WARNING，422 行不报 | 复现对；但 **422 行也出事了，而且是 Oops，预测错** |
| riscv F5 / dyn：不复现 | 对 |
| arm64 plain：复现，另有 B-2 改坏项 | 复现对；后果同样是 Oops，系统在 B-2 的改坏之前就挂了 |
| arm64 F5：不复现 S5，但仍有 B-2 改坏项 | 对 |
| x86_64 各格 | 没法对照（无效） |

**预测错的原因：编码表有盲区。** 编码表说 riscv、arm64 的 `pte_pfn` 读 device-exclusive 项不会出错。实际上：
- riscv 的 `pte_pfn` 用了运行时补丁，探针折叠不出常量，记成了“未知”，排序时当成了“不出错”；
- 探针只用了一个很小的页框号 `0x12345`，真实的页框号位数更多，有的位会落进另一套编码里。

### 冒烟测试（`judge_smoke.*`，不计入）

用的是修订前的测试程序。x86_64 那次回收扫到了大页，报了 420 行和 422 行共 32 次 WARNING，没有 Oops，页正常换出。riscv 那次同样是 WARNING 后 Oops。

## 看出的几点

1. **S5 比上游修复说明里写的严重。** 上游写的是“会 VM_WARN_ON_FOLIO”，我们在 riscv、arm64 的调试构建上看到的是 Oops。原因是 422 行的检查本身要对读错的 pfn 取 `struct page`。上游的修复（批处理前先查 present）把这个也一起消掉了。
2. **编码表要补两处**：
   - 多换几个页框号来探 `pte_pfn` 这类读取值的接口；
   - 探针算不出常量的格子不能当作“不出错”，应该单独标为“未知”。
3. **x86_64 的回收为什么扫不到这个大页，没有查清。** 同样的程序在 riscv、arm64 上能扫到，冒烟时 x86_64 也扫到过一次。可能和 x86_64 的内存布局、zram 交换的时机有关。

## 文件

- 判据：`criteria.md`、`predictions.json`、`criteria_amendment1.md`、`criteria_amendment2.md`、`criteria_sha256.txt`
- 测试程序与构建：`s5.c`、`cc_check.sh`、`build.sh`、`build.log`、`build_f5.sh`、`build_f5.log`、`kernels/`
- 运行：`run.sh`、`run_all.sh`、`smoke.sh`、`run_main.log`、`runs/`、`runs_first/`、`runs_second/`
- 判定：`judge.py`、`judge_smoke.*`、`judge_main.*`、`stats.json`
- kbuild：`profiles.json` 加了 `dbgvm` 档；`mutations/s5dyn.json`（F5）。WSL 新树 `df2908090cda_{arm64,x86_64,riscv}_dbgvm`，保留作复用。
