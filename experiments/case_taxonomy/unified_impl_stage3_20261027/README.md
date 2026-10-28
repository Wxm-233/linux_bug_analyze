# 有界统一实现·第三阶段：薄统一入口

2026-10-27。执行横向复核建议第3项：输入组织→适配器选择→契约评价→分层报告。开始前按用户指示把sjy_test推送到origin（`dbe6392..73d0d6a`）。没有新实验、内核运行或模型调用。

## 实现

- `linux_bug_analyze/adapters/`：注册表`REGISTRY`与6个适配器——`smmu_qtest`、`virtio_split_trace`、`virtio_layout`、`btrfs_min`、`acpi_env_console`、`sparc_projection`。每个只把一个已存输入投影为事实（及必要的类型声明），不判定关系；模块文档注明迁移来源脚本。
- `linux_bug_analyze/unified_check.py`：读`unified_case_v1`清单（案例、家族/机制、修订、证据层级、依据文档、适配器、配置符号、输入定位、关系、可选期望），对每个输入调适配器、写带来源SHA的证据文件、用共享构建器生成v2契约、由`contract_protocol_v2`判定，输出`report.json`与`report.md`。未注册适配器的输入标`unsupported`、不判定；适配器异常标`adapter_failed`；适配器缺少关系所需事实判不足。关系与依据只来自清单，入口本身不推导要求。
- `tests/test_unified_check.py`4项（判定与期望、未注册适配器、适配器失败与缺事实、清单schema）。WSL全量447项，仍为原有2个pycparser导入错误、63跳过。

## 跑通已存开发材料（run2）

`build_manifests.py`从原轮材料生成7份清单（关系照搬原轮，期望取原结果）：

| 案例 | 家族/机制 | 证据层 | 输入 | 判定分布 | 与原结论 |
| --- | --- | --- | ---: | --- | --- |
| acpi_env | 固件平台/作用域政策提供者 | archived_runtime | 4 | 满足5、违反3 | 4/4 |
| sparc_identity_chain | CPU身份/身份·数量·准备 | source_projection | 24 | 满足89、不适用16、违反15 | 24/24 |
| smmu_qtest | IOMMU/有序命令提交 | archived_runtime | 14 | 违反3、满足5、不适用2、不足4 | 14/14 |
| virtio_split_trace | DMA/对象代次发布回收 | archived_runtime | 60 | 满足109、违反5、不足6 | 60/60 |
| virtio_layout | DMA/维护粒度隔离 | archived_runtime | 4 | 满足2、违反2 | 4/4 |
| btrfs_min | 内存几何/裁剪算术 | archived_runtime | 12 | 满足11、违反1 | 12/12 |
| sparc_compiled_objects | CPU身份/编译位宽 | compiled_object | 1 | 未判定（unsupported） | — |

另`compare_facts.py`核对迁移后的适配器事实与原脚本存下的事实：118/118完全相同。SPARC编译对象适配器依赖原轮反汇编窗口规则，尚未迁入包，故意保留为unsupported示例。

**首次运行失败已保留**（`run1_failed_relative_out/`）：输出目录以相对路径传入，证据文件相对项目根的路径计算失败；入口改为先解析绝对路径后run2通过。

## 边界

- 统一的是入口、契约表示、证据与判定流程；事实提取仍按接口适配，关系、依据、角色与合法资格仍人工登记于清单。这不是N1自动推导，也不是独立评价。
- 未迁入的适配器：拓扑归档、die导出/镜像桥、Btrfs挂载/观察点、SPARC编译对象、ARM64身份启动等，仍在各原轮脚本。
- 样本到期限稳定性未处理，deadline恒为不足。

## 下一步（待用户决定）

按冻结的评价协议准备独立评价：冻结方法版本（核心v1/v2、构建器、入口、适配器SHA）、写定准入判据、核定主模型可用输出/推理参数；付费调用须用户另行授权。或先迁移剩余适配器。
