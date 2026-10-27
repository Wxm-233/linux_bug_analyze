# Kimi-K3.1-Pro-HighSpeed最小调用资格与默认切换

## 10月27日 最新维护：主分析切换Kimi-K3.1-Pro-HighSpeed，最小实测通过

按用户“模型换成Kimi-K3.1-Pro-HighSpeed，试试”的新指示执行。ISRC直连认证模型目录200、三项中包含该精确标识；发送1次最小请求，5.422秒完整交付KIMI_DIAG_OK，actual_models仅Kimi-K3.1-Pro-HighSpeed、stop/DONE/EOF齐备，无refusal或错误。可见用量161 token，usage_known=false，不当完整账单；每调用独立1M口径不变。这里只确认平台有该模型且可调用，不独立宣称全球最新版本或分析质量更高。

已将AGENTS和current_analysis_backend主模型更新为Kimi-K3.1-Pro-HighSpeed，独立配置kimi-k31-pro-highspeed-20261027仅引用原仓库外密钥文件；没有复制密钥。K3完整旧路由、成功研究结果与失败/未知费用保留在历史。仍采用证书校验HTTPS直连、连接30秒/上传60秒/读空闲600秒/墙钟900秒，不修改系统代理或ccSwitch，无自动回退/重试。

入口改为读取主路由JSON的model和credential_profile；传输器按请求的精确模型验证响应，不再硬编码只认K3。4项本地模型门控测试通过：新名匹配成功、旧响应不得算新模型成功、反向错配也拒判、历史K3仍可显式验证；这些不调用API。本轮只有1次模型生成及1次目录GET，未重跑旧缓存源码任务，无新内核实验、接口结论或缺陷，独立正例/正常0/0。

下一项仍是virtio限定用途方法评审。新模型的大源码任务尚未执行，旧缓存补充任务失败停点保留，不能将短测写成研究分析完成。后续新授权范围内的主分析默认使用此精确模型，仍需源码/实验复核。

证据：模型调用测试/2026-10-27/kimi_k31_pro_highspeed_trial/（catalog、prompt、call_plan、events、final、receipt、model_gate_tests）；linux_bug_analyze/experiments/case_taxonomy/kimi_k31_trial_20261027/（authorization、qualification、README及旧路由/代码/工作文档备份）。规划及当日日志、待办、进展、交接同步维护，三份WSL镜像以notes_sync成功收据为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

