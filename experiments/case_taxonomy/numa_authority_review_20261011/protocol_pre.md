# NUMA native/compat：一次现存材料权威核查

2026-10-11。接续配置机制收束，限定现存NUMA材料，不新增Git/网页/模型检索或运行测试。两份既有综述已在规划时阅读；本轮不是盲测，不将它们当直接ABI权威。

## 范围与来源

固定八项相对于项目仓库的材料：experiments/case_taxonomy/numa_boundary_2026_09_28.md、final_summary_authority_cards.md；experiments/numa_entry/README.md；experiments/case_taxonomy/numa_padding_probe.c；experiments/numa_entry/compat_start.S；analysis_out/numa-padding-20260928/results.jsonl；analysis_out/numa-boundary-review-20260921/results.json；analysis_out/numa-entry-20260915-v2/followup/harness.c。

首次本轮正文读取前，记录每项可用/缺失、大小、SHA256及协议身份。总量1MiB上限；缺文件、超限不换路径或扩读依赖。只读现有文件，不复制已有大资源，不执行harness/探针/旧runner，不运行uname或读取当前环境来替代历史环境。两份综述前读状态明确保留。

## 两入口、两主张

入口限定native用户位图与32位compat用户位图。两项待裁定主张：①实际maxnode及用户ABI字宽决定调用者可提供的存储上界；②历史转换/尾部读取是否越过该上界、额外字是否影响结果。

先区分96位两项harness长度错误与65位两项剩余边界，不能称四个内核问题。核对本轮材料究竟是历史函数切片、当前WSL进程实测还是直接规范，记录版本/配置/语言字宽/指针单位；不把本地Linux HEAD与受测WSL构建当相同源码。

结果只汇总现存证据与缺口。ABI文字与源码若有范围解释差异，保存两边主张，不用补丁、返回码或多数架构代替权威。确切运行二进制对应源码/适用ABI不足时输出insufficient，不判新缺陷、不提出未经裁定的补丁。

## 验收及后续

完成一张裁定卡、两入口对照表及一个集中待领域确认问题；逐条附现有材料链接、身份和证据层级。允许验证已保存JSON与摘要，禁止新增实验/交叉编译/修改旧结果。独立只读复核、root身份核验后更新唯一日志、导航及两端待办。

本项有界材料包可完成，NUMA实际接口裁定、D3/D4整体及D2独立检测仍未完成。新确认0、独立阳性0、原12条6/5/1保持。缺口列为待领域输入；不自动向人员发消息。本轮不再扩I3C/KUnit配置网格，下一步转回已确认案例的五维与可自动提取检查的证据覆盖。
