# 同一公共调用、不同构建选中不同实现时的输出参数比较（outparam_20261120）

2026-11-20 深夜～11-21 凌晨，Claude。用户：“开始第一步”。gpt-6.2-astra 第二次规划（`plan2_20261120/astra_plan.md`）第二节的第一步。归入实现一致性检查。

- 判据 `criteria.md`（85c426f7…），写于实现和运行之前；修订 1（f5fdb0c4…）写于第一次绑定核验失败之后、审查之前。实现上的 3 处调整记在 `devlog.md`。
- 统计行：Codex 调用 1（盲审，周额度 70% → 70%）；其他模型调用 0；构建 0（只预处理已有编译命令对应的文件）。

## 结论

**未过线，停掉这种输出参数比较。** 绑定层（按构建预处理、按真实包含链选定义）经两组共 24 个样本核验全对，可以留作基础设施；但在它上面做“输出参数是否被写”的比较，两个榜单前 8 条都没有一条完整线索，两人盲审 9/9 一致排除。

最重要的发现：**同一调用点在不同构建下选中不同实现，绝大多数是“功能开关”造成的，不是“架构”造成的。** 例如空桩在功能关闭时被选中，而调用方本来就为此做了初始化，或者那条分支在该配置下根本走不到。在审查的 9 条里，5 条是调用方已初始化，2 条是合法的功能差异。

## 第 1 天：分母（`scope.py` → `scope_summary.json`；大表在 WSL `/root/work/outparam/scope.csv.gz`）

- 输入：`mm/`、`kernel/` 下至少在两个 defconfig 里编入的 355 个 `.c`，按原编译命令改成 `-E` 预处理 940 次，全部成功；2 分 16 秒，峰值 3.3 GB。
- 调用点 101,545 个（修订 1 之后）：

| 状态 | 数 |
|---|---|
| 双侧可绑定且不同 | 17,666（4,973 个接口） |
| 双侧同实现 | 55,683 |
| 一侧缺席 | 25,430 |
| 解析未知 | 1,946 |
| 间接调用 | 820 |

- 抽查的 24 个“不同”里，大多数是**同一份定义在不同构建下预处理后的函数体不同**（配置宏、HZ 常量等），定义位置真正不同的只有少数（功能开关下的真实现和桩）。

## 绑定核验（判据第六节第 1 条、修订 1）

| 轮次 | 结果 |
|---|---|
| 第一次，原 12 个 | **30/31，未过**：`perf_tp_event` 的调用方在 arm64 上被 `#ifdef CONFIG_EVENT_TRACING` 掉，脚本却仍按名字给 arm64 绑了一份定义 |
| 修正（只在调用点确实存在的构建上绑定）后，原 12 个 | 31/31 |
| 修正后，按新种子另抽 12 个 | 33/33 |

预期都是我只看源码、`#if` 条件和三份 `.config` 填的（`expect_helper.py`、`caller_ctx.py`），填完记 SHA（`criteria_sha256.txt`）后才对账。

## 第 2 天：输出参数比较（`outparam.py` → `pairs_summary.json`、`ranked_*.json`；明细在 WSL `/root/work/outparam/`）

- 四份微型对照 4/4 符合预期（`selftest.log`）。
- “双侧可绑定且不同”且实参是 `&局部变量` 的调用点 2,329 个；分析了 1,444 个，其余 885 个“局部变量”判断不成立。
- 报告 59 条，合并后 19 条，涉及 10 个接口。证据分数：2 分 3 条、1 分 15 条、0 分 1 条；**没有一条同时满足“一侧明确未写、对侧必写”和“调用方成功后干净地读”**。

## 第 3 天：审查（`review/`）

- 粗排、证据排序各取前 8 条，重叠 7 条，共 9 条；打乱、隐去来源后，我先判（`claude_labels.json`），Codex 盲判（`codex_labels.json`、`codex_notes.md`）。
- 结论一致 9/9 排除；原因类别一致 5/9，裁定见 `adjudication.json`。
- 去留判定见 `decision.md`。

## 分析器自身的问题（审查中发现，冻结后不再改）

- 调用方一侧没认出**指定初始化器**（`struct x v = { .a = … }` 会把省略的成员清零），也没把 `memset(&v, …)` 的初始化显示出来（评分用的“干净读”判断不受影响，但审查材料里“调用前初始化”一栏一直显示“无”）。
- `switch` 被建模成“可以整个跳过”，凭空多出一条“未写”路径。
- 经回调写入（例如经 cookie 写 `c.len`）判断不了。

## 下一步（按规划，首轮未过线）

停止新引擎实现。绑定正确、差异大多合法，所以按规划转为：在新评测集分析侧逐例登记“父树里最早可见的公共依赖、架构选择、必须观察的状态”，即每个漏报的第一个断点；交付哪些形态有自动化前提、哪些只能人工核验。

## 文件

- 判据：`criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`、`devlog.md`、`decision.md`
- 第 1 天：`scope.py`、`run_scope.sh`、`scope_summary.json`（另 `_run1`、`_run2` 为修正前）、`scope.log`、`scope_run1.log`
- 绑定核验：`binding_sample.py`、`binding_sample.json`、`binding_sample2.json`、`expect_helper.py`、`caller_ctx.py`、`expect_evidence.txt`、`expect_evidence2.txt`、`caller_ctx2.txt`、`binding_expect.json`、`binding_expect2.json`、`binding_check_run1.csv`、`binding_check.csv`、`binding_check2.csv`
- 第 2 天：`outparam.py`、`run_op.sh`、`selftest.log`、`op.log`、`pairs_summary.json`（另 `_run1`、`_run2`）、`ranked_coarse.json`、`ranked_evidence.json`（另 `_run2`）
- 审查：`review_packets.py`、`review/packets.md`、`review/items.json`、`review/source_map.json`、`review/claude_labels.json`、`review/codex_prompt.md`、`review/codex_labels.json`、`review/codex_notes.md`、`review/adjudication.json`
