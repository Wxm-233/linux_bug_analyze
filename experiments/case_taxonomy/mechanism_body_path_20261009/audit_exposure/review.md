# 固定32项独立曝光审计

2026-10-09。仅检索此前 case_taxonomy 的 md/json/tsv 记录，排除完整本轮目录。使用 rg 固定字符串检索每条完整 commit 与前12位；范围、命令、原始输出、匹配全文均保留。没有访问新 Git、源码、补丁或模型结果。

范围共752个文件，32项池对应222条引用。30项在定义域无证据；2项确认已审阅源码或参与规则开发；无未决项。范围文件指纹在写结论前逐条复核未变化。这里的“无证据”不代表全球盲样，旧短判定也可能已读取材料。

- bnxt_re `95b087f87b78`：case_reviews.md 第15行明确描述 encoded/CPU/硬件表示传递及修复路径；此前两个选样协议明确标记固定12组源码已读。pilot TSV 是元数据引用，不单独作为源码曝光依据。
- PWM `09f688f0718f`：endian_producer_single_revision_review.md 第3行明确已读父版用于开发，第11行给出字段赋值候选和实际规则输出；endian_consumer_holdout_review.md 第7行也已描述旧/修复写入语义。旧元数据文件引用本身不单独证明源码读过。
- i3c `7a2bccd1a27f`：全40位及前12位在上述定义范围都没有引用；允许按协议进入有限取证，但不称独立阳性或全球未知案例。

与标题REP匹配相交后：3项标题命中，2项已曝光被排除，唯一未有定义域源码曝光证据的项是 i3c。此处不解释其缺陷原因，也不预测正文是否有长度机制。

metadata_pool SHA-256：`187f2d7d289cf715d54fb985cb353103ce30c7838a2cc149433b0f47acbc69f9`。
exposure_audit SHA-256：`57939acd9913e63b6ab4bd03b3740f793942bcbdb69ee00b0ac897aed82e2ebc`。
scope_search SHA-256：`6a50868edc9f706fdf9cac144a191ba00f2f76cc5d11c154364ce03a7518a63f`。
