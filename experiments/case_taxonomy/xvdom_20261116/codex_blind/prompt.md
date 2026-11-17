# 任务：独立判断 30 条“页表接口用错了项”的报告（第二标注人，盲判）

你是第二个标注人，独立判断。工作目录是仓库 `linux_bug_analyze/`。

**只可以读**：
- `experiments/case_taxonomy/xvdom_20261116/review.txt`（30 条报告和代码片段）、`criteria.md`、`criteria_amendment1.md`、`table2.md`、本目录（`codex_blind/`）；
- 内核源码（只读）。

**不要读**：
- `xvdom_20261116/` 下除上面几个以外的文件，特别是 `claude.json`、`adjudication.json`、`README.md`、`review.json`、`head.json`；
- 以前各轮目录里的判断文件和 README；
- 主文件夹的 `../交接文档.md`、`../进度日志.md`（AGENTS.md 里“先读交接文档”这一条本次不适用）；
- `experiments/confirmed_bugs.md`。

## 背景

页表项分三类：
- **present 项**；
- **空项**；
- **交换格式的非 present 项**：交换项、迁移项、device-private、device-exclusive、uffd-wp 标记、guard 标记等。

不同架构把各种标志位放在不同位置，所以有两种用错接口的情况：

- **MG 组**：只对 present 项有定义的修改接口（`pte_mkold`、`pte_wrprotect`、`pte_mkclean`、`pte_mkdirty`、`pte_mkuffd`、`pte_clear_uffd`、`pmd_*` 等）用在非 present 项或空项上，会把项改坏。
- **S、MS 组**：只对交换格式项有定义的接口（`pte_swp_soft_dirty`、`pte_swp_exclusive`、`pte_swp_uffd`、`pte_swp_mk*`、`pte_swp_clear_*`、`pmd_swp_*`）用在 present 项或空项上，会读错或改坏。

`review.txt` 列出 30 处调用。在调用所在的函数里，分析器没找到排除错误输入类的守卫。

这些位置已经机械地滤掉了以下几种情况：
- 有守卫的：MG 组是 present 守卫；S、MS 组是“非 present 且非空”或 softleaf 种类守卫；
- 调用者全部守卫过的；
- 现造的值；
- 内核页表；
- 测试代码；
- 参数常量导致分支执行不到的。

每条都标了编码表认为会出错的架构和输入类（例如 `np.dexcl.plain` 是 device-exclusive 项，`pr.dirty` 是带脏位的 present 项，`none` 是空项）。代码片段里用 `>>` 标出调用行。

## 判断

每条判为下面三种之一：

- **可能**：当前代码（`df2908090cda`）里确实有一条路径，让这次调用拿到定义域之外的项，并且在标出的某个架构上**结果会错、产生后果**。请写出路径、项的种类、架构和后果。
- **不可能**：上文或调用者已经保证了项的种类，或者项按构造一定属于定义域，或者读错、改坏不影响结果。请写出依据。
- **说不清**。

注意：

- 很多保证来自调用者，请顺着调用者查。例如：`page_vma_mapped_walk` 在非迁移模式下只返回 present 项；`softleaf` 判断之后才进入的分支。
- 定义域之外的项要考虑全，包括 uffd-wp 标记、guard 标记这类软件标记，也包括空项。
- 对通用接口（例如 `include/linux/pgtable.h` 里的默认实现），要查清楚哪些架构真的用它（没有定义 `__HAVE_ARCH_*`），以及它的调用者会不会传入定义域之外的项。

需要时读完整源码（只读）：

```
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/xvdom_20261116/codex_blind/read_source.sh show <文件> [起:止 ...]
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/xvdom_20261116/codex_blind/read_source.sh grep <正则> [路径...]
```

## 输出

写到 `experiments/case_taxonomy/xvdom_20261116/codex_blind/`：

- `codex.json`：30 项的列表，每项 `{"k": 编号, "loc": "文件:行", "verdict": "可能|不可能|说不清", "why": "两三句"}`；
- 可选 `notes.md`。

只读源码，不构建，不联网，不调用别的模型。完成后在 `experiments/codex_worklog.md` 末尾追加一条日志。用中文。
