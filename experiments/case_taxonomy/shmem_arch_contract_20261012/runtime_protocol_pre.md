# R3 shmem完整运行链：事前范围与可行性

2026-10-13，R2收束后制定；未开始本阶段安装、完整内核编译或启动。固定已读旧版3390916aca7af1893ed2ebcdfee1d6fdb65bb058和修复版9fd154ba926b34c833b7bfc4c14ee2e931b3d743。这是同一历史案例的因果验证，不是新样本盲测。

## 目的与固定范围

验证架构配置派生PMD阶数如何经真实shmem分配、页缓存插入及部分打洞/拆分进入公共xarray限制。保留x86_64/4K、ARM64/4K、ARM64/64K三个profile，各旧/修复，共最多六个主运行单元。桥接ARM64/4K用以区分ISA与页几何；预计阶数来自实际目标头的9/9/13，运行时仍须核实。公共政策上限与精确消费者WARN阈值分开，不能据修复逻辑自己生成期望。

同profile旧/修复保持相关Kconfig、内存、CPU数量、tmpfs/THP策略、文件大小、偏移与操作顺序；版本身份可明确标记。不同架构/页几何所需配置差异记录，不要求所有config完全相同。范围冻结，暂不加CPU热插拔、设备、并发或额外模式网格。

## 可行性结果与前置门槛

已有ARM64交叉gcc、静态目标libc、qemu-aarch64用户态和x86系统模拟器。缺qemu-system-aarch64；用户态模拟器不能替代目标内核。shmem缓存已有修复源码与三套prepared配置，但没有完整Image/vmlinux，旧源码需按固定commit单独导出。不得用die的5.16内核替代本例版本。WSL约14.7GiB可用内存，先顺序评估单个4GiB guest，不并行大页运行；是否能实际获得512MiB连续folio仍未知。

开始构建前先核最小系统模拟器包及实际可达Kconfig、目标console、页大小和页分配上限；保存工具/构建障碍，不把依赖不足算内核失配。历史C函数保持原行为。需要仪器化时先明确位置与只观察的变更、保存patch并一致应用旧/修复，不能强制预填order、替代分配器或绕过正常选择。

## 必须观测的完整链

1. 实际启动指定版本及架构；目标页大小、PMD几何、THP/tmpfs策略、内存资源与相关配置成立。
2. 同一文件/操作的实际folio阶数、大小和来源明确。旧64K必须观察到真实order13分配，不能由“支持PMD”推断已经分配512MiB。分配失败退回基页应标为路径不足。
3. 该folio实际进入shmem_add_to_page_cache，多索引项与对象身份可连接；分离的选择程序或值条目不能替代。
4. 部分打洞/截断确实针对该folio，并进入基页拆分目标，再观测xas_split_alloc的原阶数、xa_shift/目标、WARN与内部error。仅fallocate返回0/ENOMEM不能证明或否定该限制。
5. 修复版应在选择处拒绝不适合该公共路径的PMD，并观察实际后备页/操作路径；不要求修复版也分配order13来“通过拆分”。两4K组保留正常可达的合法大页与拆分行为。sysfs全局deny/force不得混入旧15条选择结果，采用何种实际策略须记录。

### 历史观测路线初查

已核对目标版本的kprobetrace文档与源码，优先评估tracefs动态kprobe/kretprobe：历史机制支持$argN和$retval，可在返回点关联原入参与返回值。相关ARM64 prepared配置尚未启用FTRACE/KPROBES，后续观察配置必须旧/修复对称声明。实际符号保留、探针注册、参数读取与漏捕尚未实测，不能将文档支持等同已经取得事件。

| 需要的事实 | 待实施的具体历史入口 |
| --- | --- |
| 自然大页分配 | shmem_alloc_hugefolio返回非空，对应alloc_pages_mpol的真实PMD order |
| 插入成功 | shmem_add_to_page_cache的folio/mapping/index与返回0 |
| 同对象的部分打洞 | shmem_fallocate的PUNCH_HOLE参数、truncate_inode_partial_folio的folio及范围 |
| 实际基页拆分 | split_huge_page_to_list_to_order的new_order=0，再到xas_split_alloc的entry和order |
| 内部错误 | 同一链上的WARN、返回及内部错误路径，并保留用户态读回作辅助 |

事件须按同一folio、mapping、index、进程和顺序关联，不能仅统计各函数出现过。实际folio_order先判断large，再取_flags_1低8位；不存在可直接猜测的_folio_order字段。需要读取布局时必须从本目标版本/config生成偏移与标志，实际xas_split_alloc order作独立核对。

可行性输入拟独立tmpfs huge=always、文件覆盖一个PMD、大页内少量写入，再在内部做一字节KEEP_SIZE|PUNCH_HOLE，检查打洞处归零和相邻数据。已复核历史shmem_undo_range会处理partial folio，truncate_inode_partial_folio对large folio调用split_folio；具体对象和分配仍须运行观察。未实际大页分配/插入则判路径不足。debugfs split_huge_pages为主动拆分，不能替代自然partial punch链；ShmemHugePages计数和通用filemap插入事件不能代替本版本自定义shmem插入的对象证据。

