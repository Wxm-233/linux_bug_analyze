# 任务：独立判断 14 条“没查 present 就用受限接口”的报告（第二标注人，盲判）

你是第二个标注人，独立判断。**不要读**：`experiments/case_taxonomy/reach_20261115/` 下除 `review_new.txt`、`criteria.md` 和本目录以外的文件（特别是 `review_new_judgement.json`、`README.md`、`head.json`）；也不要读 `p1check_20261115`、`contract_20261115`、`encrank_20261115`、`p1dyn_20261115` 下的判断文件和 README；主文件夹 `../交接文档.md`、`../进度日志.md`（AGENTS.md 里“先读交接文档”本次不适用）。可以读 `encrank_20261115/table.md`（各架构读错表）。

## 背景

页表项不 present 时（交换项、迁移项、device-private、device-exclusive、uffd 标记），`pte_pfn`、`pte_dirty`、`pmd_special` 这类只对 present 项有定义的接口会读到另一套编码里的位。`review_new.txt` 列出 14 处在同一函数里没查 present 就调用这些接口的位置（已经机械地滤掉了内核页表、现造的值、调用者全部守卫过的情况），每条标了编码表认为会读错的架构，并附代码（`>>` 标出行）。第 13、14 条是附加项。

## 判断

每条判为：
- **可能**：当前代码（`df2908090cda`）里确实存在一条路径，让这次调用拿到非 present 项，并且在标出的某个架构上**结果会错、产生后果**（写出路径、项的种类、架构和后果）；
- **不可能**：上文或调用者已保证 present，或者项按构造一定 present，或者读错不影响结果；写出依据；
- **说不清**。

需要时读完整源码（只读）：`wsl -u root -- git -C /root/repos/linux show df2908090cda:<文件>`，`git grep` 找调用者。

## 输出（写到本目录 `experiments/case_taxonomy/reach_20261115/codex_blind/`）

`codex_new.json`：14 项列表，每项 `{"k": 编号, "loc": "文件:行", "verdict": "可能|不可能|说不清", "why": "两三句"}`；可选 `notes.md`。只读，不构建，不联网，不调用别的模型。完成后在 `experiments/codex_worklog.md` 末尾追加一条日志。用中文。
