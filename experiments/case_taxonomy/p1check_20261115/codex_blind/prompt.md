# 任务：独立判断 30 条静态检查报告（第二标注人，盲判）

你是第二个标注人，独立判断，**不要读**：
- `experiments/case_taxonomy/p1check_20261115/` 下除 `review_o1.txt`、`criteria.md`、`criteria_amendment1.md` 和本目录以外的文件（尤其是 `review_o1_judgement.json`、`README.md`、`*.json` 结果）；
- 主文件夹 `../交接文档.md`、`../进度日志.md`（AGENTS.md 里“先读交接文档”这一条本次不适用）。

## 背景（一句话）

静态检查 P1 报告：公共代码对一个页表项调用了“只对 present 条目有定义”的接口（如 `pmd_young`、`pte_dirty`、`pud_pfn`、`pmd_page`），而在同一函数里没有找到对它的 present 判断。页表项不 present 时（交换项、迁移项、device-private 项、uffd 标记、PROT_NONE 以外的非 present 项），这些接口读到的位是另一种编码，各架构结果不同。检查不跨函数，所以调用者或上文可能已经保证了 present。

## 输入

`experiments/case_taxonomy/p1check_20261115/review_o1.txt`：30 条报告，每条有文件、行号（`>>` 标出）、函数、接口和实参，以及附近代码。

需要时在 WSL 里读完整源码和调用者（只读，版本是 `df2908090cda`）：
```
wsl -u root -- git -C /root/repos/linux show df2908090cda:<文件>
wsl -u root -- git -C /root/repos/linux grep -n <函数名> df2908090cda -- mm fs kernel include
```

## 判断

每条判为：
- **可能**：在当前代码里，确实存在一条路径，使这次调用拿到非 present 的条目（写出路径或条件）；
- **不可能**：调用者或上文已经保证条目 present，或者这个条目按构造一定 present（写出依据）；
- **说不清**。

## 输出（写到 `experiments/case_taxonomy/p1check_20261115/codex_blind/`）

`codex_o1.json`：30 项列表，每项 `{"k": 编号, "loc": "文件:行", "verdict": "可能|不可能|说不清", "why": "两三句理由"}`。另写 `notes.md` 记最难判的几条。

只读，不构建，不联网，不调用别的模型。完成后在 `experiments/codex_worklog.md` 末尾追加一条日志（只写做了什么、输出在哪）。用中文。
