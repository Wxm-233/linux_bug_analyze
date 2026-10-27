# D3 / N2.27：采集前接触史元数据审查

日期：2026-10-23。角色：助手研究侧只读接触史复核，不是源码主分析或检测结果。固定唯一候选`f1fe8eefd2dd383beaf1748d8246a421c43865c5`、父版`c00e13726b6c728370686b6d6e0e71b0a9f37f03`，只依据本阶段selection/protocol/method_identity/source_plan及既有研究清单、源manifest、文件名/路径记录审查。

本接触审查没有阅读本组父版/修复源码正文、commit正文、diff或旧assessment，没有运行组件、测试、模型、编译、启动或取源。父源采集由主流程另行进行，采集后的新文件名在目录清单中可见，但未纳入本次旧正文接触证明。后续正常/支持域审核将另立记录。

## 1. 审查范围与限制

使用`rg --files`列举`experiments/case_taxonomy`内JSON文件名，限定包含manifest/selection/protocol/source/parent_files/documents/contact/exposure/git_metadata等标识的既有记录，共解析291份可读元数据文件；本新stage排除，不搜索新父源内容。responses/requests/proposals/diagnostic/raw/logs/parent_sources/sources/observer_sources及私有真值目录排除；assessment/oracle/repair_evidence/response文件名排除。JSON遍历跳过text/source/content/stdout/stderr/body/assessment/analysis/reasoning/message/diff/patch/prompt/response等正文与答案字段，字符串只查单行有限元数据。另检查既有文件名，未读取旧raw结果正文。

此范围不是整个项目、聊天、外部模型或历史所有文件的全局取证，也不覆盖未被这些文件名规则纳入的嵌入材料。没有命中只表示本范围未取得相应证据，不证明从未供应、从未阅读或未用于开发。

## 2. 八路径的具体既有记录

| 本组父源路径 | 既有命中 | 本次能确认的接触层级 |
| --- | --- | --- |
| `drivers/net/wireless/mediatek/mt76/mt7603/dma.c` | `core_consumer_qualification_20261017/git_metadata.json`的`/records/405/changes/0/path` | 候选变更路径元数据；未在本次元数据范围找到此完整父源供应manifest |
| `drivers/net/wireless/mediatek/mt76/mt7603/mac.c` | 同文件`/records/405/changes/1/path` | 候选变更路径元数据；未在本范围找到此完整父源供应manifest |
| `drivers/net/wireless/mediatek/mt76/mt7603/mt7603.h` | 本范围未发现旧精确路径记录 | 旧具体供应/阅读未知，不能称已证明无接触 |
| `drivers/net/wireless/mediatek/mt76/mt7603/mac.h` | 本范围未发现旧精确路径记录 | 同上 |
| `drivers/net/wireless/mediatek/mt76/mt76.h` | 本范围未发现旧精确路径供应记录 | 共享头不能因同属mt76而自动认定已读；当前仍未知 |
| `drivers/net/wireless/mediatek/mt76/dma.h` | 本范围未发现旧精确路径供应记录 | 同上 |
| `include/linux/bitfield.h` | `bounded_interface_holdout_20261003/producer/manual_review/source_manifest_extra.json`的`/2`和`/6`，parent/fixed版本均登记完整源 | 确认共享位操作接口头已经供应。parent revision `ea58aae8458480d6391c404e62f1a4b30462b9c3`，fixed revision `1cfa6d4e5bd9bfb15d165d8d843163363929ba1b`，均SHA `7b0641d03c5c64148811a028634cbd468effcf14d65fb86a75f59bf1ef61b744`；不证明本组mt7603消费者/对象已读 |
| `include/linux/byteorder/generic.h` | ocfs2、PWM、request_copy等既有供应manifest；例如`cross_subsystem_facts_20261003/ocfs2/source_manifest.json`的`/31`、`/66` | 确认共享转换接口头已供应。ocfs2 parent/fix登记SHA `6b3facab3b763a327c3c24c198f1a43ac0f3e8964e5feb0292d909694f90589d`；共享接口背景不等于本组选定关系或同修复家族 |

元数据中相同路径可同时出现在source_path与saved_path，因此不将字符串命中次数计作不同源码、不同案例或研究样本。

## 3. 本候选的初筛、提名与排除史

所有500池条目均已有历史DeepSeek短筛接触，不称模型全局未见。

`core_consumer_qualification_20261017/exposure_index.json`的`/items/405`将本hash标记为`protocol_selection_metadata_reference_only`，所列命中指向`final_synthesis_repr_v2_selection_pre.json`；`source_review_evidence_paths`、`existing_holdout_paths`等当时为空，`family_status=unknown`，`global_non_exposure_proved=false`及`independent_eligibility_proved=false`。

后者`/known_exclusions/5`确实曾按“mt76 same driver family as the earlier mt7996 holdout”排除本hash。该原始排除须披露，不能改写为没有接触；但其单位是宽泛驱动家族，**不直接证明本组具体编码字段—消费者关系或同一修复因果家族已用于方法开发**。本轮协议明确按较窄关系/修复家族审资格，不能将旧宽排除自动转换为已证实相同关系，也不能反向当作独立性通过。

## 4. mt7996与本组的关系仍需区分

`endian_producer_holdout_protocol_pre.json:/targets/0`登记旧候选`54ccb836ffb28eacba51b674cbe94cb5613f8441`、父版`ef1ea24cb0ecfd42c1ff266d92613163792aec77`和`drivers/net/wireless/mediatek/mt76/mt7996/mcu.c`。旧选择记录也将其列为earlier producer holdout read，目录存在`producer_holdout_54cc_mcu_raw.json`结果文件；本次未读该raw或旧assessment，不根据结果文件名重建检测成败。

可确认mt76驱动及表示生产端研究背景已存在；但mt7996/mcu.c与本组mt7603/dma.c、mac.c是不同源位置，不能只因驱动前缀相同，就判断其描述符、字段、读取用途、操作方向或修复因果相同。共享`mt76.h/dma.h`是否被该旧输入间接供应，本次有限manifest没有给出确认，仍保留未知。

## 5. 当前准入含义

- 历史短筛：已接触。
- 旧元数据提名/宽驱动家族排除：已接触，必须披露。
- 共享bitfield/byteorder接口头：已有具体供应证据。
- 本组mt7603两个C文件及四个驱动头的旧完整供应：本审查范围未找到，范围外未知。
- 本组具体函数、编码字段—消费者关系及规则开发使用：尚未由本次元数据建立；取得父源后必须再核具体位置，不能从路径未命中直接判未读。
- 同修复因果家族：unknown。相同驱动名、作者、标题或通用转换接口不提供充分证据。
- 正式独立正/正常与方法形状支持：本接触记录均不赋真值、不计通过；后续由父版限定资格审查单列决定。

本次未取得足以直接证明本组具体关系已用于开发的记录，因此可继续唯一组的父版资格审核；这只是允许继续审查，不是“独立性已证明”或“方法已检出”。若后续支持域、规范依据、正常参照或具体接触不满足，按协议不足收束，不更换组或改写方法。
