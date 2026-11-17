# 判据：可达候选剩余条目的两人盲判（restblind_20261116）

2026-11-16，Claude。用户：“盲判剩余候选”。本文件在生成审查材料、做任何判断之前写定，SHA 存入 `criteria_sha256.txt`。

## 一、对象（写死）

可达性过滤正式版 `reachdead_20261116/head.json` 的 59 条可达候选里，**以前没审过的全部条目**。“审过”指位置（文件、行）出现在下面任一处：

- `p1check_20261115/o1_adjudication.json`（P1 前 30）；
- `contract_20261115/top30.json`（契约前 30）；
- `encrank_20261115/new_adjudication.json`（encrank 新前列 26 条）；
- `reach_20261115/new_adjudication.json`（reach 新审 12 条 + 附加 2 条）；
- `reachf4_20261116/changes_judgement.json`（page_table_check 的 9 条）。

按这个规则算出 27 条（名次 29～59 中的 27 条）。其中 `mm/huge_memory.c:1609`（`insert_pmd`）我在 `s3pfn_20261116` 里分析过，**我对它的判断不算盲判**，在结果里单独标出；Codex 对它仍是盲判。

## 二、判断（写死，与 reach 轮相同）

每条判为：

- **可能**：当前代码（`df2908090cda`）里确实存在一条路径，让这次调用拿到非 present 项（交换、迁移、device-private、device-exclusive、uffd-wp 标记、guard 标记等），并且在编码表标出的某个架构上结果会错、产生后果。要写出路径、项的种类、架构和后果；
- **不可能**：上文或调用者已保证 present，或者项按构造一定 present，或者读错不影响结果。要写出依据；
- **说不清**。

## 三、流程（写死）

1. 生成 `review.txt`（每条：位置、函数、接口、编码表读错的架构、前 30 行后 8 行代码）和 `review.json`；
2. 派 Codex（gpt-6.1-sol，max）盲判：只给 `review.txt`、本判据和编码表 `encrank_20261115/table.md`，可以只读查看源码；**不许读**我的判断文件、本轮 README、以前各轮的判断文件和 README、主文件夹的交接文档和进度日志。输出 `codex_blind/codex.json`；
3. 我在**不看** Codex 输出的情况下独立判断，写 `claude.json`；
4. 两份都完成后，算原始一致率和 Cohen κ（三类）；
5. 不一致的条目，我读双方理由并核对源码后裁定，写 `adjudication.json`。两人都判“可能”的条目直接记“可能”，但我仍要核实关键步骤。

## 四、参考线（不是通过条件）

- 27 条全部有两份判断；
- 原始一致率 ≥ 70%；
- 记录裁定“可能”的条数（不设下限）。裁定“可能”的，记为新疑点，并写出动态验证方案（本轮不做动态验证）。

## 五、规则

不安装、不联网、不构建；不调用大模型，Codex 第二标注人除外；只读 `/root/repos/linux`；不改旧轮次文件；不对外报告。统计行：模型调用 0；Codex 调用 1；构建 0；新确认缺陷 0；新疑点按实际写。
