# N2.12 词汇接线回放独立审查（2026-10-18）

只读协议、`replay.py`、两项开发测试、`developer_replay_results.json` 与原冻结文件摘要；未修改或重新执行原分析、原比较。协议列出的六个受保护文件 SHA-256 与磁盘一致，含原 `program_results.json` (`fb34eb9a…`)、原 `source_check_results.json` (`dddbe617…`)、方法基线 (`a89db3ef…`)、原比较器 (`20214e35…`) 和参考冻结文件。原比较结果仍为 **2 match、2 mismatch、16 insufficient**。

回放对原 `analysis` 深拷贝，给每个事件保存 `original_kind`，仅把带 `field.access=read` 的 `load` 改词汇为 `field_load`、带 `field.access=write` 的 `store` 改为 `field_store`，以及本参考中的 `branch→condition`、`scalar_assign→assignment`；未增加/删除事件，调用原冻结 `evaluate`，并检查依赖、控制边、事件 ID 与逐事件还原后原数据一致。原两版 packet 均没有同时带 `indexed` 与 `field` 的事件，索引访问且无字段元数据不会变成成员字段。两项开发测试通过；实际文件仅保存一次回放。

新回放的 **12 match、8 insufficient、0 mismatch** 归属是选择器词汇接通；两版的 F02 字段写入及局部关系/显示控制边现在能按已有事实被选中。八个不足恰为 F01/F03/F04/F10 各两版，仍由旧比较器全局 opaque E16 的覆盖策略触发，未放宽旧规则。这里没有新 Linux 样本、没有重新提取事实，更没有契约、别名、可达性或自动发现能力的增益；结果必须与原冻结分数并列，而不能代替它。

泛化边界：代码按 `field.access` 判断，而未显式拒绝未来一个事件同时带 `field` 与 `indexed` 的异常混合形状；本次固定 packet 中该形状为零，因此不影响本轮归属。`condition` 和 `assignment` 的映射也仅适用于这份已揭示的有限参考，不应推成所有条件或赋值类别的普遍等价规则。
