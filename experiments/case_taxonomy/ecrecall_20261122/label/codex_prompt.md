# 任务：历史提交的独立标注（第二标注人，盲标）

## 背景

这是一个防御性的研究项目：我们在开发一个静态分析器，在 Linux 内核源码里找“公共代码和各架构实现之间约定不一致”的**功能正确性问题**。其中一个检查叫“编码一致性”：它在 20 个构建上把页表/交换项的取值级接口组合起来（构造 → [单参数修改] → 观察，或交换项编码 → 解码 → 读字段），逐位求值，跨架构比较。现在要测它的历史召回，需要先确定一批“这个检查原则上能处理的”历史修复提交。请你**独立**标注下面 25 个提交，第一标注人（Claude）已标过，请不要看他的结果。

说明：只读公开的内核 git 历史，不需要写任何代码、补丁或触发程序。

## 判断标准：“EC 可处理类型”，三条同时满足才标“是”

- (a) 修复前，某架构的取值级接口——构造（`pfn_pte`/`pfn_pmd`/`mk_pte` 类）、单参数修改（`pte_mk*`、`pte_wrprotect`、`pte_clear_*`、`pmd_mkinvalid` 等）、观察（`pte_present/young/dirty/write/read/leaf/bad/…`）、交换项编解码（`__swp_entry`、`__pte_to_swp_entry`、`pte_swp_*`、公共层 `swp_entry`/`softleaf_*`）——对某些输入给出与通用约定或其他架构不一致的**值**；
- (b) 这种不一致只看头文件、按值求值就能看出：不涉及锁、原子操作、TLB/缓存刷新、页表遍历指针、运行时状态（全局变量、CPU 特性、虚拟化转换），也不是两参数接口（`pte_modify`、`pte_access_permitted`、`pte_accessible(mm, pte)` 等）本身的问题；
- (c) 涉及的架构在这 20 个构建之内：riscv（rv64、rv32）、x86（x86_64、i386、i386 PAE）、arm64、powerpc（ppc64le radix/hash、ppc64e、ppc32 book3s、44x、8xx）、s390、loongarch、mips（32、32 XPA、64）、arm（含 LPAE）、hexagon。

## 不要读

- `experiments/case_taxonomy/` 下除本文件和 `experiments/case_taxonomy/ecrecall_20261122/pool.tsv` 以外的所有内容（含第一标注人的结论和分析器结果）；`experiments/confirmed_bugs.md`、`experiments/README.md`；
- 主文件夹的 `../交接文档.md`、`../进度日志.md`、`../日志/`（本任务不需要；AGENTS.md 里“先读交接文档”这一条本次不适用）；
- 所有 `sealed*` 目录、`*_sealed*` 文件、`模型调用测试/codex/` 下的运行记录。

## 可以读

- `experiments/case_taxonomy/ecrecall_20261122/pool.tsv`（25 个提交：哈希、日期、标题）；
- 内核 git：`wsl -u root -- git -C /root/repos/linux show <哈希>`、`git log`、`git show <版本>:<路径>`。

## 输出

写到 `experiments/case_taxonomy/ecrecall_20261122/label/codex_labels.json`：

```json
[{"hash": "018e9828eb52", "label": "是|否", "why": "一句理由，指出是哪个接口、哪种取值不一致，或不满足哪一条"}]
```

25 条都要有。最后在 `experiments/codex_worklog.md` 追加一行本次任务记录。
