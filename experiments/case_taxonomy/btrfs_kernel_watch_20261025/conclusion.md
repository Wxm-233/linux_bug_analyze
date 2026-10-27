## 10月25日 最新闭环：父版实际内核两个parse区间写监测完成

本轮把前轮合成观察点客户端用于真实父版观测内核。模型调用0、累计保守记账仍965430；未重发被拒请求。只对既有super.i追加offsetof常量并独立交叉编译汇编，未重建或修改原Image。取得info.super_copy偏移768、info.sectorsize偏移3260、info.max_inline偏移648、super.sectorsize偏移144；实际vmlinux符号定位btrfs_parse_options。Image/initrd按旧清单SHA核验。

**实际执行：**1次QEMU TCG单CPU内核启动，独立克隆原blank.img；2次读写挂载、2次卸载后只读挂载、6个文件，2条目标裁剪记录，全部持久读回成功。追加nokaslr便于符号定位，并受断点/单步暂停影响，不能称与未调试运行完全相同的时序。克隆盘在`/root/.cache/linux-bug-analyze/btrfs-kernel-watch-20261025.img`，原Image、initrd、原磁盘保留。原父版观测内核配置不变，无新增内核构建。

在parse入口通过参数寄存器读取info与真实options，按返回地址和SP约束本次返回；不使用旧日志地址或缓存值反推路径。对当前super对象的sectorsize四字节以及info的super_copy八字节指针槽安装写观察点；对info.max_inline安装自然写正控制。监测区间为本次函数入口至返回，不是初始化至全部文件消费。

| 目标区间 | 入口缓存 | 磁盘字段入口/返回 | 自然写正控制 | 目标观察点命中 |
|---|---:|---:|---|---:|
| max_inline=2048 | 4096 | 65536 / 65536 | 2048→2048，再2048→2048 | 字段0、指针0 |
| max_inline=8192 | 4096 | 65536 / 65536 | 2048→8192，再8192→4096 | 字段0、指针0 |

每个正控制命中后仅撤max_inline观察点并单步一条指令；两个目标观察点一直保持安装。协议审计验证4次正控制停止与4次单步均有两个目标点；目标点若在单步中触发会失败，不静默越过。故相较前轮合成程序，这次取得真实内核虚拟地址上的工作正控制，并避免因正控制单步而撤掉真正监测目标。失败安装响应的合成审计控制返回拒绝；不计真实案例。

运行日志的info/super指针、缓存和磁盘样本与入口/返回记录一致，两个挂载虽复用地址仍以独立事件记录。新盘超级块和文件树经既有投影器核验，生效值与6文件布局均与同版原观测基线一致，EXPERIMENT_DONE failures=0。verify首次遇到int键与历史JSON字符串键比较差异，规范化键后通过，未改运行事实/重启内核。准备时initrd查找层级错误亦已记录在local_failures.md。

**支持的有限结论：**本次两个调试运行区间内，在已安装的两个目标虚拟地址范围上没有记录到CPU写事件，且自然写正控制工作。它比只比较两端值多出持续观察点证据，但仍不是全局无写者证明。不覆盖DMA、物理/虚拟别名、未监测对象、其他CPU及未运行路径；断点暂停改变时序，目标字段没有做破坏性注入写，故也不能声称该地址的所有写法已经独立校准。没有在入口之前覆盖super_copy初始化区间，没有验证修复版对应区间。

**自动检查进度：**新增有限RSP区间事件、运行对象绑定及trace覆盖审核，可作为证据层记录；通用核心未改，C消费期限/whole_path仍insufficient，不把一次无触发结果自动升级为必要条件已满足。A/B已有判定不变，仍1个已读开发案例、独立正例/正常样本0/0。主源码语义缺口与模型拒绝/预算停点仍保留。

证据入口：`linux_bug_analyze/experiments/case_taxonomy/btrfs_kernel_watch_20261025/`，含protocol_pre.md、prepared.json、compiled/offsets.s、compiled/parse.disasm、runtime/rsp.jsonl、runtime/boot.log、runtime/super.txt、runtime/tree.txt、results.json、verified.json及local_failures.md。WSL内核Git仍`/root/repos/linux`，项目挂载仍`/mnt/d/homework/software/linux_bug_analyze`。

下一步优先把本次区间证据以明确监测范围接入现有外部审核/检查协议，拒绝跨对象、错区间和缺正控制的输入；对别名/覆盖不足继续拒绝无条件期限提升。若进一步跑修复版或扩大监测，先说明其增加的区分力和对象范围，不重复现有完整网格。表示接口/R3暂缓，VT-d后置，Word未改。日志、待办、进展和交接按本轮notes_sync收据同步。
