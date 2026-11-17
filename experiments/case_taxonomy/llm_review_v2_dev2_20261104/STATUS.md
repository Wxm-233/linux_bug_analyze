# 停点：复核第2版开发第2轮（进行中）

- 判据：`criteria.md`，SHA见`criteria_sha256.txt`。标签沿用第1轮的`labels3.json`（`553fdfb7…`）。
- 已完成：
  - `facts2.py`。自测（`selftest.log`）中发现共同调用者解析有误：`git grep`输出带版本前缀，导致一律找不到。已修正，`start_kernel`中`setup_arch`与`jump_label_init`的先后现在给对了。
  - `build.py`已生成120个提示词，写入`模型调用测试/2026-11-04/llm_review_v2_dev2_20261104/D{1,2}_nn`。
  - `run_calls.py`、`check_step2.py`、`score.py`已写好。
- **等用户同意后调用**，顺序如下：
  1. `run_calls.py step1_index.json`（Windows）；
  2. `check_step2.py`（WSL）；
  3. `run_calls.py step2_index.json`；
  4. `score.py`（WSL）。

## 本轮已完成

结果见`README.md`。
