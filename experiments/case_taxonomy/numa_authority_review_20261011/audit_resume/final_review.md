# NUMA有限材料包独立最终审阅

2026-10-11。审阅者：`/root/numa_final_audit`。结论为 **PASS（有限材料包的保存记录、源码形状与裁定表述一致性）**；NUMA实际接口裁定仍为 **insufficient**。这不是新内核缺陷确认、ABI正确性证明或独立运行阳性。

审阅仅使用`protocol_pre.md`与`materials_pre.json`固定的八份原材料，共37427字节，以及本阶段生成的待审阅产物。八份原材料的长度、SHA-256均与清单一致；`pause_manifest.json`列出的六个冻结文件哈希均未改变。没有新增Git、网页或外部模型检索，没有执行历史harness、探针、runner或新内核测试；仅进行文本读取、保存JSON解析、哈希与已有公式计算。`review_existing.py`只读检查，未由本审阅者执行。

## 保存记录与尾部含义

9/21的原JSON具有12个唯一组合：3个variant × effective_bits 65/96 × tail 0/1。实际入口参数分别为66/97，全部与bits+1一致。`parsed_evidence.json`的12个索引及variant、bits、maxnode、tail、长度、返回值逐项与原JSON一致；原记录中的consumed/value/page_faults也与保存返回值一致。

| variant | effective_bits / 入口maxnode | 可读字节 | tail 0 / 1保存返回值 |
| --- | --- | ---: | --- |
| original_effective_bits | 65 / 66 | 12 | -14 / -14 |
| original_effective_bits | 96 / 97 | 12 | -14 / -14 |
| declared_maxnode | 65 / 66 | 12 | -14 / -14 |
| declared_maxnode | 96 / 97 | 16 | 0 / -22 |
| declared_maxnode_padded64 | 65 / 66 | 16 | 0 / -22 |
| declared_maxnode_padded64 | 96 / 97 | 16 | 0 / -22 |

按既有报告的调用者32位字宽存储规则，97需16字节而66需12字节。因此96位两组保持为既有harness长度勘误；65位两组保持为同一compat边界的未决观察。三种variant不是12个新案例，也不证明原ABI预期正确。分配变换仅由JSON字段及README既有报告交叉支持，变换runner、历史编译产物及执行收据不在八材料中；最终卡已明确这一缺口。

保存harness的第190行在`((uint32_t*)data)[2]`设置node64：偏移8，位于66位声明取整的12字节内部。补足16字节后tail=1返回-22，不能证明第四个范围外字改变判断。保存源码的64位内核字模型以8字节指针步长取尾段、再读取两个32位compat字，65有效位的首段范围为字节[8,16)；这只能直接裁定切片形状。

9/28原JSONL的四行返回值为[-14,0,-22,-22]，参数与探针数组一致。探针第73行的`p[132]=1`设置bit1056；同maxnode=1026、同136可读字节，仅该额外字由零变非零时，保存结果0变为-22。这批对照才支持范围外额外字影响判断的既有观察。maxnode=1057一行只作为另列的136字节拒绝对照；按报告的声明存储口径bit1056容纳于136字节中，但它不解决`--maxnode`解释，最终卡没有将其升级为双方边界语义均已证明的正常对照。

## 来源层级与最终卡

`source_quotes.json`的九段引文、源文件哈希与行范围全部与固定源码吻合。公开ABI正文、Microsoft同名标签源码、WSL环境、真实native大矩阵及静态i386 ELF身份均只存在于既有报告或不在固定包中，最终卡保留reported/缺失层级，没有升级为本轮直接primary核验。保存JSON的身份核对也没有升级为历史产物与执行链的身份确认。

最终卡已修正审阅提出的两项表述：明确9/21 variant执行身份不足；适用权威或可达路径不足时输出insufficient，条件齐备且算术超界时才生成复核候选。非零tail表达式也已精确为源码中的类型转换索引。native/compat入口、用户存储单位、内核指针单位、两项勘误与两项未决观察分开，集中领域确认问题仍待回答。无未解决的材料包表述问题。

材料包可完成；新确认0、独立阳性0、原12条6/5/1保持。接口裁定、D3/D4整体及通用自动检查未完成。

## 被审阅的新阶段产物身份

以下身份为本次最终读取时的SHA-256；若任何产物后续修改，应按新身份重新核对。

| 文件 | 字节 | SHA-256 |
| --- | ---: | --- |
| authority_card.md | 7022 | dd08e4a44d41664b7d810fe33a1349f9479c673a6855ba4da5cdd938bb654d8f |
| authority_card.json | 2910 | c0a03c002fdfa0f84dd85e06e60e6e55713cabe482310b6520621688785f3327 |
| checkpoint_complete.md | 1628 | 2cbbfef475e719b0e4ca256bf0d6cdc00b9d85263d28a51790bf304330dd73b7 |
| parsed_evidence.json | 7543 | a78d0e836a115a13a25c97fde763d794712c98ce4a98cb07ccbe1e5a35ca07f4 |
| source_quotes.json | 9604 | 9848b213228fec815ecadfa5da0385537f3e5312f107294c6a7c485c8e200c98 |
| review_existing.py（只读） | 5758 | 710f43684edc3cf89b31b6f9a78ad0eadbfe8794cb8d3d7fd0db1c7f205609fb |

冻结材料清单身份：`materials_pre.json` SHA-256为74ad9af7957d059ad5a34002c9b559eb6667cfca9d8f1aa99124db1f7cb4b672。协议身份为cb848d97a9e7803af645923b11b5b53a958f02d43e791e2bb64daa7631b43939。
