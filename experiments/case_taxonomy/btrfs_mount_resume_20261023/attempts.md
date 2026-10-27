# 执行准备中的失败记录

所有命令的argv、开始时间、耗时和退出码保存在本轮analysis_out下commands/，不覆盖旧日志。

1. 首次allnoconfig配置后，准入断言发现VIRTIO_BLK未生效，尚未编译。读同版drivers/block/Kconfig后补BLK_DEV。
2. 第二次配置仍未生效；读同版drivers/virtio/Kconfig后补VIRTIO_MENU。两次均是测试配置依赖缺失，不是案例故障或模型调用失败。
3. 首个64K历史内核成功构建后，测试init链接失败，输出路径build/init与内核已有目录重名。改为pid1.elf，不修改内核源码；原015-init_build.log保留。
4. 上述修正后继续同一固定矩阵，不更换样本、历史版本或预期。最终运行init源不含版本分支，两个版本使用同一测试程序。

本轮无项目模型请求；旧Btrfs模型拒绝记录保持原样。
