# 宏事实与跨架构采集（2026-10-28）

按用户“做宏+跨架构采集”实施；实现前设计见`design.md`。试点3（`mm/madvise.c`，修复提交`9457056ac426`，父版`6c8e2a25`）已在`static_vocab_20261028`接触过，**不计评价**。

## 实现

- `kernel_facts.collect_tree`/`tree_query`（树层，22个`arch/*`，无需交叉编译器）：各架构顶层Kconfig的`select`行、`kconfig_deps`（`depends on`原文）、请求UAPI头经宿主`gcc -E -dM -nostdinc`的宏定义与整数值（架构无该头时按`asm-generic`回退并标注）。
- 构建层：x86/arm64/s390/sparc/riscv五架构以defconfig＋`MEMORY_FAILURE`等覆盖编译`mm/madvise.c`，`.config`实际值与返回码作事实；5/5构建成功。
- `candidate_bridge.arch_needs`/`build_arch_queries`：从候选与源码推出头、宏、配置符号；Kconfig依赖中的`ARCH_*`/`HAVE_*`转为`arch_selects_*`；`formalization_prompt(per_arch=True)`说明同一关系逐架构求值。
- `arch_run.py prepare/evaluate`：每个架构作独立上下文交核心判定，按架构汇总（E3维度：同用途跨架构对照）。

## 采集结果（ma_pilot3b）

2候选、15/14条查询×22架构共638格，答394格（未答者多为无构建的架构的`config_*`/`builds_ok`）。关键事实：

| 架构 | MADV_HWPOISON | MADV_SOFT_OFFLINE | select ARCH_SUPPORTS_MEMORY_FAILURE | 构建中MEMORY_FAILURE |
| --- | --- | --- | --- | --- |
| alpha、xtensa | 否 | 否 | 否 | 无构建 |
| mips | 是（100） | 否 | 否 | 无构建 |
| x86、arm64 | 是 | 是 | 是 | 开 |
| parisc、powerpc | 是 | 是 | 是 | 无构建 |
| s390、sparc、riscv | 是 | 是 | 否 | 关（覆盖无效，以`.config`为准） |
| 其余12个 | 是 | 是 | 否 | 无构建 |

## 形式化与判定

Kimi（必要条件模式、逐架构）两次调用形式化完全相同：c0 `build_context ⇒ defines_MADV_DONTNEED`；c1 `config_memory_failure ⇒ defines_MADV_HWPOISON ∧ defines_MADV_SOFT_OFFLINE`。研究者复核（`researcher_review_ma_pilot3b.json`）：c0忠实但弱；c1忠实，并把scope规范化为`arch_selects_ARCH_SUPPORTS_MEMORY_FAILURE`（`MEMORY_FAILURE`依赖该符号，树层22架构可得；模型scope只在5个有构建的架构可答）。

| 判定 | c0 | c1（模型scope） | c1（规范化scope） |
| --- | --- | --- | --- |
| 未复核 | 22×insufficient | insufficient/not_applicable/facts_unavailable | — |
| 复核后 | 22×satisfied | 满足2（x86、arm64），不适用3（s390、sparc、riscv），事实不可得17 | 满足4（x86、arm64、parisc、powerpc），不适用18 |

父版没有任何架构判为violated。这与提交性质一致：`9457056ac426`是新增`MADV_DONTNEED_LOCKED`的功能提交（附“fix mips build”），并非修复本候选所述的不一致；本试点**没有可检出的缺陷**，只说明链路在跨架构维度能走到审后判定。Alpha/Xtensa/MIPS缺少这两个宏但不能启用`MEMORY_FAILURE`，正是规范化后判“不适用”而非“违反”的原因。

## 反事实对照（`controls.json`，合成事实，origin `synthetic_assumption`）

6/6符合预期：alpha、mips假设可启用MEMORY_FAILURE→violated；x86去掉HWPOISON、parisc去掉SOFT_OFFLINE→violated；x86不改→satisfied；alpha不改→not_applicable。合成对照只检验判定链，不是缺陷。

## 发现并修正的错误（保留attempt1）

首轮`ma_pilot3`中`defines_*`取自先列出的`asm/mman-common.h`（通用回退），使Alpha被误报为定义`MADV_HWPOISON`；对照`alpha_can_enable_memory_failure`得satisfied而非violated，暴露了该错误。修正为可被架构覆盖的入口头（`arch/*/include/uapi/asm/*.h`）优先，加回归断言（`tests/test_arch_facts.py`），以新标签`ma_pilot3b`重新采集与形式化。旧结果、审前结果、复核与对照保存在`attempt1/`，不回改。

注：本轮复核文件在ma_pilot3b首次evaluate前写入（形式化与attempt1逐字段一致，判断沿用），因此`ma_pilot3b_results.json`的unreviewed格即审前结果，未另存before_review文件。

## 边界与遗留

- 宏过滤仍有噪声：`MADV_`、`MIPS`、`RISC`、`UAPI`、`MEMORY_FAILURE`被当作宏查询（恒为未定义，无害但浪费查询）。
- `-dM`是用户态包含链终态，不等于内核编译单元中使用点的可见性；Kconfig只看顶层`select`，不展开`source`与条件真值。
- 未安装新交叉编译器：alpha/mips/hppa可经apt取得，xtensa无；安装需用户另行批准。
- 规范化scope由研究者给出，模型自身scope在无构建的架构不可答——目前审后判定仍依赖人工。

## 统计

Kimi调用2次（ma_pilot3、ma_pilot3b形式化），均完整交付（19819、16744 token）；树层采集2轮×2（deps/final）、构建5个；0内核启动；新确认缺陷0；独立正例/正常0/0。评价方法冻结仍过期；代码未提交。
