# 任务：独立判断 23 条“TLB / 缓存钩子”候选（第二标注人，盲判）

你是第二个标注人，独立判断。工作目录是仓库 `linux_bug_analyze/`。

**只可以读**：`experiments/case_taxonomy/tlbhook_20261117/review.txt`、本目录 `codex_blind/`、内核源码（只读）。

**不要读**：`tlbhook_20261117/` 下的其他文件（特别是 `criteria*.md`、`claude.json`、`adjudication.json`、`README.md`、`head.json`、`recall.json`）；以前各轮的判断文件和 README；主文件夹的 `../交接文档.md`、`../进度日志.md`（AGENTS.md 里“先读交接文档”这一条本次不适用）；`experiments/confirmed_bugs.md`。

## 背景

公共代码修改页表或页内容后，要调用钩子让架构做 TLB 或缓存维护：`update_mmu_cache`（新建用户映射后）、`flush_cache_vmap` / `flush_tlb_kernel_range`（新建或修改内核映射后）、`flush_cache_page` / `flush_cache_range`（改用户映射前）、`flush_dcache_page`（内核写页内容后）。这些钩子在 x86、arm64 上多数是空的，但 riscv（TLB 可能缓存无效项，需要 sfence.vma）和缓存有别名的架构（arm、mips、parisc、sh、sparc、xtensa 等）需要它们。

`review.txt` 每条是分析器报出的一处可能缺维护的地方（规则说明写在每条开头）。分析器是词法的，可能把与映射无关的函数、回调函数（调用方做了刷新）、刷新被包了一层的情况误报出来。

## 判断

- **可能**：在某个具体架构上，确实会因为缺这项 TLB 或缓存维护（或钩子效果不够）而出错，例如访问刚建立的映射时读到旧内容或触发无法自愈的异常、用户看到旧数据、页面别名导致数据不一致。请写出架构、触发路径和后果。
- **不可能**：调用者或回调的调用方已经刷新；后续路径一定会刷新；与映射无关；架构有别的机制处理（例如缺页处理会修复假性异常），这个设计是有意的；或者涉及的架构都不需要这项维护。请写出依据。
- **说不清**。

需要时读完整源码（只读）：

```
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/tlbhook_20261117/codex_blind/read_source.sh show <文件> [起:止 ...]
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/tlbhook_20261117/codex_blind/read_source.sh grep64 <base64 编码的正则> [路径...]
```

## 输出

写到 `experiments/case_taxonomy/tlbhook_20261117/codex_blind/`：
- `codex.json`：23 项的列表，每项 `{"k": 编号, "verdict": "可能|不可能|说不清", "why": "两三句"}`；
- 可选 `notes.md`。

只读源码，不构建，不联网，不调用别的模型。完成后在 `experiments/codex_worklog.md` 末尾追加一条日志。用中文。
