# 方法版本M3登记与回归——回归不符，停止冻结（2026-10-28）

按用户“Register M3”实施。登记`registration_m3.md`（SHA `dff55052…`）在实现前写定，声明M3的改动都是看过die、shmem与阶段A的s04之后设计的，三者只作回归用例。**回归中s04与事先预期不符，按登记停止冻结，未写`method_freeze_v3.json`，未运行阶段B。**

## 实现（`check_families.py`、`m3_eval.py`）

- **F3**：`#ifndef M`/`#if !defined(M)`（M为`__HAVE_ARCH_*`/`HAVE_ARCH_*`/`__ARCH_HAS_*`/`ARCH_HAS_*`）到匹配`#endif`之间（不含`#else`）的顶层函数F；契约`not(defined_M) or and(emits_F…)`；路径含`/libstub/`等的标为隔离上下文子集。
- **F1d**：恢复函数直接使用可覆盖宏，但只在回退定义为占位值（字面量、NULL、true/false、`((void)(x), 字面量)`）时生成。
- **执行器**：追踪全部失败记`trace_failed`、只有一个成功记`single_trace`；多消费者文件按(修订, 上下文, 文件)分别构建。
- 测试`tests/test_check_families.py`新增1项（共7项）。

## 回归（7个判定上下文）

| 用例 | 事先预期 | 观察 | 结论 |
| --- | --- | --- | --- |
| die | 父版独有11、修复版独有0、两版都报6；F3/F1d无父版独有 | 11 / 0 / 6（全部主线已解决），F3/F1d 0 | 符合 |
| shmem | 父版独有1（F2 arm64 64K）、修复版独有0 | 1 / 0 / 0 | 符合 |
| s04 | F3 `__HAVE_ARCH_STRNCMP`父版独有恰为arm64、arm64 64K两格；s390、sparc64等不构建libstub者事实不可得 | 父版独有**3格**：arm64、arm64 64K、**sparc64**；修复版独有0；两版都报1格（`__HAVE_ARCH_STRSTR`在s390） | **不符** |

## 不符的原因

sparc64与s390都没有`CONFIG_EFI`/`CONFIG_EFI_STUB`，但Kbuild仍按请求单独编出了`drivers/firmware/efi/libstub/string.o`（返回码0）。sparc64定义`__HAVE_ARCH_STRNCMP`，因此父版判违反；s390的`strstr`观察同理。这两格观察来自**在该配置下本不参与构建的文件**，是伪影。我的预期错在假设“不构建libstub的上下文会编译失败”；方法按事实判定，本身没有算错，但暴露出事实层的共性缺口：只检查“能否编译”，不检查“是否被该配置的Kbuild选中”。这一缺口对F1/F2同样存在。

按登记第6节，回归不符即停止、不改规则：M3不冻结，阶段B不运行。

## 阶段B筛查（`phase_b_screen.json`，只输出计数）

按M3选样修正（排除`tools/`、`scripts/`、`samples/`与include guard）重判附录3阶段B的10个样本：只有3个仍在范围内，7个记“M3选样不适用”。研究者未看任何阶段B样本内容。阶段B即使运行，有效样本也只有3个。

## 下一步（须用户决定）

- 另立版本M3a：在M3基础上增加适用性事实“文件在本配置的Kbuild中被选中”（按所在目录`Makefile`的`obj-$(CONFIG_…)`/`lib-$(CONFIG_…)`与`.config`判定），未选中的上下文判“不适用”；先登记、再以die、shmem、s04回归（s04预期回到arm64、arm64 64K两格），通过后冻结。
- 阶段B只剩3个有效样本，评价规模过小；可考虑在附录3基础上用M3修正后的选样规则继续扫描后备池补足样本，同样须先登记。

## 统计

Kimi调用0次；构建为三例回归；0内核启动；新确认缺陷0；独立正例/正常0/0。本轮代码未提交（b708726之后）。
