# 任务：独立判断 27 条“没查 present 就用受限接口”的报告（第二标注人，盲判）

你是第二个标注人，独立判断。工作目录是仓库 `linux_bug_analyze/`。

**只可以读**：
- `experiments/case_taxonomy/restblind_20261116/review.txt`（27 条报告和代码片段）、`criteria.md`、本目录（`codex_blind/`）；
- `experiments/case_taxonomy/encrank_20261115/table.md`（各架构读错表）；
- 内核源码（只读）。

**不要读**：`restblind_20261116/` 下除上面几个以外的文件（特别是 `claude.json`、`adjudication.json`、`README.md`、`review.json`）；以前各轮目录（`p1check_*`、`contract_*`、`encrank_*` 中除 table.md 外、`reach*`、`s3dyn_*`、`s3pfn_*`、`p1dyn_*`）里的判断文件和 README；主文件夹的 `../交接文档.md`、`../进度日志.md`（AGENTS.md 里“先读交接文档”本次不适用）；`experiments/confirmed_bugs.md`。

## 背景

页表项不 present 时（交换项、迁移项、device-private、device-exclusive、uffd-wp 标记、guard 标记），`pte_pfn`、`pte_dirty`、`pmd_write`、`pmd_uffd` 这类只对 present 项有定义的接口会读到另一套编码里的位。`review.txt` 列出 27 处在同一函数里没查 present 就调用这些接口的位置。这些位置已经机械地滤掉了：调用点上有 present/trans_huge/access_permitted 守卫的、调用者全部守卫过的、现造的值、内核页表、测试代码、参数常量导致分支不执行的。每条标了编码表认为会读错的架构，并附代码（`>>` 标出行）。

## 判断（见 criteria.md 第二节）

每条判为：
- **可能**：当前代码（`df2908090cda`）里确实存在一条路径，让这次调用拿到非 present 项，并且在标出的某个架构上**结果会错、产生后果**（写出路径、项的种类、架构和后果）；
- **不可能**：上文或调用者已保证 present，或者项按构造一定 present，或者读错不影响结果；写出依据；
- **说不清**。

注意：很多函数的“present”是由调用者保证的（例如在 `pmd_trans_huge` 加锁之后、`softleaf` 判断之后），请顺着调用者查。非 present 项的种类要考虑全，包括 uffd-wp 标记、guard 标记这类“软件标记”。

需要时读完整源码（只读）：

```
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/restblind_20261116/codex_blind/read_source.sh show <文件> [起:止 ...]
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/restblind_20261116/codex_blind/read_source.sh grep <正则> [路径...]
```

## 输出（写到 `experiments/case_taxonomy/restblind_20261116/codex_blind/`）

`codex.json`：27 项列表，每项 `{"k": 编号, "loc": "文件:行", "verdict": "可能|不可能|说不清", "why": "两三句"}`；可选 `notes.md`。只读，不构建，不联网，不调用别的模型。完成后在 `experiments/codex_worklog.md` 末尾追加一条日志。用中文。
