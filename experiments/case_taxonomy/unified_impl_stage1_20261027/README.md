# 有界统一实现·第一阶段：共享构建器、收尾工具、评价协议与候选池

2026-10-27。按用户批准的横向复核建议第1、4项执行：抽取共享契约/账本构建器与收尾同步工具并回归，同时冻结评价协议与未接触候选池。**公共核心`contract_protocol.py`未改（SHA `42d37cc4…`）；没有新实验、内核运行或模型调用。**

## 1. 共享契约/账本构建器

新模块`linux_bug_analyze/contract_envelope.py`：`build_envelope(spec)`按显式参数组装contract/ledger/record，`envelope_spec(item)`只抽取调用方参数（角色说明/引用/来源/状态/附加字段、文档、事实值与来源、账本/记录附加字段），结构部分由构建器重新生成；另有`document()`、`whole()`、`symbol_type()`、`symbols_used()`辅助。它不加入语义，也不批准任何事实，判定仍完全由核心作出。

回归`regress_envelopes.py`：遍历实验目录中全部376个已存完整输入（36个文件，含25个控制样例）。

| 轮次 | 主输入逐字重建 | 主输入判定一致 | 说明 |
| --- | --- | --- | --- |
| attempt1 | 17/351 | 335/351 | 比较时误含外层说明字段；构建器把声明状态硬编码为supported |
| attempt2 | 347/351 | 351/351 | 只比contract/ledger/record；状态改为显式参数（runtime_source_binding的provider_binding为unknown，否则会被静默抬成supported） |
| attempt3（最终） | **351/351** | **351/351** | 补`observation_binding`附加字段（拓扑轮带context_id/event_kind） |

判定比较含applicability、observation、deadline、whole_path及理由。25个控制中18个可逐字重建；7个不能（故意制造的对象/上下文/版本错配与缺事实），构建器只生成绑定一致的信封，正是不应复现的部分。attempt1/2结果保留。单元测试`tests/test_contract_envelope.py`5项。

## 2. 收尾同步工具

新模块`linux_bug_analyze/round_close.py`（命令`prepare/apply/sync/verify/manifest`），替代各轮复制的close_notes.py与sync_work_notes.py（65份，其中55份逐字节相同）：交付清单、三份笔记顶部插入新节并加历史行、家族规划替换/追加行/改写执行顺序段、追加当日日志，全部按记录的SHA保护；镜像同步先核镜像旧SHA与工作区新SHA再写，收据不覆盖；`verify`只读比较工作区与`/root`镜像。单元测试`tests/test_round_close.py`4项（全流程、重复prepare/中途改动拒绝、镜像被他人改动时拒绝且不写、错误spec拒绝）。首次实现中远端代码在Windows本地模式按系统代码页解码中文文件名，改为显式UTF-8后通过；对真实WSL镜像的只读`verify`一致。本轮收尾即用该工具完成。

全量测试（WSL虚拟环境）：438项，仍为原有2个pycparser导入错误、63项跳过，无新增失败。

## 3. 评价协议（先冻结）

[evaluation_protocol.md](evaluation_protocol.md)：分别评价E1要求推导、E2给定要求后的检查、E3对照选配收益；样本、接触登记、方法冻结、准入与分母、参照、基线与预算、报告与变更规则。抽样前即记录SHA（`protocol_sha_before_pool.txt`）。付费调用须用户在评价启动时另行授权。

## 4. 未接触候选池

`freeze_pool.py`在WSL只按元数据运行，不显示任何候选的标题/说明/diff：

- 总体：`candidate_hashes.txt` 118,997个（SHA `7620bfe0…`）。
- attempt1：全部判为已接触——`analysis_out/full_run/candidate_hashes.txt`是候选清单副本。保留于`pool_attempt1/`。
- attempt2（最终）：一个文件含≥2000个不同完整候选哈希视为批量清单、单列不计接触（仅上述副本，SHA与总体相同）。扫描14,935个工作区文本：已接触2,538（分析输出1,928、实验488、日志73、对照表22、资料19、待办6、模型调用测试2）；经Fixes尾注与已接触相连的家族排除1,073；未接触115,386；`random.Random(20261027)`抽300并排序为`frozen_sample.txt`。

局限：只能识别写下哈希的接触；7—9位缩写未匹配；无Fixes的同bug修复不能链接；总体是宽过滤输出，大部分样本预计在准入阶段被判为不涉及跨架构接口，这会如实计入分母。

## 下一步（待用户决定）

按建议顺序进入第2项“最小表示扩展”（compiled_object证据层；仅覆盖SMMU qtest与virtio普通split的有序事件关系；可追溯的min/max/floor/ceil），每项须逐项复现对应专用检查器已存结论。新模块及大部分实验目录仍未提交Git，是否提交由用户决定。

## 文件

`regress_envelopes.py`、`envelope_regression*.json`、`evaluation_protocol.md`、`protocol_sha_before_pool.txt`、`freeze_pool.py`、`frozen_pool.json`、`frozen_sample.txt`、`contacted_candidates.txt`、`family_linked_candidates.txt`、`pool_attempt1/`、`close_spec.json`、`delivery_manifest.json`及收尾收据。
