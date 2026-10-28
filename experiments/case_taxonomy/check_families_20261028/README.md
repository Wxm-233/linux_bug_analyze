# 方法改动M2验证：程序枚举的固定检查族（2026-10-28）

按用户“Register M2”实施。登记`registration.md`（SHA `d0493aa0…`）在实现前写定；事后修正`amendment_m2a.md`（SHA `0b77e19d…`）在看到M2结果后写定，均记在`registration_sha256.txt`。**F1/F2是看过die、shmem修复后设计的，本轮只验证实现与判别力，不说明泛化或精度。**不调用模型。

## 结论

| | die（F1） | shmem（F2） |
| --- | --- | --- |
| M2（按登记） | **命中**：只在父版报的观察9条，全是`die_id`/`die_cpus`在仅有公共回退的上下文（arm64、riscv、s390、sparc64；x86无SMP只有`die_cpus`，因其`die_id`原生）；修复版新增0条 | **未命中**：目标实例的门控函数`shmem_alloc_hugefolio`等被内联、无优化记录，事实不可得，两版都判不可得 |
| M2a（事后修正，只改F2门控） | 同M2 | **命中**：只在父版报的观察恰好1条：(`HPAGE_PMD_ORDER`≤`MAX_PAGECACHE_ORDER`，arm64 64K)；修复版新增0条 |
| 两版都报的持续观察（噪声） | 26格（8个实例：cluster/core/package等属性在回退架构导出） | 34格（F1直接使用7个函数28格；F2 `TASK_SIZE`对KMALLOC等上限的无意义配对6格） |

M2a命中是事后调整后的结果，不能计作M2命中。两例的噪声都与修复无关且两版相同；F1“直接使用”子类（如`flush_dcache_folio`在部分架构用公共回退）与F2的跨单位配对（`TASK_SIZE`对`KMALLOC_MAX_SIZE`）基本是纯噪声。

## 实现（通用）

- `linux_bug_analyze/check_families.py`：`f1_instances`（`##`拼接调用与顶层函数直接使用中的可覆盖宏——某追踪上下文来自`arch/`、另一上下文来自公共定义；导出实体为拼接出非宏名字的实参或函数名）、`f2_instances`（以`_ORDER/_SHIFT/_SIZE/_NR`结尾的架构相关几何宏G，与同后缀、名含MAX/LIMIT、展开链交于G链的上限宏L配对；门控函数为源码体中出现G或其链可达宏的顶层函数）、`contract`、`queries`。
- `provider_context`：把`arch_dependent`、`chain`提为模块函数，新增`pasted_invocations`；M1行为与测试不变。
- 测试`tests/test_check_families.py`（3项）；WSL全量471项，仍只有原有2个pycparser导入错误。
- 执行脚本`check_run.py instances/collect/evaluate/evaluate_m2a`；构建die父/修×6、shmem父/修×9全部成功，另有6次追踪构建。

## 过程中发现并修正的问题（均保留原结果）

1. **M2 F2门控被内联函数拖成不可得**（规则层）：以事后修正M2a处理，见`amendment_m2a.md`。
2. **关系编码超出核心元数上限**（实现层）：`or`/`and`最多8个参数，`PAGE_SIZE`实例有17个门控函数，M2a下暴露为27格`invalid_formalization`（M2中被“事实不可得”掩盖）。改为超过8个时嵌套（语义不变），加回归测试；修正前的M2与M2a结果保存在`die/attempt1/`、`shmem/attempt1/`。修正后die与shmem的M2结果与修正前相同，M2a的shmem目标命中也不变，无效格消失。

## 边界与下一步

- 噪声大：die两版持续观察26格对9格信号，shmem 34格对1格。要在未接触样本上可用，需按“是否随修复变化”之外的办法压噪声（例如F1只取拼接导出实体、F2限同单位且两者均为整型常量的配对），任何收紧都须先登记。
- F1把“公共回退被导出”当观察，但很多回退是合法的（如`core_id`回退为0被长期接受）；判断要靠复核或正常对照。
- 两检查族的真正检验在未接触样本与正常对照上：先重新冻结方法（含M2或M2a及噪声收紧），经用户同意后评价。

## 统计

Kimi调用0次；构建30次＋追踪6次；实例die 10、shmem 18；0内核启动；新确认缺陷0；独立正例/正常0/0。本轮代码未提交（8a18277之后）。
