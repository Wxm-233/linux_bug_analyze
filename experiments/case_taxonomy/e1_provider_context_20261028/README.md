# 方法改动M1验证：E1输入补入提供者侧宏定义（2026-10-28）

按用户“Yes, register it”实施。登记`registration.md`与模板新增节`e1_provider_template_addition.md`在实现与任何新模型调用前写定，SHA见`registration_sha256.txt`（`599464b9…`、`e7b87f7e…`），实现只按登记规则进行，未事后改规则。

## 结论

**M1在两例已接触回放上都没有修补E1断点，按登记不采用。**提供者定义按规则正确进入了提示，模型也引用了它们，但两例的E1候选仍没有指向已知缺陷，候选事实在父/修版间逐项相同，因此两份形式化提示都未发送。这是每例1次E1的结果（n=1，模型输出有随机性）。

## 实现（通用）

- `kernel_facts._macro_trace`：可追踪全部宏（`macros: "*"`），记录终态定义的源行号与完整`#define`原文。
- 新模块`linux_bug_analyze/provider_context.py`：`guard_configs`（预处理条件中最常见的至多12个`CONFIG_*`）、`pasted_names`（本文件函数式宏`##`拼接在调用处产生的名字）、`consumed`、`select`（展开链深度≤3中有宏的终态定义来自`arch/`或三上下文文本不同）、`render`（按上下文分组列“文件:行号 原文”，24 000字节上限，已在源码中给出的定义只注明不重复）、`sparse_sources`（只含所列定义行的伪源码，使候选对提供者文件的引用能被桥接解析）。
- 测试`tests/test_provider_context.py`（4项）。WSL全量468项，仍只有原有2个pycparser导入错误。
- 执行脚本`provider_run.py context/prepare/evaluate`；首次die prepare因脚本笔误（元组表达式代替赋值）在构建后中断、未产生结果文件，修正后删除该次构建输出目录重跑（构建缓存复用），不影响结论。

## 提取结果（父版，x86_64/arm64/s390 defconfig＋守卫配置）

| 案例 | 入选宏 | 字节 | 关键定义是否进入 |
| --- | ---: | ---: | --- |
| die | 15 | 4 355 | 是：`topology_die_id`/`topology_die_cpumask` x86来自`arch/x86/include/asm/topology.h:111/118`，arm64、s390为`include/linux/topology.h`回退（注明已在源码中） |
| shmem | 39 | 21 450 | `HPAGE_PMD_*`链与各架构`PMD_SHIFT`（x86 21、arm64 `ARM64_HW_PGTABLE_LEVEL_SHIFT(2)`、s390 `_SEGMENT_SHIFT`）进入；`MAX_PAGECACHE_ORDER`未进入（`shmem.c`不使用它），与登记预期一致 |

规则也带入了噪声：`CONFIG_SCHED_BOOK`等自动生成的配置宏、`__init`属性链、`raw_spin_lock`/`current`等，按登记保留。

## E1与判别核查

| 案例 | E1交付 | 候选 | 与缺陷的关系 | 两版不同的事实 | 形式化 |
| --- | --- | --- | --- | --- | --- |
| die | 完整（28 286 token，389秒） | cpumask生命周期、sibling/core语义、调度复用拓扑掩码、book/drawer宏集合 | 引用了提供者定义（如`arch/x86/include/asm/topology.h:120`），注意到s390 cluster掩码用公共默认，但无候选指向“die属性在仅有公共回退的架构上导出” | 0 | 未发送 |
| shmem | 完整（97 610 token，546秒） | swap元数据、HPAGE_PMD几何、TASK_SIZE、ZERO_PAGE、VM_MTE_ALLOWED | 新出现候选1“HPAGE_PMD几何与THP能力”，引用`arch/arm64/include/asm/pgtable-hwdef.h:49`并指出arm64 PMD_SHIFT随PAGE_SHIFT变化，但要求只涉及几何自洽，不涉及页缓存上限 | 0 | 未发送 |

构建：die父/修×6（riscv用编译参数补齐）与shmem父/修×9全部成功；核查结果`die/replay_facts.json`、`shmem/replay_facts.json`的`discrimination`字段。

## 解释与下一步

- die：缺陷所需的提供者信息已在提示中，模型仍选了别的接口——瓶颈在开放式候选生成（每例至多5条、自由选择接口），不只是输入可见性。
- shmem：约束来自第三方消费者（xarray拆分上限，经`MAX_PAGECACHE_ORDER`表达），按“被消费宏”的规则天然取不到。
- 两例都表明，比起继续给E1加上下文，更可能有效的是**固定检查族**：例如“消费者使用的可覆盖宏⇒各架构是否原生提供”“公共代码使用的页阶/几何宏⇒与相关公共上限的关系”，由程序枚举而非由模型自由挑选。这需要另行登记，并在未接触样本上评价。
- 方法冻结仍过期；M1不采用，不进入冻结。

## 统计

Kimi调用2次（两例E1），均完整交付；形式化提示2份未发送；构建30次（die 12、shmem 18）＋追踪构建6次；0内核启动；新确认缺陷0；独立正例/正常0/0。本轮代码未提交（8a18277之后）。
