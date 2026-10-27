# 有界统一实现·第二阶段：最小表示扩展与专用检查器复现

2026-10-27。按用户指示执行横向复核建议第2项：compiled_object证据层、SMMU/virtio有序事件、可追溯min/max/floor/ceil，并逐项复现专用检查器已存结论。没有新实验、内核运行或模型调用。

## 实现

新文件`linux_bug_analyze/contract_protocol_v2.py`；**v1 `contract_protocol.py`未改**（各轮按SHA `42d37cc4…`钉住）。v1 schema的输入在v2中按v1语义评价；新特性只对`architecture_contract_v2`开放：

| 扩展 | 内容 | 判定规则 |
| --- | --- | --- |
| 证据层 | `compiled_object` | v1 schema携带该层仍判不足 |
| 算术 | `min`/`max`/`floor_to`/`ceil_to`在核心内求值 | 粒度≤0判不足；操作数仍须是经审核事实 |
| 有序事件 | `event_seq`事实（`[kind, object, generation]`列表），算子`ordered_within`、`complete_within`、`exclusive_within`、`at_most_once_within`、`generations_disjoint`、`count_kind`（一个或多个种类） | 种类必须为字面量；按对象代次分组 |
| 观测资格 | 可选`observation_qualification`表达式，须在观察绑定声明中原样审核 | 不成立时判不足而非违反 |

共享构建器`contract_envelope.py`增加schema与qualification参数（并注明空事件序列须显式声明类型）。第四个缺口“样本到期限的稳定性”按横向复核建议不处理，deadline保守规则不变。

## 回归

- **v2对v1**：全部376个存量输入（合成输入分别以开启/不开启合成各评一次）共391次评价，v1与v2结果所有字段含理由完全相同；count_kind改为多种类后重跑仍0差异（两份结果均保留）。
- **构建器**：支持v2后重跑第一阶段回归，主输入仍351/351逐字重建、判定一致。
- **单元测试**：`tests/test_contract_protocol_v2.py`5项（算术含负数与零粒度、事件算子、资格不足≠违反及未审资格、v2专属特性、种类须为字面量）。WSL全量443项，仍为原有2个pycparser导入错误、63跳过，无新增失败。

## 专用检查器复现（reproduction_results.json）

| 组 | 输入 | 一致 | v2分布 | 对应专用检查器 |
| --- | --- | --- | --- | --- |
| SMMU qtest | 10回放+4控制 | 14/14 | 违反3、满足5、不适用2、不足4 | smmu_review_20261026/checker.py的observed_encoding |
| virtio普通split | 54审计+6控制 | 60/60 | 接受54、拒绝6 | virtio_add_recycle_20261027/checker.py |
| SPARC编译对象 | 4变体+6篡改控制+1层级检查 | 11/11 | 满足4、违反6、不足1 | sparc_identity_objects_20261027/check_objects.py |
| 算术 | virtio 4格布局+Btrfs 12诊断+零粒度控制 | 17/17 | 满足13、违反3、不足1 | runtime_results.json的group_geometry；Btrfs matches_archived_geometry_arithmetic |

- virtio布局用floor_to改写原`(x-1)//L == x//L`判定：首部隔离⇔`floor_to(evt,L)=evt`，尾部隔离⇔`end ≤ floor_to(lock,L)`；父版两格共享（违反）、修复两格隔离（满足），与原结论相同。Btrfs用`effective = min(request, geometry)`，12条中1条（父版64K、请求8192）违反，与原结论相同。
- **第一次复现失败已保留**（attempt1/）：virtio 40/60，route≠0的20条已接受轨迹被判不足——原检查器的FINAL映射计数包含MAP_FAIL，而资格表达式只数`map`。attempt2让`count_kind`可数多个种类（仍是计数，未加入通用加法），60/60。
- virtio 6个控制中，发布先于屏障、错误token对象、发布后失败被关系判违反；缺unmap、复用早于完成、缺FINAL由资格中的FINAL计数核对判不足。原检查器对这6项只给统一的“拒绝”；v2区分了“关系违反”与“观测不自洽”。这也说明后三项目前依赖harness自报计数，而非仅凭生命周期关系捕获。
- 未复现的原检查器细则：virtio的槽位/索引绑定与错误原因规则（-5/-28/-12对应条件）、每对象代次计数g0/g1；SMMU的读宽度检查并入适配器回复异常计数。专用检查器保留，不删除。

## 边界

- 适配器（原始转录→事件/事实）仍按接口分开，且与原检查器共享对“哪些行是什么事件”的人工登记；v2只把顺序、完整性、互斥、计数和算术移入核心审计。
- 复现对象都是已读开发材料；不是独立评价，独立正例/正常0/0。

## 下一步（待用户决定）

第3项“薄统一入口”（输入组织→适配器选择→契约评价→分层报告），或先提交Git；独立评价须另行授权付费调用。
