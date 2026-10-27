# 下一阶段冻结选样勘误

日期：2026-09-26。此文件在源码复核后补写，不修改预先保存的 `next_stage_protocol_pre.md`、`next_stage_selection_pre.json` 或原始机器输出。

1. 选样 JSON 将 `git -C /root/repos/linux log --all --no-merges --format=%H%x09%cs%x09%s -- drivers/base/topology.c` 的候选池记为 **53**。收尾用 `git rev-list --count --no-merges --all HEAD -- drivers/base/topology.c` 与原样 `git log` 重跑均为 **54**。追查发现 WSL 启动警告在第一条 SHA 前插入 NUL 字节，早先按“行首为 40 位 SHA”解析工具输出时漏掉 `fb506e31b3d52f7faaec00352c2732ce31c1f930`；去除 NUL 后计数为 54。只对标题列匹配 `book|drawer` 的结果仍是原先列出的三条（`f1045056c726`、`a62247e1f5c1`、`b40d8ed4e42c`），入选样本和 8 组配置未改变。原选样文件保持冻结状态，**54 是经复核的池规模**；以后不应把未经清理的命令包装层输出直接按行首 SHA 计数。
2. JSON 中 `recorded_utc` 写作 **10:41:50 UTC**，Windows 文件系统显示该 JSON 创建与最后写入时间均为 **10:42:40 UTC**；protocol 文件为 **10:40:16 UTC**，原始运行输出为 **10:43:51 UTC**。因此 `recorded_utc` 只能看作文件中声明的采集时间，不能作为文件实际冻结时间的证据。现有文件时间支持“protocol 与选样文件均早于本轮机器运行”，但不等于具有外部独立的不可变时间戳。
3. 冻结 v1 的 8 条 `insufficient` 记录在顶层 `reason` 使用通用句 `interface build reachability is unknown`；每条 `evidence.unknown_reasons` 实际说明 book/drawer 家族不受支持。该输出只能记为**解析范围拒判**，不说明所查配置的实际构建可达性未知，也不是八次正确行为分类。

这些勘误不改变 bcachefs 的源码与布局原型结论，也不把该定向探针升级为未知案例自动发现。后续若重做选样，应输出完整元数据查询结果及哈希，并在冻结时用文件落盘哈希和实际时间记录，避免只能依赖自报数字。
