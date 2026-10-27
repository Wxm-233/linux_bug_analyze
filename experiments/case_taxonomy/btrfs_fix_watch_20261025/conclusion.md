## 10月25日 最新闭环：修复版对应监测成功，首次单步失败保留

按用户继续下一步，先冻结父版采集器、事实/操作数解析器及区间适配器，再采集修复版对应对照。新增模型调用0，累计保守记账仍965430。修复观测Image/initrd经原清单SHA核验，独立从修复版super.i编译offsetof常量与读取vmlinux入口符号，未重建或覆盖Image。四字段偏移与父版一致，Image/vmlinux身份不同，initrd和空白盘SHA相同；仍单CPU QEMU TCG、nokaslr与相同观察协议。

**实际执行和失败：**本轮2次启动尝试，首次在第一个max_inline=2048区间第二次正控制单步后，返回T05但PC仍为原写指令地址，违反冻结协议的pc+4条件，采集器立即中止。没有完整挂载成功记录，不能计完整区间。failure.json、runtime/和首个独立磁盘均保留。没有放宽条件；仅更换新输出目录和独立空白盘克隆，以同一协议复跑1次，完成2目标区间、2次读写挂载、2次卸载后只读挂载、6文件及持久读回。首次失败不是已证Btrfs问题，也不能断言是QEMU错误；原因未明，一次不复现不足以证明可靠性。

**成功运行配对（单位字节）：**

| 请求 | 父版缓存/相邻磁盘值 | 修复缓存/相邻磁盘值 | 父版写入序列 | 修复写入序列 |
|---|---|---|---|---|
| 2048 | 4096 / 65536 | 65536 / 65536 | 请求2048→裁剪2048 | 请求2048→裁剪2048 |
| 8192 | 4096 / 65536 | 65536 / 65536 | 请求8192→裁剪4096 | 请求8192→裁剪8192 |

两版成功运行的每个区间均捕获2次自然写正控制；当前super.sectorsize与info.super_copy指针槽目标观察点均0写记录。正控制单步期间两个目标点保持安装。修复成功运行的6文件布局、生效值、读回与原修复观测基线一致，EXPERIMENT_DONE failures=0。原父版成果只作配对重放，不重计本轮新增。

**冻结检查器结果：**原btrfs_watch_facts.py及解析器SHA保持不变，能接受两版4个完整区间；对首次失败原始trace明确拒判single-step PC mismatch，没有将其截断记录当无写证据。修复版声明绑定父版Image的控制也拒判。没有根据修复缓存65536修改路径准入条件。compare.py保留所有尝试及已核paired记录，不计算从两次试验推导的“成功率”。

**作用和边界：**在相同取证协议下，可以保留旧版/修复版的缓存失配及实际裁剪差异，也能区分区间记录有效与采集失败。2048虽行为相同，缓存状态仍有差异。仍只是1个已读修复家族开发对照，独立正例/正常样本0/0。有限虚拟范围的无目标写记录不等于排除别名、DMA、全部CPU或无调试时的写者；C与whole_path均insufficient，未自动批准源码稳定性要求。首轮单步失败给采集器增加明确可靠性限制，不能只汇报成功复跑。

证据入口：`linux_bug_analyze/experiments/case_taxonomy/btrfs_fix_watch_20261025/`内frozen_inputs.json、prepared.json、compiled/、failure.json、runtime/、runtime_repeat/、results_repeat.json、verified_repeat.json、comparison.json。失败盘`/root/.cache/linux-bug-analyze/btrfs-fix-watch-20261025.img`、成功盘`/root/.cache/linux-bug-analyze/btrfs-fix-watch-repeat-20261025.img`分开保留，原Image/磁盘未改。WSL项目挂载仍`/mnt/d/homework/software/linux_bug_analyze`，Linux Git仍`/root/repos/linux`。

下一步优先诊断单步PC未前进：设计有界诊断，补停止原因/寄存器等状态，区分未执行指令、异常/中断或调试协议状态；先独立保留诊断结果，不放宽成功规则或重复直到通过。必要时给不能覆盖的采集状态返回不足，而不是把错误隐藏在自动重试里。暂不扩大挂载网格或宣称完整自动检测。源码主分析的拒绝及预算边界仍保留；表示接口/R3暂缓，VT-d后置，Word未改。日志与三份工作文档同轮更新并核镜像收据。
