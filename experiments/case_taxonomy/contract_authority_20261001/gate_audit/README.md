# 独立只读审计：契约门控与已保存的 HCI 投影

审计日：2026-10-01。脚本 [`audit_saved.py`](audit_saved.py) 只读调用门控的合成夹具并核对**已经保存**的投影文件；结果见 [`audit.json`](audit.json)。没有重新编译投影，也没有读取新留出补丁、运行内核或控制器。审计所用 `authority_gate.py` SHA-256 为 `b39af51a6f7bd430c3aa92e279763dcc7a7b72c2645b2cd8f215359cf9295132`，具体版本指纹均在 JSON 中。

门控在本审计探针中的状态符合设计边界：无归属审阅为 `conditional`；修订、字段绑定或引文错误为 `insufficient`；已报告冲突即使绑定错误也保持 `conflict`；外部规范历史适用性未知仍为 `conditional`。`machine_contract_proven`、`runtime_reachability_proven`、`full_kernel_proven`、`external_protocol_proven` 在就绪样例中仍均为 `false`。

**关键范围限制。** 将第一字段 `consumer_format` 的证据换成第二字段的**同版真实引文**后，门控仍返回 `reference_integrity=matched` 和 `source_contract_ready`，同时 `machine_contract_proven=false`。这说明它能核对文件、版本元数据、哈希、行号与引文，而**不能自动认证引文是否足以支持逐字段语义**；`source_contract_ready` 只能读作“有归属审阅者提交了局部契约卡且材料完整”，不是机器证明。跨字段引文没有触发自动拒判是有意分离引用完整性与语义审阅的结果，不宜在论文或汇报中称为已自动验证权威契约。额外源码的修订归属依赖调用方提供的同版元数据，门控本身不认证其 Git 提交成员关系。

保存的 `provider_projection/results.json` 经独立解析：源摘录与五份父版原始 blob/全文件 SHA-256 匹配，输入与运行脚本哈希和记录一致，保存的 stdout 可逐行还原 `targets.rows`。三组条件输入下，x86_64 的父版与修复版均 0 组格式不符；s390x 父版 3 组、修复版 0 组。实际读端投影读取命令字节的数值与独立按小端解码的 oracle 一致，非零读取响应、写完成错误和缺少已发命令三条分支保留预置成员值。所有这些仅是**注入响应和替身上下文中的历史源码函数/赋值投影**；临时可执行文件已随原运行的临时目录清理，本次未重放执行，更没有真实控制器或历史内核运行证据。

最终开发门控另以 [`audit_final_lock.py`](audit_final_lock.py) 核对，结果固定在 [`final_audit.json`](final_audit.json)：`development_final_lock/results.json` 的门控、运行脚本、输入计划哈希均与当前文件一致，`root_test_final_lock.json` 的 **17 项测试**成功且代码版本相同；五种输出依次为局部已审阅材料齐备、外部历史依据待定、缺源引用、已报告冲突和无卡拒判，四个机器/运行/外部证明标记始终为 `false`。最终门控用到的第六个 `include/linux/skbuff.h` 源文件，其自校验 Git blob 也由对父版 `git ls-tree` 的独立只读查询核对；其余五份与本目录保存的原始父版文件逐字节匹配。本项没有改变前述“匹配引文不等于语义证明”的范围限制。
