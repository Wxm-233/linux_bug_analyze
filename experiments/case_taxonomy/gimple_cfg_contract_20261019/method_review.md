# N2.13 CFG 有限事实方法冻结前审查（2026-10-19）

只读 `gimple_cfg_facts.py`、14项合成开发测试、`run_analysis.py` 与已登记协议；未运行真实两片 CFG 方法，未修改 N2.11/N2.12 冻结代码或旧20项查询。审查版模块 SHA-256=`fc37188ca2c8a8fc72073157ce53a51307f99cded7bf1faa528b7e87924531eb`，测试 SHA-256=`14dd22dac1f7bf53e73ca109d598e70398cbd0278fd626247bf45c16c1732216`；`development_tests_initial.json` 记录14项通过，仍属组件开发。

方法严格读取 CFG record 的函数/loop/successor metadata、`<bb N> :` 块与正文终结语句；块集合与 successor 键须一致，显示的真/假目标或 goto 目标须与该块 compiler successor 集合吻合，否则整片不足。物理相邻块、`[INV]`、源标签和显示文本不会自行制造边或极性。循环退出仅来自声明的 loop membership 与直接 successor；`branch_to_store` 只覆盖两臂各自单后继、在共同块前的有限 normal-graph 前缀，经过循环绕回再次评价原分支的路径不算同次条件下的 store。call/asm 的 normal successor 及诊断支路回合均明示不证明必返回或运行可达；opaque control 使输入不足。

预审提出的两处跨 IR 门槛已关闭：CFG注解含 `discrim` 而旧GIMPLE没有时，完整坐标不相等就保守 `insufficient_discriminator_not_comparable`；若两个旧事件同 shape+locus 争一个 CFG 事件，两者均为 `ambiguous_old_shape_locus_match`，不再各称唯一。路径、源行/列、规范语句形状须同时唯一，临时名不重命名；根适配器还固定旧 `program_results.json` 的已知 SHA `fb34eb9a…`、旧方法基线及其文件，防过期 packet 借用相同自报源摘要。反例测试分别覆盖 metadata/极性矛盾、物理顺序、循环再入、asm、缺坐标、discriminator、双旧映一新与不支持控制语句。

当前未见阻断冻结的具体问题。支持状态只代表已观察 GCC 形状的**编译器正常控制图有限事实**；`branch_to_store` 不是必发生关系，跨pass唯一匹配也不是同一运行值/对象证明。实际两片的可解析范围、映射不足、call/asm及未知效果应在冻结后原样报告；不能据此自动完成跨架构接口义务、实际首次消费、锁规范或独立样本检出。

## 实际已读源码回放后的归属核对

`program_results.json` 于 09:54:57 保存，晚于本审查文件的预审版（09:54:43），但本阶段**没有在真实回放前生成独立的 method_baseline.json**；`method_notes.md` 又于 09:55:01 保存。因此上述“冻结前”只表示审查发生在运行前，不能写成独立盲测或基线先封存后的评估。原模块/测试 SHA、14项及合并29项开发测试有记录；两片仍是已读源码的开发回放，未据实际结果修改方法。

`results_summary.json` 对 old_s390/old_x86 分别给出22块、32条编译器正常边、10处分支极性、63条旧事件双向唯一绑定；其余116/119条绑定不足，主要是89条形状或精确源位点缺失及27/30条 discriminator 不可比。每个 profile 仅有一条 `branch_to_store`：bb17真臂经bb18字段写入，在bb19汇合；这只支持该受限臂前缀的局部关系。bb9真臂到bb10的 loop-exit、bb20含asm诊断后继也仍只是编译器图事实，不能推出运行可达、asm必返回或有效准备对象。实际结果与审前限定一致，但不是新样本检出或自动语义契约验证。
