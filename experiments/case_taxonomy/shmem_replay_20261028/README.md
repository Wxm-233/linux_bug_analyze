# 已知跨架构缺陷回放2：shmem PMD页阶超过页缓存上限（2026-10-28）

按用户批准推进，设计与事先判别标准见`design.md`。修复`9fd154ba926b`，父版`3390916aca7a`。本案例已在`shmem_arch_contract_20261012`深度接触；本轮新增事实与修正是在本案例上开发的，只计回放判别力，不计新缺陷、泛化或独立评价。

## 一句话结论

E1断点重现且更早：4个候选（swap元数据恢复、GFP zone约束、dcache刷新、MTE许可）**没有一个涉及页阶与页缓存上限**，候选事实在父/修版间逐项相同，形式化提示因此未发送。研究者指定的新事实（编译单元宏取值＋函数优化后恒返回0）有判别力：事后契约父版仅arm64 64K违反、修复版0违反；只看宏关系的对照两版arm64 64K都违反——修复改的是消费者行为而不是宏值。

## 新事实（通用）

- `kernel_facts.collect`可选`macro_values`：取Kbuild保存的该文件编译命令，编译`#include`原源文件并追加`long long probe(void){return (M);}`的探针（带原型以适应`-Werror`，属性用`__used__`/`__noinline__`以避开内核同名宏），从探针函数的优化后GIMPLE读`return <整数>;`。与架构无关，可求`min()`等语句表达式；不是整型常量（如`nr_cpu_ids`）或非宏则不答；`-dD`追踪显示从未定义的名字不再整轮编译。
- 可选`optimized_functions`：正常编译加`-fdump-tree-optimized`；查询`returns_only_zero`判函数体（去掉声明、块标签、`# DEBUG`行）是否只剩`return 0;`。
- `candidate_bridge.tu_needs(trace_all=True)`：追踪候选全部标识符，采集后只为确为宏者建事实；候选文本大写标识符做取值探针（上限16），引用所在函数与候选提到的函数（上限12）做折叠事实。
- **修正**`evaluate_candidate`：缺失事实时先判`facts_unavailable`，不再给缺失事实默认bool类型（否则整型比较会误报`invalid_formalization`）。首次事后评估受此影响的结果保留在`attempt1/`（alpha/mips/parisc判为invalid_formalization、对照5/6）。
- 测试`tests/test_tu_macro_facts.py`共7项；WSL全量464项，仍只有原有2个pycparser导入错误。

## 过程与结果

1. **工具链**：用户批准后apt安装alpha/mips/hppa交叉编译器（收据`toolchain_install_receipt.txt`），本轮用于alpha、mips、parisc上下文。
2. **E1**（冻结模板，父版`mm/shmem.c`，175KB）：Kimi完整交付（90416 token，569秒），4候选均与本缺陷无关。结构原因：协议只给修复触及文件，`MAX_PAGECACHE_ORDER`（`include/linux/pagemap.h`）与xarray拆分上限（`lib/xarray.c`）都不在输入中。
3. **构建**：父/修×9上下文（x86_64、arm64 4K、arm64 64K、s390、sparc64、riscv、alpha、mips、parisc），18次全部成功。
4. **候选事实**：追踪61个标识符，5个确为宏；4候选9–22条事实。机械核查`discrimination_check.json`：每个上下文父/修事实（是否可答与取值）逐项相同，故形式化提示（`模型调用测试/2026-10-28/shmem_replay_formalize_unsent/`）未发送。
5. **研究者事后事实与契约**（`hindsight_run.py`，借用修复语义，不计链路检测）：

| 上下文 | HPAGE_PMD_ORDER | MAX_PAGECACHE_ORDER | shmem_is_huge恒0（父/修） | 事后契约（父/修） | 只看宏关系（父/修） |
| --- | ---: | ---: | --- | --- | --- |
| x86_64、arm64 4K、riscv | 9 | 9 | 否/否 | 满足/满足 | 满足/满足 |
| arm64 64K | 13 | 11 | 否/**是** | **违反/满足** | 违反/违反 |
| s390 | 8 | 8 | 否/否 | 满足/满足 | 满足/满足 |
| sparc64 | 10 | 10 | 否/否 | 满足/满足 | 满足/满足 |
| alpha、mips、parisc | 不答（无THP，BUILD_BUG占位） | 8 | 无记录（头文件桩） | 事实不可得 | 事实不可得 |

事后契约：THP开启时，`shmem_is_huge`折叠为恒0，或`HPAGE_PMD_ORDER ≤ MAX_PAGECACHE_ORDER`。达到事先标准（父版arm64 64K违反、x86与arm64 4K不违反；修复版无违反）。x86、arm64 4K/64K取值与`shmem_arch_contract_20261012`已核实的9/9、9/9、13/11一致；s390、sparc64、riscv为本轮新增源码一致上下文（未运行验证）。合成对照`controls.json` 6/6。

## 边界与遗留

- 两次回放的共同断点在E1：die的候选措辞不承诺，shmem的候选根本没触及。只给触及文件的E1输入看不到提供者侧（架构头、公共上限定义），这是协议层面的限制，不是提示措辞小问题。
- `evaluate_candidate`仍在应用scope之前检查关系事实，因此无THP上下文是“事实不可得”而非“不适用”。
- 取值探针只给整型常量；`returns_only_zero`只认恒0，不认其他常量或部分折叠。
- 未启动内核；ARM64 64K的运行时触发证据仍在shmem_arch_contract。

## 统计

Kimi调用1次（E1，完整交付），形式化提示1份未发送；构建18次（另有探针与事后采集复用构建缓存）；0内核启动；新确认缺陷0；独立正例/正常0/0。评价方法冻结仍过期；本轮代码未提交（8a18277之后）。
