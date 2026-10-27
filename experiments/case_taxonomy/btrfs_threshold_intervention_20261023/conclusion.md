## 10月23日 最新闭环：Btrfs同内核阈值干预与真实事实提取

继续用户授权的WSL Btrfs研究。本轮复用修复版ARM64/64K原历史Image，核对Image、配置、init和磁盘哈希，不重编内核、不请求项目模型、不使用旧拒绝内容。表示类接口和R3仍暂缓，VT-d后置，Word/GitHub未改。

**新增实验：**从同一空白64K扇区/64K节点磁盘复制两份，启动前SHA相同。2次QEMU分别按4096→8192及8192→4096顺序挂载，同Image、同initrd、同资源；共4次读写挂载、4次只读重挂、28文件。各文件fsync、即刻读回及卸载重挂后读回均一致。不是重复此前六格，也不将旧构建计作新增。

实际阈值均符合请求，两个顺序的布局结果完全相同：1024/4095/4096字节文件在两阈值均inline；4097/6144/8192在4096阈值为regular、8192阈值为inline；8193两阈值均regular。落盘树而非st_blocks用于判型。结合此前父版4096/修复8192，说明在已测无压缩负载下，同一修复实现仅改变选项就足以重现对应布局差异；加强阈值归因，但不是逐行补丁消融，也不保证全部资源/并发条件。两个顺序不是统计重复或随机评价。

**自动化新增：**代码根`linux_bug_analyze/btrfs_runtime_facts.py`提供受限真实输出适配器，从boot/super/tree取页与扇区几何、实际选项、文件名/inode/长度/extent；核文件系统UUID、root5、挂载区间、重挂读回与记录唯一性。对象标识含运行context，即使两克隆同UUID也不混为同一对象。新28记录和旧归档36记录均经程序重新提取；旧六次启动仅回放，不重跑/重计。输出保留树行号、输入hash、archived_runtime/program_projection来源和first_consumption/whole_path不足。

人工选定的有限判据单列：①本轮已登记有效请求的生效上限与min(request,真实磁盘sectorsize)比较；②实际inline长度不得超过有效max_inline。程序计算真实值和局部关系，不将size<=limit当普遍充分条件，regular为此单向长度条件not_applicable，不等于文件或全路径正常。旧矩阵只有parent-64K/64K的8192请求违反该有效上限参照；这是已知开发例回放，不是新发现。依据复用旧super.c:780–796、inode.c:341–368及10/12条件模板，语义判据不是模型或程序新推导。

先做8项内存证据损坏控制，再因复核发现挂载阶段/子卷需要显式绑定补至10项；最终全部拒判，包含错UUID、重复文件、缺持久读回、错文件名、缺extent、错顺序、缺完成标记、选项日志矛盾、错挂载区间、错子卷。控制不改原始输出，不算真实缺陷/独立正常样本。没有完整接入通用contract_protocol核心：精确消费期限和内存对象绑定仍未获证，不能自动填supported绕过其门槛。

入口`linux_bug_analyze/experiments/case_taxonomy/btrfs_threshold_intervention_20261023/README.md`；事前protocol_pre.md、执行run.py/init.c、分析analyze.py与results.json；原始命令/日志/树/manifest在`linux_bug_analyze/analysis_out/btrfs-threshold-intervention-20261023/`；WSL独立缓存`/root/.cache/linux-bug-analyze/btrfs-threshold-intervention-20261023/`。首次两启动均完成，无新构建或项目模型调用。仍是1个已读案例，正式独立正/正常0/0。

当前待办：

- [x] 同一修复内核4096/8192直接干预、交叉顺序和边界长度验证。
- [x] 真实观测到受限事实及局部必要关系的程序核验；10项损坏证据控制。
- [ ] 下一项继续Btrfs源码—运行事实衔接：先冻结现有源码模板与新适配器，明确字段/对象/版本/消费期限的接口；尝试复用既有词法字段提取，不能由裁剪结果反推消费时缓存值，也不能把磁盘UUID当内核fs_info指针证明。不能证明的绑定保持不足，不无限扩大parser。
- [ ] 完整root生命周期、精确消费时值、N1自动要求推导、N2自动选配、通用核心接线与独立评价仍未完成。暂不新增重复网格或宣布接口完成。

日志和三份工作文档按本轮notes_before.json/notes_update.json旧SHA保护更新；WSL镜像成功以本目录notes_sync.json为准，旧轮次收据保持。
