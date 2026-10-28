# 已知跨架构缺陷回放：die拓扑属性（设计，实现前写定）

2026-10-28。用户选择“在有已知跨架构缺陷的已接触案例上回放，检验宏/跨架构事实能否区分父版与修复版”。

## 案例与接触状态

修复`2c4dcd7fd57b`（topology/sysfs: export die attributes only if an architectures has support），父版`555a0ce4558d`。父版`drivers/base/topology.c`对所有架构导出`die_id`、`die_cpus`、`die_cpus_list`；只有x86（SMP）原生定义`topology_die_id`与`topology_die_cpumask`，其余架构由`include/linux/topology.h`的`#ifndef`回退给出假值（-1、`cpumask_of(cpu)`）。修复在回退前加`TOPOLOGY_DIE_SYSFS`门控。

本案例已在`die_arch_contract_20261013`（真实构建、预处理、对象、四次启动）及后续规则开发中**深度接触**；本轮是旧案例回放，只检验工具链判别力，不计新缺陷、不计泛化、不计独立评价。

## 输入（沿用冻结E1模板，不加提示）

E1：冻结的`eval_prep_20261028/e1_prompt_template.md`，填入修复提交触及的C/H文件在父版的完整内容（`drivers/base/topology.c`、`include/linux/topology.h`），不含架构头、修复差异或提交说明。1次Kimi调用，无自动重试。

## 新事实（内核编译单元视角，构建层）

`kernel_facts.collect`新增可选项：
- `macros`：先以`KCFLAGS=-dD`生成该文件预处理结果，按行标记跟踪每个请求宏的`#define`/`#undef`事件及所在文件，记最终是否定义、最终定义所在文件（相对源码/构建根）。随后正常构建覆盖`.i`，不影响既有事实。
- 目标对象全部已定义符号（`nm`非`U`）。
- `make_vars`：附加make变量（GCC13编译5.16历史主机工具需`HOSTCFLAGS=-Wno-error=...`，沿用die_arch_contract已声明的兼容选项）；只在提供时进入构建配置哈希，旧缓存键不变。

新查询：`macro_defined(macro)`（编译单元终态）、`macro_from_arch(macro)`（终态定义来自`arch/`下头文件，即非公共回退；未定义为假）、`object_defines_token(token)`（对象中有符号名等于该标识符或以`_`分隔包含它，如`dev_attr_die_id`）。

`candidate_bridge`新增`tu_needs`/`build_tu_queries`：候选文本与引用行中、在给定源码里以`#define`/`#ifdef`/`#ifndef`/`defined()`出现的标识符作为宏追踪对象，生成`defined_<M>`、`arch_provides_<M>`；引用行中的小写标识符生成`emits_<id>`；另含`build_context`、`builds_ok`与候选中`CONFIG_*`。

## 上下文与判定

构建配置6个：x86_64 defconfig（SMP）、x86_64 defconfig＋SMP关、s390、arm64、sparc64、riscv（均为defconfig）。父版与修复版各构建6次`drivers/base/topology.c`。形式化只看父版的事实名与类型（值盲，必要条件模式，逐上下文），1次Kimi调用；同一形式化分别在父版与修复版事实上逐上下文判定（未复核/复核后）。

预先写定的判别标准（来自die_arch_contract已核实事实，非本轮结果）：父版至少s390与x86无SMP应判violated、x86 SMP不应判violated；修复版各上下文均不应判violated。达到即“该候选形式化在此案例上可区分父版与修复版”；只用`defined_*`（终态）而不用来源的形式化预期两版都满足，记为不可区分。

## 对照与边界

合成反事实对照检查判定链；构建失败如实记录不重试。不安装新交叉编译器。`-dD`来源是预处理视角，不等于运行时属性可见性（运行时证据见die_arch_contract启动记录）。
