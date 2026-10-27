# Kimi连接诊断及传输入口修复

## 10月27日 最新维护：Kimi连通诊断与传输入口修复

按用户“确认kimi为何连不上并尝试修复”要求，暂先处理工具连接，不启动新内核实验。DNS/TCP/TLS正常（直连约0.203秒），系统代理和直连无认证GET均快速401；既有密钥认证模型目录200，Kimi-K3存在。无密钥、认证头或完整代理凭据写入仓库；凭据仍仓库外经内存读取。

同一195字节最小请求、同一payload SHA的顺序对照：系统代理127.0.0.1:7892路径62.25秒TimeoutError，无HTTP/正文；禁用本入口代理后15.672秒完整Kimi-K3/stop/DONE/EOF，正文KIMI_DIAG_OK。修复入口再次直连实测45.266秒完成，建连0.187秒、响应头45.234秒。表明当前代理路径有异常，认证/模型可用；顺序对照仍可能受服务时变影响，不断言所有历史超时都由代理造成。原181.234秒失败没有阶段日志，无法事后精确定位其连接/上传/响应头环节。

修复：保留旧runner备份，将run_kimi_review.py改用kimi_transport.py；默认证书校验直连ISRC，本机系统代理与ccSwitch未改。允许显式--proxy-mode system诊断，不自动切换/重试。旧urlopen的180秒限制位于外层900秒内，可提前中断；新设置分开连接30秒、上传60秒、读空闲600秒、总墙钟900秒，并记录connect/upload/response_headers/sse_read/EOF及时间。出现refusal、错误模型、缺正文/stop/DONE/EOF仍不算完整交付；隐藏推理不保存，错误不输出认证信息。

验证：6个本地测试方法通过，含4个超时阶段及6种完成门控子场景、拒绝后正常结束仍拒判、坏SSE/结束后追加数据、旧收据保护、保密与keepalive。没有向API发这些单元测试。实际生成请求共3个：1个系统代理失败，2个直连成功；成功请求可见用量143+168=311 token，失败用量未知，不计0，也不当完整账单。2次认证目录GET及无认证网络检查另列，不计生成请求。原172602字节缓存源码prompt和失败收据未改、未重发；原大任务仍未由修复入口验证完成。

这轮属于分析工具维护，不新增接口结论、模型要求、内核实验或Linux缺陷，独立正例/正常仍0/0。研究下一项仍是virtio限定用途方法评审；Kimi缓存补充分析的原失败停点保留，未来调用使用修复入口，已有短测不能充大源码稳定性证明。主模型仍Kimi-K3，预算每调用独立1M，旧Claude记录不变。

证据：模型调用测试/2026-10-27/kimi_connection_repair/（network、两路径minimal_receipt、v2_minimal、test_results、runner备份、diagnosis）；linux_bug_analyze/experiments/case_taxonomy/kimi_transport_repair_20261027/（authorization、diagnosis、README、notes收据及维护前文档）。AGENTS、路由和规划已同步维护；日志、待办、进展、交接同轮更新，三份WSL镜像以notes_sync成功收据为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

