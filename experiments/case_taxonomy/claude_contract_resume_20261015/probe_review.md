# 公共消费者的最小逻辑反例原型

2026-10-15。为了核对模型候选的必要性与充分性，本轮自动从既有 `source_packet.json` 提取同父版本的三个完整函数：`sched_core_lock` 240–248、`sched_core_unlock` 250–258、`sched_core_cpu_starting` 5753–5794。仅删除材料行号前缀，原判断、循环、返回及注释均保留；生成文件通过 `#line` 记录原告警位置。

这是 **用户态 C 模拟**。mock 提供固定集合、runqueue、IRQ、锁调用记录和 WARN_ON_ONCE 站点状态；没有真实内核锁、硬件或并发，也没有证明构造输入可在真实启动中到达。五项是同一已读案例的逻辑输入，不是五个新增缺陷或独立检测阳性；本原型没有 API 调用、密钥读取、内核启动或 R3 操作；并行的模型接口尝试另见本目录总报告。

## 运行结果

固定目标 CPU 为1；除了第四项的 `rq0->core=rq2` 外，每项开始时所有 rq 均自指。WARN_ON_ONCE 站点状态每项重置。表中成员来自未修改消费者内部实际调用到 mock 锁函数的记录。

| 逻辑输入 | 集合含目标 | 锁／解锁成员 | 原告警行 | 目标 CPU 最终 core |
| --- | --- | --- | --- | --- |
| 空集合 | 否 | 均为空 | 5779 | 1（保持自指） |
| 仅自身 `{1}` | 是 | 均为 `[1]` | 无 | 1 |
| 仅其他 CPU `{0}` | 否 | 均为 `[0]` | 无 | 1 |
| 自身与其他 `{0,1}`，其他成员没有自指 leader | 是 | 均为 `[0,1]` | 5779 | 1 |
| 正常双成员 `{0,1}`，CPU0 是 leader | 是 | 均为 `[0,1]` | 无 | 0 |

所有输入结束时 mock held 状态均归零。结果直接保存在 [probe_results.json](probe_results.json)；程序单次执行的原始 JSON 为 [probe_stdout.json](probe_stdout.json)。

**两个具体边界得到程序印证：**不包含当前 CPU 的单成员集合也能没有 WARN；包含当前 CPU、但找不到有效其他 leader 时仍会 WARN。因此不能把“有无 WARN”等价为“成员条件是否成立”，也不能把 containsSelf 当作充分条件。空集合导致本版 `!core_rq` 告警只是一个具体路径；它不证明任何架构都必然产生空集合。正常双成员输入确认了第二轮确实把当前 CPU 接到已有 leader，而第一轮跳过当前 CPU。

这支持把自动检查拆为：接口集合身份、消费阶段、初始 rq／leader 条件和架构提供者履约几部分。成员条件仍是有消费依据的必要候选，但真实适用性、集合完整性及并发稳定性需要其他证据。

## 编译与执行收据

第一轮编译使用 `-Wall -Wextra -Werror`，被原消费者5770／5786的 int 与 unsigned 比较警告拒绝，执行0次。原收据逐字保存在 [probe_compile_initial.json](probe_compile_initial.json)。显式恢复只去除 harness 的 `-Werror`，保留其他警告与全部原源码；恢复时对生成 C 文件 SHA256 一致性作检查。第二次编译返回0，之后**仅执行一次**，退出0。没有为获得预期结果修改原消费者或逻辑输入，也没有重跑五输入。

[run_consumer_probe.py](run_consumer_probe.py) 保存每个提取函数 SHA256、packet SHA256、准确 revision、编译命令/输出、执行命令/输出和 binary SHA256。binary 位于项目 `analysis_out/claude-contract-resume/consumer_probe`，没有放入实验源码目录。生成 C 保存在 [consumer_probe.c](consumer_probe.c)；脚本读取既有结果后会拒绝重复执行，恢复入口也只允许这次特定的编译警告。

## 仍未解决

- 架构准备流程能否到达这些状态，尤其 singleton-other 与缺 leader 的人为构造，未证明。
- 源码5755取得指针与随后采样/遍历之间的值等价、跨CPU改写和真实锁语义未模拟。
- 该原型核对的是已读消费者的局部逻辑，不能认证模型整体分析准确率或独立泛化能力。

