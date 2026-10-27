## 10月23日 最新闭环：Btrfs实际配置源码与运行档案的受限关联

本轮承接用户“继续”，冻结复用10/11字段提取器、10/12条件模板、preprocessed_evidence、btrfs_runtime_facts和通用contract_protocol共5份方法文件，前后SHA一致。未请求项目模型、未使用旧拒绝正文，未修改原方法以适配结果。

**实际新增：**在已有父/修复×ARM64 4K/64K四个历史构建中生成8份完整disk-io.c/super.c预处理输出，保留真实Kbuild命令。配置和Image在前后哈希均不变。4个源码路径×2历史版本的归档记录与本地Git对象逐份相等。新内核编译/启动、挂载、文件记录均0；前轮6格36文件只重提，不重算实验。

冻结提取器从两版完整源重新枚举出sectorsize候选，字段名不是本轮提取器输入：父版写入在调用btrfs_parse_options之后，修复版在之前；仍仅词法先后，不升级为CFG支配。冻结模板重新识别磁盘__le32、缓存u32及get_unaligned_le32引用。四个实际配置各取得open_ctree、btrfs_parse_options、btrfs_super_sectorsize、btrfs_sb共16个唯一完整定义及GCC行映射，按绝对源路径匹配。实际getter为get_unaligned_le32(&s->sectorsize)，btrfs_sb返回sb->s_fs_info；这增加配置内定义证据，不证明底层加载语义、完整对象生命周期或实际回调路径。

新增bridge.py把源码候选/条件模板、配置内定义和旧真实运行按revision/profile/Image/config/page关联。6格均可形成版本化档案关联；盘几何来自btrfs-progs的dump-super解码文本，映射到源码候选字段仍是显式人工指定，不冒充内核getter实际执行值。旧max_inline/extent局部关系仍由真实运行适配器取得，原结果不变。

**关键边界：**六格cache==disk_at_consumer均保持insufficient。当前日志记录裁剪结果而非实际缓存操作数；min(request,cache)不可一般逆推，例如request=4096时cache=4096或65536都可能给4096。UUID/root5/inode是档案文件身份，不是fs_info内存对象或消费期限证明。未为了接入通用核心伪造supported账本，完整核心连接仍缺实际缓存、对象和期限。历史模板中的旧unknown字段作为原组件输出保留，本轮新增证据在外层单列，不回改旧记录。

8项负控制全部拒判：错版本、profile、Image、配置、页大小、未登记字段映射、将裁剪结果冒充消费缓存、缺配置内定义。它们是方法控制，不是独立样本；本轮是1已读案例的有限接线，正式独立正例/正常例仍0/0。N1自动语义推导、N2自动选配及泛化均未因此完成。

入口`linux_bug_analyze/experiments/case_taxonomy/btrfs_source_runtime_bridge_20261023/README.md`；protocol_pre.md、frozen_methods.json、collect.py、analyze.py、bridge.py、results.json及next_observation.md。原始源/完整.i/Kbuild命令/定义区域在`linux_bug_analyze/analysis_out/btrfs-source-runtime-bridge-20261023/`；仍复用WSL `/root/.cache/linux-bug-analyze/btrfs-mount-resume-20261023/`。首次采集和分析均完成，无失败或重跑；没有新增付费请求、内核运行或确认缺陷。

当前待办：

- [x] 冻结组件、复用源码候选/模板，并取得真实配置内定义。
- [x] 按版本和实际构建身份关联旧运行，拒绝错误绑定及逆推缓存。
- [ ] 下一项按next_observation.md，先审核最小消费现场观测方案，再做父/修复64K目标条件配对。直接记录参与裁剪的值及同次对象/事件，控制观测变换；不要再用终态输出代替消费时值。
- [ ] 完整root生命周期、精确消费证明、N1/N2自动方法、通用核心完整接线与独立评价继续未完成。表示接口与R3暂缓，VT-d后置，Word/GitHub未改。

当日日志、待办、进展、交接说明同轮维护；本轮notes_before.json/notes_update.json纳入三文档旧SHA保护，WSL同步状态以notes_sync.json为准。
