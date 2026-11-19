# 召回样本的双人盲判结果（判据三.3）

- 标注人：Claude（`claude_labels.json`，先写完）；Codex gpt-6.1-sol 推理 max（`codex_labels.json`，新会话，盲判）。Codex 本次约用 2% 周额度，累计 52%。
- 样本：机械预筛后 8 条（`prefiltered.json`、`packets/`）。

| 样本 | 提交 | 覆盖函数 | Claude | Codex |
|---|---|---|---|---|
| 001 | 18a4e5cf633f | arm64 `arch_unregister_cpu` | 是 | 是 |
| 002 | 195a1b7d8388 | arm64 `alloc_insn_page` | 否 | 否 |
| 003 | a179a4bfb694 | riscv `hugetlb_mask_last_page` | 否 | 否 |
| 004 | 7df548840c49 | x86 `cpu_show_mmio_stale_data` | 否 | 否 |
| 005 | 1d5f82d9dd47 | x86 `bpf_jit_free` | 否 | 否 |
| 006 | f1797e4de114 | powerpc `module_alloc` | 否 | 否 |
| 007 | 4aa9340584e3 | s390 `arch_kimage_file_post_load_cleanup` | 否 | 否 |
| 008 | b89ddf4cca43 | arm64 `bpf_jit_alloc_exec` | 否 | 否 |

一致率 8/8，κ = 1.0（两人都是 1 个“是”、7 个“否”）。没有分歧，不需要裁定。

**正样本**（去掉开发样本 18a4e5cf）：**0 个**。按判据三.6，正样本少于 4 个，只报告数字、不下结论；召回无法计算。

7 个“否”的共同点：函数确实同名，但修的是别的问题。
- 架构自己额外需要的步骤漏了（002 设置内存权限）；
- 架构特有的情况漏了（003 NAPOT）；
- 修复前根本没有覆盖实现，修复是新加一个，用来补通用实现的不足（005、007）；
- 改告警、改分配范围、改报告内容（004、006、008）。
