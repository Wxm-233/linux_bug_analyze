# 判据：编码一致性引擎第四轮——历史召回与多版本（ecrecall_20261122）

2026-11-22，Claude。用户：“开始第四轮”。接第三轮（`ecnoise_20261122`：EC 加三条去噪规则，df2908090cda 上 8 行候选）。写于挖样本标注、实现和运行之前（第三轮引擎 `ec3.py` 冻结，本轮不改任何判定规则）。

## 一、样本供给（机械 + 两人盲标）

1. **候选池（脚本 `pool.sh`，机械）**：`v5.4..df2908090cda` 的非合并提交，满足全部条件：
   - 改动了 `arch/{riscv,x86,arm64,powerpc,s390,loongarch,mips,arm,hexagon}/include/asm/` 下的 `pgtable*.h`、`pte*.h`、`hugetlb.h`、`*hash*.h`（含子目录），或 `include/linux/{pgtable,swapops,leafops}.h`；
   - 标题含接口名：`(pte|pmd|pud)_[a-z_]+`、`p?d_`、`{pte,pmd}`、`swp`、`swap entr`、`PAGE_PROT_NONE`、`_PAGE_[A-Z_]+`、`soft.?dirty` 之一；
   - 标题含修正语气：`fix|correct|comply|semantic|must|wrong|broken|incorrect|let |ensure|missing|preserve|keep|don't|do not|only care|return true|return false` 之一；
   - 标题不含：`typo|comment|build|compile|warning|cleanup|clean up|rename|refactor|return bool|implement|batch|add architecture|standardi|params|include`。
2. **两人盲标**：我和 Codex（gpt-6.1-sol，推理 max，新会话）各自读每个提交的 diff 和说明，独立判断它是不是 **“EC 可处理类型”**：
   - (a) 修复前，某架构的取值级接口——构造 `pfn_T`/`mk_pte` 类、单参数修改（`T_mk*`、`T_wrprotect`、`T_clear_*` 等）、观察（`T_present/young/dirty/write/leaf/bad/…`）、交换项编解码（`__swp_*`、`*_swp_*`、`swp_entry`/`softleaf` 公共层）——对某些输入给出与通用约定或其他架构不一致的值；
   - (b) 这种不一致在只看头文件、按值求值时就能看出：不涉及锁、原子操作、TLB/缓存刷新、页表遍历指针、运行时状态（全局变量、CPU 特性），不是两参数接口（`pte_modify`、`pte_access_permitted` 等）的问题；
   - (c) 涉及的架构在本项目的 20 个构建之内。
   - 不看 EC 的任何输出。每个提交给“是 / 否”和一句理由。我的标注调用 Codex 前封存（记 SHA）。分歧由我裁定并写理由。
3. 标为“是”的就是召回样本。

## 二、召回测量：回注法（主测）

对每个召回样本：
1. 取修复提交里对上面那些头文件的改动，**反向**打到 df2908090cda 的对应文件副本上（`patch -R`，允许偏移和 fuzz 2，不手工改写）；打不上的记“无法回注”，从分母里去掉并单列。
2. 副本放在覆盖目录，只对受影响的构建（该架构的构建；改公共头文件时为全部构建）把覆盖目录插到编译命令的对应 `-I` 之前，源码工作树不动。
3. 用冻结的 `ec3.py` 只重新求值受影响的构建，其余构建复用第三轮的 `beh_*.json`，再表决、复现、分组。
4. **命中**：出现第三轮基线 8 行之外的新候选行，其架构是样本的架构，且被指认的接口、或示例组合里的某个接口，属于修复改动的接口（从 diff 的改动行和所在宏/函数名自动取）。
5. 报：召回 = 命中 / 可回注样本数（Wilson 95% 区间）；参考线 1/3。逐例列出命中行，或未命中的原因（接口不在 EC 组合里、构建里没开对应配置、规则 1/2/3 排除、多数表决没形成规律、求值不精确等）。

## 三、多版本（演示与交叉核对）

1. `mkvariants.sh <版本>`：自动在任意版本上生成 20 个构建的头文件变体（`git archive` 导出源码，各构建复用 df2908090cda 的 `.config` 做 `olddefconfig`，再 `prepare` 和 `mm/memory.o`，只留 `.config`、生成的头文件、`mm/.memory.o.cmd`），失败的构建记下原因、不参加。
2. `ec3.py` 加按版本选构建目录的入口（只是选目录，判定规则不变），`scan5.py scan <版本>` 在该版本上跑 scan3 的 8 个引擎 + EC。
3. 至少在一个召回样本的父版本上真跑一次（取日期最近、可回注的样本），比较该版本上 EC 是否报出这个样本，与回注法的结论是否一致。

## 四、门槛与报告

- 没有通过/不通过的门槛；召回参考线 1/3，报实际值和区间。
- 必须报告：池子大小、两人标注一致率与 κ、样本数、可回注数、命中数、逐例原因；多版本运行的构建成功数、各引擎条数。

## 五、其他

不读封存材料；不对外报告；Codex 调用前后报额度；变体和临时源码用完即删，只留必要文件；不运行内核。
