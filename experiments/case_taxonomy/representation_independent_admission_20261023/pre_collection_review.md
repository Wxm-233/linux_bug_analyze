# D3 / N2.27 父版采集前有限复核

2026-10-23。独立助手研究侧只读审查，范围为本阶段协议、选择、方法身份、source_plan与采集脚本，以及N2.26既有方法摘要。未读取本组父版正文、子提交正文/差异、修复、旧模型回答；未运行采集器、组件、测试、编译、模型或内核。

**无父版采集阻断；仅允许固定八文件用于后续资格审查，不授予正例、正常或独立评价资格。**

## 选择与接触边界

- 唯一组固定 `f1fe8eefd2dd383beaf1748d8246a421c43865c5`，父版 `c00e13726b6c728370686b6d6e0e71b0a9f37f03`。标题只作读侧关系线索；它可能是等价整理、值提取或当前支持域外形状，不能据标题认定缺陷。
- 八条父版路径在读源前已固定，包含mt7603两个C文件及六份已命名头；selection与source_plan的顺序、唯一性、父版和选择SHA均一致，已有ls-tree记录无缺失。不是读取该提交全部八个改动C文件，也不因所选文件内容不足扩展到其余改动文件。
- 独立单位是具体字段/实际consumer关系和修复因果家族。旧mt7996/mt76驱动背景、历史500短筛和元数据排除引用必须披露；同driver背景不等于同故障，hash未命中也不证明所有函数未接触。具体函数供应/开发使用及家族仍待后续审查，本轮不能标strict unseen。
- 问题与正常资格都待父版/隔离oracle证据；同用途正常需有积极局部保证及非空语义域，不以无告警、零站点或不同业务用途替代。若支持域、必要依据或接触条件不足，原样停止，不改checker、换组或回写预期。

## 采集和方法

collect_parent只以argv执行本地Git。plan为固定父版的ls-tree文件名查询；collect只执行八次 `git show <parent>:<path>`，不读commit message/diff或子版。`GIT_NO_LAZY_FETCH=1` 禁止缺对象时隐式补取，`GIT_OPTIONAL_LOCKS=0` 限制可选锁写；缺对象或其他失败即停止，没有fetch/API/构建/启动入口。

脚本采集前要求本门控、ready计划、相同父版/路径/selection SHA及不存在旧manifest，目标目录独占创建；逐项保存字节、SHA、argv和stderr，异常保存stopped与已完成项，不自动重试或覆盖。后续修复若需要，仍须先固定父版资格/预测，再按协议另登记释放，不由本次门控自动授权读取。

representation_source、representation_semantics和contract_protocol三个当前SHA均与method_identity及N2.26的登记一致。该身份表只是复用组件，不是完整检测器冻结，也未执行新方法。本轮不按新源形状调整它们；后续提取前仍须保存具体材料、查询和判准。

## 当前身份记录

- protocol_pre SHA：`fe27b0e1e2fc58b66eddd078ae30f9d7141efb47b9dc61ede10b7cc1ef6180a5`
- selection_pre SHA：`6a863f95da77a3e9c6a29c73b7f56260e255193bbfbca672bb2664b8cd760451`
- method_identity SHA：`b73cce08baf393b2bc4054b5efe183f73107256f8299edecb811cd46efa554f6`
- source_plan SHA：`ac8fe625a06149ce87145da791869a4dbe0aad56d0244487ab2476a51c57e358`
- collect_parent SHA：`c7cdec55de427337d4c288535d44fb5b5e28584ceea1df991ab774c3966b9293`

最终检查时source_manifest与parent_sources均尚不存在；门控只允许这一次有界父版收集。R3和完整文件系统/硬件运行范围不变，独立0/0不因采集而增加。

PARENT_COLLECTION_GATE: PASS
