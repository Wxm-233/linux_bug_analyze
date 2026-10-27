# N2.2 已选两格归档回放的独立复核（2026-10-17）

范围仅为事前选出的 P01（旧版 s390）与 P03（同版 x86_64）。我只读了本阶段协议、选择回执/输入、回放脚本及结果、原 `run_runtime.py` 的 `analyse` 函数第 235–275 行，以及这两格的 `kernel.config`、`autoconf.h`、`build.json`、`boot.json` 和 QEMU 标准输出/错误日志。没有打开 P02/P04 的运行结果或事件，也未重跑构建、启动或模型调用。

## 选择与读取边界

回放前预登记的 `protocol_pre.json` SHA-256 为 `5e592b315eee94d0a6f0c35492b3b9b2a5569260c8299eb0acced16956631f30`。当前 `example_pool.json` 的 SHA-256 为 `c9df5ae59b39c75f4e4bf5bd337f36a390eb182de90d1b7b470cce77d015caa2`，`selection.json` 为 `5b0284553cef2061e139f6d87e3618dde2ce9eac3c9205e16da65f45f0dec114`；两者均与先存 `selection_receipt.json` 和 `replay/input_identity.json` 相符，保存的选择仍只有 P01/P03 一对。

`run_selected_replay.py`（SHA-256 `32e6d5cb65b8dee1c1e5c02591405a93d3081f95d89bde6f2151529ca3e32425`）先核对上述摘要，随后由保存的 profile ID 映射读取材料；循环只遍历 `selected={P01,P03}`，解析后的目录必须位于原 profiles 目录且名称为 `old_s390` 或 `old_x86`。每格读取六件归档文件，末尾再次核对原选择摘要。它会读取包含四格**元数据路径**的 provenance，但不会因而打开未选两格的结果/事件。静态调用图没有构建、启动或批处理入口：脚本 AST 解析原 runner，`exec` 的模块仅含原 `analyse` 函数，命名空间只注入 `re`；脚本自身不导入或调用原 runner 的 main/build/boot。`opened_profile_artifacts` 记录的 12 个文件也只属于选中两格。以上是对脚本和保存记录的审查，不是操作系统级文件访问审计。

## 观察与真值边界

原 `analyse` 第 251–270 行的 `foundation` 检查事件唯一性和顺序、CPU/状态一致性、用户态观察、字段内部一致性等；其中没有按 `old/fixed` 设置 self 期望，也没有以 WARN 或 `EXPECTED_CONTRAST` 判定结果。按旧/修复版本设定的期望只在第 271–275 行 `contract`/`status` 中，回放脚本没有引用这些字段。`archive_events_reproduced` 比较的是同一原解析器重新提取的事件与原归档事件，说明解析复现一致，**不是独立测量**；`all(foundation.values())` 在此充当日志/上下文有效性前提，未把旧版的期望结果带入 `relation_truth`。回放实际使用 `lock_snapshot` 的 `self==1` 判局部关系，`locks` 仅作为诊断字段。

我独立核对 P01/P03 各六件文件摘要均与 `selected_replay.json` 所列相同；两格 build revision 都是 `88b604263f3d6eedae0b1c2c3bbd602d1e2e8775`，arch 分别为 `s390`、`x86`，build/boot profile 名一致，boot 归档记为第一次尝试 exit code 0。配置与 autoconf 摘要和事前 pool 相符。标准输出坐标也准确：P01 第 149 行为 CPU1 `lock_snapshot`，`self=0, locks=0, mask=0`；P03 第 109 行为 CPU1 `lock_snapshot`，`self=1, locks=1, mask=2`。每格原日志中 CPU1 的该相位各出现一次。两格解析基础条件均为真，因此保存的局部关系一违背、一满足，与原始日志字段一致；并没有把原始日志的 WARN 或原 runner 的预设对照状态当作结论。

`foundation.mask_stable_before_consumer` 这个**沿用的旧键名**只要求五个离散观察点（`arch_before_notify`、`notify_enter`、`cpuhp_before`、`core_enter`、`lock_snapshot`）的 mask 数值相同。它不能证明这些时点之间全区间稳定，更不能证明观测点就是全局首次实际内容读取。`binding` 已将 `exact_loop_read_proved`、`global_first_read_proved`、`interval_stability_proved` 明确记为 `false`；CPUHP 状态数值、CPU1 角色与配置摘要构成有限绑定，实际对象地址没有记录。不同架构的机器/CPU 型号可比性和接口要求仍属已读研究者审阅范围，不能由本回放自动证明。

审查结论：可以报告“已保存选择的两格旧版归档在相同抽象场景下呈现局部 self 关系差异”，并报告具体日志坐标和限制；不能报告新内核运行、新发现缺陷、独立选择增益、真实 SMT/热插拔复入覆盖，或精确首次消费与全区间稳定的系统级验证。
