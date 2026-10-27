## 10月23日 最新实验停点：Btrfs历史真实挂载与持久布局对照完成

用户在新的具体实验对话明确恢复WSL Btrfs，覆盖此前“暂存Btrfs、下一项VT-d”的优先级。没有重新调用模型或使用旧拒绝的部分回答。表示接口及R3 shmem继续暂缓；不转论文、不改Word、不推GitHub。

本轮完成未加观测补丁的Linux5.14-rc7父/修复×ARM64 4K/64K四个历史内核构建、6次QEMU启动；64K页分别配64K/4K磁盘，4K页配4K磁盘。各启动执行max_inline=2048/8192两次读写挂载，共12次读写挂载、12次卸载后只读重挂、36条文件记录。所有文件fsync、当场读回和重挂后持久读回一致，六格结束标记均failures=0。同页配置的两版.config字节一致；测试init源码/二进制一致，实际关键源码与固定Git对象一致，磁盘镜像仅在guest挂载。

**新增实测结论：**64K页/64K盘请求8192，父版实际4096、修复版8192；6144和8192字节文件由父版regular变为修复版inline。类型通过停机后的btrfs dump-tree、inode号和文件名联合绑定，不由mount成功或st_blocks推定。2048请求下两版小文件1024均inline、大文件均regular；4K页/4K盘下8192请求两版均裁到4096、布局一致。64K页/4K盘两版可完成读写，但内核均有experimental subpage提示，全部文件regular，单列为条件边界，不充“应inline”正常参照或成熟支持保证。默认2048在/proc/mounts省略，通过内核原生max_inline日志核对，不能误报缺字段。

这使本案从“源码预测、尚无真实挂载”推进到“固定合法配置中的真实参数与持久文件布局差异”。这是1个已读开发案例，四个构建、六次启动、36文件不是新缺陷数；正式独立正例/正常例仍0/0。未测性能收益、资源压力、压缩、并发、完整root生命周期或精确内存对象/消费时点；不宣称全自动检测或CPU ISA跨架构运行对照。修复涉及一组初始化搬移，尚未单独干预排除其中其他变化的影响。

证据入口：`linux_bug_analyze/experiments/case_taxonomy/btrfs_mount_resume_20261023/README.md`，事前协议`protocol_pre.md`，观察核验`verify.py`与`results.json`。原始构建/启动/命令/树输出位于`linux_bug_analyze/analysis_out/btrfs-mount-resume-20261023/`；真实源码/构建/磁盘在WSL `/root/.cache/linux-bug-analyze/btrfs-mount-resume-20261023/`。本轮安装btrfs-progs6.6.3；两次配置依赖未生效和一次init输出命名冲突均保留在attempts.md及原始命令日志，不当案例失败。模型调用0，旧模型失败和原Btrfs停点文件不回改。

当前已完成与下一步：

- [x] 历史内核构建、真实挂载、有效选项、落盘extent及同用途正常对照。
- [ ] 下一项继续Btrfs：在同一修复内核做max_inline=4096/8192的直接干预对照，以进一步分离参数阈值与其他初始化搬移影响；协议先登记。
- [ ] 随后将磁盘几何、有效配置、输入选项、文件对象及落盘类型接入受限事实/契约核验；区分人工给定要求与程序取得事实，不把本轮日志解析当自动推导。
- [ ] E1完整root/消费对象与阶段绑定、E2剩余机制归因、E3自动流程、E4独立评价仍未全部完成，不能宣布Btrfs接口完成。VT-d后置，CPU未证部分保留。

本轮同一日合并日志与三份工作文档同步维护；新轮次notes_before.json/notes_update.json包含三文档旧SHA保护，Windows/WSL同步结果以notes_sync.json成功收据为准。
