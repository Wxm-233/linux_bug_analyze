# 交换项编解码结论的独立复核（swaprev_20261122，第八轮）

2026-11-22，Claude。用户：“做独立复核”。对应第七次规划（astra）原定第 8 天“独立复核”。判据 `criteria.md`（SHA e2a6bed9…），写于准备材料和调用 Codex 之前。第二审查人是 Codex（gpt-6.1-sol，推理 max），新会话、无沙箱（要进 WSL 读源码）。

## 结论

- **8 条中 6 条一致，Cohen κ ≈ 0.68。** 关键的两条（arm LPAE 截断是真实问题、x86_64 原生测试漏测）和 loongarch 原生测试误报，双方独立得出相同结论，连引入提交、关键位数都一致。
- **两处分歧，裁定后一条改判、一条维持**：
  - **R2 mips32 XPA：采纳 Codex 的“不可达”，是我原来判错了。** 我按 4K 页算出“32GB 以上截断”，实际这个配置是 16K 页（XPA 在 Kconfig 里要求 `!PAGE_SIZE_4KB`），截断从 128GB 开始；而且 Malta 的内存都在 32 位物理地址内。前几轮里相关的说法都已追加更正。
  - **R4 mips64：维持“不可达”。** Codex 判“可能”，是因为它没找到物理内存上限的证据。我补上了内核自己的出处：MIPS 的 `sparsemem.h` 定义 `MAX_PHYSMEM_BITS 48`，低于截断起点 2^52。
- **QEMU 实验的复核**：Codex 判“基本确认（有可补的漏洞）”，自己解码 pagemap 后结果与我一致。它指出我的 README 写过头的地方（“永久卡死”“内存拿不回来”“不开 DEBUG_VM 只会无声卡死”都没有直接观察到），以及对照组不只改了页帧号。我同意，已在 `lpaeqemu_20261122/README.md` 和 `confirmed_bugs.md` B-2026-11-22-1 追加更正，结论措辞收窄为“300 秒内没有完成”等实际观察到的现象。
- 复核之后，第五～七轮的违反里**真正计入的只剩 arm LPAE**（已登记），另有两个原生测试自身的问题（x86_64 漏测、loongarch 误报）。

## 一、逐条结果

| 编号 | 对象 | 我（调用前封存） | Codex（盲判） | 裁定 |
|---|---|---|---|---|
| R1 | arm LPAE 迁移项页帧号 | 真实问题 | 真实问题 | 真实问题 |
| R2 | mips32 XPA | 可能 | 不可达 | **不可达**（我判错：页大小、平台都没核对） |
| R3 | ppc44x | 不可达 | 不可达 | 不可达 |
| R4 | mips64 | 不可达 | 可能 | **不可达**（补内核出处 `MAX_PHYSMEM_BITS 48`） |
| R5 | i386 PAE（对照） | 不是问题 | 不是问题 | 不是问题 |
| R6 | 不开 LPAE 的 arm（对照） | 不是问题 | 不是问题 | 不是问题 |
| R7 | x86_64 原生测试输入 | 测试缺陷/漏测 | 测试缺陷/漏测 | 测试缺陷/漏测（`a3a3e215c9c1`） |
| R8 | loongarch 原生 PMD 测试 | 测试缺陷/误报 | 测试缺陷/误报 | 测试缺陷/误报（`c0a80c2ce68d`） |

双方给的关键数值（`review/codex_review.json`、`review/claude_review.json`）：R1 都是 `SWP_PFN_BITS` 26、编码 24 位、LPAE 40 位物理地址（Codex 另引 `pgtable-3level-hwdef.h:73-76`）；R7 都是 `max_swap_offset = 0`、本意是 2^50-1；R8 都是偏移第 36 位落到 PMD 第 60 位（`_PAGE_PRESENT_INVALID`）、合法页帧号 34 位。裁定理由在 `review/adjudication.json`。

## 二、QEMU 实验的复核（`review/codex_qemu_review.md`）

| 问题 | Codex 的意见 | 我的处理 |
|---|---|---|
| 失败能否另有原因 | 多页偏移都恰好丢掉同一个高位，单靠锁竞争、内存压力解释不了；但对照组同时改变了 `mem_map` 跨度和 QEMU 访问的地址 | 同意；更硬的对照是同一段内存跨过 64GB、比较 2^24 两侧的页，留作可选的补充实验 |
| 数值是否自洽 | 自己解码 5 个条目：类型都是 30，偏移等于拆分前页帧号的低 24 位（第 5 个是推算） | 与我的解码一致 |
| 写过头的地方 | “永久卡死”“内存拿不回来”“清除时对不上”“不开 DEBUG_VM 只会无声卡死”都超出日志 | 同意，已追加更正 |
| HIGHPTE | 结论限定于关 HIGHPTE；静态结论不受影响；早期卡死的根因未定（同时切换了 EXPERT） | 同意 |
| 总评 | 基本确认（有可补的漏洞） | 同意 |

## 三、更正了哪些记录（只追加说明）

- `pfnswap_20261121/README.md`：mips32xpa 截断起点改为 128GB、Malta 上不可达；mips64 补出处。
- `swapcmp_20261122/README.md`：mips32 XPA 3 格改为不计入，计入的违反只剩 arm LPAE。
- `lpaeqemu_20261122/README.md`：新增“复核后的更正”一节。
- `../../confirmed_bugs.md` B-2026-11-22-1：追加“复核”一条。

## 四、文件

- `criteria.md`、`criteria_sha256.txt`（含材料和两份提示的 SHA）
- `review/packets.md`（盲审材料）、`review/codex_prompt.md`、`review/codex_prompt_qemu.md`
- `review/claude_review.json` + `review/claude_review_sha256.txt`（调用前封存，调用后核对未变）
- `review/codex_review.json`、`review/codex_notes.md`、`review/codex_qemu_review.md`（Codex 产出）
- `review/adjudication.json`（一致性、裁定理由、更正清单）

统计：模型调用：Codex 2 次（新会话 `01a2011a-c3d4-71d0-9e05-d4cf22c54434`，周额度 5.0% → 7.0% → 8.0%）；构建 0；没有运行内核；没有改写提示（Codex 没有拒绝）。
