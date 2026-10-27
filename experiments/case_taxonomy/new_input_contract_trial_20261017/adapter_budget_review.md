# N2.6 budget v2 独立限域复核（2026-10-17）

结论：在登记的预算分类与采集版本兼容范围内，未见阻断问题。这是方法/材料身份审查，不是 E/F 的词法检查、语义判定或执行效果验证。我未阅读 E/F 父版正文、修复、模型回答或新检查结果，也未重跑测试。

- 时序：`adapter_amendment_v2.json` 在 v2 修改前登记，但父版正文当时已由其他角色读取；记录明确 `revised_adapter_frozen_before_parent_body_reading: false`。v2 不能称为“读父版前冻结”的方法。登记称模型预测及实际 selected-case checker 输出当时尚无；本次审查未据后续输出调整规则。
- 代码范围：比较保留的 `run_raw_candidate_checks.v1.py` 与当前文件，仅有两处行为修改：补源预算把 `.c` 计实现、`.h` 或文件名恰为 `Kconfig` 计 authority/config，并拒绝其它路径类；采集源的 `adapter_baseline_sha256` 必须等于当前基线指定的 `collection_baseline_sha256`。原有单例上限（实现≤2、authority/config≤2、补源≤4、每案总≤8）仍在。未新增 C 语法、CFG、效果或配置可达性推理。
- 版本绑定：v1 baseline SHA-256 为 `14362c51d83caf80c2f1d2e61dccc9570fc29c1f01a435e20a1abc3f556f2f2f`；v2 为 `d05c12595def8e990747854401a2be8a3fb401266513a0d7afd365a39055c1c9`，其中 `collection_baseline_sha256` 精确指向 v1。当前 `run_raw_candidate_checks.py` SHA-256 为 `021d5a837d2d87a1385e28752aff59e139aa7a6f5aff4165b73e4329ef1b7625`；保留的 v1 为 `3032e47faf172ed03536053a70b28b6e55d88c526cfd4411f432ec49476c03b2`。两版基线对 selection、initial plan、N2.5 checker、collector、preprocessed lexer 的登记摘要相同；未见 locator/lexer/parser 改动。旧采集 artifact 的元数据仍标 v1 SHA，未改源 artifact；这里只核身份/摘要，未读取正文。
- 测试记录：`adapter_tests_budget_v2.json` 记录修后 13 项测试、`exit_code: 0`，涵盖两 `.c`＋`.h`＋`Kconfig` 可入预算及第三 `.c`、第三 authority、未分类路径拒绝。测试文件与记录 SHA 一致。这是保存的执行记录，本审计未独立重跑。
- Packet/preflight：E/F 的 `packet_manifest_*.pre_amendment.json` 与当前 manifest 逐字段比较，均仅 `adapter_baseline_sha256` 从 v1 改为 v2；`prompt_sha256` 和 `prompt_utf8_bytes` 未变。`packet_preflight.json` 记录 7＋7 份文档 source-bound、baseline/selection/plan 绑定通过，范围限材料身份。首次 preflight 的物理 prompt 字节断言因 Windows CRLF 与 runner `read_text()` 的 LF 规范化不同而失败，`preflight_first_failure.json` 记录在网络前且请求数 0；修后按实际发送的逻辑字节核摘要，另外记录物理文件摘要。此差异不应描述为更改 prompt，也不提升为语义成立或执行可达性。

保留的边界：`.h`/`Kconfig` 分类只是补源预算身份，不能证明相关配置启用、接口权威性、跨架构差异或检查有效性；source-bound 也不能代替独立 oracle。E/F 真实 checker 与模型输出须另行评估，并披露本次读父版后的 v2 方法修订。
