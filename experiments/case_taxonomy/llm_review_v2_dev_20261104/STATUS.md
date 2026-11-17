# 停点：复核第2版开发轮（进行中）

- 判据：`criteria.md`（`a645afd1…`）。三类标签：`labels3.json`（`553fdfb7…`）。
- 已完成：
  - `facts.py`、`factcheck2.py`，自测`selftest.py` → `selftest.log`，7条全对；
  - `build.py`生成60个提示词，写入`模型调用测试/2026-11-04/llm_review_v2_dev_20261104/D1_nn`；
  - `check_step2.py`、`score.py`、`run_calls.py`已写好。
- **等用户同意后调用**，顺序如下：
  1. `run_calls.py step1_index.json`（Windows）；
  2. `check_step2.py`（WSL）；
  3. `run_calls.py step2_index.json`；
  4. `score.py`（WSL）。

## 本轮已完成

结果见`README.md`。
