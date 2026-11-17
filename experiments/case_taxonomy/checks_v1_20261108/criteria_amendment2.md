# 判据修订 2（2026-11-08 14:40，Claude，写于第二次评估运行之前）

第一次真实内核评估（13 个目标，12:20–14:28）跑完后，我在核对汇总时发现两个我自己代码里的错误，导致第一次的结果整体无效。按失败规则（自己的代码错 → 修正后重跑），本修订只修工具、加防护，**不改任何判据、阈值、样本或期望集**。

## 发现的问题

- **所有单元都在解析时出现致命错误。** 13 个目标的每个单元 `unit_status` 都是 `fatal`，原因相同：`'generated/autoconf.h' file not found`。
  - 内核 `compile_commands.json` 里的 `-I./include`、`-include ./include/linux/kconfig.h` 是相对 `directory`（即 `O=` 构建目录）写的。
  - 抽取器 `ctx_extract.py` 解析前没有切换到这个目录，相对路径就按 Python 进程的当前目录去找，所以找不到。
  - 后果：`CONFIG_*` 宏全部未定义，`IS_ENABLED()` 全按关闭处理，按配置条件编译的代码走错分支。clang 遇到致命错误后虽然还会继续产生 AST（所以函数数看着正常），但这些结果不能用。
  - 自测没发现它，是因为自测的编译命令用的是绝对路径 `-I`。
- **`indirect_calls`、`inline_asm` 两个计数一直是 0。**
  - `ctx_analyze.py` 的 `count()` 写成了 `if t in kinds: kinds[t] += 1`，而 `kinds` 一开始是空字典，所以永远不计数。
  - 这只影响汇总里的两个计数，不影响标记本身。

## 修订条目

1. `ctx_extract.py` 在解析每个单元前执行 `os.chdir(row["directory"])`。
2. `ctx_analyze.py` 的 `count()` 改为无条件计数。
3. 自测 `selftest/verify.py` 改为：
   - 编译命令用相对路径 `-I include`；
   - 额外要求两个单元都解析干净（`unit_status == {"ok": 2}`）；
   - 额外要求计数器能数对一个小样例（icall 2 个、asm 1 个）。

   期望集 `EXPECTED` 一条没改。我做了反向检查：去掉第 1 条修正后，新自测会失败（`unit_status_clean: false`）。
4. `eval_samples.py` 在分析前检查 `extract_done.json`：只要有一个单元不是 `ok`（`fatal` 或 `error`），就停下报告，不继续计分。
5. 第一次运行的产物移到 `invalid_run1_autoconf/` 留档，不参与任何统计：
   - `results/`、`sample_eval.json`；
   - 修正前的自测结果。

   `/root/work/checks_v1/cache` 删掉重抽。构建目录保留，构建本身没有问题。

## 不变的部分

判据第 5、6 节（≥4/6 命中参考线、当前版本人工核对的抽样方法与种子 20261108、≥25% 疑似真问题参考线）和修订 1 全部不变。
