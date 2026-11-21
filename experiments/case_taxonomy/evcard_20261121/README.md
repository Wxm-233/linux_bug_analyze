# 证据卡 + 两种排序的等预算对照（evcard_20261121）

2026-11-21，Claude。用户：“开始第 1 步”。`plan3_20261121/README.md` 第二节第 1 步（参考 astra 第一周，做了三处调整）。

- 判据 `criteria.md`（60802e5a…），写于实现和运行之前。
- 修订 1（132e1688…，第一次生成证据卡之后、核对和审查之前）：已审记录补上各轮的 README 和审查材料（文件名含 packet），审查时遇到认得的已审项当场排除。
- 统计行：Codex 调用 1（第二审查人，周额度 73% → 74%）；其他模型调用 0；构建 0。

## 结论

**新排序没过线，保留旧排序；但新排序找到 1 条完整线索，按规则进入第 3 步核验。**

| | 旧排序前 12 | 新排序（证据卡）前 12 |
|---|---|---|
| 完整线索 | 0 | **1** |
| 未决 | 0 | 2 |
| 排除 | 12 | 9 |

- 门槛要求新排序多出 ≥ 2 个完整线索根因、且涉及 ≥ 2 个接口；实际多出 1 个，**未达到**。
- 两榜不重叠，独有项共 24 条（≥ 4），有区分度。
- 两人一致 22/24；两条分歧都是“排除”对“未决”，裁定取“未决”（`review/adjudication.json`）。

## 那条完整线索

**x86 `amd_get_mmconfig_range()`（`arch/x86/kernel/amd_nb.c:165-167`）**：

- **截断**：把 AMD Fam10h+ 的 MMCONFIG 基址写进 `struct resource` 的 `start`/`end`。基址读自 64 位 MSR，最多 48 位；`resource_size_t` 在不开 PAE 的 x86_32 上只有 32 位（`PHYS_ADDR_T_64BIT` 没选），赋值前没有检查放不放得下。`AMD_NB` 在 32 位上也能开。
- **使用者**：
  - `drivers/pnp/quirks.c:301` 起的 quirk，用这个范围判断重叠，并补加内存保留区；
  - `arch/x86/pci/amd_bus.c:212` 起，用它从 MMIO 范围里扣除。
- **后果**：截断后两处都会落在错误的低地址上。
- **能推翻判断的观察**：32 位非 PAE 内核所支持的平台上，MMCONFIG 窗口一定在 4G 以下；或者调用方之前已经拒绝了 4G 以上的范围。
- **影响面**：很窄，只在“32 位非 PAE 内核 + MMCONFIG 基址在 4G 以上的 AMD 机器”上出现。还没查上游有没有人报过，也没有动态验证。

## 看出的几点

1. **旧排序前 12 条全是 ORD 的交换簇报告**（`SWAPFILE_CLUSTER`）。`orddom` 那一轮就说过这一类是噪声，旧排序把已知的噪声类排在最前。证据卡的消费栏对 ORD 都是“未知”（报告行是函数开头的 `{`），所以新排序把它们挪到了后面。
2. **新排序的前 12 条主要是 arch 目录下的 WT 和 WK**，但多数仍是误报：值域放得下、有意截断、已有守卫、32 位分支、合法的平台特例。证据卡目前只能认出很少几类反证。
3. **卡片核对 12/12 正确**：字段按规则生成没有出错。问题在于这些规则能表达的证据太少，不在于生成有误。
4. **池子很不均匀**：去掉已审项后剩 535 条，其中 WT 510 条；其他引擎的候选在前几轮基本都审过了。所以这一步的对照主要是在比较 WT 和 ORD。

## 文件

- `criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`
- `cards.py`：已审判断、合并、证据卡、两种排序、抽样；输出 `cards.jsonl`、`inventory.csv`、`queues.csv`、`cards_summary.json`（第一次运行的留作 `cards_summary_run1.json`）
- 卡片核对：`card_sample.json`、`card_expect.json`（记了 SHA）、`card_check.json`
- 审查：`review_packets.py`、`review/packets.md`、`review/items.json`、`review/source_map.json`、`review/claude_review.json`（记了 SHA）、`review/codex_prompt.md`、`review/codex_review.json`、`review/codex_notes.md`、`review/adjudication.json`