若动态观测不足，先保存对旧/修复一致的纯观察补丁，读取真实字段且保持历史分支/返回/分配行为；结果注明仪器化。当前未冻结脚本、目标偏移、timeout或注册方式，未批量启动六格。

## 验收与停止

结果分为契约失配、合法保留、修复阻断及路径/资源不足。无WARN不自动等于正常：旧内核可能从未取得大页。返回码成功也不自动等于修复：打洞内部可能吞掉拆分错误。结合原始内核记录和文件行为逐层验收，保留不完整链与失败材料，不重试到“成功”为止。

先以旧ARM64/64K的单个路径试验核实可观测性及实际分配资源，再运行剩余固定单元；只对有明确基础设施原因的失败有限修正，已完成格不重跑。具体timeout/重试上限随脚本冻结，在首次启动前明确，不静默扩网。

输出合并到本目录README及已有因果卡、当前代办、今日唯一日志；大型产物在WSL独立缓存。没有新确认缺陷、模型调用或独立自动检测阳性。完整链结果齐备后才决定是否升级R3；R5架构依据移除/合法差异/不完整修复另行验证。

## 首格实施协议v1（首次构建/启动前，2026-10-13）

本次只实施旧ARM64/64K一格，不立即展开六格。系统模拟器最小包安装已完成：唯一qemu-system-arm，下载11.0 MB，占用60.4 MB，无现有包升级。旧源码从固定commit导入独立runtime缓存，既有修复归档和prepared结果不改。采用allnoconfig生成实际64K/VA48最小内核，相关THP/tmpfs/compaction/追踪能力经olddefconfig实际核验；实际头派生几何、folio及xarray字段布局，不手填偏移。MAX_PAGE_ORDER包含上界，order13合法，不改为14。

固定4GiB、单CPU、TCG、virt-8.2/gicv3、CPU max、PL011控制台、独立静态PID1和无网络/磁盘的initramfs。仅观察：动态kretprobe记录alloc_pages_mpol的order/page、shmem成功插入、同folio partial truncate、new_order=0拆分及xas_split_alloc的order/shift/node。只在PID1作用域启用事件；必须注册精确符号，优化变体ABI不猜。先核符号后启动；trace overrun/dropped与kretprobe missed须为0。

独立tmpfs huge=always,size=1G，ftruncate为目标头产生的PMD大小512MiB，第一次pwrite两字节5aa5到基页内offset=2*PAGE_SIZE+17，再对首字节KEEP_SIZE|PUNCH_HOLE，读回两字节。记录默认defrag/shmem_enabled与buddyinfo，不本轮静默改为强制回收。实际分配可失败并回退，届时判路径不足；系统调用/读回不决定契约结论。

首次QEMU超时300秒；主场景最多一次，若具体注册/console/init基础设施失败可至多两次修正重试，保留每次日志，不靠改变输入或分配强度重试到成功。内核编译超时900秒，六workers；不并行大内存运行。脚本只产生OBSERVED_UNREVIEWED，后续由真实对象链判定和独立复核给出结论。源码不修改；动态观测不足时暂停并另声明仪器化方案，不能悄悄加补丁。

首格实现文件摘要（用于确认启动前实现）：run_first.py=e3e762c3ba8b10f19a74e02f7d44802aa6c8b08623c3f627da2adcfd4e7a7a57, init_shmem.c=3ac7fb194a30a374b8b37c59e943471692d515f5930cc13265d971e66b04a111, layout.c=767f2afe47a2a61c6c98a79b0708e56ff8200b0671fef5091f46534189dd58b2。

### 首格观测补充v2（首次启动前）

初版完整内核编译成功，但alloc_pages_mpol与shmem_add_to_page_cache精确符号缺失，先停止，没有启动；原符号/错误记录与未仪器化Image保留。采用已声明的纯观测方案：仅在独立旧归档mm/shmem.c的巨大分配返回前与页缓存插入成功/失败返回前，PID1作用域trace_printk记录真实page/folio、order、mapping/index及原结果。原allocator、分支和返回均不改；完整差异保存runtime/observation.patch。未来同profile修复版需一致应用同类观察。

部分截断、split与xarray均补入口/返回探针，以区分入口状态与可能已变化的返回状态；shmem_fallocate参数/返回另做路径对照。该历史版由实际CONFIG_TRACING=y提供trace_printk，没有独立TRACE_PRINTK选项；版本标签增加obs1。所有结果注明带观测补丁的历史内核运行。预读取回严格要求2字节00a5，但内容正确仍不替代内部链。首次缺符号不是机制失配，不能算通过。

构建完成后以boot-only复用同一Image和initramfs；启动前核对本格配置、观测源码、PID1和产物绑定，并确认ELF64/AArch64。核对仅服务于本次启动，不追加历史材料封存流程。
