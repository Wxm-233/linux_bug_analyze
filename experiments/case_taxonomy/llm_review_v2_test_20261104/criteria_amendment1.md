# 修订1：等价性自测改为“同一哈希种子下逐条一致”（运行MIPS之前写，未看MIPS候选）

## 起因

按第二节，用`rules_mips.py`对LoongArch在`v6.12`上运行，结果与旧文件`llm_review_expand_20261103/flags_la/flags_v6.12.json`比较：
- 新结果70条，旧文件69条；
- 多出的一条是R10的`swsusp_arch_resume`（缺`get_safe_page`），其余69条逐条一致。

查原因：
- 冻结规则`mech_scan_riscv_20261102/modules.py`的`defs_in()`用集合存放每个函数的定义文件；
- R10在参照架构有多个同名定义时取第一个`.c`文件，而集合的遍历顺序取决于Python每次运行的随机哈希种子；
- x86有`hibernate_32.c`和`hibernate_64.c`两个`swsusp_arch_resume`，取到哪一个，决定了三个参照实现的共同调用中有没有`get_safe_page`。

旧的LoongArch结果中，这条标记在各版本之间时有时无：v6.5、v6.7、v6.9、v6.10、v6.11、v6.13、v6.16、v6.19有，其余版本没有，而这个函数本身没有变化。可见这是冻结规则本身的不确定性，不是移植引入的。旧文件是在没有固定种子的情况下生成的，无法逐条复现。

## 改动

1. **等价性自测**：在LoongArch `v6.12`上，用`PYTHONHASHSEED=0`和`PYTHONHASHSEED=1`两个种子，分别运行原文件`rules_la.py`和`rules_mips.py`。同一种子下两者须逐条一致，才运行MIPS。与旧文件的差异照实报告。
2. **MIPS运行固定种子**：`PYTHONHASHSEED=0`，以便复现。
3. **L组不受影响**：L组的候选池按第二节从旧文件重新算出。冻结规则的这一不确定性在README中注明。

规则的判断条件、正则、阈值都不改。
