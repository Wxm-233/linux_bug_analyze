# shmem 补丁 v3 的重测（s6v3_20261118）

2026-11-18，Claude。用户：“准备 v3 并重测”。判据 `criteria.md`（SHA 记在 `criteria_sha256.txt`），写在构建和运行之前。

**结论：两格都与预测一致，v3 补丁说明里的 “With this change: 0/3” 成立。**

| 格 | 内核 | 结论 | 说明 |
|---|---|---|---|
| plain_force（对照） | 7.3-rc2 `pg64k`（arm64、64K 页） | **复现**（有效 3/3，异常 3/3） | 每次都拿到 512MB 的整块 PMD folio（`ShmemPmdMapped: 524288 kB`），换出时报 `WARNING: lib/xarray.c:1051 at xas_split_alloc` |
| v3_force | `pg64k` + F6v3（与 v3 补丁代码一致：force 分支设 `mask` 并 `goto out;`） | **不复现**（有效 3/3，异常 0/3） | 不再产生 13 阶 folio（`whole_pmd_folio=0`，`ShmemPmdMapped: 0`） |

- 内核：kbuild，变异 `tools/kbuild/mutations/s6v3.json:F6v3`，增量编译 20 秒。第一次写的预检正则没考虑 `READ_ONCE` 展开后带分号，在构建之前用模拟文本发现并改正。
- 复现程序沿用 `s6dyn_20261116/s6.c`（只读）；`run.sh`、`judge.py` 复制自 s6dyn，只改了输出目录。
- 统计行：模型调用 0；Codex 调用 0；构建 1。

文件：`criteria.md`、`criteria_sha256.txt`、`build_run.sh`、`build.log`、`build_run.log`、`run.sh`、`judge.py`、`runs/main/`、`judge_main.{json,txt}`、`kernels/`
