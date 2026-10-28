# 已知跨架构缺陷回放：die拓扑属性（2026-10-28）

按用户“Replay a known bug”实施，设计（含事先判别标准）见`design.md`。修复`2c4dcd7fd57b`，父版`555a0ce4558d`。本案例已在`die_arch_contract_20261013`及后续规则开发中深度接触，且本轮桥接改进是**看到本案例失败后做的**；结果只说明工具链在该案例上的判别力，不计新缺陷、泛化或独立评价。

## 一句话结论

新的编译单元宏来源事实与对象符号事实**能**区分父版与修复版（事后契约在父版4个回退上下文判违反、修复版0违反；只用“宏是否定义”的同一契约两版都满足）。但端到端链路**没有**检出：E1候选把要求写成“若要准确描述多级拓扑则须成套覆盖”，并承认回退可为有意的不支持表示，形式化模型据此判不可表达。

## 实现（通用，非本案例专用）

- `kernel_facts.collect`：可选`macros`以`KCFLAGS=-dD`先生成预处理结果，按行标记记每个宏的`#define`/`#undef`事件与终态定义文件；对象全部已定义符号；可选`make_vars`（仅提供时进入构建配置哈希，旧缓存键不变）。新查询`macro_defined`、`macro_from_arch`（终态定义来自`arch/`）、`object_defines_token`。
- `candidate_bridge.tu_needs`/`build_tu_queries`：从候选文本与引用行取源码中作宏使用的标识符，生成`defined_*`、`arch_provides_*`；非预处理引用行的小写标识符生成`emits_*`；逐构建上下文提示`per_arch='build'`。
- 测试`tests/test_tu_macro_facts.py`（4项）。WSL全量461项，仍只有原有2个pycparser导入错误。

## 过程

1. **E1**（冻结模板，父版`drivers/base/topology.c`、`include/linux/topology.h`，模板SHA与冻结一致）：Kimi完整交付，5个候选。候选0（`topology_*_id`/`topology_*_cpumask`通用sysfs导出）与本缺陷相关；其余为sibling/core掩码语义、book/drawer访问器、NUMA映射、memoryless节点。
2. **构建**：父版/修复版×6上下文（x86_64 SMP、x86_64无SMP、s390、arm64、sparc64、riscv），沿用die_arch_contract的GCC13主机兼容选项。10/12成功；riscv两版均在`vdso_prepare`失败（5.16的vdso汇编与新binutils不兼容，需`zicsr`扩展），主回放中记录为该上下文无事实。**补充**：随后按用户要求以`-march=rv64imafdc_zicsr_zifencei`编译参数（等同上游`6df2a016c0c8`，不改源码）重建，两版均成功，见`riscv_supplement/`。
3. **attempt1（保留在`attempt1/`）**：首版桥接对候选0只生成`emits_include`、`emits_asm`等噪声事实，无任何die事实（通配接口名`topology_*_id`、引用行不含具体宏名、`what`中的“第183-206行”未读取）。机械核查：5个候选在每个上下文中父版与修复版事实逐项相同（`attempt1_discrimination_check.json`），任何形式化都不可能区分，因此未发送其形式化提示（`die_replay_formalize_attempt1_unsent/`）。
4. **桥接改进（在本案例上看到失败后做的，通用）**：通配标识符匹配源码宏；读取引用`what`中的行范围（上限80行）；`emits_*`跳过预处理行。候选0事实增至65条，含`arch_provides_topology_die_id/cpumask`、`emits_die_id/die_cpus`。
5. **形式化**（值盲，必要条件模式，逐上下文）：Kimi完整交付（51533 token，751秒）。候选0、1不可表达；候选2–4给出必要条件。

## 关键事实（父版）

| 上下文 | die_id来源 | die_cpumask来源 | 导出die属性（父→修） |
| --- | --- | --- | --- |
| x86_64 SMP | arch/x86 | arch/x86 | 是→是 |
| x86_64 无SMP | arch/x86 | 公共回退 | 是→否 |
| s390、arm64、sparc64 | 公共回退 | 公共回退 | 是→否 |
| riscv（补充） | 公共回退 | 公共回退 | 是→否 |

所有成功上下文中两宏终态均“已定义”，只有来源能区分；与die_arch_contract已核实的x86 SMP 3→3、s390 3→0、x86无SMP 3→0一致，arm64、sparc64为本轮新增的源码一致上下文（未启动验证）。

## 判定（`replay_results.json`，复核见`researcher_review.json`）

| 契约 | 父版 | 修复版 |
| --- | --- | --- |
| 候选0（模型） | 不可表达 | 不可表达 |
| 候选0事后契约：导出⇒两宏均来自arch/ | x86 SMP满足；x86无SMP、s390、arm64、sparc64违反；riscv事实不可得（补充后违反） | 5个满足；riscv事实不可得（补充后满足） |
| 候选0事后对照：导出⇒两宏均已定义 | 5个满足 | 5个满足 |
| 候选2（复核接受） | s390满足，其余不适用 | 同父版 |
| 候选3、4（复核不接受：scope用观测事实无依据） | 未复核：不足/不适用 | 同父版 |

事后契约借用了修复语义，由研究者写出，**不是链路检测**；它说明事实与判定核心在该案例上具备判别力，并实证“同名宏终态存在≠架构原生提供”的陷阱（只用`defined_*`时两版无差别）。事先标准（父版至少s390与x86无SMP违反、x86 SMP不违反；修复版无违反）达到。

合成反事实对照（`controls.json`）5/5符合预期。

## 边界与遗留

- 链路断点在E1表述：候选没有把“导出须有原生提供者”写成要求。改E1提示或加“导出面与提供者来源”的固定检查属方法改动，须先登记再在未接触样本上评价。
- 桥接仍有噪声事实（`emits_buf`、`emits_topology_`等）；`arch_provides_*`把`arch/`下任何定义都当原生，不区分架构头内部的回退。
- `-dD`来源是预处理视角；运行时可见性证据仍在die_arch_contract的启动记录。
- riscv已用编译参数补齐（`riscv_supplement/`）；`replay_results.json`保持原样，补充结果另存为`riscv_supplement/riscv_results.json`。

## 统计

Kimi调用2次（E1、形式化），均完整交付（19553、51533 token）；attempt1形式化未发送。构建12次（10成功、2失败），补充riscv构建2次均成功；0内核启动；新确认缺陷0；独立正例/正常0/0。评价方法冻结仍过期；代码未提交。
